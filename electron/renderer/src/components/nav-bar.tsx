"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Gamepad2, Settings, Cpu, Gauge, Joystick, Search, Telescope } from "lucide-react";
import { motion } from "motion/react";
import { Button, Kbd, Tooltip } from "@heroui/react";
import { Navbar } from "@heroui-pro/react";
import { ThemeSwitcher } from "./theme-switcher";
import { WindowControls } from "./window-controls";
import { useGames } from "@/hooks/use-games";
import { OPEN_COMMAND_PALETTE_EVENT } from "@/lib/command-palette-events";

const NAV_ITEMS = [
  { href: "/", label: "Games", icon: Gamepad2 },
  { href: "/environment", label: "Environment", icon: Settings },
  { href: "/system", label: "System", icon: Cpu },
  { href: "/mangohud", label: "MangoHud", icon: Gauge },
  { href: "/scopebuddy", label: "ScopeBuddy", icon: Telescope },
  { href: "/controllers", label: "Controllers", icon: Joystick },
] as const;

const SOURCE_LEDS = [
  { key: "steam", short: "S", label: "Steam", countKey: "steam" as const },
  { key: "heroic", short: "H", label: "Heroic", countKey: "heroic" as const },
  { key: "lutris", short: "L", label: "Lutris", countKey: "lutris" as const },
] as const;

function dotClass(count: number, isLoading: boolean, hasError: boolean): string {
  if (hasError) return "bg-warning shadow-[0_0_6px_rgba(245,158,11,0.55)] animate-pulse";
  if (isLoading) return "bg-warning/60 animate-pulse";
  if (count > 0) return "bg-success shadow-[0_0_6px_rgba(34,197,94,0.45)]";
  return "bg-border";
}

function dotTooltip(count: number, label: string, isLoading: boolean, hasError: boolean): string {
  if (hasError) return `${label} · offline`;
  if (isLoading) return `${label} · loading…`;
  return `${label} · ${count} game${count === 1 ? "" : "s"}`;
}

function openCommandPalette() {
  window.dispatchEvent(new CustomEvent(OPEN_COMMAND_PALETTE_EVENT));
}

export function NavBar() {
  const pathname = usePathname();
  const { data, isLoading, error } = useGames();
  const hasError = error != null;

  // Surface the packaged app version (== electron/package.json#version) in the
  // brand block so the navbar self-updates on every bump. Outside the Electron
  // shell (e.g. `next dev` in a browser tab) the bridge is absent — render
  // nothing rather than a stale hardcoded fallback.
  const [appVersion, setAppVersion] = useState<string | null>(null);
  useEffect(() => {
    const electron = window.electron;
    if (!electron?.getVersion) return;
    let cancelled = false;
    electron.getVersion().then(
      (v) => {
        if (!cancelled) setAppVersion(v);
      },
      () => {},
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Navbar
      position="static"
      maxWidth="full"
      height="4.5rem"
      shouldBlockScroll={false}
      aria-label="Primary"
      className="protonshift-navbar app-region-drag @container/nav relative z-50 border-b border-transparent bg-surface-elevated/80 shadow-glow-sm backdrop-blur-xl"
    >
      <div
        className="pointer-events-none absolute bottom-2 left-0 top-2 z-0 w-0.5 rounded-full bg-gradient-to-b from-neon-cyan via-neon-purple to-neon-pink opacity-60"
        aria-hidden
      />
      <Navbar.Header className="relative z-10 max-w-full gap-2 px-3 @md/nav:gap-3 @md/nav:px-4">
        <Navbar.Brand className="min-w-0 shrink-0 select-none">
          <motion.div
            className="app-region-no-drag flex min-w-0 items-center gap-2 @md/nav:gap-2.5"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
          >
            <Link
              href="/"
              prefetch
              className="flex min-w-0 items-center gap-2 @md/nav:gap-2.5 outline-none"
              aria-label="ProtonShift home"
            >
              <Image
                src="/logo-nav.png"
                alt=""
                width={44}
                height={44}
                className="shrink-0 rounded-xl drop-shadow-[0_0_12px_var(--theme-glow-primary)]"
                priority
              />
              <div className="hidden min-w-0 flex-col gap-1 @2xl/nav:flex">
                <span
                  className="navbar__brand-chroma text-xs font-bold uppercase tracking-[0.22em] text-foreground"
                  aria-hidden
                >
                  ProtonShift
                </span>
                <div className="navbar__brand-scanline h-[2px] w-full max-w-[7.5rem] rounded-full opacity-90" aria-hidden />
                <p className="text-muted hidden font-mono text-[10px] leading-tight tracking-wide @6xl/nav:block">
                  {appVersion ? `v${appVersion}` : "v0.9.6"} · Linux gaming HUD
                </p>
              </div>
            </Link>
          </motion.div>
        </Navbar.Brand>

        <Navbar.Separator className="protonshift-navbar__sep mx-0.5 h-7 @md/nav:mx-1" />

        <Navbar.Content className="app-region-no-drag relative flex shrink-0 gap-0.5">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Navbar.Item
                key={href}
                href={href}
                isCurrent={active}
                className="relative shrink-0 rounded-lg px-2 py-1.5 @5xl/nav:px-3"
                render={(props) => <Link href={href} prefetch {...props} />}
              >
                {active && (
                  <motion.span
                    layoutId="nav-active-pill"
                    className="nav-active-pill-hud pointer-events-none absolute inset-0 -z-10 rounded-lg border border-neon-cyan/60 bg-neon-cyan/15 shadow-glow-sm"
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    aria-hidden
                  >
                    <span
                      className="absolute inset-x-2 top-0 h-px rounded-full bg-gradient-to-r from-transparent via-neon-cyan to-neon-pink/80"
                      aria-hidden
                    />
                  </motion.span>
                )}
                <Icon className="size-4 shrink-0" data-slot="icon" aria-hidden />
                <Navbar.Label className="hidden @5xl/nav:inline">{label}</Navbar.Label>
              </Navbar.Item>
            );
          })}
        </Navbar.Content>

        {/* Entire navbar is the drag region; every interactive child opts out explicitly with app-region-no-drag */}
        <Navbar.Spacer className="min-h-9 flex-1 basis-0 cursor-default select-none self-stretch" />

        <div className="app-region-no-drag hidden shrink-0 items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-muted @3xl/nav:flex">
          {SOURCE_LEDS.map(({ key, short, label, countKey }) => {
            const count = data?.[countKey]?.length ?? 0;
            const tip = dotTooltip(count, label, isLoading, hasError);
            return (
              <Tooltip key={key} delay={0}>
                <span
                  tabIndex={0}
                  className="flex cursor-default items-center gap-1 rounded outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/50"
                  aria-label={tip}
                >
                  <span
                    className={`size-1.5 shrink-0 rounded-full ${dotClass(count, isLoading, hasError)}`}
                    aria-hidden
                  />
                  <span className="leading-none opacity-70" aria-hidden>
                    {short}
                  </span>
                </span>
                <Tooltip.Content>{tip}</Tooltip.Content>
              </Tooltip>
            );
          })}
        </div>

        <Navbar.Content className="app-region-no-drag flex shrink-0">
          <Tooltip delay={0}>
            <Button
              variant="ghost"
              size="sm"
              className="h-9 gap-2 rounded-lg border border-neon-cyan/40 bg-surface-secondary/40 px-2.5 text-muted hover:border-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan @4xl/nav:px-3"
              aria-label="Open command palette"
              onPress={openCommandPalette}
            >
              <Search className="size-4 shrink-0" aria-hidden />
              <span className="hidden text-xs font-medium @4xl/nav:inline">Search</span>
              <Kbd className="pointer-events-none hidden h-5 text-[10px] @4xl/nav:inline-flex">
                <Kbd.Abbr keyValue="command" />
                <Kbd.Content>K</Kbd.Content>
              </Kbd>
            </Button>
            <Tooltip.Content>Open command palette · ⌘K</Tooltip.Content>
          </Tooltip>
        </Navbar.Content>

        <Navbar.Separator className="protonshift-navbar__sep app-region-no-drag mx-0.5 h-7 @md/nav:mx-1" />

        <Navbar.Content className="app-region-no-drag flex shrink-0 items-center gap-2">
          <ThemeSwitcher />
          <WindowControls />
        </Navbar.Content>
      </Navbar.Header>
    </Navbar>
  );
}
