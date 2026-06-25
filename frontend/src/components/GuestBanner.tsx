import { useGuest } from '../context/GuestContext';

export default function GuestBanner() {
  const { isGuest, exitGuestMode } = useGuest();

  if (!isGuest) return null;

  return (
    <div className="fixed top-14 left-0 right-0 z-40 bg-rasoi-amber-light border-b border-rasoi-amber/30 px-4 py-2">
      <div className="max-w-6xl mx-auto flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-lg">🥄</span>
          <span className="text-gray-700">
            You're browsing as a <span className="font-bold text-rasoi-amber">Guest</span>
            <span className="hidden sm:inline text-gray-500"> — your pantry is saved locally in this browser.</span>
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="hidden sm:inline text-xs text-gray-500 italic">Sign up to sync across devices</span>
          <button
            onClick={exitGuestMode}
            className="text-xs font-semibold text-rasoi-amber hover:text-rasoi-dark underline underline-offset-2 transition-colors"
          >
            Exit guest
          </button>
        </div>
      </div>
    </div>
  );
}
