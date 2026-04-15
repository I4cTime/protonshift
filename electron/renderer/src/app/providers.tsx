"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Provider as JotaiProvider, useAtomValue, useSetAtom } from "jotai";
import { useState, useEffect, type ReactNode } from "react";
import { ToastProvider } from "@heroui/react";
import { themeAtom, THEMES, getStoredTheme } from "@/lib/theme";
import { SplashScreen } from "@/components/splash-screen";

function ThemeSync() {
  const themeId = useAtomValue(themeAtom);
  const setTheme = useSetAtom(themeAtom);

  useEffect(() => {
    const stored = getStoredTheme();
    if (stored !== themeId) setTheme(stored);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const meta = THEMES[themeId];
    const el = document.documentElement;
    el.setAttribute("data-theme", themeId);
    el.style.colorScheme = meta.colorScheme;
    el.classList.remove("dark", "light");
    el.classList.add(meta.colorScheme);
  }, [themeId]);

  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 2,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <JotaiProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeSync />
        <SplashScreen />
        {children}
        <ToastProvider placement="top end" maxVisibleToasts={4} />
      </QueryClientProvider>
    </JotaiProvider>
  );
}
