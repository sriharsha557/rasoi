/**
 * RasOI Kitchen Intelligence - TypeScript Type Definitions
 * 
 * This module defines all TypeScript interfaces used throughout the frontend
 * application for type safety and API contracts.
 * 
 * Validates: Requirements 2.1 (Pantry data structure), 4.5 (Recipe structure)
 */

/**
 * Pantry Item interface representing an ingredient in the user's inventory.
 * 
 * Validates: Requirement 2.1 - Pantry inventory data structure
 */
export interface PantryItem {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  acquisitionDate: string; // ISO 8601 format
  expirationDate: string;  // ISO 8601 format
  isExpiring: boolean;
  isExpired: boolean;
  createdAt: string;       // ISO 8601 format
  updatedAt: string;       // ISO 8601 format
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
 * Chammach mascot message context types.
 */
export type ChammachContext = 'idle' | 'pantry' | 'recipes' | 'cooking';

/**
 * Chammach message interface for contextual guidance.
 */
export interface ChammachMessage {
  text: string;
  context: ChammachContext;
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
 * Chammach agent WebSocket event pushed by the backend.
 */
export interface ChammachEvent {
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
  id: 'south_indian' | 'bengali' | 'punjabi' | string;
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
  id: 'blinkit' | 'zepto' | string;
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
