/**
 * RasOI Kitchen Intelligence - RecipeList Component
 * 
 * Displays meal recommendation cards with ingredient matching and expiration indicators.
 * Provides navigation to detailed recipe view for selected recipes.
 * 
 * Validates: Requirements 4.3 (Display recipes), 4.4 (Prioritize expiring items),
 *            4.6 (Match percentage)
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRecipe } from '../context/RecipeContext';
import { usePantry } from '../context/PantryContext';
import apiClient, { ApiError } from '../services/apiClient';
import type { Recipe } from '../types';

/**
 * RecipeList Component
 * 
 * Fetches recipe recommendations based on pantry inventory and displays
 * them as interactive cards. Shows match percentage, prep time, and
 * badges for recipes using expiring items.
 */
export default function RecipeList() {
  const navigate = useNavigate();
  const { state: recipeState, dispatch: recipeDispatch } = useRecipe();
  const { state: pantryState } = usePantry();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Fetch recipe recommendations on component mount
   */
  useEffect(() => {
    const fetchRecipes = async () => {
      setIsLoading(true);
      recipeDispatch({ type: 'SET_LOADING', payload: true });
      setError(null);

      try {
        const response = await apiClient.getRecipes(true, 5);
        recipeDispatch({ type: 'SET_RECIPES', payload: response.recipes });
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to load recipe recommendations. Please try again.';
        setError(errorMessage);
      } finally {
        setIsLoading(false);
        recipeDispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    // Only fetch if pantry has items
    if (pantryState.pantryItems.length > 0) {
      fetchRecipes();
    } else {
      setIsLoading(false);
      recipeDispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [recipeDispatch, pantryState.pantryItems.length]);

  /**
   * Handle recipe card click - navigate to recipe view
   */
  const handleSelectRecipe = (recipe: Recipe) => {
    recipeDispatch({ type: 'SELECT_RECIPE', payload: recipe });
    navigate(`/recipe/${recipe.id}`);
  };

  /**
   * Get match percentage color styling
   */
  const getMatchColor = (percentage: number): string => {
    if (percentage >= 80) return 'text-green-600';
    if (percentage >= 50) return 'text-yellow-600';
    return 'text-orange-600';
  };

  /**
   * Get match percentage background color
   */
  const getMatchBgColor = (percentage: number): string => {
    if (percentage >= 80) return 'bg-green-100';
    if (percentage >= 50) return 'bg-yellow-100';
    return 'bg-orange-100';
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <svg
            className="animate-spin h-12 w-12 text-blue-600 mx-auto mb-4"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p className="text-gray-600">Finding delicious recipes for you...</p>
        </div>
      </div>
    );
  }

  // Empty pantry state
  if (pantryState.pantryItems.length === 0) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <svg
            className="w-24 h-24 text-gray-300 mx-auto mb-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            No Ingredients Yet
          </h2>
          <p className="text-gray-600 mb-6">
            Add ingredients to your pantry to get personalized recipe recommendations.
          </p>
          <a
            href="/"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Scan Ingredients
          </a>
        </div>
      </div>
    );
  }

  // No recipes found
  if (recipeState.recipes.length === 0 && !isLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <svg
            className="w-24 h-24 text-gray-300 mx-auto mb-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            No Recipes Available
          </h2>
          <p className="text-gray-600 mb-6">
            We couldn't find any recipes based on your current pantry. Try adding more ingredients!
          </p>
          {error && (
            <p className="text-sm text-red-600 mb-4">{error}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">
          Recommended Recipes
        </h1>
        <p className="text-gray-600">
          Based on your {pantryState.pantryItems.length} pantry {pantryState.pantryItems.length === 1 ? 'item' : 'items'}
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-start">
            <svg
              className="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Recipe Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {recipeState.recipes.map((recipe) => (
          <div
            key={recipe.id}
            onClick={() => handleSelectRecipe(recipe)}
            className="bg-white rounded-lg shadow-lg overflow-hidden cursor-pointer transform transition-transform hover:scale-105 hover:shadow-xl"
          >
            {/* Recipe Card Header */}
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-6 text-white relative">
              {/* Expiring Items Badge */}
              {recipe.usesExpiringItems && (
                <div className="absolute top-3 right-3">
                  <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Uses Expiring
                  </span>
                </div>
              )}

              <h3 className="text-xl font-bold mb-2 pr-24">{recipe.name}</h3>
              
              {/* Prep Time */}
              <div className="flex items-center text-blue-100">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm">{recipe.prepTimeMinutes} minutes</span>
              </div>
            </div>

            {/* Recipe Card Body */}
            <div className="p-6">
              {/* Match Percentage */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Ingredient Match
                  </span>
                  <span className={`text-lg font-bold ${getMatchColor(recipe.matchPercentage)}`}>
                    {Math.round(recipe.matchPercentage)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${getMatchBgColor(recipe.matchPercentage)}`}
                    style={{ width: `${recipe.matchPercentage}%` }}
                  />
                </div>
              </div>

              {/* Ingredient Count */}
              <div className="mb-4">
                <div className="flex items-center text-sm text-gray-600 mb-1">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  <span>
                    {recipe.ingredients.length} ingredients
                  </span>
                </div>
                <div className="flex items-center text-sm text-gray-600">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span>
                    {recipe.steps.length} steps
                  </span>
                </div>
              </div>

              {/* Missing Ingredients */}
              {recipe.missingIngredients.length > 0 && (
                <div className="mb-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Missing Ingredients:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {recipe.missingIngredients.slice(0, 3).map((ingredient, index) => (
                      <span
                        key={index}
                        className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                      >
                        {ingredient}
                      </span>
                    ))}
                    {recipe.missingIngredients.length > 3 && (
                      <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                        +{recipe.missingIngredients.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* View Recipe Button */}
              <button className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2">
                <span>View Recipe</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Help Text */}
      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-600 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div>
            <h3 className="text-sm font-medium text-blue-800 mb-1">
              Recipe Recommendations
            </h3>
            <p className="text-sm text-blue-700">
              Recipes are prioritized based on expiring ingredients in your pantry. 
              The match percentage shows how many ingredients you already have. 
              Click any recipe card to see detailed step-by-step cooking instructions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
