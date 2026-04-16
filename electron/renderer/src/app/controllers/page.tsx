"use client";

import { useState } from "react";
import {
  Gamepad2,
  Copy,
  RefreshCw,
  Info,
  Usb,
  Hash,
  MapPin,
  ChevronDown,
  Unplug,
} from "lucide-react";
import {
  Alert,
  Button,
  Chip,
  Description,
  Disclosure,
  Separator,
  Skeleton,
  Spinner,
  Tooltip,
} from "@heroui/react";
import { PageShell } from "@/components/page-shell";
import { GlowCard } from "@/components/glow-card";
import { api } from "@/lib/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

const TYPE_META: Record<
  string,
  { chipColor: "accent" | "success" | "danger" | "warning" | "default"; label: string }
> = {
  xbox: { chipColor: "success", label: "Xbox" },
  playstation: { chipColor: "accent", label: "PlayStation" },
  nintendo: { chipColor: "danger", label: "Nintendo" },
  steam: { chipColor: "accent", label: "Steam" },
  "8bitdo": { chipColor: "warning", label: "8BitDo" },
  generic: { chipColor: "default", label: "Generic" },
};

export default function ControllersPage() {
  const qc = useQueryClient();
  const { data: controllers, isLoading, error, isRefetching } = useQuery({
    queryKey: ["controllers"],
    queryFn: api.getControllers,
    staleTime: 10_000,
  });

  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [loadingMapping, setLoadingMapping] = useState<Record<string, boolean>>({});

  async function handleCopyMapping(controllerId: string) {
    try {
      const result = await api.getControllerSdlMapping(controllerId);
      await navigator.clipboard.writeText(result.mapping);
      appShowToast("SDL mapping copied to clipboard");
    } catch {
      appShowToast("Failed to get mapping", "error");
    }
  }

  async function handleRevealMapping(controllerId: string) {
    if (mappings[controllerId]) return;
    setLoadingMapping((prev) => ({ ...prev, [controllerId]: true }));
    try {
      const result = await api.getControllerSdlMapping(controllerId);
      setMappings((prev) => ({ ...prev, [controllerId]: result.mapping }));
    } catch {
      appShowToast("Failed to fetch mapping", "error");
    } finally {
      setLoadingMapping((prev) => ({ ...prev, [controllerId]: false }));
    }
  }

  const controllerCount = controllers?.length ?? 0;
  const typeCounts = controllers?.reduce<Record<string, number>>((acc, c) => {
    acc[c.controller_type] = (acc[c.controller_type] || 0) + 1;
    return acc;
  }, {}) ?? {};

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
              <Gamepad2 className="size-5" />
              Controllers
              {controllerCount > 0 && (
                <Chip size="sm" variant="secondary" className="text-[10px]">
                  {controllerCount} detected
                </Chip>
              )}
            </h2>
            <Description className="mt-1">
              Detected game controllers, joysticks, and gamepads connected to this system.
              Copy SDL mappings for per-game controller configuration.
            </Description>
          </div>
          <Tooltip delay={0}>
            <Button
              variant="outline"
              size="sm"
              isIconOnly
              aria-label="Refresh controllers"
              isDisabled={isRefetching}
              onPress={() => qc.invalidateQueries({ queryKey: ["controllers"] })}
            >
              <RefreshCw className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            </Button>
            <Tooltip.Content>Re-scan connected controllers</Tooltip.Content>
          </Tooltip>
        </div>

        {/* Loading state */}
        {isLoading ? (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl border border-neon-cyan/20 bg-surface-elevated p-5"
              >
                <div className="flex items-center gap-4">
                  <Skeleton className="size-12 rounded-xl" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-5 w-48 rounded-lg" />
                    <div className="flex gap-2">
                      <Skeleton className="h-5 w-16 rounded-full" />
                      <Skeleton className="h-5 w-28 rounded-lg" />
                    </div>
                  </div>
                  <Skeleton className="h-8 w-32 rounded-lg" />
                </div>
              </div>
            ))}
          </div>

        /* Error state */
        ) : error ? (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Title>Failed to detect controllers</Alert.Title>
              <Alert.Description>
                Check that the backend is running and <code className="text-neon-cyan">/proc/bus/input/devices</code> or <code className="text-neon-cyan">/dev/input/js*</code> is accessible, then try refreshing.
              </Alert.Description>
            </Alert.Content>
          </Alert>

        /* Empty state */
        ) : !controllers || controllerCount === 0 ? (
          <GlowCard className="p-8">
            <div className="flex flex-col items-center gap-4 text-center">
              <div className="flex size-16 items-center justify-center rounded-2xl bg-surface-deep border border-border">
                <Unplug className="size-8 text-text-muted/50" />
              </div>
              <div>
                <p className="text-sm font-medium text-text-primary">
                  No game controllers detected
                </p>
                <Description className="mt-1">
                  Connect a controller via USB or Bluetooth and press refresh to re-scan.
                  Devices are detected from <code className="text-neon-cyan">/proc/bus/input</code> and <code className="text-neon-cyan">/dev/input/js*</code>.
                </Description>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onPress={() => qc.invalidateQueries({ queryKey: ["controllers"] })}
              >
                <RefreshCw className="size-3.5" />
                Scan Again
              </Button>
            </div>
          </GlowCard>

        /* Controller list */
        ) : (
          <>
            {/* Type summary chips */}
            {Object.keys(typeCounts).length > 1 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                {Object.entries(typeCounts).map(([type, count]) => {
                  const meta = TYPE_META[type] || TYPE_META.generic;
                  return (
                    <Chip
                      key={type}
                      size="sm"
                      color={meta.chipColor}
                      variant="soft"
                      className="gap-1"
                    >
                      <Gamepad2 className="size-3" />
                      {count} {meta.label}
                    </Chip>
                  );
                })}
              </div>
            )}

            <div className="space-y-4">
              {controllers.map((ctrl, idx) => {
                const meta = TYPE_META[ctrl.controller_type] || TYPE_META.generic;
                const mapping = mappings[ctrl.id];
                const isLoadingMap = loadingMapping[ctrl.id];

                return (
                  <GlowCard key={ctrl.id} className="p-0" delay={idx * 0.05}>
                    {/* Main row */}
                    <div className="flex items-center justify-between p-5">
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-surface-deep border border-border">
                          <Gamepad2 className="size-6 text-neon-cyan" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-base font-semibold text-text-primary truncate">
                            {ctrl.name}
                          </h3>
                          <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <Chip
                              color={meta.chipColor}
                              size="sm"
                              variant="soft"
                            >
                              {meta.label}
                            </Chip>
                            <Chip size="sm" variant="secondary" className="gap-1">
                              <Usb className="size-3" />
                              Connected
                            </Chip>
                          </div>
                        </div>
                      </div>
                      <Tooltip delay={0}>
                        <Button
                          variant="outline"
                          size="sm"
                          onPress={() => handleCopyMapping(ctrl.id)}
                          className="gap-1.5 shrink-0"
                        >
                          <Copy className="size-3" />
                          Copy SDL
                        </Button>
                        <Tooltip.Content>
                          Copy SDL_GAMECONTROLLERCONFIG mapping to clipboard
                        </Tooltip.Content>
                      </Tooltip>
                    </div>

                    <Separator />

                    {/* Detail stats */}
                    <div className="px-5 py-3 flex flex-wrap gap-x-6 gap-y-2">
                      <div className="flex items-center gap-2">
                        <MapPin className="size-3.5 text-text-muted" />
                        <span className="text-xs text-text-muted">Device</span>
                        <code className="text-xs font-mono text-text-primary">
                          {ctrl.device_path}
                        </code>
                      </div>
                      {ctrl.vendor_id && (
                        <div className="flex items-center gap-2">
                          <Hash className="size-3.5 text-text-muted" />
                          <span className="text-xs text-text-muted">Vendor:Product</span>
                          <code className="text-xs font-mono text-text-primary">
                            {ctrl.vendor_id}:{ctrl.product_id}
                          </code>
                        </div>
                      )}
                    </div>

                    <Separator />

                    {/* SDL mapping disclosure */}
                    <div className="px-5 py-3">
                      <Disclosure
                        onExpandedChange={(expanded) => {
                          if (expanded) handleRevealMapping(ctrl.id);
                        }}
                      >
                        <Disclosure.Heading>
                          <Button slot="trigger" variant="ghost" size="sm" className="gap-1.5">
                            <ChevronDown className="size-3.5" />
                            View SDL Mapping
                            <Disclosure.Indicator />
                            {isLoadingMap && <Spinner size="sm" className="ml-1" />}
                          </Button>
                        </Disclosure.Heading>
                        <Disclosure.Content>
                          <Disclosure.Body className="pt-2">
                            {mapping ? (
                              <div className="relative">
                                <pre className="text-[11px] font-mono text-text-secondary bg-surface-deep border border-border rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
                                  {mapping}
                                </pre>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  isIconOnly
                                  className="absolute top-2 right-2"
                                  aria-label="Copy mapping"
                                  onPress={() => handleCopyMapping(ctrl.id)}
                                >
                                  <Copy className="size-3" />
                                </Button>
                              </div>
                            ) : !isLoadingMap ? (
                              <p className="text-xs text-text-muted">
                                Could not load mapping.
                              </p>
                            ) : null}
                          </Disclosure.Body>
                        </Disclosure.Content>
                      </Disclosure>
                    </div>
                  </GlowCard>
                );
              })}
            </div>

            {/* SDL usage guide */}
            <GlowCard className="p-5">
              <div className="space-y-3">
                <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <Info className="size-4 text-neon-cyan" />
                  Using SDL Mappings
                </label>
                <Description>
                  SDL mappings let games recognize your controller with the correct button layout.
                  The generated mapping provides a standard Xbox-style layout as a starting point.
                </Description>
                <Separator />
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-primary">Steam launch options</p>
                  <pre className="text-[11px] font-mono text-text-secondary bg-surface-deep border border-border rounded-lg p-3 overflow-x-auto">
                    SDL_GAMECONTROLLERCONFIG=&quot;...mapping...&quot; %command%
                  </pre>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium text-text-primary">Environment variable</p>
                  <pre className="text-[11px] font-mono text-text-secondary bg-surface-deep border border-border rounded-lg p-3 overflow-x-auto">
                    export SDL_GAMECONTROLLERCONFIG=&quot;...mapping...&quot;
                  </pre>
                </div>
              </div>
            </GlowCard>

            {/* Info footer */}
            <GlowCard className="p-4">
              <div className="flex gap-3">
                <Info className="mt-0.5 size-4 shrink-0 text-neon-cyan" />
                <p className="text-xs leading-relaxed text-text-muted">
                  Controllers are detected from{" "}
                  <code className="text-neon-cyan">/proc/bus/input/devices</code>{" "}
                  (handler list) with a fallback to{" "}
                  <code className="text-neon-cyan">/dev/input/js*</code>{" "}
                  device nodes. Type classification is based on vendor name matching.
                  The SDL mapping uses a standard Xbox-style button layout — for full
                  calibration, use{" "}
                  <code className="text-neon-cyan">SDL2 Gamepad Tool</code> or{" "}
                  <code className="text-neon-cyan">AntiMicroX</code>.
                </p>
              </div>
            </GlowCard>
          </>
        )}
      </div>
    </PageShell>
  );
}
