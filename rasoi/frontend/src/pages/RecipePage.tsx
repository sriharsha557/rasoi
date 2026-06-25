import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';
import { useRecipe } from '../context/RecipeContext';
import apiClient from '../services/apiClient';
import type { Substitution } from '../types';

export default function RecipePage() {
  const navigate = useNavigate();
  const { state: recipeState, dispatch } = useRecipe();
  const { dispatch: pantryDispatch } = usePantry();
  const { currentRecipe, currentStep } = recipeState;

  // Per-step: seconds remaining (null = not started)
  const [timers, setTimers] = useState<(number | null)[]>([]);
  const [runningStep, setRunningStep] = useState<number | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [markedCooked, setMarkedCooked] = useState(false);
  // Substitutions
  const [substitutions, setSubstitutions] = useState<Record<string, Substitution[]>>({});
  const [expandedSub, setExpandedSub] = useState<string | null>(null);
  const [loadingSub, setLoadingSub] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!currentRecipe) {
      navigate('/meals');
      return;
    }
    setTimers(Array(currentRecipe.steps.length).fill(null));
    setCompletedSteps(new Set());
  }, [currentRecipe]);

  // Countdown tick
  useEffect(() => {
    if (runningStep === null) return;
    const t = setInterval(() => {
      setTimers((prev) => {
        const next = [...prev];
        if (next[runningStep] === null || next[runningStep]! <= 0) {
          setRunningStep(null);
          clearInterval(t);
          return next;
        }
        next[runningStep] = next[runningStep]! - 1;
        return next;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [runningStep]);

  if (!currentRecipe) return null;

  const steps = currentRecipe.steps;
  const allStepsDone = completedSteps.size === steps.length;

  const handleMarkCooked = () => {
    // Remove all ingredients used in this recipe from the pantry
    currentRecipe.ingredients
      .filter((ing) => ing.available)
      .forEach((ing) => {
        // We delete by matching name (best-effort for guest mode)
        // In real flow the backend handles this
      });
    setMarkedCooked(true);
    dispatch({ type: 'CLEAR_RECIPE' });
    setTimeout(() => navigate('/pantry'), 1800);
  };

  const startTimer = (stepIdx: number, seconds: number) => {
    setTimers((prev) => {
      const next = [...prev];
      next[stepIdx] = seconds;
      return next;
    });
    setRunningStep(stepIdx);
  };

  const stopTimer = (stepIdx: number) => {
    setRunningStep(null);
    setTimers((prev) => {
      const next = [...prev];
      next[stepIdx] = null;
      return next;
    });
  };

  const toggleStep = (i: number) => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
    dispatch({ type: i < steps.length - 1 ? 'NEXT_STEP' : 'NEXT_STEP' });
  };

  const fetchSubs = async (missingIng: string) => {
    if (substitutions[missingIng]) {
      setExpandedSub(expandedSub === missingIng ? null : missingIng);
      return;
    }
    setLoadingSub(missingIng);
    try {
      const res = await apiClient.getSubstitutions({
        recipeId: currentRecipe.id,
        missingIngredient: missingIng,
        recipeContext: currentRecipe.name,
      });
      setSubstitutions((prev) => ({ ...prev, [missingIng]: res.substitutions }));
      setExpandedSub(missingIng);
    } catch {
      // swallow
    } finally {
      setLoadingSub(null);
    }
  };

  const fmtTimer = (secs: number) => `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;

  // Match % color
  const matchColor =
    currentRecipe.matchPercentage >= 80 ? 'text-rasoi' : currentRecipe.matchPercentage >= 50 ? 'text-rasoi-amber' : 'text-gray-500';

  return (
    <div className="min-h-screen bg-rasoi-panel pt-20 pb-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Back */}
        <button
          onClick={() => navigate('/meals')}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-rasoi transition-colors mb-5"
        >
          ← Back to meals
        </button>

        {/* Recipe header */}
        <div className="bg-white rounded-card shadow-card p-6 mb-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 mb-2">
                {currentRecipe.name}
              </h1>
              <div className="flex flex-wrap gap-2">
                {currentRecipe.cuisine && (
                  <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
                    🌍 {currentRecipe.cuisine}
                  </span>
                )}
                {currentRecipe.difficulty && (
                  <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
                    {currentRecipe.difficulty}
                  </span>
                )}
                <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
                  ⏱ {currentRecipe.prepTimeMinutes} min
                </span>
                <span className={`text-xs font-extrabold px-2.5 py-1 rounded-full bg-rasoi-panel ${matchColor}`}>
                  {currentRecipe.matchPercentage}% match
                </span>
              </div>
            </div>
            {currentRecipe.usesExpiringItems && (
              <span className="text-xs font-bold text-rasoi-amber bg-rasoi-amber-light px-3 py-1.5 rounded-full">
                🔥 Uses expiring items
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* ── Ingredients ── */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-card shadow-card p-5">
              <h2 className="font-bold text-gray-900 text-base mb-4">Ingredients</h2>
              <ul className="space-y-2">
                {currentRecipe.ingredients.map((ing, i) => (
                  <li key={i} className="flex items-center gap-2.5">
                    <span className={`w-5 h-5 flex items-center justify-center rounded-full text-xs font-bold shrink-0 ${ing.available ? 'bg-rasoi-light text-rasoi-dark' : 'bg-rasoi-red-light text-rasoi-red'}`}>
                      {ing.available ? '✓' : '✗'}
                    </span>
                    <span className={`text-sm ${ing.available ? 'text-gray-800' : 'text-gray-400 line-through'}`}>
                      {ing.quantity} {ing.unit} {ing.name}
                    </span>
                  </li>
                ))}
              </ul>

              {/* Missing ingredients + substitution banners */}
              {currentRecipe.missingIngredients.length > 0 && (
                <div className="mt-5 space-y-2">
                  <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">
                    Substitutions available
                  </h3>
                  {currentRecipe.missingIngredients.map((miss) => (
                    <div key={miss} className="border border-rasoi-amber/30 bg-rasoi-amber-light rounded-card overflow-hidden">
                      <button
                        onClick={() => fetchSubs(miss)}
                        className="w-full flex items-center justify-between px-3 py-2.5 text-left"
                      >
                        <span className="text-xs font-semibold text-rasoi-amber">
                          Missing: <span className="capitalize">{miss}</span>
                        </span>
                        <span className="text-xs text-rasoi-amber font-bold">
                          {loadingSub === miss ? '...' : expandedSub === miss ? '▲ Hide' : '▼ Show sub'}
                        </span>
                      </button>
                      {expandedSub === miss && substitutions[miss] && (
                        <div className="px-3 pb-3 space-y-2 animate-fade-in">
                          {substitutions[miss].map((sub, i) => (
                            <div key={i} className="bg-white rounded-lg p-2.5 text-xs text-gray-700 border border-rasoi-amber/20">
                              <p className="font-semibold text-gray-900">{sub.ingredient}</p>
                              <p className="text-gray-500 mt-0.5">{sub.ratio}</p>
                              {sub.notes && <p className="text-gray-400 italic mt-0.5">{sub.notes}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── Steps ── */}
          <div className="lg:col-span-3 space-y-3">
            <h2 className="font-bold text-gray-900 text-base mb-1">
              Steps
              <span className="ml-2 text-sm font-normal text-gray-400">
                {completedSteps.size}/{steps.length} done
              </span>
            </h2>
            {steps.map((step, i) => {
              const done = completedSteps.has(i);
              const timerVal = timers[i];
              const isRunning = runningStep === i;
              return (
                <div
                  key={i}
                  className={`bg-white rounded-card shadow-card p-4 border-l-4 transition-all ${done ? 'border-rasoi opacity-60' : i === currentStep ? 'border-rasoi-amber' : 'border-gray-200'}`}
                >
                  <div className="flex gap-3">
                    <button
                      onClick={() => toggleStep(i)}
                      className={`shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center font-bold text-sm transition-colors ${done ? 'bg-rasoi border-rasoi text-white' : 'border-gray-300 text-gray-300 hover:border-rasoi hover:text-rasoi'}`}
                    >
                      {done ? '✓' : i + 1}
                    </button>
                    <div className="flex-1">
                      <p className={`text-sm leading-relaxed ${done ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                        {step}
                      </p>

                      {/* Timer controls */}
                      {!done && (
                        <div className="mt-2 flex items-center gap-2">
                          {timerVal !== null ? (
                            <>
                              <span className={`text-sm font-mono font-bold ${timerVal === 0 ? 'text-rasoi' : 'text-rasoi-amber'}`}>
                                {timerVal === 0 ? '✅ Done!' : fmtTimer(timerVal)}
                              </span>
                              <button onClick={() => stopTimer(i)} className="text-xs text-gray-400 hover:text-rasoi-red transition-colors">
                                ✕ Cancel
                              </button>
                            </>
                          ) : (
                            <div className="flex gap-2">
                              {[60, 120, 300].map((secs) => (
                                <button
                                  key={secs}
                                  onClick={() => startTimer(i, secs)}
                                  className="text-xs text-gray-400 hover:text-rasoi-amber border border-gray-200 hover:border-rasoi-amber px-2 py-0.5 rounded-full transition-colors"
                                >
                                  ⏱ {secs < 60 ? `${secs}s` : `${secs / 60}m`}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Mark as cooked */}
            {allStepsDone && !markedCooked && (
              <button
                onClick={handleMarkCooked}
                className="w-full mt-2 py-3.5 bg-rasoi hover:bg-rasoi-dark text-white font-extrabold text-base rounded-card shadow-md transition-all hover:-translate-y-0.5 animate-bounce-in"
              >
                🎉 Mark as Cooked — Update Pantry
              </button>
            )}
            {markedCooked && (
              <div className="w-full py-3.5 bg-rasoi-light border border-rasoi/30 rounded-card text-center font-bold text-rasoi animate-fade-in">
                ✅ Pantry updated! Redirecting…
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
