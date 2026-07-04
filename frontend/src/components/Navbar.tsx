import { Link, useLocation } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';

export default function Navbar() {
  const { pathname } = useLocation();
  const { state } = usePantry();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-100 shadow-sm h-14">
      <div className="max-w-6xl mx-auto px-4 h-full flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <span className="text-2xl font-extrabold tracking-tight text-gray-900 group-hover:text-rasoi transition-colors">
            Ras<span className="text-rasoi">OI</span>
          </span>
          <span className="hidden sm:inline-block text-[10px] font-semibold uppercase tracking-widest text-gray-400 mt-0.5">
            Organic Intelligence
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1 sm:gap-2">
          <NavLink to="/pantry" current={pathname}>
            🥦 Pantry
            <span className="ml-1.5 bg-white text-[#1D9E75] text-xs font-bold px-1.5 py-0.5 rounded-full">
              {state.pantryItems.length}
            </span>
          </NavLink>
          <NavLink to="/meals" current={pathname}>
            🍽 Meals
          </NavLink>
          <NavLink to="/history" current={pathname}>
            🧾 History
          </NavLink>
          <Link
            to="/planner"
            className="px-4 py-1.5 bg-[#1D9E75] hover:bg-[#16795A] text-white text-sm font-semibold rounded-pill transition-colors flex items-center"
          >
            📅 Planner
          </Link>
          <Link
            to="/scan"
            className="ml-2 px-4 py-1.5 bg-[#1D9E75] hover:bg-[#16795A] text-white text-sm font-semibold rounded-pill transition-colors"
          >
            + Scan
          </Link>
          <Link
            to="/onboarding"
            title="Profile & preferences"
            className="ml-1 w-9 h-9 flex items-center justify-center rounded-full border border-gray-200 hover:bg-gray-50 transition-colors"
          >
            ⚙️
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
