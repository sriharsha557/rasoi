/**
 * RasOI Kitchen Intelligence - Recipe Context Provider
 * 
 * Global state management for recipe recommendations and cooking flow using React Context + useReducer.
 * Provides centralized state for recipe list, selected recipe, and step navigation.
 * 
 * Validates: Requirements 4.3 (Recipe display), 6.4 (Step navigation)
 */

import React, { createContext, useContext, useReducer } from 'react';
import type { ReactNode } from 'react';
import type { Recipe } from '../types';

/**
 * Recipe state shape
 */
interface RecipeState {
  recipes: Recipe[];
  currentRecipe: Recipe | null;
  currentStep: number;
  isLoading: boolean;
}

/**
 * Action types for recipe reducer
 */
type RecipeAction =
  | { type: 'SET_RECIPES'; payload: Recipe[] }
  | { type: 'SELECT_RECIPE'; payload: Recipe }
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'RESET_STEP' }
  | { type: 'CLEAR_RECIPE' };

/**
 * Context type combining state and dispatch
 */
interface RecipeContextType {
  state: RecipeState;
  dispatch: React.Dispatch<RecipeAction>;
}

/**
 * Initial state
 */
const initialState: RecipeState = {
  recipes: [],
  currentRecipe: null,
  currentStep: 0,
  isLoading: false,
};

/**
 * Recipe reducer function
 * 
 * Handles all recipe state mutations through dispatched actions.
 */
function recipeReducer(state: RecipeState, action: RecipeAction): RecipeState {
  switch (action.type) {
    case 'SET_RECIPES':
      return {
        ...state,
        recipes: action.payload,
      };

    case 'SELECT_RECIPE':
      return {
        ...state,
        currentRecipe: action.payload,
        currentStep: 0, // Reset to first step when selecting a new recipe
      };

    case 'NEXT_STEP': {
      if (!state.currentRecipe) {
        return state;
      }
      const maxStep = state.currentRecipe.steps.length - 1;
      return {
        ...state,
        currentStep: Math.min(state.currentStep + 1, maxStep),
      };
    }

    case 'PREV_STEP':
      return {
        ...state,
        currentStep: Math.max(state.currentStep - 1, 0),
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'RESET_STEP':
      return {
        ...state,
        currentStep: 0,
      };

    case 'CLEAR_RECIPE':
      return {
        ...state,
        currentRecipe: null,
        currentStep: 0,
      };

    default:
      return state;
  }
}

/**
 * Create the context
 */
const RecipeContext = createContext<RecipeContextType | undefined>(undefined);

/**
 * RecipeProvider component
 * 
 * Wraps the application to provide global recipe state access.
 * 
 * @param children - React children to wrap with provider
 */
export function RecipeProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(recipeReducer, initialState);

  return (
    <RecipeContext.Provider value={{ state, dispatch }}>
      {children}
    </RecipeContext.Provider>
  );
}

/**
 * Custom hook to access recipe context
 * 
 * @throws Error if used outside RecipeProvider
 * @returns Recipe state and dispatch function
 */
export function useRecipe() {
  const context = useContext(RecipeContext);
  if (context === undefined) {
    throw new Error('useRecipe must be used within a RecipeProvider');
  }
  return context;
}
