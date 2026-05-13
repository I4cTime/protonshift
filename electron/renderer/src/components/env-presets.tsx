"use client";

import { useMemo } from "react";
import { Button, Chip, Text } from "@heroui/react";
import { ItemCard, ItemCardGroup } from "@heroui-pro/react";
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
      <Text.Paragraph size="xs" color="muted" className="leading-relaxed">
        Presets merge into your current variables — existing keys are updated,
        new keys are added, and nothing is removed. Save to write changes to
        disk.
      </Text.Paragraph>
      <ItemCardGroup
        variant="secondary"
        layout="list"
        className="overflow-hidden rounded-xl"
      >
        {orderedNames.map((name) => {
          const vars = presets[name];
          const meta = PRESET_META[name];
          const varCount = Object.keys(vars).length;
          const Icon = meta?.icon ?? Boxes;
          const iconColor = meta?.color ?? "text-foreground";

          return (
            <ItemCard key={name} className="py-3">
              <ItemCard.Icon className={`bg-surface-secondary ${iconColor}`}>
                <Icon className="size-4 shrink-0" aria-hidden />
              </ItemCard.Icon>
              <ItemCard.Content className="min-w-0 gap-1">
                <ItemCard.Title className="flex items-center gap-2">
                  <span className="truncate">{meta?.label ?? name}</span>
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    {varCount} var{varCount !== 1 ? "s" : ""}
                  </Chip>
                </ItemCard.Title>
                <Text.Paragraph
                  size="xs"
                  color="muted"
                  className="leading-snug"
                >
                  {meta?.description ??
                    `Applies ${varCount} environment variable${varCount !== 1 ? "s" : ""}.`}
                </Text.Paragraph>
                <div className="flex flex-wrap gap-1 pt-0.5">
                  {Object.entries(vars).map(([k, v]) => (
                    <Text.Code
                      key={k}
                      className="border-border bg-surface-deep text-muted rounded border px-1.5 py-0.5 text-[10px] leading-tight"
                    >
                      {k}={v}
                    </Text.Code>
                  ))}
                </div>
              </ItemCard.Content>
              <ItemCard.Action>
                <Button
                  size="sm"
                  variant="secondary"
                  onPress={() => onApply(vars)}
                >
                  Apply
                </Button>
              </ItemCard.Action>
            </ItemCard>
          );
        })}
      </ItemCardGroup>
    </div>
  );
}
