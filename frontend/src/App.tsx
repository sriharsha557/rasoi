import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { PantryProvider } from './context/PantryContext';
import { RecipeProvider } from './context/RecipeContext';
import { GuestProvider } from './context/GuestContext';
import Navbar from './components/Navbar';
import GuestBanner from './components/GuestBanner';
import Buddy from './components/Buddy';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import PurchaseHistory from './pages/PurchaseHistory';
import ScanPage from './pages/ScanPage';
import PantryPage from './pages/PantryPage';
import MealsPage from './pages/MealsPage';
import RecipePage from './pages/RecipePage';
import PlannerPage from './pages/PlannerPage';
import CollectAndGoPage from './pages/CollectAndGoPage';

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
              <Route path="/onboarding" element={<OnboardingPage />} />
              <Route path="/history" element={<PurchaseHistory />} />
              <Route path="/scan" element={<ScanPage />} />
              <Route path="/pantry" element={<PantryPage />} />
              <Route path="/meals" element={<MealsPage />} />
              <Route path="/planner" element={<PlannerPage />} />
              <Route path="/recipe" element={<RecipePage />} />
              <Route path="/recipe/:id" element={<RecipePage />} />
              <Route path="/collect-and-go" element={<CollectAndGoPage />} />
            </Routes>
            <Buddy />
          </BrowserRouter>
        </RecipeProvider>
      </PantryProvider>
    </GuestProvider>
  );
}

export default App;
