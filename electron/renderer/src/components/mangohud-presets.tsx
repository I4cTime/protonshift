"use client";

import { useMemo } from "react";
import { Button, Chip, Description } from "@heroui/react";
import {
  Zap,
  Monitor,
  BarChart3,
  Cpu,
  Bug,
  BatteryLow,
  Radio,
  Eye,
  type LucideIcon,
} from "lucide-react";

/** Metadata for each preset — descriptions, icons, and tag counts live here,
 *  the actual key→value map comes from the backend via the `presets` prop. */
const PRESET_META: Record<
  string,
  {
    label: string;
    description: string;
    icon: LucideIcon;
    color: string;
  }
> = {
  minimal: {
    label: "Minimal",
    description:
      "Just the FPS counter — nothing else. Perfect when you want a quick glance without clutter.",
    icon: Zap,
    color: "text-green-400",
  },
  standard: {
    label: "Standard",
    description:
      "FPS, frame time, CPU/GPU usage and temps, plus RAM and VRAM. A balanced everyday overlay.",
    icon: Monitor,
    color: "text-blue-400",
  },
  full: {
    label: "Full",
    description:
      "Every toggle enabled — all CPU, GPU, memory, I/O, and system info metrics. Shows everything MangoHud can display.",
    icon: Eye,
    color: "text-purple-400",
  },
  "fps-only": {
    label: "FPS Only",
    description:
      "Large, transparent FPS counter in the top-right corner. Ideal for clean screenshots or recording with a subtle readout.",
    icon: Zap,
    color: "text-emerald-400",
  },
  "cpu-gpu": {
    label: "CPU + GPU",
    description:
      "Focused on processor and graphics card: load, temps, clocks, and VRAM. Helps isolate whether a game is CPU- or GPU-bound.",
    icon: Cpu,
    color: "text-orange-400",
  },
  benchmark: {
    label: "Benchmark",
    description:
      "All performance-critical metrics plus frame-time logging to ~/mangohud_logs. Run a scene, then analyse the CSV with MangoPlot.",
    icon: BarChart3,
    color: "text-cyan-400",
  },
  "battery-saver": {
    label: "Battery Saver",
    description:
      "Caps FPS to 30 and shows only the essentials (FPS, CPU/GPU temps). Designed for laptops on battery to reduce power draw.",
    icon: BatteryLow,
    color: "text-yellow-400",
  },
  streaming: {
    label: "Streaming",
    description:
      "Compact top-right overlay with smaller text and a semi-transparent background. Keeps key stats visible without distracting viewers.",
    icon: Radio,
    color: "text-pink-400",
  },
  debug: {
    label: "Debug",
    description:
      "Full overlay plus frame-time logging. Intended for troubleshooting performance regressions — everything on screen and on disk.",
    icon: Bug,
    color: "text-red-400",
  },
};

function countMetrics(config: Record<string, string>): {
  toggles: number;
  values: number;
} {
  let toggles = 0;
  let values = 0;
  for (const v of Object.values(config)) {
    if (v === "") toggles++;
    else values++;
  }
  return { toggles, values };
}

interface MangoHudPresetsProps {
  presets: Record<string, Record<string, string>>;
  onApply: (presetName: string) => void;
}

export function MangoHudPresets({ presets, onApply }: MangoHudPresetsProps) {
  const orderedNames = useMemo(() => {
    const preferred = [
      "minimal",
      "fps-only",
      "standard",
      "cpu-gpu",
      "benchmark",
      "battery-saver",
      "streaming",
      "full",
      "debug",
    ];
    const known = preferred.filter((n) => n in presets);
    const extra = Object.keys(presets).filter((n) => !preferred.includes(n));
    return [...known, ...extra];
  }, [presets]);

  return (
    <div className="space-y-3">
      <Description className="text-xs leading-relaxed text-text-muted">
        Presets replace your entire config with a curated set of toggles and
        values. Pick one as a starting point, then customise the metrics and
        values below. Your changes are not saved until you press Save.
      </Description>
      <div className="flex flex-col gap-3">
        {orderedNames.map((name) => {
          const config = presets[name];
          const meta = PRESET_META[name];
          const { toggles, values } = countMetrics(config);
          const Icon = meta?.icon ?? Monitor;
          const iconColor = meta?.color ?? "text-text-secondary";

          return (
            <div
              key={name}
              className="flex items-start gap-4 rounded-xl border border-border bg-surface-secondary/30 p-4 transition-colors hover:border-border-secondary"
            >
              <div
                className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-secondary ${iconColor}`}
              >
                <Icon className="size-5" />
              </div>
              <div className="min-w-0 flex-1 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-text-primary">
                    {meta?.label ?? name}
                  </span>
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    {toggles} metric{toggles !== 1 ? "s" : ""}
                  </Chip>
                  {values > 0 && (
                    <Chip size="sm" variant="secondary" className="text-[10px]">
                      {values} value{values !== 1 ? "s" : ""}
                    </Chip>
                  )}
                </div>
                <p className="text-xs leading-relaxed text-text-muted">
                  {meta?.description ??
                    `Applies ${toggles + values} parameters.`}
                </p>
              </div>
              <Button
                size="sm"
                variant="secondary"
                className="shrink-0 self-center"
                onPress={() => onApply(name)}
              >
                Apply
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
