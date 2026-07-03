import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

export interface DemoUser {
  id: string;
  email: string;
  displayName: string;
  cuisinePref: string[];
  servings: number;
  dietaryRestrictions: string[];
}

export const DEMO_USER: DemoUser = {
  id: '5d6b4c66-945a-414e-92e4-8fe99ca89e6a',
  email: 'raja@rasoi.app',
  displayName: 'Rasoi Raja',
  cuisinePref: ['Indian'],
  servings: 2,
  dietaryRestrictions: [],
};

interface GuestContextType {
  isGuest: boolean;
  demoUser: DemoUser | null;
  enterGuestMode: () => void;
  exitGuestMode: () => void;
}

const GuestContext = createContext<GuestContextType | undefined>(undefined);

const STORAGE_KEY = 'rasoi_guest';
const DEMO_USER_STORAGE_KEY = 'rasoi_demo_user';

export function GuestProvider({ children }: { children: ReactNode }) {
  const [isGuest, setIsGuest] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true';
    } catch {
      return false;
    }
  });
  const [demoUser, setDemoUser] = useState<DemoUser | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true' ? DEMO_USER : null;
    } catch {
      return null;
    }
  });

  const enterGuestMode = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    localStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(DEMO_USER));
    setIsGuest(true);
    setDemoUser(DEMO_USER);
  };

  const exitGuestMode = () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(DEMO_USER_STORAGE_KEY);
    setIsGuest(false);
    setDemoUser(null);
  };

  return (
    <GuestContext.Provider value={{ isGuest, demoUser, enterGuestMode, exitGuestMode }}>
      {children}
    </GuestContext.Provider>
  );
}

export function useGuest() {
  const ctx = useContext(GuestContext);
  if (!ctx) throw new Error('useGuest must be used within GuestProvider');
  return ctx;
}
