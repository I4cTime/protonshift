import { atom } from "jotai";

export const THEME_IDS = [
  "quantum-void",
  "molten-core",
  "frost-glass",
  "solar-bloom",
] as const;

export type ThemeId = (typeof THEME_IDS)[number];

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  colorScheme: "dark" | "light";
  accent: string;
  secondary: string;
  surface: string;
}

export const THEMES: Record<ThemeId, ThemeMeta> = {
  "quantum-void": {
    id: "quantum-void",
    label: "Quantum Void",
    colorScheme: "dark",
    accent: "#00D1FF",
    secondary: "#B266FF",
    surface: "#0f0f14",
  },
  "molten-core": {
    id: "molten-core",
    label: "Molten Core",
    colorScheme: "dark",
    accent: "#FF6B35",
    secondary: "#FFB800",
    surface: "#0d0806",
  },
  "frost-glass": {
    id: "frost-glass",
    label: "Frost Glass",
    colorScheme: "light",
    accent: "#0066FF",
    secondary: "#6C5CE7",
    surface: "#f0f4f8",
  },
  "solar-bloom": {
    id: "solar-bloom",
    label: "Solar Bloom",
    colorScheme: "light",
    accent: "#16A34A",
    secondary: "#EA580C",
    surface: "#faf5ee",
  },
};

const DEFAULT_THEME: ThemeId = "quantum-void";

const baseThemeAtom = atom<ThemeId>(DEFAULT_THEME);

export const themeAtom = atom(
  (get) => get(baseThemeAtom),
  (_get, set, next: ThemeId) => {
    set(baseThemeAtom, next);
    if (typeof window !== "undefined") {
      localStorage.setItem("gsh-theme", next);
    }
  },
);

/**
 * Call once in a top-level client component's useEffect to hydrate the
 * persisted theme without causing an SSR/client mismatch.
 */
export function getStoredTheme(): ThemeId {
  if (typeof window === "undefined") return DEFAULT_THEME;
  const stored = localStorage.getItem("gsh-theme");
  if (stored && THEME_IDS.includes(stored as ThemeId)) return stored as ThemeId;
  return DEFAULT_THEME;
}

export const themeMetaAtom = atom((get) => THEMES[get(themeAtom)]);
