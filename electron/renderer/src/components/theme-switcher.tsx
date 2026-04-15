"use client";

import { useState, useRef, useEffect } from "react";
import { useAtom } from "jotai";
import { motion, AnimatePresence } from "motion/react";
import { Palette, Check, Sun, Moon } from "lucide-react";
import { themeAtom, THEMES, THEME_IDS, type ThemeId } from "@/lib/theme";

export function ThemeSwitcher() {
  const [themeId, setThemeId] = useAtom(themeAtom);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const current = THEMES[themeId];

  return (
    <div className="relative" ref={ref}>
      <motion.button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl border-2 border-neon-cyan/40 bg-surface-deep/60 text-text-secondary hover:border-neon-cyan hover:text-neon-cyan transition-all hover:shadow-glow-sm"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Switch theme"
      >
        <Palette className="size-5" />
        <div className="flex gap-1.5">
          <span
            className="size-4 rounded-full ring-2 ring-white/30 shadow-lg"
            style={{ backgroundColor: current.accent }}
          />
          <span
            className="size-4 rounded-full ring-2 ring-white/30 shadow-lg"
            style={{ backgroundColor: current.secondary }}
          />
        </div>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute right-0 top-full mt-3 w-72 rounded-2xl bg-surface-elevated border-2 border-neon-cyan/30 shadow-glow-md overflow-hidden backdrop-blur-2xl z-[100]"
            initial={{ opacity: 0, y: -10, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.9 }}
            transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <div className="px-4 pt-3 pb-2">
              <p className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Choose Theme
              </p>
            </div>
            <div className="px-2 pb-2 space-y-1">
              {THEME_IDS.map((id) => (
                <ThemeOption
                  key={id}
                  id={id}
                  active={id === themeId}
                  onSelect={(t) => {
                    setThemeId(t);
                    setOpen(false);
                  }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ThemeOption({
  id,
  active,
  onSelect,
}: {
  id: ThemeId;
  active: boolean;
  onSelect: (id: ThemeId) => void;
}) {
  const meta = THEMES[id];
  const isLight = meta.colorScheme === "light";
  const ModeIcon = isLight ? Sun : Moon;

  return (
    <motion.button
      onClick={() => onSelect(id)}
      className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all ${
        active
          ? "bg-neon-cyan/15 border-2 border-neon-cyan/50 shadow-glow-sm"
          : "border-2 border-transparent hover:bg-surface-mid hover:border-neon-cyan/20"
      }`}
      whileHover={{ x: 3 }}
      whileTap={{ scale: 0.97 }}
    >
      {/* Color preview strip */}
      <div
        className={`w-12 h-8 rounded-lg flex overflow-hidden shrink-0 outline outline-2 ${
          active ? "outline-neon-cyan" : "outline-white/15"
        }`}
      >
        <div className="flex-1" style={{ backgroundColor: meta.surface }} />
        <div className="flex-1" style={{ backgroundColor: meta.accent }} />
        <div className="flex-1" style={{ backgroundColor: meta.secondary }} />
      </div>

      <div className="flex flex-col items-start min-w-0 flex-1">
        <span className={`text-sm font-semibold truncate ${active ? "text-neon-cyan" : "text-text-primary"}`}>
          {meta.label}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-text-muted">
          <ModeIcon className="size-3" />
          <span className="capitalize">{meta.colorScheme} mode</span>
        </span>
      </div>

      {active && (
        <motion.div
          className="shrink-0 size-6 rounded-full flex items-center justify-center"
          style={{ backgroundColor: meta.accent }}
          layoutId="theme-check"
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        >
          <Check className="size-3.5 text-white" strokeWidth={3} />
        </motion.div>
      )}
    </motion.button>
  );
}
