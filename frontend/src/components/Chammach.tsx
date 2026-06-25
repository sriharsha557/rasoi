import { useState, useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';
import { useRecipe } from '../context/RecipeContext';
import { useGuest } from '../context/GuestContext';

interface Msg { text: string; emoji: string }

const DIALOGUE: Record<string, Msg> = {
  '/':        { text: 'Hey! Scan your fridge to get started!', emoji: '👋' },
  '/scan':    { text: "Upload a photo and I'll figure out what you have!", emoji: '📸' },
  '/meals':   { text: 'Expiring items come first — zero waste, full plates!', emoji: '🍽️' },
};

function getDialogue(
  pathname: string,
  expiringCount: number,
  pantryCount: number,
  recipeName: string | null,
  isGuest: boolean
): Msg {
  if (pathname === '/') {
    return isGuest
      ? { text: 'Welcome back, guest! Ready to scan?', emoji: '👋' }
      : DIALOGUE['/'];
  }
  if (pathname === '/scan') return DIALOGUE['/scan'];
  if (pathname === '/pantry') {
    if (pantryCount === 0) return { text: "Your pantry is empty. Let's scan something!", emoji: '🛒' };
    if (expiringCount > 0)
      return { text: `${expiringCount} item${expiringCount > 1 ? 's' : ''} expiring soon — let me find a recipe!`, emoji: '⚠️' };
    return { text: 'Your pantry looks great! Want to see what you can cook?', emoji: '😊' };
  }
  if (pathname === '/meals') return DIALOGUE['/meals'];
  if (pathname === '/recipe') {
    if (recipeName) return { text: `Let's cook ${recipeName}! Tap each step when done.`, emoji: '👨‍🍳' };
    return { text: "Follow the steps and I'll keep you on track!", emoji: '✅' };
  }
  return { text: "I'm here if you need me!", emoji: '🥄' };
}

export default function Chammach() {
  const { pathname } = useLocation();
  const { state: pantryState } = usePantry();
  const { state: recipeState } = useRecipe();
  const { isGuest } = useGuest();

  const expiringCount = pantryState.pantryItems.filter(i => i.isExpiring || i.isExpired).length;
  const msg = getDialogue(pathname, expiringCount, pantryState.pantryItems.length, recipeState.currentRecipe?.name ?? null, isGuest);

  const [visible, setVisible] = useState(true);
  const [wiggling, setWiggling] = useState(false);
  const [msgKey, setMsgKey] = useState(0);

  useEffect(() => {
    setVisible(true);
    setMsgKey(k => k + 1);
  }, [pathname, expiringCount]);

  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(() => {
      setWiggling(true);
      setVisible(true);
      setTimeout(() => setWiggling(false), 700);
    }, 10000);
    return () => clearTimeout(t);
  }, [msgKey, visible]);

  const toggle = useCallback(() => setVisible(v => !v), []);

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-2 select-none" role="complementary" aria-label="Chammach assistant">
      {visible && (
        <div key={msgKey} className="animate-fade-in relative max-w-[230px] bg-white border border-gray-200 shadow-card rounded-card px-3.5 py-2.5 text-sm text-gray-800 font-medium leading-snug">
          <span className="mr-1">{msg.emoji}</span>
          {msg.text}
          <div className="absolute -bottom-[7px] right-9 w-3 h-3 bg-white border-r border-b border-gray-200 rotate-45" />
        </div>
      )}
      <button onClick={toggle} title={visible ? 'Dismiss' : 'Show hint'} aria-label="Chammach talking spoon" className={`focus:outline-none cursor-pointer ${wiggling ? 'animate-wiggle' : ''}`}>
        <SpoonSVG />
      </button>
    </div>
  );
}

function SpoonSVG() {
  return (
    <svg width="56" height="130" viewBox="0 0 56 130" fill="none" xmlns="http://www.w3.org/2000/svg" className="drop-shadow-md hover:scale-110 transition-transform">
      <rect x="23" y="58" width="10" height="68" rx="5" fill="#1D9E75" />
      <path d="M 18 52 Q 28 60 38 52" fill="#1D9E75" />
      <ellipse cx="28" cy="30" rx="22" ry="26" fill="#1D9E75" />
      <ellipse cx="21" cy="20" rx="6" ry="8" fill="rgba(255,255,255,0.18)" />
      <circle cx="20" cy="28" r="5" fill="white" />
      <circle cx="36" cy="28" r="5" fill="white" />
      <circle cx="21" cy="29" r="2.5" fill="#111827" />
      <circle cx="37" cy="29" r="2.5" fill="#111827" />
      <circle cx="22" cy="27" r="1" fill="white" />
      <circle cx="38" cy="27" r="1" fill="white" />
      <path d="M 19 38 Q 28 46 37 38" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <ellipse cx="14" cy="36" rx="4" ry="3" fill="rgba(255,120,120,0.25)" />
      <ellipse cx="42" cy="36" rx="4" ry="3" fill="rgba(255,120,120,0.25)" />
    </svg>
  );
}
