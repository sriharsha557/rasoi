import { useNavigate } from 'react-router-dom';
import { useGuest } from '../context/GuestContext';

const features = [
  {
    icon: '📸',
    title: 'Scan & Detect',
    desc: 'Upload a fridge photo or grocery receipt. Our AI extracts every ingredient instantly.',
  },
  {
    icon: '📦',
    title: 'Live Pantry',
    desc: 'See your inventory at a glance with colour-coded expiry alerts — green, amber, red.',
  },
  {
    icon: '🍳',
    title: 'Cook Smarter',
    desc: 'Get AI-ranked meal suggestions that use what expires soonest. Zero waste, every time.',
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { isGuest, enterGuestMode } = useGuest();

  const handleGuest = () => {
    enterGuestMode();
    navigate('/scan');
  };

  return (
    <div className="flex flex-col min-h-screen bg-white">
      {/* ── Hero ── */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-24 pb-16 text-center">
        {/* Badge */}
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rasoi-light text-rasoi-dark text-xs font-semibold uppercase tracking-widest mb-6">
          🌱 Organic Intelligence
        </span>

        {/* Logo wordmark */}
        <h1 className="text-6xl sm:text-7xl font-extrabold tracking-tight text-gray-900 mb-4">
          Ras<span className="text-rasoi">OI</span>
        </h1>

        {/* Tagline */}
        <p className="text-xl sm:text-2xl font-semibold text-gray-700 max-w-lg mb-3">
          Your kitchen's organic intelligence layer.
        </p>
        <p className="text-base text-gray-500 max-w-md mb-10">
          Scan your fridge, discover zero-waste meals, and let AI handle the rest —
          one scan to cook.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={() => navigate('/scan?type=ingredient')}
            className="px-8 py-3.5 bg-rasoi hover:bg-rasoi-dark text-white font-bold text-base rounded-pill shadow-md transition-all hover:shadow-card-hover hover:-translate-y-0.5"
          >
            📷 Scan My Fridge
          </button>
          <button
            onClick={() => navigate('/scan?type=receipt')}
            className="px-8 py-3.5 bg-white hover:bg-rasoi-light text-rasoi-dark font-bold text-base rounded-pill border-2 border-rasoi transition-all hover:-translate-y-0.5"
          >
            🧾 Scan Receipt
          </button>
        </div>

        {/* Guest mode */}
        {!isGuest ? (
          <div className="mt-6 flex flex-col items-center gap-1.5">
            <div className="flex items-center gap-3 text-gray-400 text-sm">
              <span className="h-px w-12 bg-gray-200" />
              or
              <span className="h-px w-12 bg-gray-200" />
            </div>
            <button
              onClick={handleGuest}
              className="mt-1 flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-gray-600 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-pill transition-colors"
            >
              🥄 Continue as Guest
            </button>
            <p className="text-xs text-gray-400 mt-1">
              No sign-up needed — data saved locally in your browser.
            </p>
          </div>
        ) : (
          <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-rasoi-light text-rasoi-dark text-sm font-semibold">
            ✅ You're already in guest mode — <button onClick={() => navigate('/scan')} className="underline underline-offset-2">go to scan →</button>
          </div>
        )}
      </main>

      {/* ── Features ── */}
      <section className="bg-rasoi-panel border-t border-gray-100 py-14 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-2xl font-bold text-gray-800 mb-10">
            How RasOI works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="bg-white rounded-card shadow-card p-6 text-center hover:shadow-card-hover transition-shadow"
              >
                <div className="text-4xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-5 text-center text-xs text-gray-400 border-t border-gray-100">
        RasOI &nbsp;·&nbsp; Powered by Organic Intelligence &nbsp;·&nbsp; Colruyt Group India Hackathon 2025
      </footer>
    </div>
  );
}
