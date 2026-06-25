import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

interface GuestContextType {
  isGuest: boolean;
  enterGuestMode: () => void;
  exitGuestMode: () => void;
}

const GuestContext = createContext<GuestContextType | undefined>(undefined);

const STORAGE_KEY = 'rasoi_guest';

export function GuestProvider({ children }: { children: ReactNode }) {
  const [isGuest, setIsGuest] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });

  const enterGuestMode = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsGuest(true);
  };

  const exitGuestMode = () => {
    localStorage.removeItem(STORAGE_KEY);
    setIsGuest(false);
  };

  return (
    <GuestContext.Provider value={{ isGuest, enterGuestMode, exitGuestMode }}>
      {children}
    </GuestContext.Provider>
  );
}

export function useGuest() {
  const ctx = useContext(GuestContext);
  if (!ctx) throw new Error('useGuest must be used within GuestProvider');
  return ctx;
}
