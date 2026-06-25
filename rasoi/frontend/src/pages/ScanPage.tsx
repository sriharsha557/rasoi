import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Scanner from '../components/Scanner';
import type { ScanType } from '../types';

export default function ScanPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const rawType = params.get('type');
  const initialType: ScanType = rawType === 'receipt' ? 'receipt' : 'ingredient';

  // Scroll to top on mount
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div className="min-h-screen bg-rasoi-panel pt-20 pb-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Back */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-rasoi transition-colors mb-6"
        >
          ← Back
        </button>

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-extrabold text-gray-900">
            {initialType === 'receipt' ? '🧾 Scan Receipt' : '📷 Scan Ingredients'}
          </h1>
          <p className="text-gray-500 mt-1">
            {initialType === 'receipt'
              ? 'Upload your grocery receipt and we\'ll add everything to your pantry.'
              : 'Take or upload a photo of your fridge, shelf, or counter.'}
          </p>
        </div>

        {/* Scanner component */}
        <Scanner
          initialScanType={initialType}
          onScanComplete={() => navigate('/pantry')}
        />
      </div>
    </div>
  );
}
