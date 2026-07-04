import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useGuest } from '../context/GuestContext';
import { usePantry } from '../context/PantryContext';
import apiClient from '../services/apiClient';
import type { PantryResponse } from '../types';

// TEMP (demo recording): always route "Get Started" through onboarding, even
// if this user already completed it, so the flow is show-able every take.
// Flip back to false to restore the normal skip-if-completed behaviour.
const ALWAYS_SHOW_ONBOARDING = true;

const DIALOGUES = [
  'Namaste! Show me your fridge!',
  "What's for dinner? Let me decide!",
  'I found 3 meals you can cook!',
  'No cream? Use milk + butter!',
  'Well cooked! Pantry updated!',
];

const STEPS = [
  { emoji: '📸', label: 'Scan your pantry', detail: 'One photo of your fridge or shelf — tell us your tastes once, at setup.' },
  { emoji: '🧠', label: 'Get tonight\'s pick', detail: 'Food Buddy matches a meal to what you already have.' },
  { emoji: '👨‍🍳', label: 'Cook & shop', detail: 'Step-by-step guidance — missing items are one tap away.' },
];

function daysAgo(isoDate: string): string {
  const then = new Date(isoDate).getTime();
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  return `${days} days ago`;
}

export default function LandingPage() {
  const navigate = useNavigate();
  const { isGuest, demoUser, enterGuestMode } = useGuest();
  const { dispatch } = usePantry();

  const [sessionPrompt, setSessionPrompt] = useState<PantryResponse | null>(null);
  const [dialogue, setDialogue] = useState(DIALOGUES[0]);
  const [speechVisible, setSpeechVisible] = useState(false);
  const [isWiggling, setIsWiggling] = useState(false);
  const [mouthOpen, setMouthOpen] = useState(true);
  const [visibleCards, setVisibleCards] = useState<boolean[]>(Array(STEPS.length).fill(false));
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const dIdxRef = useRef(0);

  const buddyTalk = () => {
    dIdxRef.current = (dIdxRef.current + 1) % DIALOGUES.length;
    setDialogue(DIALOGUES[dIdxRef.current]);
    setSpeechVisible(true);
    setIsWiggling(true);
    setTimeout(() => setIsWiggling(false), 500);
    let t = 0;
    const interval = setInterval(() => {
      t++;
      setMouthOpen(t % 2 === 0);
      if (t > 8) { clearInterval(interval); setMouthOpen(true); }
    }, 140);
    setTimeout(() => setSpeechVisible(false), 3200);
  };

  // Scroll-in cards
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          const idx = cardRefs.current.indexOf(e.target as HTMLDivElement);
          if (e.isIntersecting && idx !== -1) {
            setTimeout(() => {
              setVisibleCards((prev) => {
                const next = [...prev];
                next[idx] = true;
                return next;
              });
            }, idx * 120);
          }
        });
      },
      { threshold: 0.2 }
    );
    cardRefs.current.forEach((el) => el && obs.observe(el));
    return () => obs.disconnect();
  }, []);

  // Auto-talk after 2s
  useEffect(() => {
    const t = setTimeout(() => buddyTalk(), 2000);
    return () => clearTimeout(t);
  }, []);

  const handleGuest = async () => {
    enterGuestMode();
    if (ALWAYS_SHOW_ONBOARDING) {
      navigate('/onboarding');
      return;
    }
    try {
      const { preferences } = await apiClient.getPreferences();
      if (!preferences.onboardingCompleted) {
        navigate('/onboarding');
        return;
      }
    } catch {
      navigate('/onboarding');
      return;
    }

    // Session-based pantry: greet with "resume last scan" vs "start fresh"
    // instead of assuming a live inventory is still accurate.
    try {
      const pantry = await apiClient.getPantry();
      if (pantry.hasLastScan && pantry.items.length > 0) {
        setSessionPrompt(pantry);
        return;
      }
    } catch {
      // No session data reachable — fall through to a fresh scan
    }
    navigate('/scan');
  };

  const handleResumeSession = () => {
    if (!sessionPrompt) return;
    dispatch({ type: 'SET_ITEMS', payload: sessionPrompt.items });
    dispatch({
      type: 'SET_SESSION',
      payload: {
        hasLastScan: sessionPrompt.hasLastScan,
        scanDate: sessionPrompt.scanDate,
        scanType: sessionPrompt.scanType,
      },
    });
    setSessionPrompt(null);
    navigate('/pantry');
  };

  const handleStartFresh = () => {
    // Clear any previously scanned session so the fresh scan starts empty.
    dispatch({ type: 'SET_ITEMS', payload: [] });
    dispatch({
      type: 'SET_SESSION',
      payload: { hasLastScan: false, scanDate: null, scanType: null },
    });
    setSessionPrompt(null);
    navigate('/scan');
  };

  return (
    <div className="flex flex-col min-h-screen bg-white font-sans">

      {/* ── Keyframes ── */}
      <style>{`
        @keyframes landingOrb1 { 0%,100%{transform:translate(0,0)} 33%{transform:translate(18px,-12px)} 66%{transform:translate(-10px,8px)} }
        @keyframes landingOrb2 { 0%,100%{transform:translate(0,0)} 33%{transform:translate(-14px,10px)} 66%{transform:translate(12px,-8px)} }
        @keyframes landingOrb3 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(10px,14px)} }
        @keyframes landingPulseRing { 0%{transform:scale(1);opacity:.5} 100%{transform:scale(1.6);opacity:0} }
        @keyframes landingFadeUp { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
        @keyframes landingShimmer { 0%,100%{opacity:.4} 50%{opacity:1} }
        @keyframes landingScanLine { 0%{top:0%} 100%{top:100%} }
        @keyframes landingCardIn { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }
        @keyframes landingWiggle { 0%,100%{transform:rotate(0)} 25%{transform:rotate(-10deg)} 75%{transform:rotate(10deg)} }
        @keyframes landingBlink { 0%,90%,100%{transform:scaleY(1)} 95%{transform:scaleY(0.1)} }
        @keyframes landingFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }

        .landing-orb1 { animation: landingOrb1 8s ease-in-out infinite; }
        .landing-orb2 { animation: landingOrb2 10s ease-in-out infinite; }
        .landing-orb3 { animation: landingOrb3 12s ease-in-out infinite; }
        .landing-pulse-ring { animation: landingPulseRing 2.4s ease-out infinite; }
        .landing-shimmer { animation: landingShimmer 2s ease-in-out infinite; }
        .landing-scan-line { animation: landingScanLine 1.8s ease-in-out infinite; position:absolute; left:0; right:0; height:2px; background:#1D9E75; opacity:.7; }
        .landing-blink { animation: landingBlink 4s ease-in-out infinite; transform-origin: center; }
        .landing-blink-delay { animation: landingBlink 4s .3s ease-in-out infinite; transform-origin: center; }
        .landing-float { animation: landingFloat 3.2s ease-in-out infinite; }
        .landing-wiggle { animation: landingWiggle .5s ease-in-out; }

        .anim-a { animation: landingFadeUp .5s ease both; }
        .anim-b { animation: landingFadeUp .6s .1s ease both; }
        .anim-c { animation: landingFadeUp .6s .2s ease both; }
        .anim-d { animation: landingFadeUp .6s .3s ease both; }
        .anim-e { animation: landingFadeUp .6s .4s ease both; }
        .anim-f { animation: landingFadeUp .6s .5s ease both; }
        .anim-g { animation: landingFadeUp .7s .7s ease both; }
      `}</style>

      {/* ── Hero ── */}
      <main className="relative flex flex-col items-center justify-center px-6 pt-20 pb-6 text-center overflow-hidden">

        {/* Floating orb — single, subtle */}
        <div className="landing-orb1 absolute -top-16 -left-10 w-52 h-52 bg-rasoi-light rounded-full pointer-events-none opacity-70" />

        {/* Badge */}
        <div className="anim-a relative z-10 inline-flex items-center gap-2 bg-rasoi-light text-rasoi-dark text-xs font-semibold tracking-widest uppercase px-3 py-1.5 rounded-full mb-4">
          <span className="landing-shimmer w-1.5 h-1.5 rounded-full bg-rasoi" />
          End the daily 'what to cook' struggle
        </div>

        {/* Logo */}
        <div className="anim-b relative z-10 mb-2">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900" style={{ letterSpacing: '-1px', lineHeight: 1 }}>
            Food<span className="text-rasoi">Buddy</span>
          </h1>
        </div>

        {/* Hook — a specific value proposition, not a vague question */}
        <p className="anim-c relative z-10 text-2xl sm:text-3xl font-bold text-gray-900 mb-2 max-w-md leading-tight">
          Know tonight's dinner before you open the fridge.
        </p>
        {/* Problem → Solution */}
        <p className="anim-d relative z-10 text-sm text-gray-600 max-w-sm leading-relaxed mb-1">
          You have food. You have no plan. You waste both.
        </p>
        <p className="anim-d relative z-10 text-base text-gray-800 font-semibold max-w-sm leading-relaxed mb-6">
          Show us your pantry. We'll tell you what to cook.
        </p>

        {/* CTA */}
        <div className="anim-e relative z-10 flex flex-col items-center gap-2 mb-6">
          {!isGuest ? (
            <>
              <button
                onClick={handleGuest}
                className="flex items-center gap-2 px-7 py-3.5 bg-rasoi hover:bg-rasoi-dark text-white font-bold text-base rounded-pill shadow-md transition-all hover:scale-[1.03] active:scale-[.97]"
              >
                <CameraIcon /> Get Started — Show me your pantry
              </button>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Quick one-time setup: tastes, diet, budget — then just scan and cook.
              </p>
            </>
          ) : (
            <button
              onClick={handleGuest}
              className="inline-flex items-center gap-1.5 px-6 py-3 bg-rasoi-light text-rasoi-dark font-bold text-sm rounded-pill"
            >
              ✅ {demoUser?.displayName ?? 'Captain Cook'}: Continue →
            </button>
          )}
        </div>

        {/* Buddy — one support element: the animated mascot + its speech bubble */}
        <div
          className="anim-g landing-float relative z-10 cursor-pointer select-none flex flex-col items-center"
          onClick={buddyTalk}
        >
          {/* Speech bubble */}
          <div
            className="absolute -top-14 left-1/2 -translate-x-1/2 whitespace-nowrap bg-white border border-gray-200 shadow-card rounded-card px-3 py-2 text-xs text-gray-800 font-medium transition-opacity duration-300"
            style={{ opacity: speechVisible ? 1 : 0, pointerEvents: 'none' }}
          >
            {dialogue}
            <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-200" />
          </div>

          {/* Animated spoon */}
          <BuddySpoon wiggling={isWiggling} mouthOpen={mouthOpen} />
        </div>
      </main>

      {/* ── How it works ── */}
      <section className="bg-rasoi-panel py-8 px-6">
        <p className="text-center text-lg font-semibold text-gray-800 mb-5">How Food Buddy works</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
          {STEPS.map((step, idx) => (
            <FeatureCard
              key={step.label}
              visible={visibleCards[idx]}
              cardRef={(el) => { cardRefs.current[idx] = el; }}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="w-6 h-6 shrink-0 rounded-full bg-rasoi text-white text-xs font-bold flex items-center justify-center">
                  {idx + 1}
                </span>
                <div className="w-10 h-10 rounded-xl bg-rasoi-light flex items-center justify-center text-xl">
                  {step.emoji}
                </div>
              </div>
              <p className="font-semibold text-base text-gray-900 mb-1">{step.label}</p>
              <p className="text-[13px] text-gray-600 leading-snug">{step.detail}</p>
            </FeatureCard>
          ))}
        </div>
      </section>

      {/* ── Magic ── */}
      <section className="bg-rasoi py-10 px-6 text-center">
        <div className="max-w-xl mx-auto">
          <p className="text-3xl mb-3">🥄✨</p>
          <p className="text-white text-base sm:text-lg font-semibold leading-relaxed">
            Buddy knows what you've cooked, what's available, what you need —
            and just tells you what to make tonight.
          </p>
        </div>
      </section>

      {/* ── Close ── */}
      <section className="py-14 px-6 text-center border-b border-gray-100">
        <p className="text-lg sm:text-xl font-medium text-gray-500 max-w-xl mx-auto leading-snug">
          This is not a recipe app.
        </p>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900 max-w-xl mx-auto leading-snug mt-1">
          This is the end of the daily kitchen dilemma.
        </p>
      </section>

      {/* ── Footer ── */}
      <footer className="py-5 text-center text-[11px] text-gray-500 border-t border-gray-100">
        Food Buddy &nbsp;·&nbsp; End the daily 'what to cook' struggle &nbsp;·&nbsp; Colruyt Group India Hackathon 2025
      </footer>

      {/* ── Welcome back / start fresh prompt ── */}
      {sessionPrompt && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-card shadow-2xl p-6 w-full max-w-sm text-center animate-bounce-in">
            <div className="text-4xl mb-3">🥄</div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">Welcome back!</h3>
            <p className="text-sm text-gray-500 mb-5">
              Your last scan was {daysAgo(sessionPrompt.scanDate ?? '')} with {sessionPrompt.items.length} item{sessionPrompt.items.length !== 1 ? 's' : ''}.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={handleResumeSession}
                className="w-full py-2.5 bg-rasoi hover:bg-rasoi-dark text-white font-semibold text-sm rounded-pill transition-colors"
              >
                Continue from last scan
              </button>
              <button
                onClick={handleStartFresh}
                className="w-full py-2.5 border border-gray-200 hover:bg-gray-50 text-gray-600 font-semibold text-sm rounded-pill transition-colors"
              >
                Start a fresh scan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ─────────────────────────────────────────────── */

function FeatureCard({
  visible,
  cardRef,
  children,
}: {
  visible: boolean;
  cardRef: (el: HTMLDivElement | null) => void;
  children: React.ReactNode;
}) {
  return (
    <div
      ref={cardRef}
      className="bg-white border border-gray-100 rounded-card p-4 text-left hover:-translate-y-1 transition-all"
      style={{
        opacity: 0,
        ...(visible ? { animation: 'landingCardIn .5s ease forwards' } : {}),
      }}
    >
      {children}
    </div>
  );
}

function BuddySpoon({ wiggling, mouthOpen }: { wiggling: boolean; mouthOpen: boolean }) {
  return (
    <svg
      width="64"
      height="130"
      viewBox="0 0 64 130"
      fill="none"
      className={wiggling ? 'landing-wiggle' : ''}
      style={{ filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.15))' }}
    >
      {/* Bowl */}
      <ellipse cx="32" cy="28" rx="22" ry="24" fill="#1D9E75" />
      <ellipse cx="32" cy="28" rx="16" ry="17" fill="#5DCAA5" />
      {/* Handle */}
      <rect x="28" y="50" width="8" height="70" rx="4" fill="#1D9E75" />
      <rect x="30" y="50" width="5" height="70" rx="3" fill="#0F6E56" opacity=".35" />
      {/* Left eye */}
      <g className="landing-blink">
        <ellipse cx="22" cy="22" rx="4" ry="5" fill="white" opacity=".9" />
        <circle cx="23" cy="23" r="2.5" fill="#04342C" />
        <circle cx="23.8" cy="22.2" r=".8" fill="white" />
      </g>
      {/* Right eye */}
      <g className="landing-blink-delay">
        <ellipse cx="42" cy="22" rx="4" ry="5" fill="white" opacity=".9" />
        <circle cx="43" cy="23" r="2.5" fill="#04342C" />
        <circle cx="43.8" cy="22.2" r=".8" fill="white" />
      </g>
      {/* Mouth */}
      <ellipse cx="32" cy="37" rx="7" ry={mouthOpen ? 4 : 1.5} fill="#04342C" />
      <ellipse cx="32" cy="36.5" rx="5" ry={mouthOpen ? 2.5 : 1} fill="#5DCAA5" />
      {/* Highlights */}
      <ellipse cx="18" cy="26" rx="3" ry="4" fill="#9FE1CB" opacity=".5" />
      <ellipse cx="46" cy="26" rx="3" ry="4" fill="#9FE1CB" opacity=".5" />
      <ellipse cx="22" cy="32" rx="3.5" ry="2" fill="#E8836A" opacity=".45" />
      <ellipse cx="42" cy="32" rx="3.5" ry="2" fill="#E8836A" opacity=".45" />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  );
}

