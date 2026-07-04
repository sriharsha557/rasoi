/**
 * MissingIngredientCard — for a missing pantry ingredient, shows the
 * suggested product (brand, price, quality tier) from the Supabase
 * suggest_product_for_missing RPC, with Blinkit/Zepto order links.
 */

import { useEffect, useState } from 'react';
import apiClient, { ApiError } from '../services/apiClient';
import { useGuest } from '../context/GuestContext';

const TIER_STYLES = {
  premium: 'bg-rasoi text-white',
  standard: 'bg-rasoi-light text-rasoi-dark border border-rasoi/30',
  budget: 'bg-rasoi-amber-light text-rasoi-amber border border-rasoi-amber/30',
};

function openInNewTab(url) {
  if (!url) return;
  window.open(url, '_blank', 'noopener,noreferrer');
}

/**
 * Pass `suggestion`/`isLoading`/`error` when a parent (e.g. RecipeView, which
 * also needs the price data for a summary banner) has already fetched the
 * suggestion — the card renders in controlled mode and skips its own fetch.
 * Omit all three to let the card fetch independently, keyed on ingredientName/userId.
 */
export default function MissingIngredientCard({
  ingredientName,
  userId,
  suggestion: controlledSuggestion,
  isLoading: controlledIsLoading,
  error: controlledError,
}) {
  const isControlled =
    controlledSuggestion !== undefined || controlledIsLoading !== undefined || controlledError !== undefined;

  const { demoUser } = useGuest();
  const effectiveUserId = userId || demoUser?.id;

  const [suggestion, setSuggestion] = useState(isControlled ? controlledSuggestion ?? null : null);
  const [isLoading, setIsLoading] = useState(isControlled ? Boolean(controlledIsLoading) : true);
  const [error, setError] = useState(isControlled ? controlledError ?? null : null);

  useEffect(() => {
    if (isControlled) {
      setSuggestion(controlledSuggestion ?? null);
      setIsLoading(Boolean(controlledIsLoading));
      setError(controlledError ?? null);
      return;
    }

    if (!ingredientName || !effectiveUserId) return;
    let cancelled = false;

    setIsLoading(true);
    setError(null);
    apiClient
      .getSuggestion(ingredientName, effectiveUserId)
      .then((data) => {
        if (!cancelled) setSuggestion(data.suggestion);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Could not load a suggestion for this ingredient.');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isControlled, controlledSuggestion, controlledIsLoading, controlledError, ingredientName, effectiveUserId]);

  if (isLoading) {
    return (
      <div className="w-full max-w-md mx-auto bg-white border border-rasoi/15 rounded-card shadow-card p-5 animate-pulse">
        <div className="h-3 w-28 bg-rasoi-light rounded mb-3" />
        <div className="h-5 w-40 bg-rasoi-light rounded mb-4" />
        <div className="h-20 w-full bg-rasoi-panel rounded-lg" />
      </div>
    );
  }

  if (error || !suggestion) {
    return (
      <div className="w-full max-w-md mx-auto bg-white border border-gray-100 rounded-card shadow-card p-5">
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-1">Missing ingredient</p>
        <h3 className="text-base font-bold text-gray-900 mb-2">{ingredientName}</h3>
        <p className="text-xs text-red-500">{error || 'No suggestion available right now.'}</p>
      </div>
    );
  }

  const {
    product_name: productName,
    brand,
    variant,
    price_inr: priceInr,
    quality_tier: qualityTier,
    reason,
    blinkit_url: blinkitUrl,
    zepto_url: zeptoUrl,
  } = suggestion;

  const tierClass = TIER_STYLES[(qualityTier || '').toLowerCase()] ?? TIER_STYLES.standard;

  return (
    <div className="w-full max-w-md mx-auto bg-white border border-rasoi/15 rounded-card shadow-card p-5">
      <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-1">Missing ingredient</p>
      <h3 className="text-base font-bold text-gray-900 mb-3">{ingredientName}</h3>

      <div className="rounded-lg bg-rasoi-panel border border-rasoi/10 p-4 mb-4">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div>
            <p className="text-sm font-semibold text-gray-900">{productName}</p>
            {(brand || variant) && (
              <p className="text-xs text-gray-500 mt-0.5">
                {brand}
                {brand && variant ? ' · ' : ''}
                {variant}
              </p>
            )}
          </div>
          {qualityTier && (
            <span className={`shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-pill ${tierClass}`}>
              {qualityTier}
            </span>
          )}
        </div>

        {priceInr != null && (
          <p className="text-xl font-bold text-rasoi-dark mt-2">₹{Number(priceInr).toFixed(2)}</p>
        )}

        {reason && <p className="text-xs text-gray-500 mt-2 leading-relaxed">{reason}</p>}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => openInNewTab(blinkitUrl)}
          disabled={!blinkitUrl}
          className={`flex-1 py-2.5 rounded-pill text-sm font-semibold transition-colors ${
            blinkitUrl ? 'bg-rasoi text-white hover:bg-rasoi-dark' : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          Order on Blinkit
        </button>
        <button
          type="button"
          onClick={() => openInNewTab(zeptoUrl)}
          disabled={!zeptoUrl}
          className={`flex-1 py-2.5 rounded-pill text-sm font-semibold border transition-colors ${
            zeptoUrl
              ? 'border-rasoi text-rasoi-dark hover:bg-rasoi-light'
              : 'border-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          Order on Zepto
        </button>
      </div>
    </div>
  );
}
