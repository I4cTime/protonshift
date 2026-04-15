"use client";

import { useMemo } from "react";
import { Button, Chip, Description } from "@heroui/react";
import {
  MonitorCog,
  Cpu,
  Layers,
  Puzzle,
  AppWindow,
  Gamepad2,
  Bug,
  Boxes,
  type LucideIcon,
} from "lucide-react";

const PRESET_META: Record<
  string,
  {
    label: string;
    description: string;
    icon: LucideIcon;
    color: string;
  }
> = {
  "Proton (NVIDIA)": {
    label: "Proton (NVIDIA)",
    description:
      "Enable Wayland support in Proton and keep the NVIDIA shader disk cache without periodic cleanup. Reduces stutter after the first run.",
    icon: MonitorCog,
    color: "text-green-400",
  },
  "Proton (AMD)": {
    label: "Proton (AMD)",
    description:
      "Enable Wayland in Proton, use the RADV Vulkan driver, and turn on GPL pipeline and NGG stream-out for better shader compilation on AMD GPUs.",
    icon: Cpu,
    color: "text-red-400",
  },
  "DXVK / VKD3D": {
    label: "DXVK / VKD3D",
    description:
      "Enable DXVK async shader compilation and state cache for DirectX 9/10/11, and DXR ray-tracing via VKD3D for DirectX 12 titles.",
    icon: Puzzle,
    color: "text-purple-400",
  },
  "Shader cache": {
    label: "Shader cache",
    description:
      "Maximise shader caching across Mesa, RADV, and NVIDIA drivers. Sets a 4 GB cache limit and skips cleanup to eliminate repeated compilation stutters.",
    icon: Layers,
    color: "text-cyan-400",
  },
  Wayland: {
    label: "Wayland",
    description:
      "Force Wayland as the display backend for Proton, SDL, GTK, and Qt applications. Use this if you run a Wayland compositor and want native Wayland rendering.",
    icon: AppWindow,
    color: "text-blue-400",
  },
  Gamemode: {
    label: "Gamemode",
    description:
      "Tell Steam to activate Feral GameMode, which applies CPU governor, I/O priority, and GPU clock optimisations while a game is running.",
    icon: Gamepad2,
    color: "text-yellow-400",
  },
  "Proton (Debug)": {
    label: "Proton (Debug)",
    description:
      "Enable Proton and Wine debug logging, plus DXVK and VKD3D diagnostic output. Useful for troubleshooting crashes — generates large log files.",
    icon: Bug,
    color: "text-orange-400",
  },
};

interface EnvPresetsProps {
  presets: Record<string, Record<string, string>>;
  onApply: (presetVars: Record<string, string>) => void;
}

export function EnvPresets({ presets, onApply }: EnvPresetsProps) {
  const orderedNames = useMemo(() => {
    const preferred = [
      "Proton (NVIDIA)",
      "Proton (AMD)",
      "DXVK / VKD3D",
      "Shader cache",
      "Wayland",
      "Gamemode",
      "Proton (Debug)",
    ];
    const known = preferred.filter((n) => n in presets);
    const extra = Object.keys(presets).filter((n) => !preferred.includes(n));
    return [...known, ...extra];
  }, [presets]);

  return (
    <div className="space-y-3">
      <Description className="text-xs leading-relaxed text-text-muted">
        Presets merge into your current variables — existing keys are updated,
        new keys are added, and nothing is removed. Save to write changes to
        disk.
      </Description>
      <div className="flex flex-col gap-3">
        {orderedNames.map((name) => {
          const vars = presets[name];
          const meta = PRESET_META[name];
          const varCount = Object.keys(vars).length;
          const Icon = meta?.icon ?? Boxes;
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
                    {varCount} var{varCount !== 1 ? "s" : ""}
                  </Chip>
                </div>
                <p className="text-xs leading-relaxed text-text-muted">
                  {meta?.description ??
                    `Applies ${varCount} environment variable${varCount !== 1 ? "s" : ""}.`}
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {Object.entries(vars).map(([k, v]) => (
                    <code
                      key={k}
                      className="rounded bg-surface-secondary px-1.5 py-0.5 text-[10px] font-mono text-text-muted"
                    >
                      {k}={v}
                    </code>
                  ))}
                </div>
              </div>
              <Button
                size="sm"
                variant="secondary"
                className="shrink-0 self-center"
                onPress={() => onApply(vars)}
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
