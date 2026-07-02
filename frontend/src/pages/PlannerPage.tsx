import { useEffect, useState } from 'react';
import apiClient from '../services/apiClient';
import type { CuisineProfile, WeeklyPlannerResponse } from '../types';

const REGION_LABELS: Record<string, string> = {
  south_indian: 'South Indian',
  bengali: 'Bengali',
  punjabi: 'Punjabi',
};

export default function PlannerPage() {
  const [region, setRegion] = useState('south_indian');
  const [householdSize, setHouseholdSize] = useState(2);
  const [profiles, setProfiles] = useState<CuisineProfile[]>([]);
  const [planner, setPlanner] = useState<WeeklyPlannerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    window.scrollTo(0, 0);
    Promise.all([
      apiClient.getCuisineProfiles(),
      apiClient.getWeeklyPlanner(region, householdSize, 7),
    ])
      .then(([profileResponse, plannerResponse]) => {
        setProfiles(profileResponse.profiles);
        setPlanner(plannerResponse);
        setError(null);
      })
      .catch(() => setError('Could not load the weekly planner. Check that the backend is running.'))
      .finally(() => setIsLoading(false));
  }, [region, householdSize]);

  const summary = planner?.nutritionalSummary.dailyAverage;
  const groceryItems = planner?.groceryList ?? [];

  return (
    <main className="min-h-screen bg-rasoi-light pt-20 pb-12 px-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <section className="bg-rasoi border border-rasoi-dark rounded-card shadow-card p-5 md:p-6 text-white">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-white/75">Weekly Meal Planner</p>
              <h1 className="text-3xl md:text-4xl font-extrabold text-white mt-1">
                Plan meals, groceries, and nutrition together
              </h1>
              <p className="text-sm text-white/80 mt-2 max-w-2xl">
                Regional menus are scaled for the household, matched against pantry items, and converted into delivery-ready grocery lists.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 min-w-full sm:min-w-[360px] lg:min-w-[420px]">
              <label className="text-sm font-semibold text-white">
                Cuisine profile
                <select
                  value={region}
                  onChange={(event) => setRegion(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-white/30 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-white/70"
                >
                  {(profiles.length ? profiles : Object.entries(REGION_LABELS).map(([id, name]) => ({ id, name, staples: [], flavor_notes: [], preferred_meals: [] }))).map((profile) => (
                    <option key={profile.id} value={profile.id}>{profile.name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-semibold text-white">
                Household servings
                <input
                  type="number"
                  min="1"
                  max="12"
                  value={householdSize}
                  onChange={(event) => setHouseholdSize(Number(event.target.value))}
                  className="mt-1 w-full rounded-lg border border-white/30 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-white/70"
                />
              </label>
            </div>
          </div>
        </section>

        {error && (
          <div className="rounded-card border border-rasoi-red bg-rasoi-red-light px-4 py-3 text-sm font-semibold text-rasoi-red">
            {error}
          </div>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-[1.5fr_0.9fr] gap-6">
          <div className="bg-white border border-gray-100 rounded-card shadow-card p-4 md:p-5">
            <div className="flex items-center justify-between gap-3 mb-4">
              <h2 className="text-xl font-extrabold text-gray-950">7-day plan</h2>
              {planner && <span className="text-xs font-bold text-rasoi bg-rasoi-light px-2.5 py-1 rounded-full">{planner.profile.name}</span>}
            </div>

            {isLoading ? (
              <div className="grid gap-3">
                {[...Array(7)].map((_, index) => (
                  <div key={index} className="h-24 rounded-card bg-gray-100 animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="grid gap-3">
                {planner?.days.map((day) => (
                  <article key={day.date} className="border border-gray-100 rounded-card p-4 hover:border-rasoi-light transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                      <div>
                        <p className="text-xs font-bold uppercase tracking-widest text-gray-400">
                          {new Date(day.date).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
                        </p>
                        <h3 className="text-lg font-extrabold text-gray-900 mt-1">{day.mealName}</h3>
                      </div>
                      <span className="text-xs font-bold text-gray-600 bg-gray-100 rounded-full px-2.5 py-1 w-fit">
                        {day.servings} servings
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="bg-rasoi-light text-rasoi-dark font-semibold rounded-full px-2.5 py-1">
                        {day.nutrition.calories} kcal
                      </span>
                      <span className="bg-gray-100 text-gray-700 font-semibold rounded-full px-2.5 py-1">
                        {day.nutrition.protein_g}g protein
                      </span>
                      <span className="bg-gray-100 text-gray-700 font-semibold rounded-full px-2.5 py-1">
                        {day.usesPantryItems.length} pantry matches
                      </span>
                      {day.missingIngredients.length > 0 && (
                        <span className="bg-rasoi-amber-light text-rasoi-amber font-semibold rounded-full px-2.5 py-1">
                          {day.missingIngredients.length} to buy
                        </span>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          <aside className="space-y-6">
            <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
              <h2 className="text-lg font-extrabold text-gray-950">Nutrition average</h2>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <Metric label="Calories" value={summary?.calories ?? 0} suffix="kcal" />
                <Metric label="Protein" value={summary?.protein_g ?? 0} suffix="g" />
                <Metric label="Carbs" value={summary?.carbs_g ?? 0} suffix="g" />
                <Metric label="Fiber" value={summary?.fiber_g ?? 0} suffix="g" />
              </div>
            </section>

            <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-extrabold text-gray-950">Grocery delivery</h2>
                <span className="text-xs font-bold text-gray-500">Blinkit / Zepto</span>
              </div>
              <div className="mt-4 space-y-2 max-h-48 overflow-auto pr-1">
                {groceryItems.length === 0 ? (
                  <p className="text-sm text-gray-500">Your pantry covers this plan.</p>
                ) : groceryItems.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-sm border-b border-gray-100 pb-2">
                    <span className="font-semibold text-gray-800 capitalize">{item.name}</span>
                    <span className="text-gray-500">{item.quantity} {item.unit}</span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {planner?.deliveryPartners.map((partner) => (
                  <a
                    key={partner.id}
                    href={partner.cartUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-center rounded-lg bg-rasoi text-white text-sm font-bold px-3 py-2 hover:bg-rasoi-dark transition-colors"
                  >
                    {partner.name}
                  </a>
                ))}
              </div>
            </section>

            <section className="bg-white border border-gray-100 rounded-card shadow-card p-5">
              <h2 className="text-lg font-extrabold text-gray-950">Household</h2>
              <div className="mt-3 space-y-2">
                {planner?.household.members.map((member) => (
                  <div key={member.id} className="rounded-lg bg-gray-50 px-3 py-2">
                    <p className="text-sm font-bold text-gray-900">{member.name}</p>
                    <p className="text-xs text-gray-500">{member.servings} serving preference</p>
                  </div>
                ))}
              </div>
            </section>
          </aside>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value, suffix }: { label: string; value: number; suffix: string }) {
  return (
    <div className="rounded-card bg-gray-50 p-3">
      <p className="text-xs font-bold uppercase tracking-wider text-gray-400">{label}</p>
      <p className="text-xl font-extrabold text-gray-950 mt-1">
        {value}<span className="text-xs font-bold text-gray-500 ml-1">{suffix}</span>
      </p>
    </div>
  );
}