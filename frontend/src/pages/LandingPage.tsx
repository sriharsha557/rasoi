import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useGuest } from '../context/GuestContext';

const DIALOGUES = [
  'Namaste! Show me your fridge!',
  'Your paneer expires tomorrow!',
  'I found 3 meals you can cook!',
  'No cream? Use milk + butter!',
  'Well cooked! Pantry updated!',
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { isGuest, enterGuestMode } = useGuest();

  const [dialogue, setDialogue] = useState(DIALOGUES[0]);
  const [speechVisible, setSpeechVisible] = useState(false);
  const [isWiggling, setIsWiggling] = useState(false);
  const [mouthOpen, setMouthOpen] = useState(true);
  const [visibleCards, setVisibleCards] = useState<boolean[]>([false, false, false]);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const dIdxRef = useRef(0);

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
    const t = setTimeout(() => chammachTalk(), 2000);
    return () => clearTimeout(t);
  }, []);

  const chammachTalk = () => {
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

  const triggerScan = (type: string) => {
    setDialogue('Show me what you have!');
    setSpeechVisible(true);
    setIsWiggling(true);
    setTimeout(() => { setIsWiggling(false); setSpeechVisible(false); }, 2400);
    navigate('/scan?type=' + type);
  };

  const handleGuest = () => { enterGuestMode(); navigate('/scan'); };

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
      <main className="relative flex flex-col items-center justify-center px-6 pt-28 pb-10 text-center overflow-hidden">

        {/* Floating orbs */}
        <div className="landing-orb1 absolute -top-16 -left-10 w-52 h-52 bg-rasoi-light rounded-full pointer-events-none" />
        <div className="landing-orb2 absolute top-5 -right-8 w-40 h-40 bg-rasoi-light rounded-full pointer-events-none" />
        <div className="landing-orb3 absolute bottom-0 left-1/3 w-28 h-28 rounded-full pointer-events-none" style={{ background: '#f0faf5' }} />

        {/* Badge */}
        <div className="anim-a relative z-10 inline-flex items-center gap-2 bg-rasoi-light text-rasoi-dark text-xs font-semibold tracking-widest uppercase px-3 py-1.5 rounded-full mb-5">
          <span className="landing-shimmer w-1.5 h-1.5 rounded-full bg-rasoi" />
          Organic Intelligence
        </div>

        {/* Logo */}
        <div className="anim-b relative z-10 mb-3">
          <h1 className="text-6xl sm:text-7xl font-bold text-gray-900" style={{ letterSpacing: '-2px', lineHeight: 1 }}>
            Ras
            <span className="text-rasoi relative inline-block">
              OI
              <span className="landing-pulse-ring absolute rounded-md border-2 border-rasoi" style={{ inset: '-4px' }} />
            </span>
          </h1>
        </div>

        {/* Tagline */}
        <p className="anim-c relative z-10 text-xl sm:text-2xl font-semibold text-gray-800 mb-2">
          Your kitchen's organic intelligence layer.
        </p>
        <p className="anim-d relative z-10 text-sm text-gray-500 max-w-sm leading-relaxed mb-7">
          Scan your fridge, discover zero-waste meals, and let AI handle the rest — one scan to cook.
        </p>

        {/* CTA row */}
        <div className="anim-e relative z-10 flex flex-col sm:flex-row gap-2.5 justify-center mb-4">
          <button
            onClick={() => triggerScan('ingredient')}
            className="flex items-center gap-2 px-6 py-3 bg-rasoi hover:bg-rasoi-dark text-white font-semibold text-sm rounded-pill shadow-md transition-all hover:scale-[1.03] active:scale-[.97]"
          >
            <CameraIcon /> Scan my fridge
          </button>
          <button
            onClick={() => triggerScan('receipt')}
            className="flex items-center gap-2 px-6 py-3 border border-gray-200 hover:bg-gray-50 text-gray-800 font-semibold text-sm rounded-pill transition-all hover:scale-[1.03]"
          >
            <ReceiptIcon /> Scan receipt
          </button>
        </div>

        {/* Guest / OR */}
        <div className="anim-f relative z-10">
          <div className="flex items-center gap-3 justify-center mb-3">
            <span className="h-px w-12 bg-gray-200" />
            <span className="text-xs text-gray-400">or</span>
            <span className="h-px w-12 bg-gray-200" />
          </div>
          {!isGuest ? (
            <>
              <button
                onClick={handleGuest}
                className="inline-flex items-center gap-2 px-5 py-2 border border-gray-200 hover:bg-gray-50 text-gray-600 text-sm font-medium rounded-pill transition-colors"
              >
                🥄 Continue as Guest
              </button>
              <p className="text-[11px] text-gray-400 mt-1.5">
                No sign-up needed — data saved <span className="text-rasoi">locally</span> in your browser.
              </p>
            </>
          ) : (
            <button
              onClick={() => navigate('/scan')}
              className="inline-flex items-center gap-1.5 px-5 py-2 bg-rasoi-light text-rasoi-dark text-sm font-semibold rounded-pill"
            >
              ✅ Go to scan →
            </button>
          )}
        </div>

        {/* Chammach */}
        <div
          className="anim-g landing-float relative z-10 mt-6 cursor-pointer select-none flex flex-col items-center"
          onClick={chammachTalk}
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
          <ChammachSpoon wiggling={isWiggling} mouthOpen={mouthOpen} />

          {/* Introduction tag */}
          <div className="mt-3 bg-white border border-rasoi/20 rounded-card shadow-card px-4 py-2.5 text-center max-w-[220px] mx-auto">
            <p className="text-xs font-semibold text-rasoi leading-snug">Hi, I'm Chammach! 🥄</p>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">
              Your kitchen assistant — I'll guide you through every step.
            </p>
          </div>
        </div>
      </main>

      {/* ── How it works ── */}
      <section className="bg-rasoi-panel border-t border-gray-100 py-12 px-6">
        <p className="text-center text-xl font-semibold text-gray-800 mb-8">How RasOI works</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto">

          {/* Card 1 — scan bar */}
          <FeatureCard visible={visibleCards[0]} cardRef={(el) => { cardRefs.current[0] = el; }}>
            <div className="w-11 h-11 rounded-xl bg-rasoi-light flex items-center justify-center mx-auto mb-3">
              <div className="relative w-8 h-8 rounded-lg bg-white overflow-hidden">
                <div className="landing-scan-line" />
              </div>
            </div>
            <p className="font-semibold text-sm text-gray-900 mb-1">Scan & detect</p>
            <p className="text-xs text-gray-500 leading-relaxed">
              Upload a fridge photo or grocery receipt. Our <span className="text-rasoi font-medium">AI</span> extracts every ingredient instantly.
            </p>
          </FeatureCard>

          {/* Card 2 — expiry dots */}
          <FeatureCard visible={visibleCards[1]} cardRef={(el) => { cardRefs.current[1] = el; }}>
            <div className="w-11 h-11 rounded-xl bg-rasoi-light flex items-center justify-center mx-auto mb-3">
              <GridIcon />
            </div>
            <p className="font-semibold text-sm text-gray-900 mb-1">Live pantry</p>
            <p className="text-xs text-gray-500 leading-relaxed mb-2">
              See your inventory at a glance with colour-coded expiry alerts —
            </p>
            <div className="flex gap-1.5 justify-center">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#27ae60' }} />
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#e67e22' }} />
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#c0392b' }} />
            </div>
          </FeatureCard>

          {/* Card 3 */}
          <FeatureCard visible={visibleCards[2]} cardRef={(el) => { cardRefs.current[2] = el; }}>
            <div className="w-11 h-11 rounded-xl bg-rasoi-light flex items-center justify-center mx-auto mb-3">
              <ChefHatIcon />
            </div>
            <p className="font-semibold text-sm text-gray-900 mb-1">Cook smarter</p>
            <p className="text-xs text-gray-500 leading-relaxed">
              Get <span className="text-rasoi font-medium">AI-ranked</span> meal suggestions that use what expires soonest. Zero waste, every time.
            </p>
          </FeatureCard>

        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-5 text-center text-[11px] text-gray-400 border-t border-gray-100">
        RasOI &nbsp;·&nbsp; Powered by Organic Intelligence &nbsp;·&nbsp; Colruyt Group India Hackathon 2025
      </footer>
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
      className="bg-white border border-gray-100 rounded-card p-6 text-center hover:-translate-y-1 transition-all"
      style={{
        opacity: 0,
        ...(visible ? { animation: 'landingCardIn .5s ease forwards' } : {}),
      }}
    >
      {children}
    </div>
  );
}

function ChammachSpoon({ wiggling, mouthOpen }: { wiggling: boolean; mouthOpen: boolean }) {
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

function ReceiptIcon() {
  return (
    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M14 2H6a2 2 0 00-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 00-2-2z" />
      <line x1="16" y1="8" x2="8" y2="8" />
      <line x1="16" y1="12" x2="8" y2="12" />
      <line x1="10" y1="16" x2="8" y2="16" />
    </svg>
  );
}

function GridIcon() {
  return (
    <svg width="22" height="22" fill="none" stroke="#1D9E75" strokeWidth="2" viewBox="0 0 24 24">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

function ChefHatIcon() {
  return (
    <svg width="22" height="22" fill="none" stroke="#1D9E75" strokeWidth="2" viewBox="0 0 24 24">
      <path d="M6 13.87A4 4 0 017.41 6a5.11 5.11 0 0114 1.08 4 4 0 012 3.42 3.84 3.84 0 01-2.4 3.5" />
      <rect x="6" y="17" width="12" height="4" rx="1" />
      <line x1="6" y1="13" x2="18" y2="13" />
    </svg>
  );
}
