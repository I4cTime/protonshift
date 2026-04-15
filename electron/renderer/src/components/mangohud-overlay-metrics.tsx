"use client";

import { useMemo, type Dispatch, type SetStateAction } from "react";
import { Label, Tag, TagGroup } from "@heroui/react";
import {
  Activity,
  Cpu,
  MonitorCog,
  MemoryStick,
  HardDrive,
  Cog,
  EyeOff,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";

export interface MangoHudToggleParam {
  key: string;
  label: string;
  type: string;
}

/** Logical groups for MangoHud overlay toggles (keys match `mangohud.py` / MangoHud.conf). */
export const MANGO_OVERLAY_TOGGLE_GROUPS: readonly {
  title: string;
  description: string;
  icon: LucideIcon;
  keys: readonly string[];
}[] = [
  {
    title: "Performance",
    icon: Activity,
    description:
      "Core framerate and frame-pacing metrics. FPS Counter shows the current rate, FPS Only strips everything else, Frame Time shows per-frame duration, and Frame Time Graph draws the rolling timing chart.",
    keys: ["fps", "fps_only", "frametime", "frame_timing"],
  },
  {
    title: "CPU",
    icon: Cpu,
    description:
      "Processor utilisation, thermals, power draw, and clock speed. Useful for spotting thermal throttling or single-thread bottlenecks during gameplay.",
    keys: ["cpu_stats", "cpu_temp", "cpu_power", "cpu_mhz"],
  },
  {
    title: "GPU",
    icon: MonitorCog,
    description:
      "Graphics-card load, temperature, power consumption, core/memory clocks, and VRAM usage. Helps identify GPU-bound scenarios and VRAM pressure.",
    keys: [
      "gpu_stats",
      "gpu_temp",
      "gpu_power",
      "gpu_core_clock",
      "gpu_mem_clock",
      "vram",
    ],
  },
  {
    title: "Memory",
    icon: MemoryStick,
    description:
      "System RAM, swap, and per-process memory consumption. High swap usage often signals that the game is exceeding physical memory.",
    keys: ["ram", "swap", "procmem"],
  },
  {
    title: "I/O",
    icon: HardDrive,
    description:
      "Disk read and write throughput of the game process. Spikes here can explain stutters caused by asset streaming or shader compilation.",
    keys: ["io_read", "io_write"],
  },
  {
    title: "System & runtime",
    icon: Cog,
    description:
      "Wine/Proton version, Vulkan driver in use, game engine identifier, CPU architecture, and whether Feral GameMode is active. Handy for bug reports and compatibility checks.",
    keys: ["wine", "vulkan_driver", "engine_version", "arch", "gamemode"],
  },
  {
    title: "Behavior",
    icon: EyeOff,
    description:
      "Controls overlay visibility. No Display hides the on-screen HUD entirely but keeps background logging active if a log output folder is configured.",
    keys: ["no_display"],
  },
];

function selectionToSet(
  selection: "all" | Iterable<unknown>,
  groupKeys: readonly string[],
): Set<string> {
  if (selection === "all") return new Set(groupKeys);
  return new Set(Array.from(selection, (k) => String(k)));
}

interface OverlayGroupDef {
  title: string;
  description: string;
  icon: LucideIcon;
  keys: readonly string[];
}

function buildGroupsWithParams(
  toggleParams: MangoHudToggleParam[],
): OverlayGroupDef[] {
  const byKey = new Map(toggleParams.map((p) => [p.key, p]));
  const grouped = new Set(
    MANGO_OVERLAY_TOGGLE_GROUPS.flatMap((g) => [...g.keys]),
  );

  const resolved: OverlayGroupDef[] = MANGO_OVERLAY_TOGGLE_GROUPS.map(
    (g) => ({
      title: g.title,
      description: g.description,
      icon: g.icon,
      keys: g.keys.filter((k) => byKey.has(k)),
    }),
  ).filter((g) => g.keys.length > 0);

  const orphanKeys = toggleParams
    .filter((p) => !grouped.has(p.key))
    .map((p) => p.key);
  if (orphanKeys.length > 0) {
    resolved.push({
      title: "Other",
      description:
        "Additional overlay toggles not assigned to a specific category.",
      icon: LayoutGrid,
      keys: orphanKeys,
    });
  }

  return resolved;
}

interface OverlayMetricGroupProps {
  group: OverlayGroupDef;
  paramByKey: Map<string, MangoHudToggleParam>;
  config: Record<string, string>;
  setConfig: Dispatch<SetStateAction<Record<string, string>>>;
}

function OverlayMetricGroup({
  group,
  paramByKey,
  config,
  setConfig,
}: OverlayMetricGroupProps) {
  const selectedKeys = new Set(group.keys.filter((k) => k in config));
  const Icon = group.icon;

  return (
    <div className="rounded-xl border border-border bg-surface-secondary/30 p-4">
      <TagGroup
        selectionMode="multiple"
        selectedKeys={selectedKeys}
        onSelectionChange={(selection) => {
          const selected = selectionToSet(selection, group.keys);
          setConfig((prev) => {
            const next = { ...prev };
            for (const k of group.keys) {
              if (selected.has(k)) {
                next[k] = prev[k] ?? "";
              } else {
                delete next[k];
              }
            }
            return next;
          });
        }}
        size="sm"
        variant="surface"
        className="w-full"
      >
        <Label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          <Icon className="size-3.5 text-neon-cyan" />
          {group.title}
        </Label>
        <p className="mt-1 text-xs leading-relaxed text-text-muted">
          {group.description}
        </p>
        <TagGroup.List className="mt-3 flex flex-wrap gap-2">
          {group.keys.map((key) => {
            const p = paramByKey.get(key);
            if (!p) return null;
            return (
              <Tag key={key} id={key} textValue={p.label}>
                {p.label}
              </Tag>
            );
          })}
        </TagGroup.List>
      </TagGroup>
    </div>
  );
}

interface MangoHudOverlayMetricsProps {
  toggleParams: MangoHudToggleParam[];
  config: Record<string, string>;
  setConfig: Dispatch<SetStateAction<Record<string, string>>>;
}

/**
 * Overlay metric toggles grouped by category, using HeroUI [TagGroup](https://heroui.com/docs/react/components/tag-group)
 * with `selectionMode="multiple"` for keyboard-accessible multi-select.
 */
export function MangoHudOverlayMetrics({
  toggleParams,
  config,
  setConfig,
}: MangoHudOverlayMetricsProps) {
  const paramByKey = useMemo(
    () => new Map(toggleParams.map((p) => [p.key, p])),
    [toggleParams],
  );

  const groups = useMemo(
    () => buildGroupsWithParams(toggleParams),
    [toggleParams],
  );

  return (
    <div className="flex flex-col gap-3">
      {groups.map((group) => (
        <OverlayMetricGroup
          key={group.title}
          group={group}
          paramByKey={paramByKey}
          config={config}
          setConfig={setConfig}
        />
      ))}
    </div>
  );
}
