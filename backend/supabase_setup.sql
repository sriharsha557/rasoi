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
-- 2b. user_last_scan
--     Session-based pantry: one row per user holding their most
--     recent scan's items as JSON. Replaces persistent pantry_items
--     + pantry_scans — expiry dates on fresh produce are unknowable
--     and users won't manually keep a live inventory in sync, so we
--     stopped pretending to track it in real time. Each new scan
--     (or a manual edit) overwrites this row; the app greets the
--     user with "resume last scan" vs "start fresh" instead.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.user_last_scan (
    user_id     UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    scan_date   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scan_type   TEXT        NOT NULL DEFAULT 'ingredient' CHECK (scan_type IN ('ingredient', 'receipt', 'fridge', 'pantry', 'manual')),
    items_json  JSONB       NOT NULL DEFAULT '[]',   -- [{name, quantity, unit, acquisition_date, expiration_date, confidence}]
    image_path  TEXT,                                -- storage path inside rasoi-scans bucket, if any
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_last_scan IS
    'Session-based pantry — most recent scan only, no persistent expiry tracking';


-- ------------------------------------------------------------
-- 2b2. pantry_scan_history
--      Append-only log of every ingredient/fridge scan's items.
--      NOT used for "what's in stock now" (that's user_last_scan) or
--      expiry tracking — purely a signal source for personalization:
--      cuisine-affinity-aware recipe suggestions and promotions, the
--      same way receipt_items already drives user_brand_preferences.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.pantry_scan_history (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    scan_type   TEXT        NOT NULL DEFAULT 'ingredient',
    items_json  JSONB       NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pantry_scan_history_user_time
    ON public.pantry_scan_history (user_id, created_at DESC);

COMMENT ON TABLE public.pantry_scan_history IS
    'Append-only ingredient-scan log for personalization (cuisine affinity, promotions) — not live pantry state';


-- ------------------------------------------------------------
-- 2d. cooked_history
--     What the user cooked and when — powers Buddy memory.
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
    'Cook history for Buddy memory — prevents repeat recommendations (PRD §8b.3)';


-- ------------------------------------------------------------
-- 2e. recipes
--     Master recipe catalogue. Indian recipes are stored here so
--     the app does not depend on external recipe APIs for Indian cuisine.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.recipes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT        NOT NULL,
    cuisine         TEXT        NOT NULL,
    meal_type       TEXT,
    diet            TEXT,
    ready_in_min    INT         CHECK (ready_in_min IS NULL OR ready_in_min >= 0),
    servings        INT         CHECK (servings IS NULL OR servings > 0),
    image_url       TEXT,
    description     TEXT,
    calories_kcal   INT         CHECK (calories_kcal IS NULL OR calories_kcal >= 0),
    protein_g       NUMERIC     CHECK (protein_g IS NULL OR protein_g >= 0),
    carbs_g         NUMERIC     CHECK (carbs_g IS NULL OR carbs_g >= 0),
    fat_g           NUMERIC     CHECK (fat_g IS NULL OR fat_g >= 0),
    fiber_g         NUMERIC     CHECK (fiber_g IS NULL OR fiber_g >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipes_filters
    ON public.recipes (cuisine, meal_type, diet, ready_in_min);

CREATE INDEX IF NOT EXISTS idx_recipes_title
    ON public.recipes (title);

COMMENT ON TABLE public.recipes IS
    'Master recipe catalogue for app-owned recipes, especially Indian cuisine';


-- ------------------------------------------------------------
-- 2f. recipe_ingredients
--     Ordered ingredient list for each recipe.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.recipe_ingredients (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id       UUID        NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    quantity        TEXT,
    is_optional     BOOLEAN     NOT NULL DEFAULT FALSE,
    sort_order      INT         NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_order
    ON public.recipe_ingredients (recipe_id, sort_order ASC);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_name
    ON public.recipe_ingredients (name);

COMMENT ON TABLE public.recipe_ingredients IS
    'Recipe ingredient rows used for pantry matching and detail display';


-- ------------------------------------------------------------
-- 2g. recipe_steps
--     Ordered cooking instructions for each recipe.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.recipe_steps (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id       UUID        NOT NULL REFERENCES public.recipes(id) ON DELETE CASCADE,
    step_number     INT         NOT NULL CHECK (step_number > 0),
    instruction     TEXT        NOT NULL,
    duration_min    INT         CHECK (duration_min IS NULL OR duration_min >= 0),
    tip             TEXT
);

CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe_order
    ON public.recipe_steps (recipe_id, step_number ASC);

COMMENT ON TABLE public.recipe_steps IS
    'Ordered recipe cooking instructions with optional durations and tips';


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

-- user_last_scan
DROP TRIGGER IF EXISTS trg_user_last_scan_updated_at ON public.user_last_scan;
CREATE TRIGGER trg_user_last_scan_updated_at
    BEFORE UPDATE ON public.user_last_scan
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ============================================================
-- 4. HELPER VIEWS
-- (none currently — session pantry has no computed expiry status)
-- ============================================================


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


-- user_last_scan
ALTER TABLE public.user_last_scan ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own last scan"
    ON public.user_last_scan FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can upsert own last scan"
    ON public.user_last_scan FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own last scan"
    ON public.user_last_scan FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- pantry_scan_history
ALTER TABLE public.pantry_scan_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own scan history"
    ON public.pantry_scan_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own scan history"
    ON public.pantry_scan_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- cooked_history
ALTER TABLE public.cooked_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own cook history"
    ON public.cooked_history FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cook history"
    ON public.cooked_history FOR INSERT
    WITH CHECK (auth.uid() = user_id);


-- recipes catalogue
ALTER TABLE public.recipes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read recipes"
    ON public.recipes FOR SELECT
    TO anon, authenticated
    USING (true);


-- recipe_ingredients catalogue
ALTER TABLE public.recipe_ingredients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read recipe ingredients"
    ON public.recipe_ingredients FOR SELECT
    TO anon, authenticated
    USING (true);


-- recipe_steps catalogue
ALTER TABLE public.recipe_steps ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read recipe steps"
    ON public.recipe_steps FOR SELECT
    TO anon, authenticated
    USING (true);


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

-- NOTE: In production, remove these and enforce auth.uid() checks.
-- These are placeholder permissive policies for hackathon demo only.

CREATE POLICY "Anon service-role access — user_last_scan"
    ON public.user_last_scan FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Anon service-role access — pantry_scan_history"
    ON public.pantry_scan_history FOR ALL
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
