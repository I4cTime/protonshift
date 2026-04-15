"use client";

import {
  Cpu,
  Thermometer,
  MemoryStick,
  Zap,
  FolderOpen,
  Monitor,
  HardDrive,
  ServerCog,
  BatteryCharging,
  Bolt,
  Leaf,
  Info,
  Layers,
  Trash2,
} from "lucide-react";
import { Button, Chip, Spinner, Tooltip } from "@heroui/react";
import { PageShell } from "@/components/page-shell";
import { GlowCard } from "@/components/glow-card";
import { useSystemInfo, useSetPowerProfile } from "@/hooks/use-system";
import { api } from "@/lib/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

const POWER_PROFILE_META: Record<
  string,
  { icon: typeof Zap; color: string; description: string }
> = {
  performance: {
    icon: Bolt,
    color: "text-red-400",
    description: "Max clocks, fans unrestricted — best FPS, highest power draw",
  },
  balanced: {
    icon: Zap,
    color: "text-yellow-400",
    description: "Dynamic clocks and fan curves — good balance for most games",
  },
  "power-saver": {
    icon: Leaf,
    color: "text-green-400",
    description: "Low clocks, quiet fans — extends battery life on laptops",
  },
};

const QUICK_FOLDERS: {
  label: string;
  path: string;
  description: string;
}[] = [
  {
    label: "MangoHud",
    path: "~/.config/MangoHud",
    description: "Global and per-game MangoHud overlay configs",
  },
  {
    label: "ProtonShift",
    path: "~/.config/protonshift",
    description: "ProtonShift profiles, fixes, and save backups",
  },
  {
    label: "Environment.d",
    path: "~/.config/environment.d",
    description: "Systemd env vars loaded on login",
  },
  {
    label: "Steam",
    path: "~/.steam/steam",
    description: "Steam install root — games, compatdata, shadercache",
  },
  {
    label: "Shader Cache",
    path: "~/.steam/steam/shadercache",
    description: "Vulkan/GL pre-compiled shader pipelines per game",
  },
  {
    label: "Compat Data",
    path: "~/.steam/steam/steamapps/compatdata",
    description: "Proton wine prefixes (per app ID)",
  },
];

export default function SystemPage() {
  const { data, isLoading, error } = useSystemInfo();
  const setPowerProfile = useSetPowerProfile();
  const qc = useQueryClient();

  const { data: displayData } = useQuery({
    queryKey: ["display-monitors"],
    queryFn: api.getMonitors,
    staleTime: 30_000,
  });

  const { data: shaderTotal } = useQuery({
    queryKey: ["shader-cache-total"],
    queryFn: api.getTotalShaderCache,
    staleTime: 60_000,
  });

  async function handleSetProfile(profile: string) {
    try {
      const result = await setPowerProfile.mutateAsync(profile);
      appShowToast(result.message || `Set to ${profile}`);
    } catch {
      appShowToast("Failed to set profile", "error");
    }
  }

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
          <ServerCog className="size-5" />
          System
        </h2>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center gap-2 py-16">
            <ServerCog className="size-8 text-text-muted/40" />
            <p className="text-sm text-red-400">Failed to load system info</p>
            <p className="text-xs text-text-muted">
              Check that the backend is running and try refreshing.
            </p>
          </div>
        ) : (
          <>
            {/* GPU cards */}
            {data?.gpus && data.gpus.length > 0 && (
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <Cpu className="size-4 text-neon-cyan" />
                  Graphics
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    {data.gpus.length} GPU{data.gpus.length !== 1 ? "s" : ""}
                  </Chip>
                </label>
                <div className="flex flex-col gap-3">
                  {data.gpus.map((gpu, index) => (
                    <GlowCard key={index} className="p-5">
                      <div className="flex items-start gap-4">
                        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-neon-cyan/10 border border-neon-cyan/20">
                          <Cpu className="size-5 text-neon-cyan" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h3 className="text-base font-semibold text-text-primary">
                            {gpu.name}
                          </h3>
                          {gpu.driver && (
                            <p className="mt-0.5 text-xs text-text-muted">
                              Driver: {gpu.driver}
                            </p>
                          )}
                          <div className="mt-3 flex flex-wrap gap-3">
                            {gpu.vram_mb != null && (
                              <div className="flex items-center gap-2 rounded-lg bg-surface-deep border border-separator px-3 py-2">
                                <MemoryStick className="size-4 text-neon-blue" />
                                <div>
                                  <p className="text-[10px] uppercase tracking-wide text-text-muted">
                                    VRAM
                                  </p>
                                  <p className="text-sm font-medium text-text-primary">
                                    {gpu.vram_mb >= 1024
                                      ? `${(gpu.vram_mb / 1024).toFixed(1)} GB`
                                      : `${gpu.vram_mb} MB`}
                                  </p>
                                </div>
                              </div>
                            )}
                            {gpu.temperature != null && (
                              <div className="flex items-center gap-2 rounded-lg bg-surface-deep border border-separator px-3 py-2">
                                <Thermometer
                                  className={`size-4 ${
                                    gpu.temperature > 80
                                      ? "text-red-400"
                                      : gpu.temperature > 60
                                        ? "text-yellow-400"
                                        : "text-green-400"
                                  }`}
                                />
                                <div>
                                  <p className="text-[10px] uppercase tracking-wide text-text-muted">
                                    Temp
                                  </p>
                                  <p className="text-sm font-medium text-text-primary">
                                    {gpu.temperature.toFixed(0)}&deg;C
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </GlowCard>
                  ))}
                </div>
              </div>
            )}

            {/* Power profile */}
            {data && data.power_profiles.length > 0 && (
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <BatteryCharging className="size-4 text-neon-cyan" />
                  Power Profile
                  {data.current_power_profile && (
                    <Chip
                      size="sm"
                      color="accent"
                      variant="soft"
                      className="capitalize text-[10px]"
                    >
                      {data.current_power_profile}
                    </Chip>
                  )}
                </label>
                <GlowCard className="p-5">
                  <p className="mb-4 text-xs leading-relaxed text-text-muted">
                    Switch between system power profiles. Performance maximises
                    clocks for gaming, balanced adapts dynamically, and
                    power-saver prioritises battery life and quiet fans. The
                    change takes effect immediately.
                  </p>
                  <div className="flex flex-col gap-2">
                    {data.power_profiles.map((profile) => {
                      const active =
                        profile.toLowerCase() ===
                        data.current_power_profile?.toLowerCase();
                      const meta =
                        POWER_PROFILE_META[profile.toLowerCase()] ??
                        POWER_PROFILE_META["balanced"];
                      const ProfileIcon = meta?.icon ?? Zap;

                      return (
                        <button
                          key={profile}
                          onClick={() => handleSetProfile(profile)}
                          className={`flex items-center gap-3 rounded-xl border p-3.5 text-left transition-all ${
                            active
                              ? "border-neon-cyan/40 bg-neon-cyan/10"
                              : "border-border bg-surface-secondary/30 hover:border-border-secondary"
                          }`}
                        >
                          <div
                            className={`flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-secondary ${meta?.color ?? "text-text-secondary"}`}
                          >
                            <ProfileIcon className="size-5" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold capitalize text-text-primary">
                                {profile}
                              </span>
                              {active && (
                                <Chip
                                  size="sm"
                                  color="accent"
                                  variant="soft"
                                  className="text-[10px]"
                                >
                                  Active
                                </Chip>
                              )}
                            </div>
                            {meta?.description && (
                              <p className="mt-0.5 text-xs text-text-muted">
                                {meta.description}
                              </p>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </GlowCard>
              </div>
            )}

            {/* Displays */}
            {displayData && displayData.monitors.length > 0 && (
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <Monitor className="size-4 text-neon-cyan" />
                  Displays
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    {displayData.monitors.length} monitor
                    {displayData.monitors.length !== 1 ? "s" : ""}
                  </Chip>
                  <Chip
                    size="sm"
                    variant="secondary"
                    className="capitalize text-[10px]"
                  >
                    {displayData.session_type}
                  </Chip>
                </label>
                <GlowCard className="p-5">
                  <div className="flex flex-col gap-2">
                    {displayData.monitors.map((monitor) => (
                      <div
                        key={monitor.name}
                        className="flex items-center gap-3 rounded-xl border border-border bg-surface-secondary/30 p-3.5"
                      >
                        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-secondary text-neon-blue">
                          <Monitor className="size-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-text-primary">
                              {monitor.name}
                            </span>
                            {monitor.primary && (
                              <Chip
                                size="sm"
                                color="accent"
                                variant="soft"
                                className="text-[10px]"
                              >
                                Primary
                              </Chip>
                            )}
                          </div>
                          <p className="mt-0.5 text-xs text-text-muted">
                            {monitor.resolution}
                            {monitor.refresh_rate &&
                              ` @ ${monitor.refresh_rate} Hz`}
                            {monitor.position && ` • ${monitor.position}`}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </GlowCard>
              </div>
            )}

            {/* Shader cache */}
            {shaderTotal && (
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <Layers className="size-4 text-neon-cyan" />
                  Shader Cache
                </label>
                <GlowCard className="p-5">
                  <div className="flex items-center gap-4">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-neon-purple/10 border border-neon-purple/20">
                      <HardDrive className="size-5 text-neon-purple" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-text-primary">
                          Total size
                        </span>
                        <Chip
                          size="sm"
                          variant="secondary"
                          className="font-mono text-[10px]"
                        >
                          {shaderTotal.size_human}
                        </Chip>
                      </div>
                      <p className="mt-0.5 text-xs text-text-muted">
                        Combined size of all per-game Vulkan/OpenGL shader
                        caches in{" "}
                        <code className="text-neon-cyan">
                          ~/.steam/steam/shadercache/
                        </code>
                        . Individual caches can be cleared from each game&apos;s
                        detail page.
                      </p>
                    </div>
                  </div>
                </GlowCard>
              </div>
            )}

            {/* Quick folders */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                <FolderOpen className="size-4 text-neon-cyan" />
                Quick Folders
              </label>
              <GlowCard className="p-5">
                <p className="mb-4 text-xs leading-relaxed text-text-muted">
                  Open common configuration and data directories in your file
                  manager. Missing folders will be reported — they may not exist
                  until the relevant tool has run at least once.
                </p>
                <div className="flex flex-col gap-2">
                  {QUICK_FOLDERS.map((folder) => (
                    <div
                      key={folder.path}
                      className="flex items-center gap-3 rounded-xl border border-border bg-surface-secondary/30 p-3.5 transition-colors hover:border-border-secondary"
                    >
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-surface-secondary text-neon-cyan">
                        <FolderOpen className="size-5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-text-primary">
                          {folder.label}
                        </p>
                        <p className="mt-0.5 text-xs text-text-muted">
                          {folder.description}
                        </p>
                        <code className="mt-1 block text-[10px] font-mono text-text-muted/70">
                          {folder.path}
                        </code>
                      </div>
                      <Tooltip delay={0}>
                        <Button
                          isIconOnly
                          variant="outline"
                          size="sm"
                          className="shrink-0"
                          aria-label={`Open ${folder.label} folder`}
                          onPress={async () => {
                            try {
                              await api.openPath(folder.path);
                            } catch {
                              appShowToast(
                                `Could not open ${folder.label} — folder may not exist yet`,
                                "error",
                              );
                            }
                          }}
                        >
                          <FolderOpen className="size-3.5" />
                        </Button>
                        <Tooltip.Content>
                          Open in file manager
                        </Tooltip.Content>
                      </Tooltip>
                    </div>
                  ))}
                </div>
              </GlowCard>
            </div>

            {/* Info footer */}
            <GlowCard className="p-4">
              <div className="flex gap-3">
                <Info className="mt-0.5 size-4 shrink-0 text-neon-cyan" />
                <p className="text-xs leading-relaxed text-text-muted">
                  GPU temperatures and VRAM are read from{" "}
                  <code className="text-neon-cyan">nvidia-smi</code> (NVIDIA) or{" "}
                  <code className="text-neon-cyan">/sys/class/drm/</code> hwmon
                  (AMD/Intel). Power profiles use{" "}
                  <code className="text-neon-cyan">system76-power</code> on
                  Pop!_OS or{" "}
                  <code className="text-neon-cyan">powerprofilesctl</code> on
                  Ubuntu and Fedora. Display info comes from{" "}
                  <code className="text-neon-cyan">xrandr</code> (X11) or{" "}
                  <code className="text-neon-cyan">wlr-randr</code> (Wayland).
                </p>
              </div>
            </GlowCard>
          </>
        )}
      </div>
    </PageShell>
  );
}
