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
  AlertCircle,
  Telescope,
  type LucideIcon,
} from "lucide-react";
import { Button, Chip, Spinner, Text, Tooltip } from "@heroui/react";
import {
  EmptyState,
  ItemCard,
  ItemCardGroup,
  KPI,
  KPIGroup,
  Widget,
} from "@heroui-pro/react";
import { PageShell } from "@/components/page-shell";
import { useSystemInfo, useSetPowerProfile } from "@/hooks/use-system";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

const POWER_PROFILE_META: Record<
  string,
  { icon: LucideIcon; color: string; description: string }
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
  battery: {
    icon: Leaf,
    color: "text-emerald-400",
    description: "Low power draw and quieter fans — best on battery or light desktop use",
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
    label: "ScopeBuddy",
    path: "~/.config/scopebuddy",
    description: "scb.conf, AppID/*.conf overrides, and envvars snippets",
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

  const { data: gamescopeAvail } = useQuery({
    queryKey: ["gamescope-available"],
    queryFn: api.getGamescopeAvailable,
    staleTime: 60_000,
  });

  const { data: scopeBuddyAvail } = useQuery({
    queryKey: ["scopebuddy-available"],
    queryFn: api.getScopeBuddyAvailable,
    staleTime: 60_000,
  });

  const { data: mangohudAvail } = useQuery({
    queryKey: ["mangohud-available"],
    queryFn: api.getMangoHudAvailable,
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
      <div className="mx-auto max-w-4xl space-y-5">
        {/* Header */}
        <div className="space-y-1">
          <Text.Heading
            level={2}
            className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
          >
            <ServerCog className="size-5 shrink-0" aria-hidden />
            System
          </Text.Heading>
          <Text.Paragraph size="xs" color="muted">
            Hardware, displays, power, and quick file-manager links — all read
            live from the host.
          </Text.Paragraph>
        </div>

        {isLoading ? (
          <Widget>
            <Widget.Content>
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            </Widget.Content>
          </Widget>
        ) : error ? (
          <Widget>
            <Widget.Content>
              <EmptyState size="md">
                <EmptyState.Header>
                  <EmptyState.Media variant="icon">
                    <ServerCog className="size-5" aria-hidden />
                  </EmptyState.Media>
                  <EmptyState.Title>Failed to load system info</EmptyState.Title>
                  <EmptyState.Description>
                    Check that the backend is running and try refreshing.
                  </EmptyState.Description>
                </EmptyState.Header>
              </EmptyState>
            </Widget.Content>
          </Widget>
        ) : (
          <>
            {/* Host gaming tools */}
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex flex-wrap items-center gap-1.5">
                  <Telescope className="text-neon-cyan size-4 shrink-0" aria-hidden />
                  Gaming tools
                </Widget.Title>
              </Widget.Header>
              <Widget.Content className="flex flex-wrap gap-2">
                <Chip
                  size="sm"
                  variant="secondary"
                  className="text-[10px] font-mono"
                  color={gamescopeAvail?.available ? "success" : "warning"}
                >
                  gamescope {gamescopeAvail?.available ? "· ok" : "· missing"}
                </Chip>
                <Chip
                  size="sm"
                  variant="secondary"
                  className="text-[10px] font-mono"
                  color={scopeBuddyAvail?.available ? "success" : "warning"}
                >
                  {scopeBuddyAvail?.available
                    ? `${scopeBuddyAvail.binary}${scopeBuddyAvail.version ? ` · v${scopeBuddyAvail.version}` : ""}`
                    : "scb · missing"}
                </Chip>
                <Chip
                  size="sm"
                  variant="secondary"
                  className="text-[10px] font-mono"
                  color={mangohudAvail?.available ? "success" : "warning"}
                >
                  MangoHud {mangohudAvail?.available ? "· ok" : "· missing"}
                </Chip>
              </Widget.Content>
            </Widget>

            {/* GPUs */}
            {data?.gpus && data.gpus.length > 0 && (
              <Widget>
                <Widget.Header>
                  <Widget.Title className="flex items-center gap-1.5">
                    <Cpu className="text-neon-cyan size-4 shrink-0" aria-hidden />
                    Graphics
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="ml-1 text-[10px]"
                    >
                      {data.gpus.length} GPU{data.gpus.length !== 1 ? "s" : ""}
                    </Chip>
                  </Widget.Title>
                </Widget.Header>
                <Widget.Content className="space-y-3">
                  {data.gpus.map((gpu, index) => (
                    <div
                      key={index}
                      className="border-border bg-surface-secondary/20 flex items-start gap-3 rounded-xl border p-3"
                    >
                      <div className="bg-neon-cyan/10 border-neon-cyan/20 flex size-10 shrink-0 items-center justify-center rounded-xl border">
                        <Cpu className="text-neon-cyan size-5" aria-hidden />
                      </div>
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <Text.Heading
                            level={3}
                            className="text-foreground min-w-0 truncate text-base font-semibold"
                          >
                            {gpu.name}
                          </Text.Heading>
                          {gpu.driver && (
                            <Chip
                              size="sm"
                              variant="secondary"
                              className="text-[10px]"
                            >
                              {gpu.driver}
                            </Chip>
                          )}
                        </div>
                        {(gpu.vram_mb != null || gpu.temperature != null) && (
                          <KPIGroup className="flex-wrap gap-0">
                            {gpu.vram_mb != null && (
                              <KPI className="min-w-[120px] flex-1 border-0 shadow-none">
                                <KPI.Header>
                                  <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                                    <MemoryStick
                                      className="text-neon-blue size-3 shrink-0"
                                      aria-hidden
                                    />
                                    VRAM
                                  </KPI.Title>
                                </KPI.Header>
                                <KPI.Content>
                                  <span className="text-foreground text-lg font-semibold tabular-nums">
                                    {gpu.vram_mb >= 1024
                                      ? `${(gpu.vram_mb / 1024).toFixed(1)} GB`
                                      : `${gpu.vram_mb} MB`}
                                  </span>
                                </KPI.Content>
                              </KPI>
                            )}
                            {gpu.vram_mb != null && gpu.temperature != null && (
                              <KPIGroup.Separator className="hidden h-8 sm:block" />
                            )}
                            {gpu.temperature != null && (
                              <KPI className="min-w-[100px] flex-1 border-0 shadow-none">
                                <KPI.Header>
                                  <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                                    <Thermometer
                                      className={`size-3 shrink-0 ${
                                        gpu.temperature > 80
                                          ? "text-red-400"
                                          : gpu.temperature > 60
                                            ? "text-yellow-400"
                                            : "text-green-400"
                                      }`}
                                      aria-hidden
                                    />
                                    Temp
                                  </KPI.Title>
                                </KPI.Header>
                                <KPI.Content>
                                  <span className="text-foreground text-lg font-semibold tabular-nums">
                                    {gpu.temperature.toFixed(0)}°C
                                  </span>
                                </KPI.Content>
                              </KPI>
                            )}
                          </KPIGroup>
                        )}
                      </div>
                    </div>
                  ))}
                </Widget.Content>
              </Widget>
            )}

            {/* Power profile */}
            {data && (
              <Widget>
                <Widget.Header>
                  <Widget.Title className="flex items-center gap-1.5">
                    <BatteryCharging
                      className="text-neon-cyan size-4 shrink-0"
                      aria-hidden
                    />
                    Power profile
                    {data.power_profiles.length > 0 &&
                      data.current_power_profile && (
                        <Chip
                          size="sm"
                          color="accent"
                          variant="soft"
                          className="ml-1 text-[10px] capitalize"
                        >
                          {data.current_power_profile}
                        </Chip>
                      )}
                  </Widget.Title>
                </Widget.Header>
                <Widget.Content
                  className={
                    data.power_profiles.length > 0 ? "space-y-3" : undefined
                  }
                >
                  {data.power_profiles.length > 0 ? (
                    <>
                      <Text.Paragraph
                        size="xs"
                        color="muted"
                        className="leading-relaxed"
                      >
                        Switch between system power profiles. Performance
                        maximises clocks for gaming, balanced adapts dynamically,
                        and power-saver (or battery on Pop!_OS) prioritises lower
                        draw and quieter fans. The change takes effect
                        immediately.
                      </Text.Paragraph>
                      <ItemCardGroup
                        variant="secondary"
                        layout="list"
                        className="overflow-hidden rounded-xl"
                      >
                        {data.power_profiles.map((profile) => {
                          const active =
                            profile.toLowerCase() ===
                            data.current_power_profile?.toLowerCase();
                          const meta =
                            POWER_PROFILE_META[profile.toLowerCase()] ??
                            POWER_PROFILE_META["balanced"];
                          const ProfileIcon = meta?.icon ?? Zap;

                          return (
                            <ItemCard
                              key={profile}
                              className={
                                active
                                  ? "border-neon-cyan/40 bg-neon-cyan/10 py-3"
                                  : "py-3"
                              }
                            >
                              <ItemCard.Icon
                                className={`bg-surface-secondary ${meta?.color ?? "text-foreground"}`}
                              >
                                <ProfileIcon
                                  className="size-4 shrink-0"
                                  aria-hidden
                                />
                              </ItemCard.Icon>
                              <ItemCard.Content className="min-w-0 gap-0.5">
                                <ItemCard.Title className="flex items-center gap-2 capitalize">
                                  <span className="truncate">{profile}</span>
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
                                </ItemCard.Title>
                                {meta?.description && (
                                  <Text.Paragraph
                                    size="xs"
                                    color="muted"
                                    className="leading-snug"
                                  >
                                    {meta.description}
                                  </Text.Paragraph>
                                )}
                              </ItemCard.Content>
                              <ItemCard.Action>
                                <Button
                                  size="sm"
                                  variant={active ? "secondary" : "primary"}
                                  isDisabled={
                                    active || setPowerProfile.isPending
                                  }
                                  onPress={() => handleSetProfile(profile)}
                                >
                                  {active ? "Active" : "Activate"}
                                </Button>
                              </ItemCard.Action>
                            </ItemCard>
                          );
                        })}
                      </ItemCardGroup>
                    </>
                  ) : (
                    <div className="flex items-start gap-3">
                      <AlertCircle
                        className="text-muted mt-0.5 size-5 shrink-0"
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1 space-y-2">
                        <Text.Paragraph
                          size="sm"
                          weight="semibold"
                          className="text-foreground"
                        >
                          Profile switching unavailable
                        </Text.Paragraph>
                        <Text.Paragraph
                          size="xs"
                          color="muted"
                          className="leading-relaxed"
                        >
                          No supported power tool responded. ProtonShift uses{" "}
                          <Text.Code className="text-neon-cyan text-[11px]">
                            system76-power
                          </Text.Code>{" "}
                          on Pop!_OS (query:{" "}
                          <Text.Code className="text-neon-cyan text-[11px]">
                            system76-power profile
                          </Text.Code>
                          ) or{" "}
                          <Text.Code className="text-neon-cyan text-[11px]">
                            powerprofilesctl
                          </Text.Code>{" "}
                          from power-profiles-daemon elsewhere.
                        </Text.Paragraph>
                        <Text.Paragraph
                          size="xs"
                          color="muted"
                          className="leading-relaxed"
                        >
                          Sandboxed installs (for example Flatpak) may not see
                          those commands on the host unless permissions allow it.
                        </Text.Paragraph>
                      </div>
                    </div>
                  )}
                </Widget.Content>
              </Widget>
            )}

            {/* Displays */}
            {displayData && displayData.monitors.length > 0 && (
              <Widget>
                <Widget.Header>
                  <Widget.Title className="flex flex-wrap items-center gap-1.5">
                    <Monitor
                      className="text-neon-cyan size-4 shrink-0"
                      aria-hidden
                    />
                    Displays
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="ml-1 text-[10px]"
                    >
                      {displayData.monitors.length} monitor
                      {displayData.monitors.length !== 1 ? "s" : ""}
                    </Chip>
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="text-[10px] capitalize"
                    >
                      {displayData.session_type}
                    </Chip>
                  </Widget.Title>
                </Widget.Header>
                <Widget.Content>
                  <ItemCardGroup
                    variant="secondary"
                    layout="list"
                    className="overflow-hidden rounded-xl"
                  >
                    {displayData.monitors.map((monitor) => (
                      <ItemCard key={monitor.name} className="py-3">
                        <ItemCard.Icon className="bg-surface-secondary text-neon-blue">
                          <Monitor className="size-4 shrink-0" aria-hidden />
                        </ItemCard.Icon>
                        <ItemCard.Content className="min-w-0 gap-0.5">
                          <ItemCard.Title className="flex items-center gap-2">
                            <span className="truncate">{monitor.name}</span>
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
                          </ItemCard.Title>
                          <Text.Paragraph
                            size="xs"
                            color="muted"
                            className="leading-snug tabular-nums"
                          >
                            {monitor.resolution}
                            {monitor.refresh_rate &&
                              ` @ ${monitor.refresh_rate} Hz`}
                            {monitor.position && ` • ${monitor.position}`}
                          </Text.Paragraph>
                        </ItemCard.Content>
                      </ItemCard>
                    ))}
                  </ItemCardGroup>
                </Widget.Content>
              </Widget>
            )}

            {/* Shader cache */}
            {shaderTotal && (
              <Widget>
                <Widget.Header>
                  <Widget.Title className="flex items-center gap-1.5">
                    <Layers
                      className="text-neon-cyan size-4 shrink-0"
                      aria-hidden
                    />
                    Shader cache
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="ml-1 font-mono text-[10px] tabular-nums"
                    >
                      {shaderTotal.size_human}
                    </Chip>
                  </Widget.Title>
                </Widget.Header>
                <Widget.Content>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                    <div className="border-neon-purple/20 bg-neon-purple/10 flex size-10 shrink-0 items-center justify-center rounded-xl border">
                      <HardDrive className="text-neon-purple size-5" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-baseline gap-3">
                        <span className="text-foreground font-mono text-lg font-semibold tabular-nums">
                          {shaderTotal.size_human}
                        </span>
                        <Text.Paragraph size="xs" color="muted">
                          combined Vulkan/OpenGL shader cache
                        </Text.Paragraph>
                      </div>
                      <Text.Paragraph
                        size="xs"
                        color="muted"
                        className="leading-relaxed"
                      >
                        Located under{" "}
                        <Text.Code className="text-neon-cyan text-[11px]">
                          ~/.steam/steam/shadercache/
                        </Text.Code>
                        . Clear per game from each Steam game&apos;s detail page.
                      </Text.Paragraph>
                    </div>
                  </div>
                </Widget.Content>
              </Widget>
            )}

            {/* Quick folders */}
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <FolderOpen
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Quick folders
                  <Chip
                    size="sm"
                    variant="secondary"
                    className="ml-1 text-[10px]"
                  >
                    {QUICK_FOLDERS.length}
                  </Chip>
                </Widget.Title>
              </Widget.Header>
              <Widget.Content className="space-y-3">
                <Text.Paragraph
                  size="xs"
                  color="muted"
                  className="leading-relaxed"
                >
                  Open common configuration and data directories in your file
                  manager. Missing folders will be reported — they may not exist
                  until the relevant tool has run at least once.
                </Text.Paragraph>
                <ItemCardGroup
                  variant="secondary"
                  layout="list"
                  className="overflow-hidden rounded-xl"
                >
                  {QUICK_FOLDERS.map((folder) => (
                    <ItemCard key={folder.path} className="py-3">
                      <ItemCard.Icon className="bg-surface-secondary text-neon-cyan">
                        <FolderOpen className="size-4 shrink-0" aria-hidden />
                      </ItemCard.Icon>
                      <ItemCard.Content className="min-w-0 gap-0.5">
                        <ItemCard.Title className="truncate">
                          {folder.label}
                        </ItemCard.Title>
                        <Text.Paragraph
                          size="xs"
                          color="muted"
                          className="leading-snug"
                        >
                          {folder.description}
                        </Text.Paragraph>
                        <Text.Code
                          className="text-muted/80 mt-0.5 block truncate text-[10px]"
                          title={folder.path}
                        >
                          {folder.path}
                        </Text.Code>
                      </ItemCard.Content>
                      <ItemCard.Action>
                        <Tooltip delay={0}>
                          <Button
                            isIconOnly
                            variant="outline"
                            size="sm"
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
                            <FolderOpen className="size-3.5 shrink-0" aria-hidden />
                          </Button>
                          <Tooltip.Content>Open in file manager</Tooltip.Content>
                        </Tooltip>
                      </ItemCard.Action>
                    </ItemCard>
                  ))}
                </ItemCardGroup>
              </Widget.Content>
            </Widget>

            {/* Info footer */}
            <Widget>
              <Widget.Content className="py-3">
                <div className="flex items-start gap-3">
                  <Info
                    className="text-neon-cyan mt-0.5 size-4 shrink-0"
                    aria-hidden
                  />
                  <Text.Paragraph
                    size="xs"
                    color="muted"
                    className="leading-relaxed"
                  >
                    GPU temperatures and VRAM are read from{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      nvidia-smi
                    </Text.Code>{" "}
                    (NVIDIA) or{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      /sys/class/drm/
                    </Text.Code>{" "}
                    hwmon (AMD/Intel). Power profiles use{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      system76-power
                    </Text.Code>{" "}
                    on Pop!_OS or{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      powerprofilesctl
                    </Text.Code>{" "}
                    on Ubuntu and Fedora. Display info comes from{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      xrandr
                    </Text.Code>{" "}
                    (X11) or{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      wlr-randr
                    </Text.Code>{" "}
                    (Wayland).
                  </Text.Paragraph>
                </div>
              </Widget.Content>
            </Widget>
          </>
        )}
      </div>
    </PageShell>
  );
}
