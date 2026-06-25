/**
 * RasOI Kitchen Intelligence - Pantry Context Provider
 * 
 * Global state management for pantry inventory using React Context + useReducer.
 * Provides centralized state for pantry items with loading and error handling.
 * 
 * Validates: Requirements 2.3 (Pantry display), 8.4 (State management)
 */

import React, { createContext, useContext, useReducer } from 'react';
import type { ReactNode } from 'react';
import type { PantryItem } from '../types';

/**
 * Pantry state shape
 */
interface PantryState {
  pantryItems: PantryItem[];
  isLoading: boolean;
  error: string | null;
}

/**
 * Action types for pantry reducer
 */
type PantryAction =
  | { type: 'ADD_ITEMS'; payload: PantryItem[] }
  | { type: 'UPDATE_ITEM'; payload: { id: string; updates: Partial<PantryItem> } }
  | { type: 'DELETE_ITEM'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_ITEMS'; payload: PantryItem[] };

/**
 * Context type combining state and dispatch
 */
interface PantryContextType {
  state: PantryState;
  dispatch: React.Dispatch<PantryAction>;
}

/**
 * Initial state
 */
const initialState: PantryState = {
  pantryItems: [],
  isLoading: false,
  error: null,
};

/**
 * Pantry reducer function
 * 
 * Handles all pantry state mutations through dispatched actions.
 */
function pantryReducer(state: PantryState, action: PantryAction): PantryState {
  switch (action.type) {
    case 'ADD_ITEMS':
      return {
        ...state,
        pantryItems: [...state.pantryItems, ...action.payload],
        error: null,
      };

    case 'UPDATE_ITEM': {
      const { id, updates } = action.payload;
      return {
        ...state,
        pantryItems: state.pantryItems.map((item) =>
          item.id === id ? { ...item, ...updates } : item
        ),
        error: null,
      };
    }

    case 'DELETE_ITEM':
      return {
        ...state,
        pantryItems: state.pantryItems.filter((item) => item.id !== action.payload),
        error: null,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
      };

    case 'SET_ITEMS':
      return {
        ...state,
        pantryItems: action.payload,
        error: null,
      };

    default:
      return state;
  }
}

/**
 * Create the context
 */
const PantryContext = createContext<PantryContextType | undefined>(undefined);

/**
 * PantryProvider component
 * 
 * Wraps the application to provide global pantry state access.
 * 
 * @param children - React children to wrap with provider
 */
export function PantryProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(pantryReducer, initialState);

  return (
    <PantryContext.Provider value={{ state, dispatch }}>
      {children}
    </PantryContext.Provider>
  );
}

/**
 * Custom hook to access pantry context
 * 
 * @throws Error if used outside PantryProvider
 * @returns Pantry state and dispatch function
 */
export function usePantry() {
  const context = useContext(PantryContext);
  if (context === undefined) {
    throw new Error('usePantry must be used within a PantryProvider');
  }
  return context;
}
