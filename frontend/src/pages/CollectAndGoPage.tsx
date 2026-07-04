import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import apiClient from '../services/apiClient';
import type { CollectAndGoSuggestResponse } from '../types';

const TIER_STYLES: Record<string, string> = {
  Everyday: 'bg-gray-100 text-gray-600 border-gray-200',
  Value: 'bg-gray-100 text-gray-600 border-gray-200',
  'Boni Selection': 'bg-rasoi-light text-rasoi-dark border-rasoi/30',
  Popular: 'bg-rasoi-light text-rasoi-dark border-rasoi/30',
  'Boni Bio': 'bg-green-50 text-green-700 border-green-200',
  'Bio-Time': 'bg-rasoi-amber-light text-rasoi-amber border-rasoi-amber/30',
  Premium: 'bg-purple-50 text-purple-700 border-purple-200',
  'Nationaal A-merk': 'bg-purple-50 text-purple-700 border-purple-200',
};

function formatPrice(price: number, currency?: string): string {
  if (currency === 'INR') return `₹${Math.round(price)}`;
  return `€${price.toFixed(2)}`;
}

export default function CollectAndGoPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const ingredient = params.get('ingredient') ?? '';
  const cuisine = params.get('cuisine') ?? '';

  const [data, setData] = useState<CollectAndGoSuggestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!ingredient) {
      setError('No ingredient specified.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    apiClient
      .getCollectAndGoSuggestion(ingredient, cuisine || undefined)
      .then((res) => setData(res))
      .catch(() => setError('Could not load shopping suggestions. Please try again.'))
      .finally(() => setLoading(false));
  }, [ingredient, cuisine]);

  return (
    <div className="min-h-screen bg-rasoi-panel pt-20 pb-12 px-4">
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-rasoi transition-colors mb-6"
        >
          ← Back to recipe
        </button>

        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-widest text-rasoi">Collect &amp; Go</p>
          <h1 className="text-3xl font-extrabold text-gray-900 mt-1">
            Shop <span className="capitalize">{ingredient || 'ingredient'}</span>
          </h1>
          {cuisine && (
            <p className="text-gray-500 mt-1 text-sm">
              Brands picked for <span className="font-semibold capitalize">{cuisine}</span> cooking.
            </p>
          )}
        </div>

        {loading && (
          <div className="rounded-card bg-white p-8 shadow-card text-center text-gray-500">
            Finding the best brands…
          </div>
        )}

        {!loading && error && (
          <div className="rounded-card bg-white p-8 shadow-card text-center">
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <button onClick={() => navigate('/meals')} className="px-5 py-2.5 bg-rasoi text-white font-bold rounded-pill">
              Back to meals
            </button>
          </div>
        )}

        {!loading && !error && data && (
          <div className="space-y-4">
            {data.profile && (
              <p className="text-[11px] text-gray-500">
                {data.profile}
                {data.source === 'purchase_history' && ' (based on your past purchases)'}
              </p>
            )}

            {data.suggestions.length > 0 ? (
              <div className="space-y-2">
                {data.suggestions.map((p, i) => (
                  <a
                    key={i}
                    href={p.shopUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between gap-2 bg-white rounded-card p-4 shadow-card border border-transparent hover:border-rasoi transition-colors"
                  >
                    <div>
                      <p className="font-semibold text-gray-900 capitalize">
                        {p.product} <span className="font-normal text-gray-400">· {p.brand}</span>
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-pill border ${TIER_STYLES[p.tier] ?? TIER_STYLES.Everyday}`}>
                          {p.tier}
                        </span>
                        {p.unit && <span className="text-[11px] text-gray-400">{p.unit}</span>}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-bold text-rasoi-dark">{formatPrice(p.price_eur, p.currency)}</p>
                      <p className="text-[10px] text-gray-400">Shop →</p>
                    </div>
                  </a>
                ))}
              </div>
            ) : (
              <a
                href="https://www.collectandgo.be/nl/home"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between gap-2 bg-white rounded-card p-4 shadow-card border border-transparent hover:border-rasoi transition-colors"
              >
                <span className="text-sm text-gray-600">No exact match in our catalogue yet — shop it directly.</span>
                <span className="font-bold text-rasoi-dark shrink-0">Collect&amp;Go →</span>
              </a>
            )}

            <a
              href="https://www.collectandgo.be/nl/home"
              target="_blank"
              rel="noopener noreferrer"
              className="block text-center px-6 py-3 bg-rasoi text-white font-bold rounded-pill hover:bg-rasoi-dark transition-colors"
            >
              Go to Collect &amp; Go
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
