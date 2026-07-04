import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/apiClient';
import type { BmiCategory, BudgetPeriod, DietType } from '../types';

const CUISINE_OPTIONS = [
  'Belgian',
  'French',
  'Italian',
  'Mediterranean',
  'Asian',
  'Indian',
  'Mexican',
  'Middle Eastern',
  'American',
  'Vegetarian',
];

const DIET_OPTIONS: { value: DietType; label: string; emoji: string }[] = [
  { value: 'vegetarian', label: 'Vegetarian', emoji: '🥦' },
  { value: 'non_vegetarian', label: 'Non-Vegetarian', emoji: '🍗' },
  { value: 'eggetarian', label: 'Eggetarian', emoji: '🥚' },
  { value: 'vegan', label: 'Vegan', emoji: '🌱' },
];

const BMI_STYLES: Record<BmiCategory, { label: string; className: string }> = {
  underweight: { label: 'Underweight', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  normal: { label: 'Normal', className: 'bg-rasoi-light text-rasoi-dark border-rasoi/30' },
  overweight: { label: 'Overweight', className: 'bg-rasoi-amber-light text-rasoi-amber border-rasoi-amber/30' },
  obese: { label: 'Obese', className: 'bg-rasoi-red-light text-rasoi-red border-rasoi-red/30' },
};

function computeBmi(heightCm: string, weightKg: string): { bmi: number; category: BmiCategory } | null {
  const height = parseFloat(heightCm);
  const weight = parseFloat(weightKg);
  if (!height || !weight || height <= 0 || weight <= 0) return null;
  const heightM = height / 100;
  const bmi = Math.round((weight / (heightM * heightM)) * 10) / 10;
  const category: BmiCategory = bmi < 18.5 ? 'underweight' : bmi < 25 ? 'normal' : bmi < 30 ? 'overweight' : 'obese';
  return { bmi, category };
}

export default function OnboardingPage() {
  const navigate = useNavigate();

  const [cuisines, setCuisines] = useState<string[]>([]);
  const [dietType, setDietType] = useState<DietType>('vegetarian');
  const [heightCm, setHeightCm] = useState('');
  const [weightKg, setWeightKg] = useState('');
  const [familySize, setFamilySize] = useState(2);
  const [budgetAmount, setBudgetAmount] = useState('');
  const [budgetPeriod, setBudgetPeriod] = useState<BudgetPeriod>('monthly');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    apiClient
      .getPreferences()
      .then(({ preferences }) => {
        if (!preferences.onboardingCompleted) return;
        setCuisines(preferences.cuisines);
        setDietType(preferences.dietType);
        setHeightCm(preferences.heightCm != null ? String(preferences.heightCm) : '');
        setWeightKg(preferences.weightKg != null ? String(preferences.weightKg) : '');
        setFamilySize(preferences.familySize || 2);
        setBudgetAmount(preferences.budgetAmount != null ? String(preferences.budgetAmount) : '');
        setBudgetPeriod(preferences.budgetPeriod);
      })
      .catch(() => setError('Could not load saved preferences — starting fresh.'))
      .finally(() => setIsLoading(false));
  }, []);

  const bmiResult = useMemo(() => computeBmi(heightCm, weightKg), [heightCm, weightKg]);

  const toggleCuisine = (cuisine: string) => {
    setCuisines((prev) =>
      prev.includes(cuisine) ? prev.filter((c) => c !== cuisine) : [...prev, cuisine]
    );
  };

  const isValid =
    cuisines.length > 0 &&
    Number(heightCm) > 0 &&
    Number(weightKg) > 0 &&
    familySize >= 1 &&
    Number(budgetAmount) >= 0 &&
    budgetAmount !== '';

  const handleSave = async () => {
    if (!isValid) {
      setError('Please fill in every field before saving.');
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await apiClient.savePreferences({
        cuisines,
        dietType,
        heightCm: Number(heightCm),
        weightKg: Number(weightKg),
        familySize,
        budgetAmount: Number(budgetAmount),
        budgetPeriod,
      });
      navigate('/scan');
    } catch {
      setError('Could not save your preferences. Check that the backend is running.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <main className="min-h-screen bg-rasoi-panel pt-24 pb-12 px-4 flex items-center justify-center">
        <p className="text-sm text-gray-500">Loading your profile…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-rasoi-panel pt-20 pb-16 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Hero */}
        <section className="bg-rasoi border border-rasoi-dark rounded-card shadow-card p-6 text-white">
          <p className="text-xs font-bold uppercase tracking-widest text-white/75">Welcome, Captain Cook 🥄</p>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white mt-1">
            Let's set up your kitchen profile
          </h1>
          <p className="text-sm text-white/80 mt-2">
            A few quick details so Buddy can tailor meals, portions, and grocery budgets to you.
          </p>
        </section>

        {error && (
          <div className="bg-rasoi-red-light border border-rasoi-red/30 text-rasoi-red text-sm rounded-card px-4 py-3">
            {error}
          </div>
        )}

        {/* Cuisines */}
        <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-1">Which cuisines do you enjoy?</h2>
          <p className="text-xs text-gray-500 mb-3">Pick as many as you like.</p>
          <div className="flex flex-wrap gap-2">
            {CUISINE_OPTIONS.map((cuisine) => {
              const active = cuisines.includes(cuisine);
              return (
                <button
                  key={cuisine}
                  type="button"
                  onClick={() => toggleCuisine(cuisine)}
                  className={`px-3.5 py-1.5 rounded-pill text-sm font-medium border transition-colors ${
                    active
                      ? 'bg-rasoi text-white border-rasoi'
                      : 'bg-white text-gray-600 border-gray-200 hover:border-rasoi/50'
                  }`}
                >
                  {cuisine}
                </button>
              );
            })}
          </div>
        </section>

        {/* Diet type */}
        <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3">Dietary preference</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {DIET_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setDietType(option.value)}
                className={`flex flex-col items-center gap-1 px-3 py-3 rounded-card text-xs font-semibold border transition-colors ${
                  dietType === option.value
                    ? 'bg-rasoi-light text-rasoi-dark border-rasoi'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-rasoi/50'
                }`}
              >
                <span className="text-lg">{option.emoji}</span>
                {option.label}
              </button>
            ))}
          </div>
        </section>

        {/* Body profile */}
        <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3">Body profile</h2>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm font-medium text-gray-700">
              Height (cm)
              <input
                type="number"
                min="0"
                max="300"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                placeholder="170"
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-rasoi/40"
              />
            </label>
            <label className="text-sm font-medium text-gray-700">
              Weight (kg)
              <input
                type="number"
                min="0"
                max="400"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                placeholder="65"
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-rasoi/40"
              />
            </label>
          </div>
          {bmiResult && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs text-gray-500">Your BMI:</span>
              <span className="text-sm font-bold text-gray-900">{bmiResult.bmi}</span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-pill border ${BMI_STYLES[bmiResult.category].className}`}
              >
                {BMI_STYLES[bmiResult.category].label}
              </span>
            </div>
          )}
        </section>

        {/* Family size */}
        <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3">Family size</h2>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => setFamilySize((n) => Math.max(1, n - 1))}
              className="w-9 h-9 rounded-full bg-rasoi-light text-rasoi-dark font-bold text-lg flex items-center justify-center hover:bg-rasoi/20"
            >
              −
            </button>
            <span className="text-xl font-bold text-gray-900 w-8 text-center">{familySize}</span>
            <button
              type="button"
              onClick={() => setFamilySize((n) => Math.min(20, n + 1))}
              className="w-9 h-9 rounded-full bg-rasoi-light text-rasoi-dark font-bold text-lg flex items-center justify-center hover:bg-rasoi/20"
            >
              +
            </button>
            <span className="text-xs text-gray-500">people eating at home</span>
          </div>
        </section>

        {/* Budget */}
        <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3">Pantry budget</h2>
          <div className="flex gap-3">
            <label className="flex-1 text-sm font-medium text-gray-700">
              Amount (€)
              <input
                type="number"
                min="0"
                value={budgetAmount}
                onChange={(e) => setBudgetAmount(e.target.value)}
                placeholder="150"
                className="mt-1 w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-rasoi/40"
              />
            </label>
            <div className="flex-1">
              <span className="text-sm font-medium text-gray-700">Period</span>
              <div className="mt-1 flex rounded-lg border border-gray-200 overflow-hidden">
                {(['weekly', 'monthly'] as BudgetPeriod[]).map((period) => (
                  <button
                    key={period}
                    type="button"
                    onClick={() => setBudgetPeriod(period)}
                    className={`flex-1 py-2 text-sm font-semibold capitalize transition-colors ${
                      budgetPeriod === period
                        ? 'bg-rasoi text-white'
                        : 'bg-white text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {period}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Save */}
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="w-full py-3 bg-rasoi hover:bg-rasoi-dark disabled:opacity-60 text-white font-semibold text-sm rounded-pill shadow-md transition-all"
        >
          {isSaving ? 'Saving…' : 'Save & continue to my kitchen →'}
        </button>
      </div>
    </main>
  );
}
