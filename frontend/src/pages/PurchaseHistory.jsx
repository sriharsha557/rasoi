/**
 * PurchaseHistory — /history
 *
 * Buying-patterns summary, a receipt timeline (expandable to line items),
 * and a brand-loyalty panel per ingredient category.
 */

import { useEffect, useState } from 'react';
import apiClient, { ApiError } from '../services/apiClient';
import { useGuest } from '../context/GuestContext';

const CATEGORY_STYLES = {
  Dairy: 'bg-blue-50 text-blue-700 border-blue-200',
  Vegetable: 'bg-rasoi-light text-rasoi-dark border-rasoi/30',
  Spice: 'bg-rasoi-amber-light text-rasoi-amber border-rasoi-amber/30',
  Grains: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  Oils: 'bg-orange-50 text-orange-700 border-orange-200',
  Lentils: 'bg-purple-50 text-purple-700 border-purple-200',
  Other: 'bg-gray-100 text-gray-600 border-gray-200',
};

const CONSISTENCY_STYLES = {
  green: { dot: 'bg-rasoi', label: 'Consistent buyer', card: 'bg-rasoi-light border-rasoi/20' },
  amber: { dot: 'bg-rasoi-amber', label: 'Mixed brands', card: 'bg-rasoi-amber-light border-rasoi-amber/20' },
  grey: { dot: 'bg-gray-400', label: 'One-time', card: 'bg-gray-50 border-gray-200' },
};

function formatMoney(value) {
  return `€${Number(value ?? 0).toFixed(2)}`;
}

export default function PurchaseHistory() {
  const { demoUser } = useGuest();
  const userId = demoUser?.id ?? 'guest';

  const [receipts, setReceipts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [summary, setSummary] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    setIsLoading(true);
    setError(null);
    Promise.all([
      apiClient.getReceiptHistory(userId),
      apiClient.getBrandPreferences(userId),
      apiClient.getBuyingSummary(userId),
    ])
      .then(([receiptData, brandData, summaryData]) => {
        setReceipts(receiptData.receipts);
        setCategories(brandData.categories);
        setSummary(summaryData);
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Could not load purchase history.');
      })
      .finally(() => setIsLoading(false));
  }, [userId]);

  const toggleReceipt = (id) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-rasoi-panel pt-24 pb-12 px-4 flex items-center justify-center">
        <p className="text-sm text-gray-500">Loading your purchase history…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-rasoi-panel pt-20 pb-16 px-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-rasoi-dark">Purchase History</p>
          <h1 className="text-2xl md:text-3xl font-extrabold text-gray-900 mt-1">Your buying patterns</h1>
        </div>

        {error && (
          <div className="bg-rasoi-red-light border border-rasoi-red/30 text-rasoi-red text-sm rounded-card px-4 py-3">
            {error}
          </div>
        )}

        {/* Your Buying Patterns */}
        {summary && (
          <section className="bg-rasoi border border-rasoi-dark rounded-card shadow-card p-5 md:p-6 text-white">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatTile label="Total spent tracked" value={formatMoney(summary.totalSpent)} />
              <StatTile label="Most purchased item" value={summary.mostPurchasedItem ?? '—'} capitalize />
              <StatTile label="Favourite store" value={summary.favouriteStore ?? '—'} />
              <StatTile
                label="Could save by switching brands"
                value={summary.potentialSavings != null ? formatMoney(summary.potentialSavings) : 'N/A'}
              />
            </div>
          </section>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Receipt timeline */}
          <section className="lg:col-span-2 bg-white border border-gray-100 rounded-card shadow-card p-5">
            <h2 className="text-sm font-bold text-gray-900 mb-4">Receipt timeline</h2>

            {receipts.length === 0 ? (
              <p className="text-sm text-gray-500">No receipts scanned yet.</p>
            ) : (
              <div className="space-y-3">
                {receipts.map((receipt) => {
                  const isExpanded = expandedId === receipt.id;
                  return (
                    <div key={receipt.id} className="border border-gray-100 rounded-card overflow-hidden">
                      <button
                        type="button"
                        onClick={() => toggleReceipt(receipt.id)}
                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-rasoi-panel transition-colors text-left"
                      >
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{receipt.storeName}</p>
                          <p className="text-xs text-gray-500">{receipt.scanDate}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <p className="text-sm font-bold text-rasoi-dark">{formatMoney(receipt.totalAmount)}</p>
                          <svg
                            className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="border-t border-gray-100 px-4 py-3 bg-rasoi-panel/50">
                          <table className="w-full text-sm">
                            <tbody>
                              {receipt.items.map((item) => (
                                <tr key={item.id} className="border-b border-gray-100 last:border-0">
                                  <td className="py-2 pr-3">
                                    <p className="font-medium text-gray-900">{item.normalized_name}</p>
                                    {item.brand && (
                                      <span
                                        className={`inline-block mt-1 text-[11px] font-semibold px-2 py-0.5 rounded-pill border ${
                                          CATEGORY_STYLES[item.category] ?? CATEGORY_STYLES.Other
                                        }`}
                                      >
                                        {item.brand}
                                      </span>
                                    )}
                                  </td>
                                  <td className="py-2 text-right text-gray-500 text-xs">
                                    {item.quantity} {item.unit}
                                  </td>
                                  <td className="py-2 pl-3 text-right font-medium text-gray-900">
                                    {formatMoney(item.total_price)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Brand Preferences panel */}
          <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
            <h2 className="text-sm font-bold text-gray-900 mb-1">Brand preferences</h2>
            <p className="text-xs text-gray-500 mb-4">By ingredient category</p>

            {categories.length === 0 ? (
              <p className="text-sm text-gray-500">Not enough purchase history yet.</p>
            ) : (
              <div className="space-y-3">
                {categories.map((cat) => {
                  const style = CONSISTENCY_STYLES[cat.consistency] ?? CONSISTENCY_STYLES.grey;
                  return (
                    <div key={cat.category} className={`rounded-lg border p-3 ${style.card}`}>
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-semibold text-gray-900">{cat.category}</p>
                        <span className="flex items-center gap-1.5 text-[11px] font-semibold text-gray-600">
                          <span className={`w-2 h-2 rounded-full ${style.dot}`} />
                          {style.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600">
                        Prefers <span className="font-semibold text-gray-900">{cat.preferredBrand}</span>
                        {cat.avgPrice != null && <> · avg {formatMoney(cat.avgPrice)}</>}
                      </p>
                      <p className="text-[11px] text-gray-400 mt-0.5">
                        Purchased {cat.timesPurchased} time{cat.timesPurchased !== 1 ? 's' : ''}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}

function StatTile({ label, value, capitalize }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-white/70">{label}</p>
      <p className={`text-lg font-bold text-white mt-0.5 ${capitalize ? 'capitalize' : ''}`}>{value}</p>
    </div>
  );
}
