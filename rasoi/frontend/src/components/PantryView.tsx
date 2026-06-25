/**
 * RasOI Kitchen Intelligence - PantryView Component
 * 
 * Displays pantry inventory with sorting, inline editing, and deletion.
 * Highlights expiring/expired items and provides empty state guidance.
 * 
 * Validates: Requirements 2.3 (Display inventory), 2.4 (Delete items),
 *            2.5 (Update quantity), 2.6 (Sort by expiration)
 */

import React, { useEffect, useState } from 'react';
import { usePantry } from '../context/PantryContext';
import apiClient, { ApiError } from '../services/apiClient';
import type { PantryItem } from '../types';

/**
 * PantryView Component
 * 
 * Fetches and displays pantry items sorted by expiration date.
 * Provides inline quantity editing with debounced API calls and
 * delete functionality with confirmation modal.
 */
export default function PantryView() {
  const { state, dispatch } = usePantry();
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);

  /**
   * Fetch pantry items on component mount
   */
  useEffect(() => {
    const fetchPantry = async () => {
      dispatch({ type: 'SET_LOADING', payload: true });
      setError(null);

      try {
        const response = await apiClient.getPantry();
        // Sort items by expiration date (earliest first)
        const sortedItems = sortByExpirationDate(response.items);
        dispatch({ type: 'SET_ITEMS', payload: sortedItems });
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to load pantry. Please refresh the page.';
        setError(errorMessage);
        dispatch({ type: 'SET_ERROR', payload: errorMessage });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    fetchPantry();
  }, [dispatch]);

  /**
   * Sort items by expiration date (earliest first)
   * Validates: Requirement 2.6
   */
  const sortByExpirationDate = (items: PantryItem[]): PantryItem[] => {
    return [...items].sort((a, b) => {
      const dateA = new Date(a.expirationDate).getTime();
      const dateB = new Date(b.expirationDate).getTime();
      return dateA - dateB;
    });
  };

  /**
   * Start editing an item's quantity
   */
  const handleStartEdit = (item: PantryItem) => {
    setEditingItemId(item.id);
    setEditValue(item.quantity.toString());
  };

  /**
   * Handle quantity input change with debounced API call
   * Validates: Requirement 2.5
   */
  const handleQuantityChange = (itemId: string, value: string) => {
    setEditValue(value);

    // Clear previous debounce timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // Validate numeric input
    const numericValue = parseFloat(value);
    if (isNaN(numericValue) || numericValue < 0) {
      return;
    }

    // Debounce API call by 800ms
    const timer = setTimeout(async () => {
      try {
        const response = await apiClient.updatePantryItem(itemId, {
          quantity: numericValue,
        });

        if (response.success) {
          dispatch({
            type: 'UPDATE_ITEM',
            payload: {
              id: itemId,
              updates: { quantity: numericValue },
            },
          });
        }
      } catch (err) {
        const errorMessage =
          err instanceof ApiError
            ? err.message
            : 'Failed to update quantity.';
        setError(errorMessage);
      }
    }, 800);

    setDebounceTimer(timer);
  };

  /**
   * Cancel editing
   */
  const handleCancelEdit = () => {
    setEditingItemId(null);
    setEditValue('');
  };

  /**
   * Confirm and delete item
   * Validates: Requirement 2.4
   */
  const handleDeleteItem = async (itemId: string) => {
    try {
      const response = await apiClient.deletePantryItem(itemId);

      if (response.success) {
        dispatch({ type: 'DELETE_ITEM', payload: itemId });
        setDeleteConfirmId(null);
      }
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to delete item.';
      setError(errorMessage);
    }
  };

  /**
   * Format date for display
   */
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  /**
   * Get expiration status styling
   * Validates: Requirements 3.2, 3.5 (Visual highlighting)
   */
  const getExpirationStyle = (item: PantryItem) => {
    if (item.isExpired) {
      return {
        bgClass: 'bg-red-50',
        borderClass: 'border-red-300',
        textClass: 'text-red-700',
        badge: 'Expired',
        badgeClass: 'bg-red-100 text-red-800 border-red-300',
      };
    } else if (item.isExpiring) {
      return {
        bgClass: 'bg-yellow-50',
        borderClass: 'border-yellow-300',
        textClass: 'text-yellow-700',
        badge: 'Expiring Soon',
        badgeClass: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      };
    }
    return {
      bgClass: 'bg-white',
      borderClass: 'border-gray-200',
      textClass: 'text-gray-700',
      badge: null,
      badgeClass: '',
    };
  };

  /**
   * Calculate days until expiration
   */
  const getDaysUntilExpiration = (expirationDate: string): number => {
    const now = new Date();
    const expDate = new Date(expirationDate);
    const diffTime = expDate.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Loading state
  if (state.isLoading) {
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
          <p className="text-gray-600">Loading your pantry...</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (state.pantryItems.length === 0) {
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
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">
            Your Pantry is Empty
          </h2>
          <p className="text-gray-600 mb-6">
            Start by scanning your ingredients or grocery receipts to build your pantry inventory.
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

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">My Pantry</h1>
        <p className="text-gray-600">
          {state.pantryItems.length} {state.pantryItems.length === 1 ? 'item' : 'items'} in your inventory
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

      {/* Pantry Items List */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Ingredient
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Quantity
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Expiration Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {state.pantryItems.map((item) => {
                const style = getExpirationStyle(item);
                const daysUntilExpiration = getDaysUntilExpiration(item.expirationDate);

                return (
                  <tr key={item.id} className={`${style.bgClass} border-l-4 ${style.borderClass}`}>
                    {/* Ingredient Name */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {item.name}
                          </div>
                          <div className="text-xs text-gray-500">
                            Added {formatDate(item.acquisitionDate)}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Quantity */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      {editingItemId === item.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="0"
                            step="0.1"
                            value={editValue}
                            onChange={(e) => handleQuantityChange(item.id, e.target.value)}
                            className="w-20 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            autoFocus
                          />
                          <span className="text-sm text-gray-700">{item.unit}</span>
                          <button
                            onClick={handleCancelEdit}
                            className="text-gray-500 hover:text-gray-700"
                            title="Cancel"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(item)}
                          className="text-sm text-gray-900 hover:text-blue-600 flex items-center gap-2"
                        >
                          <span className="font-medium">{item.quantity} {item.unit}</span>
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                      )}
                    </td>

                    {/* Expiration Date */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {formatDate(item.expirationDate)}
                      </div>
                      <div className={`text-xs ${style.textClass}`}>
                        {daysUntilExpiration < 0
                          ? `Expired ${Math.abs(daysUntilExpiration)} days ago`
                          : daysUntilExpiration === 0
                          ? 'Expires today'
                          : `${daysUntilExpiration} days remaining`}
                      </div>
                    </td>

                    {/* Status Badge */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      {style.badge && (
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${style.badgeClass}`}>
                          {style.badge}
                        </span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => setDeleteConfirmId(item.id)}
                        className="text-red-600 hover:text-red-900"
                        title="Delete item"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">
              Confirm Deletion
            </h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete this item from your pantry? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteItem(deleteConfirmId)}
                className="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
