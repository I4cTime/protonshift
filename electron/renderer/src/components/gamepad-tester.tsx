"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button, Chip, Label, Meter, Text, Tooltip } from "@heroui/react";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Vibrate,
  Wifi,
  WifiOff,
} from "lucide-react";

/* ---------------------------------------------------------------------------
 * Types
 * -------------------------------------------------------------------------*/

interface GamepadSnapshot {
  index: number;
  id: string;
  connected: boolean;
  mapping: string;
  timestamp: number;
  buttons: { pressed: boolean; touched: boolean; value: number }[];
  axes: number[];
  vid?: string;
  pid?: string;
}

interface GamepadTesterProps {
  /** Optional vendor:product id from the backend so we can highlight the matching pad. */
  matchId?: string;
  /** Whether the tester is currently visible / should poll. */
  active: boolean;
}

/** Standard W3C gamepad button indices. */
const BUTTON_LABELS: Record<number, string> = {
  0: "A",
  1: "B",
  2: "X",
  3: "Y",
  4: "LB",
  5: "RB",
  6: "LT",
  7: "RT",
  8: "Back",
  9: "Start",
  10: "L3",
  11: "R3",
  12: "↑",
  13: "↓",
  14: "←",
  15: "→",
  16: "Home",
};

/* ---------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------*/

function extractVendorProduct(id: string): { vid?: string; pid?: string } {
  // Chromium on Linux: "Xbox 360 Controller (Vendor: 045e Product: 028e)"
  const m1 = id.match(/Vendor:\s*([0-9a-f]{4})\s*Product:\s*([0-9a-f]{4})/i);
  if (m1) return { vid: m1[1].toLowerCase(), pid: m1[2].toLowerCase() };
  // Older format: "045e-028e-Name"
  const m2 = id.match(/\b([0-9a-f]{4})-([0-9a-f]{4})\b/i);
  if (m2) return { vid: m2[1].toLowerCase(), pid: m2[2].toLowerCase() };
  return {};
}

function snapshot(gp: Gamepad): GamepadSnapshot {
  const { vid, pid } = extractVendorProduct(gp.id);
  return {
    index: gp.index,
    id: gp.id,
    connected: gp.connected,
    mapping: gp.mapping,
    timestamp: gp.timestamp,
    buttons: gp.buttons.map((b) => ({
      pressed: b.pressed,
      touched: b.touched,
      value: b.value,
    })),
    axes: [...gp.axes],
    vid,
    pid,
  };
}

function matchPad(
  snaps: GamepadSnapshot[],
  matchId?: string,
): GamepadSnapshot | null {
  if (snaps.length === 0) return null;
  if (!matchId) return snaps[0] ?? null;

  const [vid, pid] = matchId.toLowerCase().split(":");
  const exact = snaps.find((s) => s.vid === vid && s.pid === pid);
  if (exact) return exact;
  // Fall back to first connected pad so the user can still test something.
  return snaps[0] ?? null;
}

/* ---------------------------------------------------------------------------
 * Sub-components
 * -------------------------------------------------------------------------*/

function FaceButton({
  label,
  pressed,
  className = "",
}: {
  label: string;
  pressed: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex size-8 items-center justify-center rounded-full border font-mono text-xs font-semibold tabular-nums transition-colors ${
        pressed
          ? "border-accent bg-accent/25 text-foreground shadow-[0_0_10px_rgba(0,229,255,0.35)]"
          : "border-border bg-surface-secondary text-muted"
      } ${className}`}
      aria-pressed={pressed}
    >
      {label}
    </span>
  );
}

function ChiclesButton({
  label,
  pressed,
}: {
  label: string;
  pressed: boolean;
}) {
  return (
    <span
      className={`inline-flex h-6 min-w-[2.5rem] items-center justify-center rounded-md border px-1.5 text-[10px] font-semibold uppercase tracking-wide transition-colors ${
        pressed
          ? "border-accent bg-accent/25 text-foreground"
          : "border-border bg-surface-secondary text-muted"
      }`}
      aria-pressed={pressed}
    >
      {label}
    </span>
  );
}

function TriggerBar({
  label,
  value,
  pressed,
}: {
  label: string;
  value: number;
  pressed: boolean;
}) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide">
        <span className={pressed ? "text-foreground" : "text-muted"}>
          {label}
        </span>
        <span className="text-muted font-mono tabular-nums">{pct}%</span>
      </div>
      <Meter
        value={pct}
        minValue={0}
        maxValue={100}
        aria-label={`${label} pressure`}
      >
        <Meter.Track>
          <Meter.Fill />
        </Meter.Track>
      </Meter>
    </div>
  );
}

function Thumbstick({
  label,
  x,
  y,
  pressed,
}: {
  label: string;
  x: number;
  y: number;
  pressed: boolean;
}) {
  const cx = Math.max(-1, Math.min(1, x));
  const cy = Math.max(-1, Math.min(1, y));
  // Box is 5rem (80px); dot is 0.75rem (12px). Halfway = 34px max travel.
  const travel = 34;
  const tx = cx * travel;
  const ty = cy * travel;
  const dist = Math.sqrt(cx * cx + cy * cy);
  const isActive = pressed || dist > 0.08;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide">
        <span className={isActive ? "text-foreground" : "text-muted"}>
          {label}
        </span>
        <span className="text-muted font-mono tabular-nums">
          {cx.toFixed(2)}, {cy.toFixed(2)}
        </span>
      </div>
      <div
        className={`relative size-20 rounded-full border-2 transition-colors ${
          pressed
            ? "border-accent bg-accent/15"
            : isActive
              ? "border-accent/50 bg-surface-deep"
              : "border-border bg-surface-deep"
        }`}
        aria-label={`${label} position`}
      >
        <div className="border-border/60 absolute inset-1/2 size-px -translate-x-1/2 -translate-y-1/2 rounded-full" />
        <div
          className="border-border/40 absolute left-1/2 top-1/2 size-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed"
          aria-hidden
        />
        <div
          className={`absolute left-1/2 top-1/2 size-3 rounded-full transition-colors ${
            isActive ? "bg-accent shadow-[0_0_8px_rgba(0,229,255,0.6)]" : "bg-muted"
          }`}
          style={{
            transform: `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px))`,
          }}
        />
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Main component
 * -------------------------------------------------------------------------*/

export function GamepadTester({ matchId, active }: GamepadTesterProps) {
  const [snaps, setSnaps] = useState<GamepadSnapshot[]>([]);
  const [vibrating, setVibrating] = useState(false);
  const [vibrateError, setVibrateError] = useState<string | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) {
      setSnaps([]);
      return;
    }

    let cancelled = false;
    const loop = () => {
      if (cancelled) return;
      const pads =
        typeof navigator !== "undefined" && "getGamepads" in navigator
          ? navigator.getGamepads()
          : [];
      const next: GamepadSnapshot[] = [];
      for (const gp of pads) {
        if (gp && gp.connected) next.push(snapshot(gp));
      }
      setSnaps(next);
      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => {
      cancelled = true;
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [active]);

  const matched = useMemo(() => matchPad(snaps, matchId), [snaps, matchId]);
  const exactMatch =
    matchId && matched
      ? matched.vid === matchId.toLowerCase().split(":")[0] &&
        matched.pid === matchId.toLowerCase().split(":")[1]
      : false;

  async function handleVibrate() {
    if (!matched) return;
    const liveGp = navigator.getGamepads()?.[matched.index];
    if (!liveGp) return;
    // Cast so we can access the experimental vibrationActuator API.
    const actuator = (
      liveGp as Gamepad & {
        vibrationActuator?: {
          playEffect?: (
            type: string,
            params: Record<string, number>,
          ) => Promise<string>;
        };
      }
    ).vibrationActuator;
    if (!actuator?.playEffect) {
      setVibrateError("Vibration not supported by this controller / browser.");
      return;
    }
    try {
      setVibrating(true);
      setVibrateError(null);
      await actuator.playEffect("dual-rumble", {
        duration: 600,
        startDelay: 0,
        strongMagnitude: 0.7,
        weakMagnitude: 0.4,
      });
    } catch {
      setVibrateError("Vibration request failed.");
    } finally {
      setVibrating(false);
    }
  }

  if (!active) return null;

  if (snaps.length === 0) {
    return (
      <div className="border-border bg-surface-deep flex items-center gap-2 rounded-lg border border-dashed p-3">
        <WifiOff className="text-muted size-4 shrink-0" aria-hidden />
        <Text.Paragraph size="xs" color="muted" className="leading-snug">
          No live gamepad signal yet. Press any button or move a stick — the
          browser only registers controllers after the first input.
        </Text.Paragraph>
      </div>
    );
  }

  if (!matched) return null;

  const btn = (i: number) => matched.buttons[i] ?? { pressed: false, value: 0 };

  return (
    <div className="space-y-3">
      {/* Status bar */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          {exactMatch ? (
            <Chip
              size="sm"
              color="success"
              variant="soft"
              className="gap-1 text-[10px]"
            >
              <CheckCircle2 className="size-3 shrink-0" />
              Matched
            </Chip>
          ) : matchId ? (
            <Chip
              size="sm"
              color="warning"
              variant="soft"
              className="gap-1 text-[10px]"
            >
              <AlertCircle className="size-3 shrink-0" />
              Showing first detected
            </Chip>
          ) : (
            <Chip
              size="sm"
              color="accent"
              variant="soft"
              className="gap-1 text-[10px]"
            >
              <Wifi className="size-3 shrink-0" />
              Live
            </Chip>
          )}
          <Chip size="sm" variant="secondary" className="text-[10px]">
            slot {matched.index}
          </Chip>
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {matched.mapping || "non-standard"}
          </Chip>
          <Text.Code className="text-muted truncate text-[11px]" title={matched.id}>
            {matched.id}
          </Text.Code>
        </div>
        <Tooltip delay={0}>
          <Button
            size="sm"
            variant="outline"
            onPress={handleVibrate}
            isDisabled={vibrating}
            className="gap-1.5"
          >
            <Vibrate className="size-3.5 shrink-0" aria-hidden />
            {vibrating ? "Rumbling…" : "Identify (rumble)"}
          </Button>
          <Tooltip.Content>
            Triggers a short dual-rumble so you can confirm which physical
            controller this card represents.
          </Tooltip.Content>
        </Tooltip>
      </div>

      {vibrateError && (
        <Text.Paragraph size="xs" color="muted" className="leading-snug">
          <AlertCircle className="mr-1 inline size-3 shrink-0" aria-hidden />
          {vibrateError}
        </Text.Paragraph>
      )}

      {/* Bumpers + Triggers */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
              Left
            </Label>
            <ChiclesButton label="LB" pressed={btn(4).pressed} />
          </div>
          <TriggerBar label="LT" value={btn(6).value} pressed={btn(6).pressed} />
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <ChiclesButton label="RB" pressed={btn(5).pressed} />
            <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
              Right
            </Label>
          </div>
          <TriggerBar label="RT" value={btn(7).value} pressed={btn(7).pressed} />
        </div>
      </div>

      {/* Misc row */}
      <div className="flex flex-wrap items-center justify-center gap-1.5">
        <ChiclesButton label="Back" pressed={btn(8).pressed} />
        <ChiclesButton label="Home" pressed={btn(16).pressed} />
        <ChiclesButton label="Start" pressed={btn(9).pressed} />
      </div>

      {/* D-Pad + Face buttons */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
            D-Pad
          </Label>
          <div className="border-border bg-surface-deep relative mx-auto grid h-24 w-24 grid-cols-3 grid-rows-3 gap-0.5 rounded-lg border p-1.5">
            <span />
            <FaceButton label="↑" pressed={btn(12).pressed} className="!size-7" />
            <span />
            <FaceButton label="←" pressed={btn(14).pressed} className="!size-7" />
            <span />
            <FaceButton label="→" pressed={btn(15).pressed} className="!size-7" />
            <span />
            <FaceButton label="↓" pressed={btn(13).pressed} className="!size-7" />
            <span />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
            Face buttons
          </Label>
          <div className="border-border bg-surface-deep relative mx-auto grid h-24 w-24 grid-cols-3 grid-rows-3 gap-0.5 rounded-lg border p-1.5">
            <span />
            <FaceButton label="Y" pressed={btn(3).pressed} className="!size-7" />
            <span />
            <FaceButton label="X" pressed={btn(2).pressed} className="!size-7" />
            <span />
            <FaceButton label="B" pressed={btn(1).pressed} className="!size-7" />
            <span />
            <FaceButton label="A" pressed={btn(0).pressed} className="!size-7" />
            <span />
          </div>
        </div>
      </div>

      {/* Sticks */}
      <div className="grid grid-cols-2 gap-3">
        <Thumbstick
          label="Left stick (L3)"
          x={matched.axes[0] ?? 0}
          y={matched.axes[1] ?? 0}
          pressed={btn(10).pressed}
        />
        <Thumbstick
          label="Right stick (R3)"
          x={matched.axes[2] ?? 0}
          y={matched.axes[3] ?? 0}
          pressed={btn(11).pressed}
        />
      </div>

      {/* Extra buttons / axes */}
      {matched.buttons.length > 17 && (
        <div className="space-y-1.5">
          <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
            Extra buttons
          </Label>
          <div className="flex flex-wrap gap-1">
            {matched.buttons.slice(17).map((b, i) => (
              <ChiclesButton
                key={`extra-${i + 17}`}
                label={BUTTON_LABELS[i + 17] ?? `B${i + 17}`}
                pressed={b.pressed}
              />
            ))}
          </div>
        </div>
      )}
      {matched.axes.length > 4 && (
        <div className="space-y-1.5">
          <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
            Extra axes
          </Label>
          <div className="grid grid-cols-2 gap-2">
            {matched.axes.slice(4).map((v, i) => {
              const pct = Math.round(((v + 1) / 2) * 100);
              return (
                <div key={`axis-${i + 4}`} className="space-y-0.5">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-muted font-mono">
                      axis {i + 4}
                    </span>
                    <span className="text-muted font-mono tabular-nums">
                      {v.toFixed(2)}
                    </span>
                  </div>
                  <Meter value={pct} minValue={0} maxValue={100}>
                    <Meter.Track>
                      <Meter.Fill />
                    </Meter.Track>
                  </Meter>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer hint */}
      <div className="text-muted flex items-center gap-1.5 text-[10px]">
        <Activity className="size-3 shrink-0" aria-hidden />
        Polled at ~60 Hz via{" "}
        <Text.Code className="text-[10px]">navigator.getGamepads()</Text.Code>.
        Some controllers only register after the first input.
      </div>
    </div>
  );
}
