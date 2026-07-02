-- ============================================================
--  RasOI — Supabase Database & Storage Setup Script
--  PRD §6b.1 (Tables) · §6b.2 (Storage) · §12.1–12.4 (Modules)
--
--  Run this once in the Supabase SQL Editor:
--  https://<project>.supabase.co/project/default/sql/new
--
--  Order:
--    1. Extensions
--    2. Tables + indexes + triggers
--    3. Row Level Security policies
--    4. Storage bucket + storage policies
-- ============================================================


-- ============================================================
-- 1. EXTENSIONS
-- ============================================================

-- uuid_generate_v4() is available by default in Supabase via pgcrypto
-- gen_random_uuid() is available natively in Postgres 13+ (Supabase default)


-- ============================================================
-- 2. TABLES
-- ============================================================

-- ------------------------------------------------------------
-- 2a. user_profiles
--     Extends Supabase Auth (auth.users) with app-level prefs.
--     PRD §12.1 — User Management Service
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id              UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT        NOT NULL,
    display_name    TEXT,
    cuisine_pref    TEXT[]      DEFAULT '{}',       -- e.g. ['Indian','Italian']
    servings        INT         DEFAULT 2 CHECK (servings > 0),
    dietary_restrictions TEXT[] DEFAULT '{}',       -- e.g. ['vegetarian','nut-free']
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_profiles IS
    'App-level user preferences extending Supabase Auth (PRD §12.1)';


-- ------------------------------------------------------------
-- 2b. pantry_items
--     Live ingredient inventory with expiry tracking.
--     PRD §12.2 — Pantry Intelligence Engine / §5.1 F2
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.pantry_items (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    quantity        NUMERIC     NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    unit            TEXT        NOT NULL DEFAULT 'pcs',
    acquisition_date DATE       NOT NULL DEFAULT CURRENT_DATE,
    expiration_date  DATE       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pantry_items_user_expiry
    ON public.pantry_items (user_id, expiration_date ASC);

CREATE INDEX IF NOT EXISTS idx_pantry_items_name
    ON public.pantry_items (user_id, name);

COMMENT ON TABLE public.pantry_items IS
    'Live pantry inventory — expiry flags computed at query time (PRD §5.1 F2)';


-- ------------------------------------------------------------
-- 2c. pantry_scans
--     Scan history — links each scan to its Supabase Storage image.
--     PRD §6b.1 / §6.2 Image Storage Flow
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.pantry_scans (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    image_path  TEXT        NOT NULL,               -- storage path inside rasoi-scans bucket
    scan_type   TEXT        NOT NULL CHECK (scan_type IN ('ingredient', 'receipt', 'fridge', 'pantry')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pantry_scans_user
    ON public.pantry_scans (user_id, created_at DESC);

COMMENT ON TABLE public.pantry_scans IS
    'Scan history linking each upload to Supabase Storage (PRD §6b.1, §6.2)';


-- ------------------------------------------------------------
-- 2d. cooked_history
--     What the user cooked and when — powers Chammach memory.
--     PRD §6b.1 / §8b.3 get_cook_history tool
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.cooked_history (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    recipe_title      TEXT        NOT NULL,
    ingredients_used  JSONB       NOT NULL DEFAULT '[]',   -- string array of ingredient names
    cooked_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cooked_history_user_time
    ON public.cooked_history (user_id, cooked_at DESC);

COMMENT ON TABLE public.cooked_history IS
    'Cook history for Chammach memory — prevents repeat recommendations (PRD §8b.3)';


-- ============================================================
-- 3. TRIGGERS — auto-update updated_at
-- ============================================================

-- Reusable trigger function
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- user_profiles
DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- pantry_items
DROP TRIGGER IF EXISTS trg_pantry_items_updated_at ON public.pantry_items;
CREATE TRIGGER trg_pantry_items_updated_at
    BEFORE UPDATE ON public.pantry_items
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 4. HELPER VIEWS
-- ============================================================

-- pantry_items_with_status
-- Adds expiry_status column: 'fresh' | 'expiring' | 'expired'
-- Matches frontend color logic: Green / Amber / Red (PRD §6c.2)
CREATE OR REPLACE VIEW public.pantry_items_with_status AS
SELECT
    *,
    CASE
        WHEN expiration_date < CURRENT_DATE               THEN 'expired'
        WHEN expiration_date <= CURRENT_DATE + INTERVAL '2 days' THEN 'expiring'
        ELSE 'fresh'
    END AS expiry_status,
    (expiration_date - CURRENT_DATE) AS days_until_expiry
FROM public.pantry_items;

COMMENT ON VIEW public.pantry_items_with_status IS
    'Pantry items enriched with expiry_status and days_until_expiry';


-- ============================================================
-- 5. ROW LEVEL SECURITY (RLS)
-- ============================================================
-- Every table is private by default.
-- Users can only access their own rows.
-- Service role (backend) bypasses RLS.

-- user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
    ON public.user_profiles FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);


-- pantry_items
ALTER TABLE public.pantry_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own pantry"
    ON public.pantry_items FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert to own pantry"
    ON public.pantry_items FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own pantry items"
    ON public.pantry_items FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own pantry items"
    ON public.pantry_items FOR DELETE
    USING (auth.uid() = user_id);


-- pantry_scans
ALTER TABLE public.pantry_scans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own scans"
    ON public.pantry_scans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scans"
    ON public.pantry_scans FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- cooked_history
ALTER TABLE public.cooked_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own cook history"
    ON public.cooked_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cook history"
    ON public.cooked_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- ============================================================
-- 6. AUTH HOOK — auto-create user_profile on sign-up
-- ============================================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, display_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user IS
    'Auto-creates a user_profiles row when a new Supabase Auth user signs up';


-- ============================================================
-- 7. STORAGE BUCKET + POLICIES
--    PRD §6b.2 — rasoi-scans (private)
--    Path: {user_id}/{timestamp}_{type}.jpg
-- ============================================================

-- Create the bucket (private = not publicly readable)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'rasoi-scans',
    'rasoi-scans',
    false,                                          -- private bucket
    5242880,                                        -- 5 MB per file (PRD §6b.2)
    ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    file_size_limit     = EXCLUDED.file_size_limit,
    allowed_mime_types  = EXCLUDED.allowed_mime_types;


-- Storage policy: authenticated users can upload to their own folder
CREATE POLICY "Authenticated users can upload own scans"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'rasoi-scans'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage policy: users can read their own uploads
CREATE POLICY "Authenticated users can read own scans"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'rasoi-scans'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage policy: users can delete their own uploads
CREATE POLICY "Authenticated users can delete own scans"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'rasoi-scans'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- Storage policy: service_role can do everything (used by backend with SUPABASE_SERVICE_KEY)
-- Note: service_role bypasses RLS by default — no explicit policy needed.


-- ============================================================
-- 8. GUEST ACCESS — anon role policies (optional)
--    Allows the backend's "guest" mode to work before auth is
--    wired up. Remove these once full Supabase Auth is live.
-- ============================================================

-- Allow anon to read/write pantry_items where user_id is null
-- (backend uses service_role key, so this is mainly for local testing)

-- NOTE: In production, remove these and enforce auth.uid() checks.
-- These are placeholder permissive policies for hackathon demo only.

CREATE POLICY "Anon service-role access — pantry_items"
    ON public.pantry_items FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Anon service-role access — pantry_scans"
    ON public.pantry_scans FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Anon service-role access — cooked_history"
    ON public.cooked_history FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ============================================================
-- DONE
-- Verify with:
--   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
--   SELECT * FROM storage.buckets WHERE id = 'rasoi-scans';
-- ============================================================
