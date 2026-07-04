import { Link, useLocation } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';

export default function Navbar() {
  const { pathname } = useLocation();
  const { state } = usePantry();

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
          {/* Primary destinations */}
          <div className="flex items-center gap-1 sm:gap-2">
            <NavLink to="/pantry" current={pathname}>
              🥦 Pantry
              <span className="ml-1.5 bg-white text-[#1D9E75] text-xs font-bold px-1.5 py-0.5 rounded-full">
                {state.pantryItems.length}
              </span>
            </NavLink>
            <NavLink to="/meals" current={pathname}>🍽 Meals</NavLink>
            <NavLink to="/planner" current={pathname}>📅 Planner</NavLink>
          </div>

          <span className="hidden sm:block w-px h-6 bg-gray-200" />

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

function NavLink({
  to,
  current,
  children,
}: {
  to: string;
  current: string;
  children: React.ReactNode;
}) {
  const isActive = current === to;
  return (
    <Link
      to={to}
      className={`px-3 py-1.5 rounded-pill bg-[#1D9E75] hover:bg-[#16795A] text-white text-sm font-semibold transition-colors flex items-center ${
        isActive
          ? 'shadow-sm ring-2 ring-[#1D9E75]/20'
          : ''
      }`}
    >
      {children}
    </Link>
  );
}
