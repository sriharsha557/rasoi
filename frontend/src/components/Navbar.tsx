import { Link, useLocation } from 'react-router-dom';
import { usePantry } from '../context/PantryContext';

export default function Navbar() {
  const { pathname } = useLocation();
  const { state } = usePantry();
  const hasItems = state.pantryItems.length > 0;

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
          {hasItems && (
            <>
              <NavLink to="/pantry" current={pathname}>
                🥦 Pantry
                <span className="ml-1.5 bg-rasoi text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                  {state.pantryItems.length}
                </span>
              </NavLink>
              <NavLink to="/meals" current={pathname}>
                🍽 Meals
              </NavLink>
            </>
          )}
          <Link
            to="/scan"
            className="ml-2 px-4 py-1.5 bg-rasoi hover:bg-rasoi-dark text-white text-sm font-semibold rounded-pill transition-colors"
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
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center ${
        isActive
          ? 'bg-rasoi-light text-rasoi-dark'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
      }`}
    >
      {children}
    </Link>
  );
}
