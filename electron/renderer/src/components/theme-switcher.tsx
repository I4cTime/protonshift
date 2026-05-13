"use client";

import { useAtom } from "jotai";
import { motion } from "motion/react";
import { Palette, Sun, Moon } from "lucide-react";
import { Button } from "@heroui/react";
import { HoverCard } from "@heroui-pro/react";
import { themeAtom, THEMES, THEME_IDS } from "@/lib/theme";

export function ThemeSwitcher() {
  const [themeId, setThemeId] = useAtom(themeAtom);

  const activeTheme = THEMES[themeId];

  return (
    <HoverCard openDelay={120} closeDelay={200}>
      <HoverCard.Trigger>
        <Button
          isIconOnly
          size="sm"
          variant="ghost"
          aria-label="Switch theme"
          className="app-region-no-drag relative size-9 rounded-lg border border-border bg-surface-deep/80 text-foreground hover:border-neon-cyan/50 hover:bg-surface-secondary"
        >
          <Palette className="size-4" aria-hidden />
          <span
            className="pointer-events-none absolute bottom-1 right-1 size-1.5 rounded-full ring-1 ring-background"
            style={{ backgroundColor: activeTheme.accent }}
            aria-hidden
          />
        </Button>
      </HoverCard.Trigger>
      <HoverCard.Content placement="bottom" className="w-72 p-3" offset={8}>
        <HoverCard.Arrow />
        <div className="grid grid-cols-2 gap-2">
          {THEME_IDS.map((id) => {
            const t = THEMES[id];
            const ModeIcon = t.colorScheme === "light" ? Sun : Moon;
            const active = id === themeId;
            return (
              <Button
                key={id}
                type="button"
                variant="ghost"
                aria-pressed={active}
                aria-label={`Switch to ${t.label} theme`}
                onPress={() => setThemeId(id)}
                className={`relative flex h-auto min-h-[5.75rem] w-full flex-col items-stretch gap-0 overflow-hidden rounded-xl border p-0 transition-colors ${
                  active ? "border-neon-cyan/60 shadow-glow-sm" : "border-border hover:border-neon-cyan/30"
                }`}
                style={{ backgroundColor: t.surface }}
              >
                <div className="flex flex-col gap-1.5 p-2.5 text-left">
                  <div className="flex items-center justify-between">
                    <span className="flex gap-0.5">
                      <span
                        className="size-2 shrink-0 rounded-full ring-1 ring-white/25"
                        style={{ backgroundColor: t.accent }}
                        aria-hidden
                      />
                      <span
                        className="size-2 shrink-0 rounded-full ring-1 ring-white/25"
                        style={{ backgroundColor: t.secondary }}
                        aria-hidden
                      />
                      <span className="size-2 shrink-0 rounded-full bg-white/25 ring-1 ring-white/20" aria-hidden />
                    </span>
                    <ModeIcon className="size-3 shrink-0" style={{ color: t.accent }} aria-hidden />
                  </div>
                  <div
                    className="h-1.5 w-full rounded-full"
                    style={{ backgroundColor: t.accent, opacity: 0.85 }}
                    aria-hidden
                  />
                  <div className="flex gap-1" aria-hidden>
                    <span className="h-2.5 flex-1 rounded-full bg-white/10" />
                    <span
                      className="h-2.5 w-6 shrink-0 rounded-full"
                      style={{ backgroundColor: t.secondary, opacity: 0.7 }}
                    />
                  </div>
                  <span
                    className="mt-0.5 text-left text-[11px] font-semibold tracking-wide"
                    style={{
                      color: t.colorScheme === "light" ? "rgba(15,23,42,0.88)" : "rgba(255,255,255,0.92)",
                    }}
                  >
                    {t.label}
                  </span>
                </div>
                {active && (
                  <motion.span
                    layoutId="theme-active-frame"
                    className="pointer-events-none absolute inset-0 rounded-xl ring-1 ring-neon-cyan/70"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    aria-hidden
                  />
                )}
              </Button>
            );
          })}
        </div>
      </HoverCard.Content>
    </HoverCard>
  );
}
