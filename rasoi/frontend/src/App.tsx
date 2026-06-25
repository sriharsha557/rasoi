import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { PantryProvider } from './context/PantryContext';
import { RecipeProvider } from './context/RecipeContext';
import { GuestProvider } from './context/GuestContext';
import Navbar from './components/Navbar';
import GuestBanner from './components/GuestBanner';
import Chammach from './components/Chammach';
import LandingPage from './pages/LandingPage';
import ScanPage from './pages/ScanPage';
import PantryPage from './pages/PantryPage';
import MealsPage from './pages/MealsPage';
import RecipePage from './pages/RecipePage';

function App() {
  return (
    <GuestProvider>
      <PantryProvider>
        <RecipeProvider>
          <BrowserRouter>
            <Navbar />
            <GuestBanner />
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route path="/pantry" element={<PantryPage />} />
              <Route path="/meals" element={<MealsPage />} />
              <Route path="/recipe" element={<RecipePage />} />
            </Routes>
            <Chammach />
          </BrowserRouter>
        </RecipeProvider>
      </PantryProvider>
    </GuestProvider>
  );
}

export default App;
