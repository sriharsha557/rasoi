import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-100 shadow-sm h-14">
      <div className="max-w-6xl mx-auto px-4 h-full flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group shrink-0">
          <span className="text-2xl font-extrabold tracking-tight text-gray-900 group-hover:text-rasoi transition-colors">
            Food<span className="text-rasoi">Buddy</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          {/* Utilities — visually lighter, secondary weight */}
          <div className="hidden sm:flex items-center gap-1">
            <Link
              to="/history"
              className={`px-3 py-1.5 rounded-pill text-sm font-medium transition-colors flex items-center gap-1 ${
                pathname === '/history'
                  ? 'bg-rasoi-light text-rasoi-dark'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              🧾 History
            </Link>
            <Link
              to="/onboarding"
              title="Profile & preferences"
              className="w-9 h-9 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
            >
              ⚙️
            </Link>
          </div>

          {/* Primary action — deliberately distinct from nav destinations */}
          <Link
            to="/scan"
            className="px-4 py-1.5 bg-rasoi hover:bg-rasoi-dark text-white text-sm font-bold rounded-pill shadow-md transition-all hover:-translate-y-px flex items-center"
          >
            + Scan
          </Link>
        </div>
      </div>
    </nav>
  );
}
