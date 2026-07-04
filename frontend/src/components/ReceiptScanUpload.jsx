/**
 * ReceiptScanUpload — upload a grocery receipt photo, extract line items via
 * the vision API, and save them to Supabase (receipt_scans / receipt_items).
 *
 * POST /api/receipt/scan (multipart/form-data: image, storeName?, scanDate?)
 */

import { useRef, useState } from 'react';
import apiClient, { ApiError } from '../services/apiClient';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp'];

const CATEGORY_STYLES = {
  Dairy: 'bg-blue-50 text-blue-700 border-blue-200',
  Vegetable: 'bg-rasoi-light text-rasoi-dark border-rasoi/30',
  Spice: 'bg-rasoi-amber-light text-rasoi-amber border-rasoi-amber/30',
  Grains: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  Oils: 'bg-orange-50 text-orange-700 border-orange-200',
  Lentils: 'bg-purple-50 text-purple-700 border-purple-200',
  Other: 'bg-gray-100 text-gray-600 border-gray-200',
};

export default function ReceiptScanUpload({ onScanComplete }) {
  const fileInputRef = useRef(null);

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [storeName, setStoreName] = useState('');
  const [scanDate, setScanDate] = useState('');

  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const validateFile = (file) => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return 'Invalid file type. Please upload a JPEG, PNG, or WEBP image.';
    }
    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return `File size (${sizeMB}MB) exceeds the 5 MB limit.`;
    }
    return null;
  };

  const handleFileSelect = (file) => {
    setError(null);
    setResult(null);

    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }

    setSelectedFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setPreviewUrl(reader.result);
    reader.readAsDataURL(file);
  };

  const handleDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); };
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); };
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFileSelect(files[0]);
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) handleFileSelect(files[0]);
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setError(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a receipt image first.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.scanReceipt(
        selectedFile,
        storeName.trim() || undefined,
        scanDate || undefined
      );

      if (response.success) {
        setResult(response);
        onScanComplete?.(response);
      } else {
        setError(response.message || 'No line items detected on this receipt.');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to scan receipt. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-white rounded-card shadow-card p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Scan a grocery receipt</h2>

        {/* Optional store / date fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          <label className="text-xs font-semibold text-gray-600">
            Store name (optional)
            <input
              type="text"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              placeholder="e.g. Colruyt"
              disabled={isUploading}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-rasoi/40"
            />
          </label>
          <label className="text-xs font-semibold text-gray-600">
            Purchase date (optional)
            <input
              type="date"
              value={scanDate}
              onChange={(e) => setScanDate(e.target.value)}
              disabled={isUploading}
              className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-rasoi/40"
            />
          </label>
        </div>

        {/* Drop zone */}
        {!previewUrl && (
          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-card p-12 text-center cursor-pointer transition-colors ${
              isDragging ? 'border-rasoi bg-rasoi-light' : 'border-gray-300 hover:border-rasoi/50 bg-rasoi-panel'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileInputChange}
              className="hidden"
            />
            <div className="flex flex-col items-center">
              <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 2H6a2 2 0 00-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 00-2-2z M8 8h8M8 12h8M8 16h5"
                />
              </svg>
              <p className="text-base font-semibold text-gray-800 mb-1">
                {isDragging ? 'Drop receipt here' : 'Drag and drop your receipt here'}
              </p>
              <p className="text-sm text-gray-600 mb-3">or click to browse</p>
              <p className="text-xs text-gray-500">Supported: JPEG, PNG, WEBP · Max 5 MB</p>
            </div>
          </div>
        )}

        {/* Preview */}
        {previewUrl && (
          <div className="mb-6">
            <div className="relative rounded-lg overflow-hidden bg-gray-100">
              <img src={previewUrl} alt="Receipt preview" className="w-full h-auto max-h-96 object-contain" />
              {!isUploading && (
                <button
                  onClick={handleClear}
                  className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-2 hover:bg-red-600 transition-colors"
                  title="Remove image"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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

        {/* Upload button */}
        {previewUrl && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className={`w-full py-3 px-6 rounded-pill font-semibold text-white transition-colors ${
              isUploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-rasoi hover:bg-rasoi-dark'
            }`}
          >
            {isUploading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Reading receipt...
              </span>
            ) : (
              'Scan receipt'
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">{result.storeName}</p>
                <p className="text-xs text-gray-500">{result.scanDate}</p>
              </div>
              <p className="text-lg font-bold text-rasoi-dark">
                €{Number(result.totalAmount ?? 0).toFixed(2)}
              </p>
            </div>

            <div className="border border-gray-100 rounded-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-rasoi-panel text-gray-500 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="text-left px-3 py-2">Item</th>
                    <th className="text-left px-3 py-2">Category</th>
                    <th className="text-right px-3 py-2">Qty</th>
                    <th className="text-right px-3 py-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((item, idx) => (
                    <tr key={item.id ?? idx} className="border-t border-gray-100">
                      <td className="px-3 py-2">
                        <p className="font-medium text-gray-900">{item.normalized_name}</p>
                        {item.brand && <p className="text-xs text-gray-400">{item.brand}</p>}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded-pill border ${
                            CATEGORY_STYLES[item.category] ?? CATEGORY_STYLES.Other
                          }`}
                        >
                          {item.category}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-gray-600">
                        {item.quantity} {item.unit}
                      </td>
                      <td className="px-3 py-2 text-right font-medium text-gray-900">
                        €{Number(item.total_price ?? 0).toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-gray-400 mt-2 text-center">
              Saved {result.items.length} item(s) to your pantry ledger.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
