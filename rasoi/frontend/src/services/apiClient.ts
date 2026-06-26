/**
 * RasOI Kitchen Intelligence - API Client Service
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
  SubstitutionsResponse,
  HealthCheckResponse,
  PantryItemUpdateRequest,
  PantryItemCreateRequest,
  CookedResponse,
  SubstitutionRequest,
  ScanType
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
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const REQUEST_TIMEOUT = 30000; // 30 seconds

/**
 * WebSocket base URL (derived from API base URL, strips /api suffix).
 * Use this to build WebSocket endpoint URLs, e.g. `${WS_BASE_URL}/ws/chammach`.
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
  scanImage: async (imageFile: File, scanType: ScanType): Promise<ScanResponse> => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('scanType', scanType);

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
    maxRecipes: number = 5
  ): Promise<RecipesResponse> => {
    const response = await axiosInstance.get<RecipesResponse>('/recipes', {
      params: {
        prioritize_expiring: prioritizeExpiring,
        max_recipes: maxRecipes,
      },
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
  markCooked: async (itemsUsed: string[]): Promise<CookedResponse> => {
    const response = await axiosInstance.post<CookedResponse>('/pantry/cooked', {
      items_used: itemsUsed,
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
};

export default apiClient;
export { API_BASE_URL };
