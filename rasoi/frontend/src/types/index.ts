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
  name: string;
  quantity: number;
  unit: string;
  available: boolean;
}

/**
 * Recipe interface for meal recommendations.
 * 
 * Validates: Requirement 4.5 - Recipe data structure with ingredients, steps, and prep time
 */
export interface Recipe {
  id: string;
  name: string;
  cuisine?: string;
  difficulty?: 'Easy' | 'Medium' | 'Hard';
  ingredients: RecipeIngredient[];
  steps: string[];
  prepTimeMinutes: number;
  matchPercentage: number;
  usesExpiringItems: boolean;
  missingIngredients: string[];
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
