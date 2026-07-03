import apiClient from './apiClient';
import type { Recipe, RecipeIngredient, RecipeSearchFilters, RecipeStep } from '../types';

const recipeService = {
  getRecipes: (filters: RecipeSearchFilters = {}, maxRecipes = 12) =>
    apiClient.searchRecipes(filters, maxRecipes),

  getRecipe: (id: string): Promise<Recipe> =>
    apiClient.getRecipe(id),

  getRecipeIngredients: (recipeId: string): Promise<RecipeIngredient[]> =>
    apiClient.getRecipeIngredients(recipeId),

  getRecipeSteps: (recipeId: string): Promise<RecipeStep[]> =>
    apiClient.getRecipeSteps(recipeId),

  searchRecipes: (filters: RecipeSearchFilters = {}, maxRecipes = 12) =>
    apiClient.searchRecipes(filters, maxRecipes),
};

export default recipeService;
