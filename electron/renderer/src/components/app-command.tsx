"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Gamepad2,
  Gauge,
  Joystick,
  LayoutGrid,
  Search,
  ServerCog,
  Settings,
  Telescope,
  FolderOpen,
} from "lucide-react";
import { Chip, Kbd } from "@heroui/react";
import { Command } from "@heroui-pro/react";
import { FOCUS_GAME_SEARCH_EVENT, OPEN_COMMAND_PALETTE_EVENT } from "@/lib/command-palette-events";
import { api } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

const ROUTES = [
  { id: "nav-games", href: "/", label: "Games", description: "Library & per-game settings", icon: Gamepad2 },
  {
    id: "nav-environment",
    href: "/environment",
    label: "Environment",
    description: "Session environment variables",
    icon: Settings,
  },
  { id: "nav-system", href: "/system", label: "System", description: "GPU, power, folders", icon: ServerCog },
  { id: "nav-mangohud", href: "/mangohud", label: "MangoHud", description: "Overlay & metrics", icon: Gauge },
  {
    id: "nav-scopebuddy",
    href: "/scopebuddy",
    label: "ScopeBuddy",
    description: "scb.conf, per-app, envvars",
    icon: Telescope,
  },
  {
    id: "nav-controllers",
    href: "/controllers",
    label: "Controllers",
    description: "SDL gamecontroller mappings",
    icon: Joystick,
  },
] as const;

export function AppCommand() {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const handleOpenChange = useCallback((next: boolean) => {
    setOpen(next);
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    function onOpenPalette() {
      setOpen(true);
    }
    window.addEventListener(OPEN_COMMAND_PALETTE_EVENT, onOpenPalette);
    return () => window.removeEventListener(OPEN_COMMAND_PALETTE_EVENT, onOpenPalette);
  }, []);

  const onAction = useCallback(
    (key: string | number) => {
      const id = String(key);
      if (id === "focus-game-search") {
        window.dispatchEvent(new CustomEvent(FOCUS_GAME_SEARCH_EVENT));
        setOpen(false);
        return;
      }
      if (id === "open-scopebuddy-config") {
        void (async () => {
          try {
            const info = await api.getScopeBuddyAvailable();
            const dir = info.config_dir || "~/.config/scopebuddy";
            await api.openPath(dir);
          } catch {
            appShowToast("Could not open ScopeBuddy config folder", "error");
          }
        })();
        setOpen(false);
        return;
      }
      if (id === "nav-games-scopebuddy-hint") {
        router.push("/");
        window.dispatchEvent(new CustomEvent(FOCUS_GAME_SEARCH_EVENT));
        setOpen(false);
        return;
      }
      if (id === "rescan-scopebuddy") {
        void (async () => {
          try {
            const info = await api.rescanScopeBuddy();
            appShowToast(
              info.available
                ? `ScopeBuddy detected: ${info.binary}${info.version ? ` v${info.version}` : ""}`
                : "ScopeBuddy still not on PATH",
              info.available ? "success" : "error",
            );
          } catch {
            appShowToast("Rescan failed", "error");
          }
        })();
        setOpen(false);
        return;
      }
      const route = ROUTES.find((r) => r.id === id);
      if (route) {
        router.push(route.href);
        setOpen(false);
      }
    },
    [router],
  );

  return (
    <Command>
      <Command.Backdrop isOpen={open} onOpenChange={handleOpenChange}>
        <Command.Container size="lg">
          <Command.Dialog>
            <Command.Header className="px-4 pb-0 pt-3">
              <Chip size="sm" variant="secondary">
                ProtonShift
              </Chip>
            </Command.Header>
            <Command.InputGroup>
              <Command.InputGroup.Prefix>
                <Search className="size-4 text-muted shrink-0" aria-hidden />
              </Command.InputGroup.Prefix>
              <Command.InputGroup.Input placeholder="Jump to page or focus game search…" />
              <Command.InputGroup.ClearButton />
              <Command.InputGroup.Suffix>
                <Kbd className="text-xs">
                  <Kbd.Content>Esc</Kbd.Content>
                </Kbd>
              </Command.InputGroup.Suffix>
            </Command.InputGroup>
            <Command.List
              renderEmptyState={() => (
                <div className="text-muted flex h-14 items-center justify-center text-sm">No matches.</div>
              )}
              onAction={onAction}
            >
              <Command.Group heading="Navigation">
                {ROUTES.map((r) => {
                  const Icon = r.icon;
                  return (
                    <Command.Item key={r.id} id={r.id} textValue={r.label}>
                      <Icon className="size-4 shrink-0 text-muted" aria-hidden />
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <span className="text-sm font-medium">{r.label}</span>
                        <span className="text-muted truncate text-xs">{r.description}</span>
                      </div>
                    </Command.Item>
                  );
                })}
              </Command.Group>
              <Command.Group heading="Games">
                <Command.Item id="focus-game-search" textValue="Focus game search">
                  <LayoutGrid className="size-4 shrink-0 text-muted" aria-hidden />
                  <span>Focus game search</span>
                </Command.Item>
              </Command.Group>
              <Command.Group heading="ScopeBuddy">
                <Command.Item id="nav-scopebuddy" textValue="Open ScopeBuddy page">
                  <Telescope className="size-4 shrink-0 text-muted" aria-hidden />
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-sm font-medium">Open ScopeBuddy page</span>
                    <span className="text-muted truncate text-xs">scb.conf · per-app · envvars · rescan</span>
                  </div>
                </Command.Item>
                <Command.Item id="open-scopebuddy-config" textValue="Open ScopeBuddy config folder">
                  <FolderOpen className="size-4 shrink-0 text-muted" aria-hidden />
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-sm font-medium">Open ScopeBuddy config folder</span>
                    <span className="text-muted truncate text-xs">~/.config/scopebuddy · scb.conf &amp; AppID</span>
                  </div>
                </Command.Item>
                <Command.Item id="rescan-scopebuddy" textValue="Rescan ScopeBuddy on PATH">
                  <Search className="size-4 shrink-0 text-muted" aria-hidden />
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-sm font-medium">Rescan ScopeBuddy on PATH</span>
                    <span className="text-muted truncate text-xs">Re-detect scb / scopebuddy after install</span>
                  </div>
                </Command.Item>
                <Command.Item id="nav-games-scopebuddy-hint" textValue="Per-game ScopeBuddy override">
                  <Telescope className="size-4 shrink-0 text-muted" aria-hidden />
                  <div className="flex min-w-0 flex-col gap-0.5">
                    <span className="text-sm font-medium">Per-game ScopeBuddy override</span>
                    <span className="text-muted truncate text-xs">
                      Games → pick title → Setup → ScopeBuddy override widget
                    </span>
                  </div>
                </Command.Item>
              </Command.Group>
            </Command.List>
            <Command.Footer className="justify-between gap-2 [&_kbd]:h-5 [&_kbd]:text-xs">
              <span className="text-muted text-xs">Open with Ctrl K or Cmd K</span>
              <div className="flex items-center gap-1.5">
                <Kbd className="text-xs">
                  <Kbd.Abbr keyValue="enter" />
                </Kbd>
                <span className="text-muted text-xs">Go</span>
              </div>
            </Command.Footer>
          </Command.Dialog>
        </Command.Container>
      </Command.Backdrop>
    </Command>
  );
}
