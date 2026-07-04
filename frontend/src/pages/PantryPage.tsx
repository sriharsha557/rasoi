import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';
import apiClient from '../services/apiClient';
import type { PantryItem } from '../types';

const EMPTY_FORM: Omit<PantryItem, 'id' | 'confidence'> = {
  name: '',
  quantity: 1,
  unit: '',
  acquisitionDate: new Date().toISOString().slice(0, 10),
  expirationDate: '',
};

function daysAgo(isoDate: string | null): string {
  if (!isoDate) return '';
  const then = new Date(isoDate).getTime();
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

export default function PantryPage() {
  const navigate = useNavigate();
  const { state, dispatch } = usePantry();
  const { pantryItems, isLoading, error, hasLastScan, scanDate } = state;

  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Load the session pantry (last scan) on mount, unless already in context
  useEffect(() => {
    window.scrollTo(0, 0);
    if (pantryItems.length === 0) {
      dispatch({ type: 'SET_LOADING', payload: true });
      apiClient
        .getPantry()
        .then((res) => {
          dispatch({ type: 'SET_ITEMS', payload: res.items });
          dispatch({
            type: 'SET_SESSION',
            payload: { hasLastScan: res.hasLastScan, scanDate: res.scanDate, scanType: res.scanType },
          });
        })
        .catch(() => dispatch({ type: 'SET_LOADING', payload: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);

  const handleDelete = async (id: string) => {
    dispatch({ type: 'DELETE_ITEM', payload: id });
    setDeleteConfirmId(null);
    try {
      await apiClient.deletePantryItem(id);
    } catch {
      // Optimistic delete – already removed from UI
    }
  };

  const handleEdit = (item: PantryItem) => {
    setEditingId(item.id);
    setFormData({
      name: item.name,
      quantity: item.quantity,
      unit: item.unit,
      acquisitionDate: item.acquisitionDate.slice(0, 10),
      expirationDate: item.expirationDate.slice(0, 10),
    });
  };

  const handleSaveEdit = async () => {
    if (!editingId) return;
    dispatch({
      type: 'UPDATE_ITEM',
      payload: { id: editingId, updates: { quantity: formData.quantity } },
    });
    setEditingId(null);
    try {
      await apiClient.updatePantryItem(editingId, { quantity: formData.quantity });
    } catch {
      // Optimistic update applied already
    }
  };

  const handleAddItem = async () => {
    if (!formData.name.trim()) return;
    setShowAddForm(false);
    setFormData(EMPTY_FORM);
    try {
      const res = await apiClient.addPantryItem({
        name: formData.name,
        quantity: formData.quantity,
        unit: formData.unit,
      });
      dispatch({ type: 'ADD_ITEMS', payload: [res.item] });
      dispatch({ type: 'SET_SESSION', payload: { hasLastScan: true, scanDate: new Date().toISOString(), scanType: 'manual' } });
    } catch {
      // Optimistic fallback — show the item locally if the API call fails
      dispatch({
        type: 'ADD_ITEMS',
        payload: [{ id: `local-${Date.now()}`, ...formData }],
      });
    }
  };

  return (
    <div className="min-h-screen bg-rasoi-panel pt-20 pb-28 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900">
              Your Pantry
              <span className="ml-2 text-lg font-semibold text-gray-400">
                ({pantryItems.length} items)
              </span>
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {hasLastScan && scanDate
                ? `From your scan ${daysAgo(scanDate)} — not a live inventory.`
                : 'Scan your fridge to get started.'}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/scan')}
              className="px-4 py-2 text-sm font-semibold border-2 border-rasoi text-rasoi rounded-pill hover:bg-rasoi-light transition-colors"
            >
              {hasLastScan ? '🔄 Start Fresh Scan' : '+ Scan Now'}
            </button>
            <button
              onClick={() => { setShowAddForm(true); setFormData(EMPTY_FORM); }}
              className="px-4 py-2 text-sm font-semibold bg-rasoi text-white rounded-pill hover:bg-rasoi-dark transition-colors"
            >
              + Add Item
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-rasoi-red-light border border-rasoi-red/30 rounded-card text-sm text-rasoi-red font-medium">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white rounded-card shadow-card p-4 animate-pulse h-28" />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && pantryItems.length === 0 && (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🥦</div>
            <h3 className="text-xl font-bold text-gray-700 mb-2">No items yet</h3>
            <p className="text-gray-400 mb-6">
              Scan your fridge or add items manually to get started.
            </p>
            <button
              onClick={() => navigate('/scan')}
              className="px-6 py-2.5 bg-rasoi text-white font-semibold rounded-pill hover:bg-rasoi-dark transition-colors"
            >
              📷 Scan Now
            </button>
          </div>
        )}

        {/* Items grid */}
        {!isLoading && pantryItems.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {pantryItems.map((item) =>
              editingId === item.id ? (
                <EditCard
                  key={item.id}
                  formData={formData}
                  setFormData={setFormData}
                  onSave={handleSaveEdit}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <ItemCard
                  key={item.id}
                  item={item}
                  confirmDelete={deleteConfirmId === item.id}
                  onEdit={() => handleEdit(item)}
                  onDeleteRequest={() => setDeleteConfirmId(item.id)}
                  onDeleteConfirm={() => handleDelete(item.id)}
                  onDeleteCancel={() => setDeleteConfirmId(null)}
                />
              )
            )}
          </div>
        )}

        {/* Add Item modal */}
        {showAddForm && (
          <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4" onClick={() => setShowAddForm(false)}>
            <div className="bg-white rounded-card shadow-2xl p-6 w-full max-w-sm animate-bounce-in" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-lg font-bold text-gray-900 mb-4">Add Ingredient</h3>
              <AddForm formData={formData} setFormData={setFormData} onAdd={handleAddItem} onCancel={() => setShowAddForm(false)} />
            </div>
          </div>
        )}
      </div>

      {/* Sticky CTA */}
      {pantryItems.length > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-30 bg-white border-t border-gray-200 px-4 py-3">
          <div className="max-w-5xl mx-auto flex items-center justify-between gap-3">
            <p className="text-sm text-gray-600">
              {pantryItems.length} ingredient{pantryItems.length !== 1 ? 's' : ''} ready to cook with
            </p>
            <button
              onClick={() => navigate('/meals')}
              className="px-5 py-2.5 bg-rasoi hover:bg-rasoi-dark text-white font-bold text-sm rounded-pill shadow-md transition-all hover:-translate-y-0.5"
            >
              What Can I Cook? →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────── */

function ItemCard({
  item, confirmDelete,
  onEdit, onDeleteRequest, onDeleteConfirm, onDeleteCancel,
}: {
  item: PantryItem;
  confirmDelete: boolean;
  onEdit: () => void;
  onDeleteRequest: () => void;
  onDeleteConfirm: () => void;
  onDeleteCancel: () => void;
}) {
  return (
    <div className="bg-white rounded-card shadow-card border-l-4 border-rasoi bg-rasoi-light/30 p-4 flex flex-col gap-2 hover:shadow-card-hover transition-shadow">
      <div className="flex items-start justify-between gap-1">
        <h3 className="font-bold text-gray-900 text-sm leading-tight capitalize">{item.name}</h3>
        <div className="flex gap-1 shrink-0">
          <button onClick={onEdit} title="Edit" className="text-gray-400 hover:text-rasoi transition-colors text-xs p-1">✏️</button>
          <button onClick={onDeleteRequest} title="Delete" className="text-gray-400 hover:text-rasoi-red transition-colors text-xs p-1">🗑️</button>
        </div>
      </div>
      <p className="text-sm text-gray-600 font-medium">
        {item.quantity} {item.unit}
      </p>

      {confirmDelete && (
        <div className="mt-1 border-t pt-2">
          <p className="text-xs text-gray-600 mb-2">Remove this item?</p>
          <div className="flex gap-2">
            <button onClick={onDeleteConfirm} className="flex-1 text-xs bg-rasoi-red text-white rounded-pill py-1 font-semibold hover:opacity-90">Yes</button>
            <button onClick={onDeleteCancel} className="flex-1 text-xs bg-gray-100 text-gray-700 rounded-pill py-1 font-semibold hover:bg-gray-200">No</button>
          </div>
        </div>
      )}
    </div>
  );
}

function EditCard({
  formData, setFormData, onSave, onCancel,
}: {
  formData: typeof EMPTY_FORM;
  setFormData: (d: typeof EMPTY_FORM) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="bg-white rounded-card shadow-card border-2 border-rasoi p-4 flex flex-col gap-2">
      <label className="text-xs text-gray-500">Quantity</label>
      <input
        className="border rounded-lg px-2 py-1 text-sm w-full"
        placeholder="Quantity"
        type="number"
        min={0}
        value={formData.quantity}
        onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) })}
      />
      <div className="flex gap-2 mt-1">
        <button onClick={onSave} className="flex-1 text-xs bg-rasoi text-white rounded-pill py-1.5 font-semibold hover:bg-rasoi-dark">Save</button>
        <button onClick={onCancel} className="flex-1 text-xs bg-gray-100 text-gray-700 rounded-pill py-1.5 font-semibold hover:bg-gray-200">Cancel</button>
      </div>
    </div>
  );
}

function AddForm({
  formData, setFormData, onAdd, onCancel,
}: {
  formData: typeof EMPTY_FORM;
  setFormData: (d: typeof EMPTY_FORM) => void;
  onAdd: () => void;
  onCancel: () => void;
}) {
  const inputCls = 'border border-gray-200 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-rasoi/30 focus:border-rasoi';
  return (
    <div className="flex flex-col gap-3">
      <div>
        <label className="text-xs font-semibold text-gray-600 mb-1 block">Ingredient name *</label>
        <input className={inputCls} placeholder="e.g. Tomato" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
      </div>
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-xs font-semibold text-gray-600 mb-1 block">Quantity</label>
          <input className={inputCls} type="number" min={0} value={formData.quantity} onChange={(e) => setFormData({ ...formData, quantity: parseFloat(e.target.value) })} />
        </div>
        <div className="flex-1">
          <label className="text-xs font-semibold text-gray-600 mb-1 block">Unit</label>
          <input className={inputCls} placeholder="g / ml / pcs" value={formData.unit} onChange={(e) => setFormData({ ...formData, unit: e.target.value })} />
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          disabled={!formData.name.trim()}
          onClick={onAdd}
          className="flex-1 py-2 bg-rasoi text-white font-bold text-sm rounded-pill hover:bg-rasoi-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Add to Pantry
        </button>
        <button onClick={onCancel} className="px-4 py-2 bg-gray-100 text-gray-700 font-semibold text-sm rounded-pill hover:bg-gray-200 transition-colors">
          Cancel
        </button>
      </div>
    </div>
  );
}
