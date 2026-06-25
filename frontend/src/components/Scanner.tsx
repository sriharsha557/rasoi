/**
 * RasOI Kitchen Intelligence - Scanner Component
 * 
 * Image upload interface for scanning ingredients and grocery receipts.
 * Supports drag-and-drop, image preview, file validation, and API integration.
 * 
 * Validates: Requirements 1.1 (Multimodal input), 1.2 (Receipt scanning),
 *            1.5 (Error handling), 8.3 (Loading indicators)
 */

import React, { useState, useRef } from 'react';
import apiClient, { ApiError } from '../services/apiClient';
import { usePantry } from '../context/PantryContext';
import type { ScanType } from '../types';

/**
 * Scanner component props
 */
interface ScannerProps {
  onScanComplete?: () => void;
  onScanError?: (error: string) => void;
  initialScanType?: ScanType;
}

/**
 * File validation constants
 */
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/jpg'];
const ACCEPTED_EXTENSIONS = ['.jpg', '.jpeg', '.png'];

/**
 * Scanner Component
 * 
 * Provides drag-and-drop and click-to-upload functionality for ingredient
 * and receipt images. Validates file type and size, shows preview, handles
 * upload with loading state, and updates pantry context on success.
 */
export default function Scanner({ onScanComplete, onScanError, initialScanType }: ScannerProps) {
  const { dispatch } = usePantry();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Component state
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scanType, setScanType] = useState<ScanType>(initialScanType ?? 'ingredient');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  /**
   * Validate file type and size
   * 
   * @param file - File to validate
   * @returns Validation result with error message if invalid
   */
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    // Check file type
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return {
        valid: false,
        error: `Invalid file type. Please upload a JPEG or PNG image.`,
      };
    }

    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `File size (${sizeMB}MB) exceeds maximum of 5MB.`,
      };
    }

    return { valid: true };
  };

  /**
   * Handle file selection and create preview
   * 
   * @param file - Selected image file
   */
  const handleFileSelect = (file: File) => {
    // Clear previous state
    setError(null);
    setSuccessMessage(null);
    
    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
      setError(validation.error || 'Invalid file');
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }

    // Set file and create preview
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  /**
   * Handle drag events
   */
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  /**
   * Handle file input change
   */
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  /**
   * Trigger file input click
   */
  const handleClickToUpload = () => {
    fileInputRef.current?.click();
  };

  /**
   * Upload image and process scan
   * 
   * Validates: Requirements 1.1, 1.2, 1.5, 8.3
   */
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select an image file first.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccessMessage(null);
    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      // Call API to scan image
      const response = await apiClient.scanImage(selectedFile, scanType);

      if (response.success && response.ingredients.length > 0) {
        // Convert ingredients to pantry items (backend assigns IDs)
        const pantryItems = response.ingredients.map((ingredient) => ({
          id: `${Date.now()}-${Math.random()}`, // Temporary ID until backend returns actual IDs
          name: ingredient.name,
          quantity: ingredient.quantity,
          unit: ingredient.unit,
          acquisitionDate: ingredient.acquisitionDate,
          expirationDate: ingredient.expirationDate,
          isExpiring: false, // Will be computed by backend
          isExpired: false,  // Will be computed by backend
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }));

        // Update pantry context
        dispatch({ type: 'ADD_ITEMS', payload: pantryItems });

        // Show success message
        const itemCount = response.ingredients.length;
        const itemWord = itemCount === 1 ? 'ingredient' : 'ingredients';
        setSuccessMessage(
          `Successfully scanned ${itemCount} ${itemWord}! Check your pantry to view them.`
        );

        // Clear preview after successful scan
        setTimeout(() => {
          setSelectedFile(null);
          setPreviewUrl(null);
          setScanType('ingredient');
        }, 2000);

        // Call success callback
        onScanComplete?.();
      } else {
        setError(response.message || 'No ingredients detected in the image.');
      }
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : 'Failed to scan image. Please try again.';
      
      setError(errorMessage);
      onScanError?.(errorMessage);
    } finally {
      setIsUploading(false);
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  /**
   * Clear selected file and preview
   */
  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setError(null);
    setSuccessMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-white rounded-card shadow-card p-6">
        {/* Scan Type Selection */}
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            What are you scanning?
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => setScanType('ingredient')}
              disabled={isUploading}
              className={`flex-1 py-3 px-4 rounded-pill font-medium transition-colors ${
                scanType === 'ingredient'
                  ? 'bg-rasoi text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              🥗 Ingredients
            </button>
            <button
              onClick={() => setScanType('receipt')}
              disabled={isUploading}
              className={`flex-1 py-3 px-4 rounded-pill font-medium transition-colors ${
                scanType === 'receipt'
                  ? 'bg-rasoi text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              🧾 Receipt
            </button>
          </div>
        </div>

        {/* Drop Zone */}
        {!previewUrl && (
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleClickToUpload}
            className={`border-2 border-dashed rounded-card p-12 text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-rasoi bg-rasoi-light'
                : 'border-gray-300 hover:border-rasoi/50 bg-rasoi-panel'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(',')}
              onChange={handleFileInputChange}
              className="hidden"
            />
            <div className="flex flex-col items-center">
              <svg
                className="w-16 h-16 text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="text-base font-semibold text-gray-800 mb-1">
                {isDragging ? 'Drop image here' : 'Drag and drop an image here'}
              </p>
              <p className="text-sm text-gray-600 mb-3">or click to browse</p>
              <p className="text-xs text-gray-500">
                Supported: JPEG, PNG · Max 5 MB
              </p>
            </div>
          </div>
        )}

        {/* Image Preview */}
        {previewUrl && (
          <div className="mb-6">
            <div className="relative rounded-lg overflow-hidden bg-gray-100">
              <img
                src={previewUrl}
                alt="Preview"
                className="w-full h-auto max-h-96 object-contain"
              />
              {!isUploading && (
                <button
                  onClick={handleClear}
                  className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-2 hover:bg-red-600 transition-colors"
                  title="Remove image"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
            {selectedFile && (
              <p className="text-sm text-gray-600 mt-2">
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>
        )}

        {/* Upload Button */}
        {previewUrl && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className={`w-full py-3 px-6 rounded-pill font-semibold text-white transition-colors ${
              isUploading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-rasoi hover:bg-rasoi-dark'
            }`}
          >
            {isUploading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin h-5 w-5 mr-3"
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
                Scanning...
              </span>
            ) : (
              `Scan ${scanType === 'ingredient' ? 'Ingredients' : 'Receipt'}`
            )}
          </button>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
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

        {/* Success Message */}
        {successMessage && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-start">
              <svg
                className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-sm text-green-700">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="mt-6 p-4 bg-rasoi-light border border-rasoi/20 rounded-card">
          <h3 className="text-sm font-semibold text-rasoi-dark mb-2">Tips for best results:</h3>
          <ul className="text-sm text-rasoi-dark/80 space-y-1 list-disc list-inside">
            <li>Ensure good lighting and clear focus</li>
            <li>Capture all ingredients in the frame</li>
            <li>For receipts, make sure text is readable</li>
            <li>Avoid shadows and glare on the image</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
