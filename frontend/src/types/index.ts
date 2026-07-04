/**
 * Food Buddy Kitchen Intelligence - TypeScript Type Definitions
 * 
 * This module defines all TypeScript interfaces used throughout the frontend
 * application for type safety and API contracts.
 * 
 * Validates: Requirements 2.1 (Pantry data structure), 4.5 (Recipe structure)
 */

/**
 * Pantry Item interface representing an ingredient in the session pantry
 * (the user's most recent scan — Food Buddy does not persist a live, continuously
 * -tracked inventory, so there's no expiry status or created/updated timestamps).
 *
 * Validates: Requirement 2.1 - Pantry inventory data structure
 */
export interface PantryItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate: string; // ISO 8601 format
  expirationDate: string;  // ISO 8601 format, estimated at scan time
  confidence?: number;     // 0-1 from the vision model
}

/**
 * Ingredient interface from scanning operations.
 * Used when adding new ingredients to the pantry.
 */
export interface Ingredient {
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate: string; // ISO 8601 format
  expirationDate: string;  // ISO 8601 format
  confidence: number;      // 0-1 from Vision API
}

/**
 * Recipe ingredient with availability tracking.
 */
export interface RecipeIngredient {
  id?: string;
  recipe_id?: string;
  name: string;
  quantity: number | string;
  unit?: string;
  is_optional?: boolean;
  isOptional?: boolean;
  sort_order?: number;
  sortOrder?: number;
  available: boolean;
}

export interface RecipeStep {
  id?: string;
  recipe_id?: string;
  step_number: number;
  stepNumber?: number;
  instruction: string;
  duration_min?: number | null;
  durationMin?: number | null;
  tip?: string | null;
}

/**
 * Recipe interface for meal recommendations.
 * 
 * Validates: Requirement 4.5 - Recipe data structure with ingredients, steps, and prep time
 */
export interface Recipe {
  id: string;
  title?: string;
  name: string;
  cuisine?: string;
  meal_type?: string | null;
  mealType?: string | null;
  diet?: string | null;
  difficulty?: 'Easy' | 'Medium' | 'Hard';
  ingredients: RecipeIngredient[];
  recipeIngredients?: RecipeIngredient[];
  steps: string[];
  cooking_steps?: RecipeStep[];
  cookingSteps?: RecipeStep[];
  ready_in_min?: number;
  readyInMin?: number;
  prepTimeMinutes: number;
  servings?: number | null;
  image_url?: string | null;
  imageUrl?: string | null;
  image?: string | null;
  description?: string | null;
  calories_kcal?: number | null;
  caloriesKcal?: number | null;
  protein_g?: number | null;
  proteinG?: number | null;
  carbs_g?: number | null;
  carbsG?: number | null;
  fat_g?: number | null;
  fatG?: number | null;
  fiber_g?: number | null;
  fiberG?: number | null;
  matchPercentage: number;
  usesExpiringItems: boolean;
  missingIngredients: string[];
  source?: 'supabase' | 'spoonacular' | string;
  /** Heuristic 0-100 re-ranking signal from the user's health profile — not medical guidance. */
  healthMatchPercentage?: number;
  healthNote?: string | null;
}

export interface RecipeSearchFilters {
  cuisine?: string;
  mealType?: string;
  diet?: string;
  maxReadyTime?: number;
}

/**
 * Substitution suggestion for missing ingredients.
 */
export interface Substitution {
  ingredient: string;
  ratio: string;
  notes: string;
  available: boolean;
}

/**
 * Buddy mascot message context types.
 */
export type BuddyContext = 'idle' | 'pantry' | 'recipes' | 'cooking';

/**
 * Buddy message interface for contextual guidance.
 */
export interface BuddyMessage {
  text: string;
  context: BuddyContext;
  duration: number; // milliseconds
}

/**
 * API Response Types
 */

export interface ScanResponse {
  success: boolean;
  ingredients: Ingredient[];
  message?: string;
  imageUrl?: string | null;   // Supabase signed URL (1 hour) — PRD §6.2
  imagePath?: string | null;  // Storage path for signed URL refresh
}

export interface PantryResponse {
  items: PantryItem[];
  hasLastScan: boolean;
  scanDate: string | null;
  scanType: string | null;
}

export interface PantryItemResponse {
  success: boolean;
  item: PantryItem;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
}

export interface RecipesResponse {
  recipes: Recipe[];
  provider?: string;
  message?: string;
}

export interface SubstitutionsResponse {
  substitutions: Substitution[];
  recommend_purchase?: boolean;
  purchase_reason?: string;
  core_function?: string;
}

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  timestamp: string;
  services: {
    database: 'up' | 'down';
    claudeVision: 'up' | 'down';
    claudeText: 'up' | 'down';
  };
}

/**
 * Request payload types
 */

export interface PantryItemUpdateRequest {
  quantity?: number;
  expirationDate?: string;
}

export interface SubstitutionRequest {
  recipeId: string;
  missingIngredient: string;
  recipeContext: string;
}

export type ScanType = 'ingredient' | 'receipt';

/**
 * Buddy agent WebSocket event pushed by the backend.
 */
export interface BuddyEvent {
  type: 'expiry_alert' | 'meal_ready' | 'substitution' | 'idle' | 'low_stock';
  dialogue: string;
  animation: 'bounce' | 'wiggle' | 'talk';
  data?: Record<string, unknown>;
}

/**
 * Request payload for creating a new pantry item manually.
 */
export interface PantryItemCreateRequest {
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate?: string;  // ISO 8601; defaults to today on backend
  expirationDate?: string;   // ISO 8601; defaults to today on backend
}

/**
 * Response from POST /api/pantry/cooked
 */
export interface CookedResponse {
  removed: number;
  remaining: number;
  message: string;
}

export interface CuisineProfile {
  id: 'belgian' | 'mediterranean' | 'asian' | string;
  name: string;
  staples: string[];
  flavor_notes: string[];
  preferred_meals: string[];
}

export interface HouseholdMember {
  id: string;
  name: string;
  dietaryPreferences: string[];
  servings: number;
}

export interface HouseholdProfile {
  id: string;
  name: string;
  members: HouseholdMember[];
  defaultServings: number;
}

export interface MealNutrition {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

export interface PlannedMealDay {
  date: string;
  mealName: string;
  region: string;
  servings: number;
  usesPantryItems: string[];
  missingIngredients: string[];
  nutrition: MealNutrition;
}

export interface GroceryItem {
  name: string;
  quantity: number;
  unit: string;
}

export interface DeliveryPartner {
  id: 'collectandgo' | string;
  name: string;
  status: string;
  cartUrl: string;
}

export interface WeeklyPlannerResponse {
  profile: CuisineProfile;
  household: HouseholdProfile;
  days: PlannedMealDay[];
  nutritionalSummary: {
    dailyAverage: MealNutrition;
    weeklyTotal: MealNutrition;
  };
  groceryList: GroceryItem[];
  deliveryPartners: DeliveryPartner[];
}

export interface CuisineProfilesResponse {
  profiles: CuisineProfile[];
}

export interface DeliveryPartnersResponse {
  partners: DeliveryPartner[];
}

/**
 * Onboarding preferences for the (single, demo) Food Buddy user.
 */
export type DietType = 'vegetarian' | 'non_vegetarian' | 'eggetarian' | 'vegan';
export type BudgetPeriod = 'weekly' | 'monthly';
export type BudgetCurrency = 'EUR' | 'INR';
export type BmiCategory = 'underweight' | 'normal' | 'overweight' | 'obese';
export type HealthCondition = 'diabetes' | 'hypertension' | 'thyroid' | 'pcos' | 'kidney' | 'allergies';
export type HealthGoal = 'weight_loss' | 'muscle_gain' | 'general_fitness' | 'maintenance';

export interface UserPreferences {
  cuisines: string[];
  dietType: DietType;
  heightCm: number | null;
  weightKg: number | null;
  bmi: number | null;
  bmiCategory: BmiCategory | null;
  familySize: number;
  budgetAmount: number | null;
  budgetPeriod: BudgetPeriod;
  budgetCurrency: BudgetCurrency;
  healthConditions: HealthCondition[];
  healthGoal: HealthGoal;
  onboardingCompleted: boolean;
}

export interface PreferencesResponse {
  preferences: UserPreferences;
}

export interface PreferencesUpdateRequest {
  cuisines: string[];
  dietType: DietType;
  heightCm: number;
  weightKg: number;
  familySize: number;
  budgetAmount: number;
  budgetPeriod: BudgetPeriod;
  budgetCurrency: BudgetCurrency;
  healthConditions: HealthCondition[];
  healthGoal: HealthGoal;
}

export interface PreferencesSaveResponse {
  success: boolean;
  preferences: UserPreferences;
}

/**
 * Grocery receipt scanning — line items extracted by the vision model
 * and persisted to Supabase (receipt_scans / receipt_items).
 */
export type ReceiptItemCategory =
  | 'Dairy'
  | 'Vegetable'
  | 'Spice'
  | 'Grains'
  | 'Oils'
  | 'Lentils'
  | 'Other';

export interface ReceiptItem {
  id?: string;
  receipt_id?: string;
  user_id?: string;
  raw_name: string;
  normalized_name: string;
  brand: string | null;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
  category: ReceiptItemCategory;
}

export interface ReceiptScanResponse {
  success: boolean;
  receiptId?: string;
  storeName?: string;
  scanDate?: string;
  totalAmount?: number;
  items: ReceiptItem[];
  message?: string;
}

/**
 * Missing-ingredient product suggestion — from the Supabase
 * suggest_product_for_missing(user_id, ingredient_name) RPC.
 */
export interface ProductSuggestion {
  action: string;
  product_name: string;
  brand: string;
  variant: string | null;
  price_inr: number;
  quality_tier: string;
  reason: string;
  upgrade_type: string | null;
  blinkit_url: string | null;
  zepto_url: string | null;
  confidence: number;
}

export interface SuggestResponse {
  ingredient: string;
  suggestion: ProductSuggestion;
}

/**
 * Purchase history — powers the /history page (receipt timeline, brand
 * loyalty per category, and a buying-patterns summary card).
 */
export interface ReceiptScanRecord {
  id: string;
  storeName: string;
  scanDate: string | null;
  totalAmount: number | null;
  items: ReceiptItem[];
}

export interface ReceiptHistoryResponse {
  receipts: ReceiptScanRecord[];
}

export type BrandConsistency = 'green' | 'amber' | 'grey';

export interface BrandPreferenceCategory {
  category: string;
  preferredBrand: string;
  avgPrice: number | null;
  timesPurchased: number;
  distinctBrands: number;
  consistency: BrandConsistency;
}

export interface BrandPreferencesResponse {
  categories: BrandPreferenceCategory[];
}

export interface BuyingPatternsSummary {
  totalSpent: number;
  mostPurchasedItem: string | null;
  favouriteStore: string | null;
  potentialSavings: number | null;
}

/**
 * Collect&Go (Colruyt Group) missing-ingredient shopping suggestions.
 * Tiered by brand: Everyday < Boni Selection < Boni Bio < Bio-Time < Nationaal A-merk.
 */
export interface CollectAndGoProduct {
  product: string;
  brand: string;
  category: string;
  unit: string;
  price_eur: number;
  currency?: 'EUR' | 'INR' | string;
  tier: string;
  shopUrl: string;
  substituted_for_tier?: string;
}

export interface CollectAndGoSuggestResponse {
  ingredient: string;
  source: 'preference' | 'purchase_history' | 'cuisine';
  profile: string;
  cuisine?: string;
  mix: Record<string, number>;
  suggestions: CollectAndGoProduct[];
  shortfall: Record<string, number>;
}
