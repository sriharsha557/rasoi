/**
 * RasOI Kitchen Intelligence - RecipeView Component
 * 
 * Step-by-step cooking interface with navigation, ingredient availability tracking,
 * and substitution suggestions for missing ingredients.
 * 
 * Validates: Requirements 6.1 (Display step), 6.2 (Navigation controls),
 *            6.3 (Step details), 6.4 (Persist step), 6.5 (Completion message)
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useRecipe } from '../context/RecipeContext';
import apiClient, { ApiError } from '../services/apiClient';
import type { Substitution } from '../types';

/**
 * RecipeView Component
 * 
 * Displays current recipe step with large readable text, progress tracking,
 * and navigation controls. Shows ingredient list with availability indicators
 * and provides substitution suggestions for missing ingredients.
 */
export default function RecipeView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state, dispatch } = useRecipe();
  const [showSubstitutions, setShowSubstitutions] = useState(false);
  const [selectedIngredient, setSelectedIngredient] = useState<string | null>(null);
  const [substitutions, setSubstitutions] = useState<Substitution[]>([]);
  const [loadingSubstitutions, setLoadingSubstitutions] = useState(false);
  const [substitutionError, setSubstitutionError] = useState<string | null>(null);

  const { currentRecipe, currentStep } = state;

  /**
   * Load recipe if not in state (e.g., direct navigation)
   */
  useEffect(() => {
    if (!currentRecipe && id) {
      // In a real app, we would fetch the recipe by ID from the backend
      // For now, redirect back to recipe list
      navigate('/recipes');
    }
  }, [currentRecipe, id, navigate]);

  /**
   * Handle next step navigation
   * Validates: Requirement 6.2
   */
  const handleNextStep = () => {
    if (currentRecipe && currentStep < currentRecipe.steps.length - 1) {
      dispatch({ type: 'NEXT_STEP' });
    }
  };

  /**
   * Handle previous step navigation
   * Validates: Requirement 6.2
   */
  const handlePrevStep = () => {
    if (currentStep > 0) {
      dispatch({ type: 'PREV_STEP' });
    }
  };

  /**
   * Request substitution for missing ingredient
   * Validates: Requirements 5.1, 5.2, 5.3
   */
  const handleRequestSubstitution = async (ingredient: string) => {
    setSelectedIngredient(ingredient);
    setShowSubstitutions(true);
    setLoadingSubstitutions(true);
    setSubstitutionError(null);

    try {
      if (!currentRecipe) return;

      const response = await apiClient.getSubstitutions({
        recipeId: currentRecipe.id,
        missingIngredient: ingredient,
        recipeContext: currentRecipe.name,
      });

      setSubstitutions(response.substitutions);
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to load substitutions. Please try again.';
      setSubstitutionError(errorMessage);
    } finally {
      setLoadingSubstitutions(false);
    }
  };

  /**
   * Close substitution modal
   */
  const handleCloseSubstitutions = () => {
    setShowSubstitutions(false);
    setSelectedIngredient(null);
    setSubstitutions([]);
    setSubstitutionError(null);
  };

  /**
   * Navigate back to recipe list
   */
  const handleBackToRecipes = () => {
    dispatch({ type: 'CLEAR_RECIPE' });
    navigate('/recipes');
  };

  // No recipe loaded
  if (!currentRecipe) {
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
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Recipe Not Found
          </h2>
          <p className="text-gray-600 mb-6">
            The recipe you're looking for doesn't exist or couldn't be loaded.
          </p>
          <button
            onClick={() => navigate('/recipes')}
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Back to Recipes
          </button>
        </div>
      </div>
    );
  }

  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === currentRecipe.steps.length - 1;
  const currentStepText = currentRecipe.steps[currentStep];

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header with Back Button */}
      <div className="mb-6">
        <button
          onClick={handleBackToRecipes}
          className="flex items-center text-blue-600 hover:text-blue-700 mb-4"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span className="font-medium">Back to Recipes</span>
        </button>
        <h1 className="text-3xl font-bold text-gray-800">{currentRecipe.name}</h1>
        <p className="text-gray-600">
          Prep time: {currentRecipe.prepTimeMinutes} minutes • {currentRecipe.ingredients.length} ingredients
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content - Current Step */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-lg p-8">
            {/* Progress Indicator */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Step {currentStep + 1} of {currentRecipe.steps.length}
                </span>
                <span className="text-sm text-gray-500">
                  {Math.round(((currentStep + 1) / currentRecipe.steps.length) * 100)}% Complete
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${((currentStep + 1) / currentRecipe.steps.length) * 100}%` }}
                />
              </div>
            </div>

            {/* Current Step Content */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                Current Step
              </h2>
              <p className="text-xl leading-relaxed text-gray-700">
                {currentStepText}
              </p>
            </div>

            {/* Navigation Controls */}
            <div className="flex gap-4">
              <button
                onClick={handlePrevStep}
                disabled={isFirstStep}
                className={`flex-1 py-3 px-6 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                  isFirstStep
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span>Previous</span>
              </button>

              <button
                onClick={handleNextStep}
                disabled={isLastStep}
                className={`flex-1 py-3 px-6 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                  isLastStep
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                <span>{isLastStep ? 'Complete' : 'Next Step'}</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Completion Message */}
            {isLastStep && (
              <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-start">
                  <svg
                    className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-green-800 mb-1">
                      Final Step!
                    </h3>
                    <p className="text-sm text-green-700">
                      You're almost done! Complete this step and enjoy your meal.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar - Ingredients */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-lg p-6 sticky top-6">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Ingredients</h3>
            
            <div className="space-y-3">
              {currentRecipe.ingredients.map((ingredient, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border ${
                    ingredient.available
                      ? 'bg-green-50 border-green-200'
                      : 'bg-orange-50 border-orange-200'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        {ingredient.available ? (
                          <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-orange-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                          </svg>
                        )}
                        <span className={`text-sm font-medium ${
                          ingredient.available ? 'text-green-900' : 'text-orange-900'
                        }`}>
                          {ingredient.name}
                        </span>
                      </div>
                      <p className={`text-xs mt-1 ml-7 ${
                        ingredient.available ? 'text-green-700' : 'text-orange-700'
                      }`}>
                        {ingredient.quantity} {ingredient.unit}
                      </p>
                    </div>

                    {/* Substitution Button for Missing Ingredients */}
                    {!ingredient.available && (
                      <button
                        onClick={() => handleRequestSubstitution(ingredient.name)}
                        className="ml-2 text-orange-600 hover:text-orange-700"
                        title="Find substitutes"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Missing Ingredients Summary */}
            {currentRecipe.missingIngredients.length > 0 && (
              <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <p className="text-xs font-medium text-orange-800 mb-1">
                  Missing {currentRecipe.missingIngredients.length} ingredient{currentRecipe.missingIngredients.length !== 1 ? 's' : ''}
                </p>
                <p className="text-xs text-orange-700">
                  Click the substitute icon to find alternatives
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Substitution Modal */}
      {showSubstitutions && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">
                    Substitutions for {selectedIngredient}
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Alternative ingredients you can use instead
                  </p>
                </div>
                <button
                  onClick={handleCloseSubstitutions}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {loadingSubstitutions && (
                <div className="text-center py-8">
                  <svg
                    className="animate-spin h-10 w-10 text-blue-600 mx-auto mb-4"
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
                  <p className="text-gray-600">Finding substitutions...</p>
                </div>
              )}

              {substitutionError && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">{substitutionError}</p>
                </div>
              )}

              {!loadingSubstitutions && !substitutionError && substitutions.length === 0 && (
                <div className="text-center py-8">
                  <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-gray-600">No substitutions found</p>
                </div>
              )}

              {!loadingSubstitutions && substitutions.length > 0 && (
                <div className="space-y-4">
                  {substitutions.map((sub, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded-lg border ${
                        sub.available
                          ? 'bg-green-50 border-green-200'
                          : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        {sub.available && (
                          <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        )}
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 mb-1">
                            {sub.ingredient}
                            {sub.available && (
                              <span className="ml-2 text-xs text-green-600 font-semibold">
                                In Your Pantry
                              </span>
                            )}
                          </h4>
                          <p className="text-sm text-gray-700 mb-2">
                            <span className="font-medium">Ratio:</span> {sub.ratio}
                          </p>
                          <p className="text-sm text-gray-600">{sub.notes}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
