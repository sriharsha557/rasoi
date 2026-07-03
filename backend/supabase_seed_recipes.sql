-- ============================================================================
-- RasOI — Recipe catalogue seed (25 recipes)
-- Cuisines: South Indian, North Indian, Pan Indian + Continental mix
--
-- Safe to run multiple times: each recipe is guarded with WHERE NOT EXISTS on
-- the title, and ingredients/steps are inserted via data-modifying CTEs that
-- only fire when the recipe row is actually created.
--
-- Run in the Supabase SQL editor (or psql) against the same project that has
-- the public.recipes / recipe_ingredients / recipe_steps tables.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Cuisine constraint
--    The deployed recipes table has a restrictive `recipes_cuisine_check`
--    constraint that only allows the Indian cuisine labels, so continental
--    rows below (Italian, American, Asian, Mediterranean) would be rejected.
--    Relax it to include every label used in this file. Run this block ONCE
--    before the inserts.
--
--    To see the current definition first (optional):
--      SELECT pg_get_constraintdef(oid) FROM pg_constraint
--      WHERE conname = 'recipes_cuisine_check';
-- ----------------------------------------------------------------------------
ALTER TABLE public.recipes DROP CONSTRAINT IF EXISTS recipes_cuisine_check;
ALTER TABLE public.recipes ADD CONSTRAINT recipes_cuisine_check
    CHECK (cuisine IN (
        'Indian','South Indian','North Indian','Pan Indian',
        'Punjabi','Bengali','Gujarati','Maharashtrian',
        'Italian','Mexican','American','Asian','Mediterranean','Continental'
    ));


-- ─────────────────────────────  SOUTH INDIAN  ──────────────────────────────

-- 1. Masala Dosa
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Masala Dosa','South Indian','Breakfast','vegetarian',40,3,'Crispy fermented rice-and-lentil crepe filled with spiced potato masala.',330,7.5,58,8,4
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Masala Dosa')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('dosa rice','2 cups',false,1),
        ('urad dal','1/2 cup',false,2),
        ('fenugreek seeds','1/2 tsp',false,3),
        ('potatoes','3 medium',false,4),
        ('onion','1 large',false,5),
        ('mustard seeds','1 tsp',false,6),
        ('turmeric powder','1/2 tsp',false,7),
        ('green chilli','2',false,8),
        ('curry leaves','1 sprig',false,9),
        ('salt','to taste',false,10)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Soak rice, urad dal and fenugreek separately for 5 hours; grind to a smooth batter and ferment overnight.',NULL),
    (2,'Boil and mash potatoes. Temper mustard seeds, curry leaves, green chilli and onion; add turmeric and potatoes.',15),
    (3,'Heat a griddle, pour a ladle of batter and spread thin into a circle.',3),
    (4,'Drizzle oil, cook until golden and crisp.',3),
    (5,'Place potato masala in the centre, fold and serve hot with chutney and sambar.',2)
) AS v(step_number, instruction, duration_min);


-- 2. Idli Sambar
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Idli Sambar','South Indian','Breakfast','vegan',30,4,'Soft steamed rice cakes served with a tangy lentil-and-vegetable stew.',280,9,52,3,6
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Idli Sambar')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('idli rice','2 cups',false,1),
        ('urad dal','1 cup',false,2),
        ('toor dal','1 cup',false,3),
        ('tamarind','lemon-sized ball',false,4),
        ('sambar powder','2 tbsp',false,5),
        ('mixed vegetables','2 cups',false,6),
        ('mustard seeds','1 tsp',false,7),
        ('turmeric powder','1/2 tsp',false,8),
        ('curry leaves','1 sprig',false,9),
        ('salt','to taste',false,10)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Grind soaked idli rice and urad dal to a batter; ferment overnight.',NULL),
    (2,'Pour batter into idli moulds and steam for 10-12 minutes.',12),
    (3,'Pressure cook toor dal until soft.',15),
    (4,'Cook vegetables with tamarind extract, sambar powder and turmeric; add mashed dal.',15),
    (5,'Temper mustard seeds and curry leaves; pour over sambar and serve with idli.',3)
) AS v(step_number, instruction, duration_min);


-- 3. Lemon Rice
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Lemon Rice','South Indian','Lunch','vegan',20,3,'Zesty tempered rice tossed with lemon, peanuts and curry leaves.',310,6,54,9,2
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Lemon Rice')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('cooked rice','3 cups',false,1),
        ('lemon','2',false,2),
        ('peanuts','1/4 cup',false,3),
        ('mustard seeds','1 tsp',false,4),
        ('chana dal','1 tbsp',false,5),
        ('green chilli','2',false,6),
        ('turmeric powder','1/2 tsp',false,7),
        ('curry leaves','1 sprig',false,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Heat oil and splutter mustard seeds; add chana dal and peanuts, fry until golden.',4),
    (2,'Add green chilli, curry leaves and turmeric.',1),
    (3,'Add cooked rice and salt; toss to coat evenly.',3),
    (4,'Turn off heat and squeeze in lemon juice; mix and serve.',1)
) AS v(step_number, instruction, duration_min);


-- 4. Medu Vada
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Medu Vada','South Indian','Snack','vegan',35,4,'Crispy golden lentil doughnuts, fluffy inside and crunchy outside.',250,8,30,11,3
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Medu Vada')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('urad dal','1 cup',false,1),
        ('green chilli','2',false,2),
        ('ginger','1 inch',false,3),
        ('black pepper','1 tsp',false,4),
        ('curry leaves','1 sprig',false,5),
        ('oil for frying','2 cups',false,6),
        ('salt','to taste',false,7)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Soak urad dal 4 hours; grind to a thick fluffy batter with minimal water.',NULL),
    (2,'Mix in chopped chilli, ginger, pepper, curry leaves and salt.',3),
    (3,'Wet hands, shape batter into rings with a hole in the centre.',5),
    (4,'Deep-fry on medium heat until golden and crisp.',8),
    (5,'Drain and serve hot with coconut chutney.',1)
) AS v(step_number, instruction, duration_min);


-- 5. Bisi Bele Bath
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Bisi Bele Bath','South Indian','Lunch','vegetarian',45,4,'Karnataka one-pot rice and lentils simmered with vegetables and spices.',380,11,60,10,7
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Bisi Bele Bath')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('rice','1 cup',false,1),
        ('toor dal','3/4 cup',false,2),
        ('mixed vegetables','2 cups',false,3),
        ('bisi bele bath powder','3 tbsp',false,4),
        ('tamarind','small ball',false,5),
        ('ghee','2 tbsp',false,6),
        ('mustard seeds','1 tsp',false,7),
        ('curry leaves','1 sprig',false,8),
        ('cashews','2 tbsp',true,9),
        ('salt','to taste',false,10)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Pressure cook rice and toor dal together until soft.',18),
    (2,'Cook vegetables with tamarind extract and bisi bele bath powder.',12),
    (3,'Combine cooked rice-dal with the vegetable mixture and salt; simmer to a thick consistency.',8),
    (4,'Temper mustard seeds, curry leaves and cashews in ghee; stir in.',3),
    (5,'Serve hot with a dollop of ghee and boondi.',1)
) AS v(step_number, instruction, duration_min);


-- ─────────────────────────────  NORTH INDIAN  ──────────────────────────────

-- 6. Paneer Butter Masala
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Paneer Butter Masala','North Indian','Dinner','vegetarian',40,4,'Paneer cubes in a rich, creamy tomato-butter gravy.',450,18,22,32,4
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Paneer Butter Masala')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('paneer','250 g',false,1),
        ('tomato','4 large',false,2),
        ('onion','1 large',false,3),
        ('butter','3 tbsp',false,4),
        ('fresh cream','1/4 cup',false,5),
        ('ginger garlic paste','1 tbsp',false,6),
        ('garam masala','1 tsp',false,7),
        ('red chilli powder','1 tsp',false,8),
        ('kasuri methi','1 tsp',true,9),
        ('salt','to taste',false,10)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Blanch tomatoes and onion, then blend to a smooth purée.',10),
    (2,'Melt butter, add ginger garlic paste and the purée; cook until it thickens.',12),
    (3,'Add chilli powder, garam masala and salt; simmer.',5),
    (4,'Stir in cream and kasuri methi.',2),
    (5,'Add paneer cubes and simmer gently for 5 minutes; serve with naan.',5)
) AS v(step_number, instruction, duration_min);


-- 7. Chana Masala
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Chana Masala','North Indian','Lunch','vegan',35,4,'Spiced chickpea curry in an onion-tomato masala.',340,14,48,9,12
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Chana Masala')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('chickpeas','2 cups',false,1),
        ('onion','2 medium',false,2),
        ('tomato','3 medium',false,3),
        ('ginger garlic paste','1 tbsp',false,4),
        ('chana masala powder','2 tbsp',false,5),
        ('cumin seeds','1 tsp',false,6),
        ('turmeric powder','1/2 tsp',false,7),
        ('coriander leaves','2 tbsp',true,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Soak chickpeas overnight and pressure cook until tender.',20),
    (2,'Temper cumin seeds; sauté onion until golden, add ginger garlic paste.',6),
    (3,'Add tomato, turmeric and chana masala; cook to a thick masala.',8),
    (4,'Add cooked chickpeas with some cooking water; simmer 8 minutes.',8),
    (5,'Garnish with coriander and serve with rice or bhature.',1)
) AS v(step_number, instruction, duration_min);


-- 8. Aloo Gobi
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Aloo Gobi','North Indian','Lunch','vegan',30,4,'Dry-spiced potato and cauliflower stir-fry.',220,6,32,8,6
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Aloo Gobi')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('potatoes','2 medium',false,1),
        ('cauliflower','1 small',false,2),
        ('onion','1 medium',false,3),
        ('tomato','1 medium',false,4),
        ('cumin seeds','1 tsp',false,5),
        ('turmeric powder','1/2 tsp',false,6),
        ('coriander powder','1 tsp',false,7),
        ('green chilli','2',false,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Temper cumin seeds; sauté onion and green chilli.',4),
    (2,'Add tomato, turmeric, coriander powder and salt; cook to a paste.',5),
    (3,'Add potato and cauliflower florets; toss to coat.',3),
    (4,'Cover and cook on low until tender, stirring occasionally.',15),
    (5,'Garnish with coriander and serve with roti.',1)
) AS v(step_number, instruction, duration_min);


-- 9. Dal Makhani
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Dal Makhani','North Indian','Dinner','vegetarian',60,5,'Slow-cooked black lentils in a buttery, creamy gravy.',400,15,40,20,10
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Dal Makhani')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('whole black urad dal','1 cup',false,1),
        ('rajma','1/4 cup',false,2),
        ('tomato','3 medium',false,3),
        ('butter','3 tbsp',false,4),
        ('fresh cream','1/4 cup',false,5),
        ('ginger garlic paste','1 tbsp',false,6),
        ('garam masala','1 tsp',false,7),
        ('red chilli powder','1 tsp',false,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Soak urad dal and rajma overnight; pressure cook until very soft.',30),
    (2,'Cook tomato purée with ginger garlic paste, chilli powder and garam masala in butter.',10),
    (3,'Add the cooked lentils and simmer on low, mashing lightly.',15),
    (4,'Stir in cream and finish with a knob of butter.',3),
    (5,'Serve hot with naan or jeera rice.',1)
) AS v(step_number, instruction, duration_min);


-- 10. Rajma Chawal
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Rajma Chawal','North Indian','Lunch','vegan',45,4,'Comforting red kidney bean curry served over steamed rice.',420,17,68,7,14
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Rajma Chawal')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('rajma','1.5 cups',false,1),
        ('rice','2 cups',false,2),
        ('onion','2 medium',false,3),
        ('tomato','3 medium',false,4),
        ('ginger garlic paste','1 tbsp',false,5),
        ('rajma masala','2 tbsp',false,6),
        ('cumin seeds','1 tsp',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Soak rajma overnight and pressure cook until soft.',25),
    (2,'Temper cumin; sauté onion, then add ginger garlic paste and tomato.',8),
    (3,'Add rajma masala and salt; cook to a thick gravy.',6),
    (4,'Add cooked rajma with water; simmer until thick.',10),
    (5,'Serve hot over steamed rice.',1)
) AS v(step_number, instruction, duration_min);


-- 11. Palak Paneer
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Palak Paneer','North Indian','Dinner','vegetarian',35,4,'Paneer cubes in a smooth, spiced spinach gravy.',330,17,14,24,5
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Palak Paneer')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('spinach','1 large bunch',false,1),
        ('paneer','200 g',false,2),
        ('onion','1 medium',false,3),
        ('tomato','1 medium',false,4),
        ('ginger garlic paste','1 tbsp',false,5),
        ('green chilli','2',false,6),
        ('garam masala','1 tsp',false,7),
        ('fresh cream','2 tbsp',true,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Blanch spinach for 2 minutes, then blend to a purée.',6),
    (2,'Sauté onion, ginger garlic paste, green chilli and tomato.',8),
    (3,'Add spinach purée, garam masala and salt; simmer.',6),
    (4,'Add paneer cubes and cream; cook gently for 4 minutes.',4),
    (5,'Serve hot with roti or rice.',1)
) AS v(step_number, instruction, duration_min);


-- 12. Chole Bhature
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Chole Bhature','North Indian','Lunch','vegetarian',50,4,'Spiced chickpea curry served with fluffy deep-fried bread.',560,16,78,20,10
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Chole Bhature')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('chickpeas','2 cups',false,1),
        ('all-purpose flour','2 cups',false,2),
        ('yogurt','1/4 cup',false,3),
        ('onion','2 medium',false,4),
        ('tomato','2 medium',false,5),
        ('chole masala','2 tbsp',false,6),
        ('ginger garlic paste','1 tbsp',false,7),
        ('oil for frying','2 cups',false,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Knead flour with yogurt, salt and water; rest the dough 2 hours.',NULL),
    (2,'Pressure cook soaked chickpeas until soft.',20),
    (3,'Cook onion, tomato, ginger garlic paste and chole masala; add chickpeas and simmer.',15),
    (4,'Roll the dough into discs and deep-fry until puffed and golden.',10),
    (5,'Serve hot bhature with the chole.',1)
) AS v(step_number, instruction, duration_min);


-- ──────────────────────────────  PAN INDIAN  ───────────────────────────────

-- 13. Vegetable Biryani
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Vegetable Biryani','Pan Indian','Dinner','vegetarian',55,4,'Fragrant layered basmati rice with spiced vegetables and herbs.',480,12,74,15,8
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Vegetable Biryani')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('basmati rice','2 cups',false,1),
        ('mixed vegetables','3 cups',false,2),
        ('onion','2 large',false,3),
        ('yogurt','1/2 cup',false,4),
        ('biryani masala','2 tbsp',false,5),
        ('ginger garlic paste','1 tbsp',false,6),
        ('mint leaves','1/4 cup',false,7),
        ('saffron','a pinch',true,8),
        ('ghee','2 tbsp',false,9),
        ('salt','to taste',false,10)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Parboil basmati rice with whole spices until 70% done; drain.',12),
    (2,'Fry onions until golden and set aside for garnish.',8),
    (3,'Cook vegetables with yogurt, ginger garlic paste and biryani masala.',12),
    (4,'Layer rice and vegetables with mint, fried onion and saffron milk.',5),
    (5,'Cover and cook on dum (low heat) for 15 minutes; fluff and serve.',15)
) AS v(step_number, instruction, duration_min);


-- 14. Vegetable Pulao
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Vegetable Pulao','Pan Indian','Lunch','vegan',30,4,'Lightly spiced one-pot rice with vegetables and whole spices.',360,8,62,9,6
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Vegetable Pulao')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('basmati rice','1.5 cups',false,1),
        ('mixed vegetables','2 cups',false,2),
        ('onion','1 large',false,3),
        ('bay leaf','1',false,4),
        ('cumin seeds','1 tsp',false,5),
        ('cinnamon stick','1 inch',false,6),
        ('green chilli','2',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Rinse and soak rice for 20 minutes.',NULL),
    (2,'Temper cumin, bay leaf and cinnamon; sauté onion and green chilli.',5),
    (3,'Add vegetables and salt; stir-fry briefly.',4),
    (4,'Add rice and water (1:1.5); cook covered until done.',18),
    (5,'Rest 5 minutes, fluff and serve with raita.',5)
) AS v(step_number, instruction, duration_min);


-- 15. Egg Curry
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Egg Curry','Pan Indian','Dinner','non-vegetarian',35,4,'Boiled eggs simmered in a spiced onion-tomato gravy.',300,16,14,20,3
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Egg Curry')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('eggs','6',false,1),
        ('onion','2 medium',false,2),
        ('tomato','3 medium',false,3),
        ('ginger garlic paste','1 tbsp',false,4),
        ('garam masala','1 tsp',false,5),
        ('red chilli powder','1 tsp',false,6),
        ('turmeric powder','1/2 tsp',false,7),
        ('coriander leaves','2 tbsp',true,8),
        ('salt','to taste',false,9)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Boil eggs, peel and lightly fry with turmeric until golden.',10),
    (2,'Sauté onion, add ginger garlic paste and tomato.',8),
    (3,'Add chilli powder, garam masala and salt; cook to a gravy.',6),
    (4,'Add eggs with water; simmer 8 minutes.',8),
    (5,'Garnish with coriander and serve with rice.',1)
) AS v(step_number, instruction, duration_min);


-- ──────────────────────────────  CONTINENTAL  ──────────────────────────────

-- 16. Margherita Pizza
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Margherita Pizza','Italian','Dinner','vegetarian',40,2,'Classic thin-crust pizza with tomato, mozzarella and basil.',520,20,66,18,4
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Margherita Pizza')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('pizza dough','1 base',false,1),
        ('tomato','2 medium',false,2),
        ('mozzarella cheese','150 g',false,3),
        ('fresh basil','8 leaves',false,4),
        ('olive oil','1 tbsp',false,5),
        ('garlic','1 clove',false,6),
        ('salt','to taste',false,7)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Preheat oven to 250°C.',NULL),
    (2,'Blend tomatoes with garlic, salt and olive oil into a quick sauce.',5),
    (3,'Spread sauce over the rolled dough and top with torn mozzarella.',3),
    (4,'Bake until the crust is crisp and cheese is bubbling.',10),
    (5,'Finish with fresh basil and a drizzle of olive oil.',1)
) AS v(step_number, instruction, duration_min);


-- 17. Spaghetti Aglio e Olio
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Spaghetti Aglio e Olio','Italian','Dinner','vegan',20,2,'Garlic and chilli spaghetti tossed in olive oil.',430,11,62,15,3
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Spaghetti Aglio e Olio')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('spaghetti','200 g',false,1),
        ('garlic','6 cloves',false,2),
        ('olive oil','4 tbsp',false,3),
        ('red chilli flakes','1 tsp',false,4),
        ('parsley','2 tbsp',false,5),
        ('salt','to taste',false,6)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Boil spaghetti in salted water until al dente; reserve some pasta water.',10),
    (2,'Gently warm sliced garlic and chilli flakes in olive oil until fragrant.',4),
    (3,'Toss drained pasta in the oil with a splash of pasta water.',2),
    (4,'Add parsley, adjust salt and serve immediately.',1)
) AS v(step_number, instruction, duration_min);


-- 18. Creamy Mushroom Risotto
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Creamy Mushroom Risotto','Italian','Dinner','vegetarian',40,3,'Slow-stirred arborio rice with mushrooms and parmesan.',470,13,58,20,3
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Creamy Mushroom Risotto')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('arborio rice','1.5 cups',false,1),
        ('mushrooms','250 g',false,2),
        ('onion','1 small',false,3),
        ('vegetable stock','4 cups',false,4),
        ('parmesan cheese','1/2 cup',false,5),
        ('butter','2 tbsp',false,6),
        ('garlic','2 cloves',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Sauté mushrooms in butter until golden; set aside.',6),
    (2,'Cook onion and garlic, add rice and toast for a minute.',3),
    (3,'Add warm stock one ladle at a time, stirring until absorbed.',20),
    (4,'Stir in mushrooms, parmesan and a knob of butter.',3),
    (5,'Season and serve creamy and hot.',1)
) AS v(step_number, instruction, duration_min);


-- 19. Caesar Salad
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Caesar Salad','American','Lunch','vegetarian',15,2,'Crisp romaine with croutons, parmesan and creamy Caesar dressing.',320,10,18,24,3
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Caesar Salad')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('romaine lettuce','1 head',false,1),
        ('bread','2 slices',false,2),
        ('parmesan cheese','1/4 cup',false,3),
        ('mayonnaise','3 tbsp',false,4),
        ('garlic','1 clove',false,5),
        ('lemon','1',false,6),
        ('olive oil','2 tbsp',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Toast cubed bread in olive oil until crisp to make croutons.',6),
    (2,'Whisk mayonnaise, grated garlic, lemon juice and parmesan into a dressing.',3),
    (3,'Toss chopped romaine with the dressing.',2),
    (4,'Top with croutons and extra parmesan; serve.',1)
) AS v(step_number, instruction, duration_min);


-- 20. Grilled Cheese Sandwich
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Grilled Cheese Sandwich','American','Snack','vegetarian',12,2,'Golden, buttery toast with a melty cheese centre.',420,15,34,26,2
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Grilled Cheese Sandwich')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('bread','4 slices',false,1),
        ('cheddar cheese','120 g',false,2),
        ('butter','2 tbsp',false,3),
        ('black pepper','1/4 tsp',true,4)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Butter the outer sides of the bread slices.',2),
    (2,'Layer cheese between two slices, buttered sides out.',1),
    (3,'Toast on a pan over medium heat until golden.',3),
    (4,'Flip and toast the other side until cheese melts.',3),
    (5,'Slice diagonally and serve hot.',1)
) AS v(step_number, instruction, duration_min);


-- 21. Vegetable Stir-Fry
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Vegetable Stir-Fry','Asian','Dinner','vegan',20,3,'Crunchy vegetables tossed in a savoury soy-garlic sauce.',210,7,26,9,6
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Vegetable Stir-Fry')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('mixed vegetables','4 cups',false,1),
        ('garlic','3 cloves',false,2),
        ('ginger','1 inch',false,3),
        ('soy sauce','2 tbsp',false,4),
        ('sesame oil','1 tbsp',false,5),
        ('spring onion','2 stalks',false,6),
        ('salt','to taste',false,7)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Heat sesame oil in a wok over high heat.',2),
    (2,'Add garlic and ginger; stir for 30 seconds.',1),
    (3,'Add vegetables and stir-fry on high, keeping them crunchy.',6),
    (4,'Add soy sauce and salt; toss to coat.',2),
    (5,'Garnish with spring onion and serve with rice or noodles.',1)
) AS v(step_number, instruction, duration_min);


-- 22. Fluffy Pancakes
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Fluffy Pancakes','American','Breakfast','vegetarian',20,3,'Soft, fluffy pancakes perfect with syrup and fruit.',350,9,52,11,2
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Fluffy Pancakes')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('all-purpose flour','1.5 cups',false,1),
        ('milk','1.25 cups',false,2),
        ('egg','1',false,3),
        ('baking powder','2 tsp',false,4),
        ('sugar','2 tbsp',false,5),
        ('butter','2 tbsp',false,6),
        ('salt','1/4 tsp',false,7)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Whisk together flour, baking powder, sugar and salt.',2),
    (2,'Mix in milk, egg and melted butter to a smooth batter.',3),
    (3,'Pour ladles of batter onto a hot greased pan.',2),
    (4,'Flip when bubbles form; cook until golden.',4),
    (5,'Serve warm with syrup and fruit.',1)
) AS v(step_number, instruction, duration_min);


-- 23. Tomato Basil Soup
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Tomato Basil Soup','Mediterranean','Lunch','vegetarian',30,4,'Silky roasted tomato soup finished with fresh basil and cream.',180,4,20,10,4
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Tomato Basil Soup')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('tomato','6 large',false,1),
        ('onion','1 medium',false,2),
        ('garlic','3 cloves',false,3),
        ('fresh basil','1/4 cup',false,4),
        ('vegetable stock','2 cups',false,5),
        ('fresh cream','2 tbsp',true,6),
        ('olive oil','1 tbsp',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Sauté onion and garlic in olive oil until soft.',5),
    (2,'Add chopped tomatoes and stock; simmer until tomatoes break down.',15),
    (3,'Blend until smooth and return to the pot.',3),
    (4,'Stir in basil and cream; season to taste.',2),
    (5,'Serve hot with crusty bread.',1)
) AS v(step_number, instruction, duration_min);


-- 24. Mac and Cheese
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Mac and Cheese','American','Dinner','vegetarian',30,4,'Creamy baked macaroni in a rich cheddar cheese sauce.',540,20,58,26,2
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Mac and Cheese')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('macaroni','300 g',false,1),
        ('cheddar cheese','200 g',false,2),
        ('milk','2 cups',false,3),
        ('butter','3 tbsp',false,4),
        ('all-purpose flour','3 tbsp',false,5),
        ('black pepper','1/2 tsp',false,6),
        ('salt','to taste',false,7)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Boil macaroni until al dente; drain.',10),
    (2,'Make a roux with butter and flour, then whisk in milk to a smooth sauce.',6),
    (3,'Stir in grated cheese until melted; season with salt and pepper.',3),
    (4,'Fold in the macaroni until well coated.',2),
    (5,'Serve hot, or bake 10 minutes for a golden top.',10)
) AS v(step_number, instruction, duration_min);


-- 25. Greek Salad
WITH r AS (
    INSERT INTO public.recipes (title, cuisine, meal_type, diet, ready_in_min, servings, description, calories_kcal, protein_g, carbs_g, fat_g, fiber_g)
    SELECT 'Greek Salad','Mediterranean','Lunch','vegetarian',15,3,'Fresh cucumber, tomato and feta with olives and oregano.',240,7,14,18,4
    WHERE NOT EXISTS (SELECT 1 FROM public.recipes WHERE title='Greek Salad')
    RETURNING id
), ing AS (
    INSERT INTO public.recipe_ingredients (recipe_id, name, quantity, is_optional, sort_order)
    SELECT r.id, v.name, v.quantity, v.is_optional, v.sort_order
    FROM r CROSS JOIN (VALUES
        ('cucumber','1 large',false,1),
        ('tomato','3 medium',false,2),
        ('red onion','1 small',false,3),
        ('feta cheese','100 g',false,4),
        ('olives','1/3 cup',false,5),
        ('olive oil','3 tbsp',false,6),
        ('dried oregano','1 tsp',false,7),
        ('salt','to taste',false,8)
    ) AS v(name, quantity, is_optional, sort_order)
    RETURNING 1
)
INSERT INTO public.recipe_steps (recipe_id, step_number, instruction, duration_min)
SELECT r.id, v.step_number, v.instruction, v.duration_min::int
FROM r CROSS JOIN (VALUES
    (1,'Chop cucumber, tomato and red onion into chunks.',5),
    (2,'Combine in a bowl with olives and cubed feta.',2),
    (3,'Drizzle with olive oil, sprinkle oregano and salt.',1),
    (4,'Toss gently and serve fresh.',1)
) AS v(step_number, instruction, duration_min);
