/**
 * Food Buddy Kitchen Intelligence - API Client Service
 * 
 * This module provides a centralized Axios-based API client for communicating
 * with the FastAPI backend. Includes error handling, request/response transformations,
 * and typed API method interfaces.
 * 
 * Validates: Requirements 8.3 (Frontend error handling), 9.2 (Backend API endpoints)
 */

import axios from 'axios';
import type { AxiosInstance, AxiosError } from 'axios';
import type {
  ScanResponse,
  PantryResponse,
  PantryItemResponse,
  DeleteResponse,
  RecipesResponse,
  Recipe,
  RecipeIngredient,
  RecipeSearchFilters,
  RecipeStep,
  SubstitutionsResponse,
  HealthCheckResponse,
  PantryItemUpdateRequest,
  PantryItemCreateRequest,
  CookedResponse,
  SubstitutionRequest,
  ScanType,
  WeeklyPlannerResponse,
  CuisineProfilesResponse,
  HouseholdProfile,
  DeliveryPartnersResponse,
  PreferencesResponse,
  PreferencesUpdateRequest,
  PreferencesSaveResponse,
  ReceiptScanResponse,
  SuggestResponse,
  ReceiptHistoryResponse,
  BrandPreferencesResponse,
  BuyingPatternsSummary,
  CollectAndGoSuggestResponse
} from '../types';

/**
 * Custom API Error class for typed error handling.
 */
export class ApiError extends Error {
  statusCode?: number;
  details?: unknown;
  
  constructor(
    message: string,
    statusCode?: number,
    details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * API Client Configuration
 */
const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL || (
  import.meta.env.PROD
    ? 'https://rasoi-backend-ml4i.onrender.com/api'
    : 'http://localhost:8000/api'
);
const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, '').endsWith('/api')
  ? rawApiBaseUrl.replace(/\/+$/, '')
  : `${rawApiBaseUrl.replace(/\/+$/, '')}/api`;
const REQUEST_TIMEOUT = 30000; // 30 seconds

/**
 * WebSocket base URL (derived from API base URL, strips /api suffix).
 * Use this to build WebSocket endpoint URLs, e.g. `${WS_BASE_URL}/ws/buddy`.
 */
export const WS_BASE_URL = API_BASE_URL
  .replace(/^https/, 'wss')
  .replace(/^http/, 'ws')
  .replace(/\/api$/, '');

/**
 * Create configured Axios instance
 */
const createAxiosInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: REQUEST_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Response interceptor for error handling
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      return Promise.reject(handleApiError(error));
    }
  );

  return instance;
};

/**
 * Transform Axios errors into ApiError instances with meaningful messages.
 * 
 * Validates: Requirement 8.3 - Frontend error handling
 */
const handleApiError = (error: AxiosError): ApiError => {
  if (error.response) {
    // Server responded with error status
    const { status, data } = error.response;
    const message = (data as { message?: string })?.message || 
                    (data as { detail?: string })?.detail ||
                    `Request failed with status ${status}`;
    
    return new ApiError(message, status, data);
  } else if (error.request) {
    // Request made but no response received
    return new ApiError(
      'No response from server. Please check your connection.',
      0,
      error.request
    );
  } else {
    // Error setting up the request
    return new ApiError(error.message || 'An unexpected error occurred');
  }
};

/**
 * Axios instance singleton
 */
const axiosInstance = createAxiosInstance();

/**
 * API Client Methods
 * 
 * Validates: Requirement 9.2 - Backend API endpoint integration
 */
const apiClient = {
  /**
   * Scan ingredient or receipt image.
   * 
   * @param imageFile - The image file to scan
   * @param scanType - Type of scan ('ingredient' | 'receipt')
   * @returns Promise with extracted ingredients
   * 
   * Endpoint: POST /api/scan
   */
  scanImage: async (
    imageFile: File,
    scanType: ScanType,
    userId?: string,
    knownExpirationDate?: string
  ): Promise<ScanResponse> => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('scanType', scanType);
    if (userId) formData.append('userId', userId);
    if (knownExpirationDate) formData.append('knownExpirationDate', knownExpirationDate);

    const response = await axiosInstance.post<ScanResponse>('/scan', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Get all pantry items.
   * 
   * @returns Promise with pantry inventory
   * 
   * Endpoint: GET /api/pantry
   */
  getPantry: async (): Promise<PantryResponse> => {
    const response = await axiosInstance.get<PantryResponse>('/pantry');
    return response.data;
  },

  /**
   * Update a pantry item's quantity or expiration date.
   * 
   * @param itemId - The pantry item ID
   * @param updates - Partial updates to apply
   * @returns Promise with updated item
   * 
   * Endpoint: PUT /api/pantry/{item_id}
   */
  updatePantryItem: async (
    itemId: string,
    updates: PantryItemUpdateRequest
  ): Promise<PantryItemResponse> => {
    const response = await axiosInstance.put<PantryItemResponse>(
      `/pantry/${itemId}`,
      updates
    );
    return response.data;
  },

  /**
   * Delete a pantry item.
   * 
   * @param itemId - The pantry item ID
   * @returns Promise with deletion confirmation
   * 
   * Endpoint: DELETE /api/pantry/{item_id}
   */
  deletePantryItem: async (itemId: string): Promise<DeleteResponse> => {
    const response = await axiosInstance.delete<DeleteResponse>(`/pantry/${itemId}`);
    return response.data;
  },

  /**
   * Get recipe recommendations based on pantry inventory.
   * 
   * @param prioritizeExpiring - Whether to prioritize expiring ingredients
   * @param maxRecipes - Maximum number of recipes to return
   * @returns Promise with recipe recommendations
   * 
   * Endpoint: GET /api/recipes
   */
  getRecipes: async (
    prioritizeExpiring: boolean = true,
    maxRecipes: number = 5,
    cuisine: string = 'any',
    filters: RecipeSearchFilters = {}
  ): Promise<RecipesResponse> => {
    const response = await axiosInstance.get<RecipesResponse>('/recipes', {
      params: {
        prioritize_expiring: prioritizeExpiring,
        max_recipes: maxRecipes,
        cuisine,
        meal_type: filters.mealType,
        diet: filters.diet,
        max_ready_time: filters.maxReadyTime,
      },
      // AI-generated (cuisine=any) recommendations can take 30-45s, well beyond
      // the default 30s timeout. Allow extra time for this call specifically.
      timeout: 90000,
    });
    return response.data;
  },

  /**
   * Search recipes with cuisine, meal type, diet, and cooking-time filters.
   *
   * Endpoint: GET /api/recipes
   */
  searchRecipes: async (filters: RecipeSearchFilters = {}, maxRecipes: number = 12): Promise<RecipesResponse> => {
    return apiClient.getRecipes(true, maxRecipes, filters.cuisine ?? 'any', filters);
  },

  /**
   * Get one full recipe by id, including ingredients and ordered cooking steps.
   *
   * Endpoint: GET /api/recipe/{id}
   */
  getRecipe: async (id: string): Promise<Recipe> => {
    const response = await axiosInstance.get<Recipe>(`/recipe/${id}`);
    return response.data;
  },

  getRecipeIngredients: async (recipeId: string): Promise<RecipeIngredient[]> => {
    const recipe = await apiClient.getRecipe(recipeId);
    return recipe.recipeIngredients ?? recipe.ingredients;
  },

  getRecipeSteps: async (recipeId: string): Promise<RecipeStep[]> => {
    const recipe = await apiClient.getRecipe(recipeId);
    return recipe.cookingSteps ?? recipe.cooking_steps ?? recipe.steps.map((instruction, index) => ({
      step_number: index + 1,
      instruction,
    }));
  },

  /**
  * Search Supabase first, then Spoonacular for continental recipe details.
   *
   * Endpoint: GET /api/recipe/search
   */
  getRecipeByName: async (query: string): Promise<RecipesResponse> => {
    const response = await axiosInstance.get<RecipesResponse>('/recipe/search', {
      params: { query },
    });
    return response.data;
  },

  /**
   * Get substitution suggestions for a missing ingredient.
   * 
   * @param request - Substitution request with recipe context
   * @returns Promise with substitution suggestions
   * 
   * Endpoint: POST /api/substitute
   */
  getSubstitutions: async (
    request: SubstitutionRequest
  ): Promise<SubstitutionsResponse> => {
    const response = await axiosInstance.post<SubstitutionsResponse>(
      '/substitute',
      request
    );
    return response.data;
  },

  /**
   * Add a new item to the pantry manually.
   *
   * Endpoint: POST /api/pantry
   */
  addPantryItem: async (data: PantryItemCreateRequest): Promise<PantryItemResponse> => {
    const response = await axiosInstance.post<PantryItemResponse>('/pantry', data);
    return response.data;
  },

  /**
   * Mark a recipe as cooked and remove used ingredients from the pantry.
   *
   * @param itemsUsed - Ingredient names to remove
   *
   * Endpoint: POST /api/pantry/cooked
   */
  markCooked: async (itemsUsed: string[], recipeTitle: string = 'Unknown Recipe'): Promise<CookedResponse> => {
    const response = await axiosInstance.post<CookedResponse>('/pantry/cooked', {
      items_used: itemsUsed,
      recipe_title: recipeTitle,
    });
    return response.data;
  },

  /**
   * Health check endpoint.
   * 
   * @returns Promise with system health status
   * 
   * Endpoint: GET /api/health
   */
  healthCheck: async (): Promise<HealthCheckResponse> => {
    const response = await axiosInstance.get<HealthCheckResponse>('/health');
    return response.data;
  },

  /**
   * Get a weekly meal plan with nutrition, household scaling, and grocery links.
   *
   * Endpoint: GET /api/planner/weekly
   */
  getWeeklyPlanner: async (
    region: string = 'south_indian',
    householdSize: number = 2,
    days: number = 7
  ): Promise<WeeklyPlannerResponse> => {
    const response = await axiosInstance.get<WeeklyPlannerResponse>('/planner/weekly', {
      params: {
        region,
        household_size: householdSize,
        days,
      },
    });
    return response.data;
  },

  /**
   * Get regional cuisine profiles.
   *
   * Endpoint: GET /api/cuisine-profiles
   */
  getCuisineProfiles: async (): Promise<CuisineProfilesResponse> => {
    const response = await axiosInstance.get<CuisineProfilesResponse>('/cuisine-profiles');
    return response.data;
  },

  /**
   * Get the current household profile.
   *
   * Endpoint: GET /api/household/profile
   */
  getHouseholdProfile: async (): Promise<HouseholdProfile> => {
    const response = await axiosInstance.get<HouseholdProfile>('/household/profile');
    return response.data;
  },

  /**
   * Get grocery delivery partner links for a list of items.
   *
   * Endpoint: GET /api/grocery/delivery-partners
   */
  getDeliveryPartners: async (items: string[] = []): Promise<DeliveryPartnersResponse> => {
    const response = await axiosInstance.get<DeliveryPartnersResponse>('/grocery/delivery-partners', {
      params: {
        items: items.join(','),
      },
    });
    return response.data;
  },

  /**
   * Get the demo user's saved onboarding preferences.
   *
   * Endpoint: GET /api/preferences
   */
  getPreferences: async (): Promise<PreferencesResponse> => {
    const response = await axiosInstance.get<PreferencesResponse>('/preferences');
    return response.data;
  },

  /**
   * Save (create or update) the demo user's onboarding preferences.
   *
   * Endpoint: PUT /api/preferences
   */
  savePreferences: async (data: PreferencesUpdateRequest): Promise<PreferencesSaveResponse> => {
    const response = await axiosInstance.put<PreferencesSaveResponse>('/preferences', data);
    return response.data;
  },

  /**
   * Scan a grocery receipt image — extracts and saves line items to Supabase.
   *
   * Endpoint: POST /api/receipt/scan
   */
  scanReceipt: async (
    imageFile: File,
    storeName?: string,
    scanDate?: string
  ): Promise<ReceiptScanResponse> => {
    const formData = new FormData();
    formData.append('image', imageFile);
    if (storeName) formData.append('storeName', storeName);
    if (scanDate) formData.append('scanDate', scanDate);

    const response = await axiosInstance.post<ReceiptScanResponse>('/receipt/scan', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get a specific product suggestion for a missing ingredient.
   *
   * Endpoint: GET /api/suggest
   */
  getSuggestion: async (ingredient: string, userId: string): Promise<SuggestResponse> => {
    const response = await axiosInstance.get<SuggestResponse>('/suggest', {
      params: { ingredient, user_id: userId },
    });
    return response.data;
  },

  /**
   * Purchase history — receipt timeline, brand loyalty, buying patterns.
   *
   * Endpoints: GET /api/history/receipts | /brand-preferences | /summary
   */
  getReceiptHistory: async (userId: string): Promise<ReceiptHistoryResponse> => {
    const response = await axiosInstance.get<ReceiptHistoryResponse>('/history/receipts', {
      params: { userId },
    });
    return response.data;
  },

  getBrandPreferences: async (userId: string): Promise<BrandPreferencesResponse> => {
    const response = await axiosInstance.get<BrandPreferencesResponse>('/history/brand-preferences', {
      params: { userId },
    });
    return response.data;
  },

  getBuyingSummary: async (userId: string): Promise<BuyingPatternsSummary> => {
    const response = await axiosInstance.get<BuyingPatternsSummary>('/history/summary', {
      params: { userId },
    });
    return response.data;
  },

  /**
   * Collect&Go (Colruyt Group) missing-ingredient shopping suggestions,
   * tiered by brand and picked from the user's stated budget preference
   * or (fallback) their purchase-history buying pattern.
   *
   * Endpoint: GET /api/collectandgo/suggest
   */
  getCollectAndGoSuggestion: async (ingredient: string, cuisine?: string): Promise<CollectAndGoSuggestResponse> => {
    const response = await axiosInstance.get<CollectAndGoSuggestResponse>('/collectandgo/suggest', {
      params: { ingredient, ...(cuisine ? { cuisine } : {}) },
    });
    return response.data;
  },
};

export default apiClient;
export { API_BASE_URL };
