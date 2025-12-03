/**
 * Theme Store
 *
 * Manages light/dark/system theme preferences with localStorage persistence.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'light' | 'dark' | 'system';
export type EffectiveTheme = 'light' | 'dark';

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  getEffectiveTheme: () => EffectiveTheme;
}

/**
 * Get system color scheme preference
 */
function getSystemTheme(): EffectiveTheme {
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'dark'; // Default to dark if can't detect
}

/**
 * Apply theme class to document root
 */
export function applyTheme(theme: EffectiveTheme) {
  if (typeof document !== 'undefined') {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      mode: 'dark', // Default to dark

      setMode: (mode: ThemeMode) => {
        set({ mode });
        const effectiveTheme = mode === 'system' ? getSystemTheme() : mode;
        applyTheme(effectiveTheme);
      },

      getEffectiveTheme: () => {
        const { mode } = get();
        return mode === 'system' ? getSystemTheme() : mode;
      },
    }),
    {
      name: 'massgen-theme',
      onRehydrateStorage: () => (state) => {
        // Apply theme on initial load
        if (state) {
          const effectiveTheme = state.mode === 'system' ? getSystemTheme() : state.mode;
          applyTheme(effectiveTheme);
        }
      },
    }
  )
);

// Listen for system theme changes
if (typeof window !== 'undefined' && window.matchMedia) {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const { mode, getEffectiveTheme } = useThemeStore.getState();
    if (mode === 'system') {
      applyTheme(getEffectiveTheme());
    }
  });
}

// Selectors
export const selectThemeMode = (state: ThemeState) => state.mode;
export const selectSetThemeMode = (state: ThemeState) => state.setMode;
