import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';
import { useRecipe } from '../context/RecipeContext';
import apiClient from '../services/apiClient';
import type { Recipe } from '../types';

export default function MealsPage() {
  const navigate = useNavigate();
  const { state: pantryState } = usePantry();
  const { state: recipeState, dispatch } = useRecipe();
  const [prioritizeExpiry, setPrioritizeExpiry] = useState(true);

  const { recipes, isLoading } = recipeState;

  useEffect(() => {
    window.scrollTo(0, 0);
    fetchRecipes(prioritizeExpiry);
  }, []);

  const fetchRecipes = (expFirst: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    apiClient
      .getRecipes(expFirst, 6)
      .then((res) => dispatch({ type: 'SET_RECIPES', payload: res.recipes }))
      .catch(() => dispatch({ type: 'SET_LOADING', payload: false }));
  };

  const handleToggle = () => {
    const next = !prioritizeExpiry;
    setPrioritizeExpiry(next);
    fetchRecipes(next);
  };

  const handleSelectRecipe = (recipe: Recipe) => {
    dispatch({ type: 'SELECT_RECIPE', payload: recipe });
    navigate('/recipe');
  };

  const expiringCount = pantryState.pantryItems.filter(
    (i) => i.isExpiring || i.isExpired
  ).length;

  return (
    <div className="min-h-screen bg-rasoi-panel pt-20 pb-10 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900">What Can I Cook?</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Based on {pantryState.pantryItems.length} items in your pantry
              {expiringCount > 0 && (
                <span className="ml-2 text-rasoi-amber font-semibold">
                  · {expiringCount} expiring soon
                </span>
              )}
            </p>
          </div>
          {/* Expiry-first toggle */}
          <label className="flex items-center gap-2.5 cursor-pointer select-none">
            <span className="text-sm font-semibold text-gray-700">🔥 Expiry-first</span>
            <div
              onClick={handleToggle}
              className={`relative w-11 h-6 rounded-full transition-colors ${prioritizeExpiry ? 'bg-rasoi' : 'bg-gray-300'}`}
            >
              <div className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all ${prioritizeExpiry ? 'left-5' : 'left-0.5'}`} />
            </div>
          </label>
        </div>

        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white rounded-card shadow-card p-5 animate-pulse">
                <div className="h-5 bg-gray-200 rounded mb-3 w-3/4" />
                <div className="h-3 bg-gray-100 rounded mb-2 w-1/2" />
                <div className="h-3 bg-gray-100 rounded mb-4 w-1/3" />
                <div className="h-8 bg-gray-100 rounded-pill mt-4" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && recipes.length === 0 && (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🍽️</div>
            <h3 className="text-xl font-bold text-gray-700 mb-2">No recipes found</h3>
            <p className="text-gray-400 mb-6">Add more items to your pantry to unlock meal ideas.</p>
            <button
              onClick={() => navigate('/pantry')}
              className="px-6 py-2.5 bg-rasoi text-white font-semibold rounded-pill hover:bg-rasoi-dark transition-colors"
            >
              Back to Pantry
            </button>
          </div>
        )}

        {/* Recipe cards */}
        {!isLoading && recipes.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 animate-fade-in">
            {recipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} onSelect={() => handleSelectRecipe(recipe)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RecipeCard({ recipe, onSelect }: { recipe: Recipe; onSelect: () => void }) {
  const matchColor =
    recipe.matchPercentage >= 80
      ? 'bg-rasoi text-white'
      : recipe.matchPercentage >= 50
      ? 'bg-rasoi-amber text-white'
      : 'bg-gray-200 text-gray-700';

  return (
    <div className="bg-white rounded-card shadow-card hover:shadow-card-hover transition-all hover:-translate-y-0.5 p-5 flex flex-col gap-3">
      {/* Top row: expiry badge + match % */}
      <div className="flex items-center justify-between">
        {recipe.usesExpiringItems ? (
          <span className="text-xs font-bold text-rasoi-amber bg-rasoi-amber-light px-2 py-0.5 rounded-full">
            🔥 Uses expiring items
          </span>
        ) : (
          <span />
        )}
        <span className={`text-xs font-extrabold px-2.5 py-1 rounded-full ${matchColor}`}>
          {recipe.matchPercentage}% match
        </span>
      </div>

      {/* Name */}
      <h3 className="text-lg font-extrabold text-gray-900 leading-tight">{recipe.name}</h3>

      {/* Meta pills */}
      <div className="flex flex-wrap gap-1.5">
        {recipe.cuisine && (
          <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
            🌍 {recipe.cuisine}
          </span>
        )}
        {recipe.difficulty && (
          <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
            {recipe.difficulty === 'Easy' ? '🟢' : recipe.difficulty === 'Medium' ? '🟡' : '🔴'} {recipe.difficulty}
          </span>
        )}
        <span className="text-xs bg-rasoi-panel text-gray-600 px-2.5 py-1 rounded-full font-medium">
          ⏱ {recipe.prepTimeMinutes} min
        </span>
      </div>

      {/* Ingredient availability dots */}
      <div className="flex flex-wrap gap-1">
        {recipe.ingredients.slice(0, 8).map((ing, i) => (
          <span
            key={i}
            title={ing.name}
            className={`w-2.5 h-2.5 rounded-full ${ing.available ? 'bg-rasoi' : 'bg-gray-300'}`}
          />
        ))}
        {recipe.ingredients.length > 8 && (
          <span className="text-xs text-gray-400">+{recipe.ingredients.length - 8}</span>
        )}
      </div>

      {/* Missing ingredients note */}
      {recipe.missingIngredients.length > 0 && (
        <p className="text-xs text-gray-400 italic">
          Missing: {recipe.missingIngredients.slice(0, 3).join(', ')}
          {recipe.missingIngredients.length > 3 && ` +${recipe.missingIngredients.length - 3} more`}
        </p>
      )}

      <button
        onClick={onSelect}
        className="mt-auto w-full py-2.5 bg-rasoi hover:bg-rasoi-dark text-white font-bold text-sm rounded-pill transition-colors"
      >
        View Recipe →
      </button>
    </div>
  );
}
