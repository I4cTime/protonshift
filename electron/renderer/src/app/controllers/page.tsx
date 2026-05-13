"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  Bluetooth,
  Cable,
  ChevronDown,
  Copy,
  Download,
  ExternalLink,
  Fingerprint,
  Gamepad2,
  Hash,
  Info,
  KeyRound,
  MapPin,
  Plug,
  RefreshCw,
  Search,
  Tags,
  Unplug,
  Usb,
  Wand2,
  Wrench,
} from "lucide-react";
import {
  Alert,
  Button,
  Chip,
  Disclosure,
  Label,
  Link as HeroLink,
  SearchField,
  Skeleton,
  Spinner,
  Text,
  Tooltip,
} from "@heroui/react";
import {
  EmptyState,
  ItemCard,
  ItemCardGroup,
  KPI,
  KPIGroup,
  Widget,
} from "@heroui-pro/react";
import { GamepadTester } from "@/components/gamepad-tester";
import { PageShell } from "@/components/page-shell";
import { api, type ControllerData } from "@/lib/api";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

/* ---------------------------------------------------------------------------
 * Constants & helpers
 * -------------------------------------------------------------------------*/

type ChipColor = "accent" | "success" | "danger" | "warning" | "default";

const TYPE_META: Record<
  string,
  { chipColor: ChipColor; label: string; iconClass: string }
> = {
  xbox: { chipColor: "success", label: "Xbox", iconClass: "text-success" },
  playstation: {
    chipColor: "accent",
    label: "PlayStation",
    iconClass: "text-neon-blue",
  },
  nintendo: { chipColor: "danger", label: "Nintendo", iconClass: "text-danger" },
  steam: { chipColor: "accent", label: "Steam", iconClass: "text-neon-cyan" },
  "8bitdo": { chipColor: "warning", label: "8BitDo", iconClass: "text-warning" },
  generic: { chipColor: "default", label: "Generic", iconClass: "text-muted" },
};

function metaFor(type: string) {
  return TYPE_META[type] ?? TYPE_META.generic;
}

/** Linux input.h bus type codes. */
const BUS_TYPES: Record<
  string,
  { label: string; short: string; chipColor: ChipColor; icon: typeof Usb }
> = {
  "0001": { label: "PCI", short: "PCI", chipColor: "default", icon: Plug },
  "0002": { label: "ISA", short: "ISA", chipColor: "default", icon: Plug },
  "0003": { label: "USB", short: "USB", chipColor: "accent", icon: Usb },
  "0005": {
    label: "Bluetooth",
    short: "BT",
    chipColor: "success",
    icon: Bluetooth,
  },
  "0010": {
    label: "Virtual",
    short: "Virtual",
    chipColor: "warning",
    icon: Cable,
  },
  "0018": { label: "I²C", short: "I²C", chipColor: "default", icon: Cable },
  "0019": { label: "Host", short: "Host", chipColor: "default", icon: Cable },
};

function busInfo(bus?: string) {
  const norm = (bus ?? "").toLowerCase().padStart(4, "0");
  return (
    BUS_TYPES[norm] ?? {
      label: norm ? `Bus 0x${norm}` : "Unknown",
      short: norm ? `0x${norm}` : "—",
      chipColor: "default" as ChipColor,
      icon: Cable,
    }
  );
}

function formatHexId(value?: string) {
  if (!value) return "—";
  return value.toLowerCase().padStart(4, "0");
}

function buildGuidFromController(c: ControllerData): string {
  // Mirrors src/game_setup_hub/controllers.py:_build_sdl_guid
  const u16 = (v?: string) => {
    const n = parseInt(v ?? "0", 16);
    return Number.isFinite(n) ? n & 0xffff : 0;
  };
  const words = [
    u16(c.bus_type || "0003"),
    0,
    u16(c.vendor_id),
    0,
    u16(c.product_id),
    0,
    u16(c.version),
    0,
  ];
  const bytes: number[] = [];
  for (const w of words) {
    bytes.push(w & 0xff, (w >> 8) & 0xff);
  }
  return bytes.map((b) => b.toString(16).padStart(2, "0")).join("");
}

const REFERENCE_TOOLS: {
  name: string;
  description: string;
  href: string;
  Icon: typeof Wrench;
}[] = [
  {
    name: "SDL2 Gamepad Tool",
    description:
      "Generate accurate SDL_GAMECONTROLLERCONFIG mappings for any pad.",
    href: "https://generalarcade.com/gamepadtool/",
    Icon: Wand2,
  },
  {
    name: "AntiMicroX",
    description:
      "Map gamepad buttons to keyboard / mouse events for games without native pad support.",
    href: "https://github.com/AntiMicroX/antimicrox",
    Icon: KeyRound,
  },
  {
    name: "sdl2-jstest",
    description:
      "CLI tool to inspect joystick events in real time and verify SDL detection.",
    href: "https://gitlab.com/sdl-jstest/sdl-jstest",
    Icon: Activity,
  },
  {
    name: "SDL community DB",
    description:
      "Crowdsourced gamepad mapping database used by SDL itself — search by GUID.",
    href: "https://github.com/mdqinc/SDL_GameControllerDB",
    Icon: Tags,
  },
];

/* ---------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------*/

type FilterMode = "all" | "xbox" | "playstation" | "nintendo" | "steam" | "8bitdo" | "generic";
type ConnectionFilter = "all" | "usb" | "bluetooth" | "other";

export default function ControllersPage() {
  const qc = useQueryClient();
  const {
    data: controllers,
    isLoading,
    error,
    isRefetching,
  } = useQuery({
    queryKey: ["controllers"],
    queryFn: api.getControllers,
    staleTime: 10_000,
  });

  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [loadingMapping, setLoadingMapping] = useState<Record<string, boolean>>(
    {},
  );
  const [openTester, setOpenTester] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<FilterMode>("all");
  const [connFilter, setConnFilter] = useState<ConnectionFilter>("all");

  /* --------------------------- Derived collections -------------------------- */

  const list = controllers ?? [];
  const controllerCount = list.length;

  const summary = useMemo(() => {
    let usb = 0;
    let bt = 0;
    let other = 0;
    const types: Record<string, number> = {};
    for (const c of list) {
      const norm = (c.bus_type ?? "").toLowerCase().padStart(4, "0");
      if (norm === "0003") usb++;
      else if (norm === "0005") bt++;
      else other++;
      types[c.controller_type] = (types[c.controller_type] || 0) + 1;
    }
    return { usb, bt, other, types };
  }, [list]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return list.filter((c) => {
      if (typeFilter !== "all" && c.controller_type !== typeFilter) return false;
      const norm = (c.bus_type ?? "").toLowerCase().padStart(4, "0");
      if (connFilter === "usb" && norm !== "0003") return false;
      if (connFilter === "bluetooth" && norm !== "0005") return false;
      if (connFilter === "other" && (norm === "0003" || norm === "0005"))
        return false;
      if (
        q &&
        !c.name.toLowerCase().includes(q) &&
        !c.device_path.toLowerCase().includes(q) &&
        !`${c.vendor_id}:${c.product_id}`.toLowerCase().includes(q)
      )
        return false;
      return true;
    });
  }, [list, search, typeFilter, connFilter]);

  /* ------------------------------- Mutations ------------------------------- */

  async function handleCopy(text: string, message: string) {
    try {
      await navigator.clipboard.writeText(text);
      appShowToast(message);
    } catch {
      appShowToast("Failed to copy", "error");
    }
  }

  async function handleCopyMapping(controllerId: string) {
    try {
      const cached = mappings[controllerId];
      const mapping = cached ?? (await api.getControllerSdlMapping(controllerId)).mapping;
      if (!cached) setMappings((prev) => ({ ...prev, [controllerId]: mapping }));
      await navigator.clipboard.writeText(mapping);
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

  function handleDownloadMapping(ctrl: ControllerData) {
    const mapping = mappings[ctrl.id];
    if (!mapping) {
      appShowToast("Open the SDL mapping section first", "error");
      return;
    }
    const safeName = ctrl.name.replace(/[^a-zA-Z0-9_-]+/g, "_").slice(0, 48);
    const blob = new Blob([mapping], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName || "controller"}-${ctrl.vendor_id || "0000"}_${ctrl.product_id || "0000"}.sdl.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function toggleTester(ctrlId: string, expanded: boolean) {
    setOpenTester((prev) => ({ ...prev, [ctrlId]: expanded }));
  }

  /* --------------------------------- Render -------------------------------- */

  return (
    <PageShell>
      <div className="mx-auto max-w-4xl space-y-5">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <Text.Heading
              level={2}
              className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
            >
              <Gamepad2 className="size-5 shrink-0" aria-hidden />
              Controllers
              {controllerCount > 0 && (
                <Chip
                  size="sm"
                  variant="secondary"
                  className="ml-1 text-[10px]"
                >
                  {controllerCount} detected
                </Chip>
              )}
            </Text.Heading>
            <Text.Paragraph size="xs" color="muted" className="leading-snug">
              Joysticks and gamepads detected by the kernel. Test inputs live,
              copy SDL mappings, and link to per-game configuration tools.
            </Text.Paragraph>
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
              <RefreshCw
                className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`}
              />
            </Button>
            <Tooltip.Content>Re-scan connected controllers</Tooltip.Content>
          </Tooltip>
        </div>

        {/* Loading state */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Widget key={i}>
                <Widget.Content>
                  <div className="flex items-center gap-3">
                    <Skeleton className="size-12 rounded-xl" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-5 w-48 rounded-lg" />
                      <div className="flex gap-2">
                        <Skeleton className="h-5 w-16 rounded-full" />
                        <Skeleton className="h-5 w-24 rounded-lg" />
                      </div>
                    </div>
                    <Skeleton className="h-8 w-32 rounded-lg" />
                  </div>
                </Widget.Content>
              </Widget>
            ))}
          </div>
        ) : error ? (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Title>Failed to detect controllers</Alert.Title>
              <Alert.Description>
                Check that the backend is running and{" "}
                <Text.Code className="text-neon-cyan">
                  /proc/bus/input/devices
                </Text.Code>{" "}
                or{" "}
                <Text.Code className="text-neon-cyan">/dev/input/js*</Text.Code>{" "}
                is accessible, then try refreshing.
              </Alert.Description>
            </Alert.Content>
          </Alert>
        ) : controllerCount === 0 ? (
          <EmptyState className="border-border rounded-2xl border border-dashed py-10">
            <EmptyState.Header>
              <EmptyState.Media variant="icon">
                <Unplug className="text-neon-cyan size-7" aria-hidden />
              </EmptyState.Media>
              <EmptyState.Title>No game controllers detected</EmptyState.Title>
              <EmptyState.Description className="text-center">
                Connect a controller via USB or Bluetooth and press refresh to
                re-scan. Devices are detected from{" "}
                <Text.Code className="text-neon-cyan">
                  /proc/bus/input
                </Text.Code>{" "}
                and{" "}
                <Text.Code className="text-neon-cyan">/dev/input/js*</Text.Code>
                .
              </EmptyState.Description>
            </EmptyState.Header>
            <EmptyState.Content className="flex justify-center pt-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onPress={() =>
                  qc.invalidateQueries({ queryKey: ["controllers"] })
                }
              >
                <RefreshCw className="size-3.5" />
                Scan again
              </Button>
            </EmptyState.Content>
          </EmptyState>
        ) : (
          <>
            {/* Summary KPIs */}
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <Activity
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Detected
                </Widget.Title>
              </Widget.Header>
              <Widget.Content>
                <KPIGroup className="flex-wrap gap-0">
                  <KPI className="min-w-[110px] flex-1 border-0 shadow-none">
                    <KPI.Header>
                      <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                        <Gamepad2 className="text-neon-cyan size-3 shrink-0" />
                        Total
                      </KPI.Title>
                    </KPI.Header>
                    <KPI.Content>
                      <span className="text-foreground text-lg font-semibold tabular-nums">
                        {controllerCount}
                      </span>
                    </KPI.Content>
                  </KPI>
                  <KPIGroup.Separator className="hidden h-8 sm:block" />
                  <KPI className="min-w-[110px] flex-1 border-0 shadow-none">
                    <KPI.Header>
                      <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                        <Usb className="text-accent size-3 shrink-0" />
                        USB
                      </KPI.Title>
                    </KPI.Header>
                    <KPI.Content>
                      <span className="text-foreground text-lg font-semibold tabular-nums">
                        {summary.usb}
                      </span>
                    </KPI.Content>
                  </KPI>
                  <KPIGroup.Separator className="hidden h-8 sm:block" />
                  <KPI className="min-w-[110px] flex-1 border-0 shadow-none">
                    <KPI.Header>
                      <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                        <Bluetooth className="text-success size-3 shrink-0" />
                        Bluetooth
                      </KPI.Title>
                    </KPI.Header>
                    <KPI.Content>
                      <span className="text-foreground text-lg font-semibold tabular-nums">
                        {summary.bt}
                      </span>
                    </KPI.Content>
                  </KPI>
                  {summary.other > 0 && (
                    <>
                      <KPIGroup.Separator className="hidden h-8 sm:block" />
                      <KPI className="min-w-[110px] flex-1 border-0 shadow-none">
                        <KPI.Header>
                          <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                            <Cable className="text-warning size-3 shrink-0" />
                            Other
                          </KPI.Title>
                        </KPI.Header>
                        <KPI.Content>
                          <span className="text-foreground text-lg font-semibold tabular-nums">
                            {summary.other}
                          </span>
                        </KPI.Content>
                      </KPI>
                    </>
                  )}
                </KPIGroup>
                {Object.keys(summary.types).length > 1 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    {Object.entries(summary.types).map(([t, n]) => {
                      const meta = metaFor(t);
                      return (
                        <Chip
                          key={t}
                          size="sm"
                          color={meta.chipColor}
                          variant="soft"
                          className="gap-1 text-[10px]"
                        >
                          <Gamepad2 className="size-3" />
                          {n} {meta.label}
                        </Chip>
                      );
                    })}
                  </div>
                )}
              </Widget.Content>
            </Widget>

            {/* Filter bar */}
            {controllerCount > 1 && (
              <Widget>
                <Widget.Content className="space-y-2.5">
                  <SearchField
                    aria-label="Filter controllers"
                    value={search}
                    onChange={setSearch}
                    fullWidth
                  >
                    <SearchField.Group>
                      <SearchField.SearchIcon>
                        <Search className="size-4" aria-hidden />
                      </SearchField.SearchIcon>
                      <SearchField.Input placeholder="Search by name, vendor:product, or device path…" />
                      <SearchField.ClearButton />
                    </SearchField.Group>
                  </SearchField>

                  <div className="flex flex-wrap items-center gap-2">
                    <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                      Type
                    </Label>
                    <FilterChip
                      label="All"
                      active={typeFilter === "all"}
                      onPress={() => setTypeFilter("all")}
                    />
                    {Object.entries(summary.types).map(([t, n]) => {
                      const meta = metaFor(t);
                      return (
                        <FilterChip
                          key={t}
                          label={`${meta.label} (${n})`}
                          color={meta.chipColor}
                          active={typeFilter === (t as FilterMode)}
                          onPress={() => setTypeFilter(t as FilterMode)}
                        />
                      );
                    })}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                      Connection
                    </Label>
                    <FilterChip
                      label="All"
                      active={connFilter === "all"}
                      onPress={() => setConnFilter("all")}
                    />
                    <FilterChip
                      label={`USB (${summary.usb})`}
                      color="accent"
                      active={connFilter === "usb"}
                      onPress={() => setConnFilter("usb")}
                    />
                    <FilterChip
                      label={`Bluetooth (${summary.bt})`}
                      color="success"
                      active={connFilter === "bluetooth"}
                      onPress={() => setConnFilter("bluetooth")}
                    />
                    {summary.other > 0 && (
                      <FilterChip
                        label={`Other (${summary.other})`}
                        color="warning"
                        active={connFilter === "other"}
                        onPress={() => setConnFilter("other")}
                      />
                    )}
                  </div>
                </Widget.Content>
              </Widget>
            )}

            {/* Per-controller cards */}
            {filtered.length === 0 ? (
              <EmptyState
                size="sm"
                className="border-border rounded-xl border border-dashed py-6"
              >
                <EmptyState.Header>
                  <EmptyState.Media variant="icon">
                    <Search className="size-5" aria-hidden />
                  </EmptyState.Media>
                  <EmptyState.Title>No matches</EmptyState.Title>
                  <EmptyState.Description>
                    Adjust the filters or clear the search to see all detected
                    controllers.
                  </EmptyState.Description>
                </EmptyState.Header>
              </EmptyState>
            ) : (
              <div className="space-y-3">
                {filtered.map((ctrl) => (
                  <ControllerCard
                    key={ctrl.id}
                    ctrl={ctrl}
                    mapping={mappings[ctrl.id]}
                    isLoadingMapping={!!loadingMapping[ctrl.id]}
                    testerOpen={!!openTester[ctrl.id]}
                    onToggleTester={(open) => toggleTester(ctrl.id, open)}
                    onRevealMapping={() => handleRevealMapping(ctrl.id)}
                    onCopyMapping={() => handleCopyMapping(ctrl.id)}
                    onCopyGuid={() =>
                      handleCopy(buildGuidFromController(ctrl), "GUID copied")
                    }
                    onCopyEnv={() =>
                      handleCopy(
                        `SDL_GAMECONTROLLERCONFIG="${mappings[ctrl.id] ?? ""}"`,
                        "Env snippet copied",
                      )
                    }
                    onDownload={() => handleDownloadMapping(ctrl)}
                  />
                ))}
              </div>
            )}

            {/* Reference tools */}
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <Wrench
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Calibration & mapping tools
                </Widget.Title>
              </Widget.Header>
              <Widget.Content>
                <ItemCardGroup variant="secondary" layout="grid">
                  {REFERENCE_TOOLS.map(({ name, description, href, Icon }) => (
                    <HeroLink
                      key={name}
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block rounded-lg no-underline"
                    >
                      <ItemCard>
                        <ItemCard.Icon className="border-border bg-surface-deep text-neon-cyan size-9 rounded-lg border">
                          <Icon className="size-4" aria-hidden />
                        </ItemCard.Icon>
                        <ItemCard.Content className="min-w-0 gap-0.5">
                          <ItemCard.Title className="flex items-center gap-1.5 text-sm">
                            {name}
                            <ExternalLink
                              className="text-muted size-3 shrink-0"
                              aria-hidden
                            />
                          </ItemCard.Title>
                          <Text.Paragraph
                            size="xs"
                            color="muted"
                            className="leading-snug"
                          >
                            {description}
                          </Text.Paragraph>
                        </ItemCard.Content>
                      </ItemCard>
                    </HeroLink>
                  ))}
                </ItemCardGroup>
              </Widget.Content>
            </Widget>

            {/* Usage guide */}
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <Info
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Using SDL mappings
                </Widget.Title>
              </Widget.Header>
              <Widget.Content className="space-y-3">
                <Text.Paragraph size="xs" color="muted" className="leading-snug">
                  SDL_GAMECONTROLLERCONFIG tells SDL-based games (most native
                  Linux titles, Proton runtime, Heroic, Lutris…) how to read
                  your pad. Apply it per-game via launch options, or globally
                  via your shell environment.
                </Text.Paragraph>

                <div className="space-y-1.5">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Steam launch options
                  </Label>
                  <pre className="border-border bg-surface-deep text-neon-cyan overflow-x-auto rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
                    SDL_GAMECONTROLLERCONFIG=&quot;...mapping...&quot; %command%
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Heroic / Lutris environment variable
                  </Label>
                  <pre className="border-border bg-surface-deep text-neon-cyan overflow-x-auto rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
                    SDL_GAMECONTROLLERCONFIG=&quot;...mapping...&quot;
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    System-wide (~/.bashrc, ~/.zshrc, ~/.profile)
                  </Label>
                  <pre className="border-border bg-surface-deep text-neon-cyan overflow-x-auto rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
                    export SDL_GAMECONTROLLERCONFIG=&quot;...mapping...&quot;
                  </pre>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    User mapping file (loaded automatically by SDL ≥ 2.0.10)
                  </Label>
                  <pre className="border-border bg-surface-deep text-neon-cyan overflow-x-auto rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
                    {`# Append the full mapping line (one per controller) to:\n~/.config/SDL_GameControllerDB.txt`}
                  </pre>
                </div>
              </Widget.Content>
            </Widget>

            {/* Info footer */}
            <Widget>
              <Widget.Content className="flex gap-3">
                <Info
                  className="text-neon-cyan mt-0.5 size-4 shrink-0"
                  aria-hidden
                />
                <Text.Paragraph
                  size="xs"
                  color="muted"
                  className="leading-relaxed"
                >
                  Controllers are detected from{" "}
                  <Text.Code className="text-neon-cyan text-[11px]">
                    /proc/bus/input/devices
                  </Text.Code>{" "}
                  with a fallback to{" "}
                  <Text.Code className="text-neon-cyan text-[11px]">
                    /dev/input/js*
                  </Text.Code>
                  . Type classification is based on vendor name matching. The
                  generated SDL mapping uses a standard Xbox-style button
                  layout — for full per-axis calibration use the SDL2 Gamepad
                  Tool, AntiMicroX, or{" "}
                  <Text.Code className="text-neon-cyan text-[11px]">
                    sdl2-jstest
                  </Text.Code>{" "}
                  above. Live input testing uses the browser&apos;s W3C Gamepad
                  API which only exposes a controller after the first input.
                </Text.Paragraph>
              </Widget.Content>
            </Widget>
          </>
        )}
      </div>
    </PageShell>
  );
}

/* ---------------------------------------------------------------------------
 * Helpers / sub-components
 * -------------------------------------------------------------------------*/

function FilterChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  color?: ChipColor;
  onPress: () => void;
}) {
  return (
    <Button
      onPress={onPress}
      size="sm"
      variant={active ? "primary" : "ghost"}
      className={`h-6 min-h-6 px-2 text-[11px] font-medium ${
        active
          ? ""
          : "border-border text-muted hover:text-foreground border"
      }`}
      aria-pressed={active}
    >
      {label}
    </Button>
  );
}

interface ControllerCardProps {
  ctrl: ControllerData;
  mapping?: string;
  isLoadingMapping: boolean;
  testerOpen: boolean;
  onToggleTester: (open: boolean) => void;
  onRevealMapping: () => void;
  onCopyMapping: () => void;
  onCopyGuid: () => void;
  onCopyEnv: () => void;
  onDownload: () => void;
}

function ControllerCard({
  ctrl,
  mapping,
  isLoadingMapping,
  testerOpen,
  onToggleTester,
  onRevealMapping,
  onCopyMapping,
  onCopyGuid,
  onCopyEnv,
  onDownload,
}: ControllerCardProps) {
  const meta = metaFor(ctrl.controller_type);
  const bus = busInfo(ctrl.bus_type);
  const BusIcon = bus.icon;
  const guid = useMemo(() => buildGuidFromController(ctrl), [ctrl]);

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex min-w-0 items-center gap-2">
          <span
            className={`border-border bg-surface-deep inline-flex size-9 shrink-0 items-center justify-center rounded-lg border ${meta.iconClass}`}
            aria-hidden
          >
            <Gamepad2 className="size-5" />
          </span>
          <span className="min-w-0 truncate" title={ctrl.name}>
            {ctrl.name}
          </span>
          <Chip color={meta.chipColor} size="sm" variant="soft" className="text-[10px]">
            {meta.label}
          </Chip>
          <Chip
            size="sm"
            color={bus.chipColor}
            variant="soft"
            className="gap-1 text-[10px]"
          >
            <BusIcon className="size-3" aria-hidden />
            {bus.short}
          </Chip>
        </Widget.Title>
        <div className="flex shrink-0 items-center gap-1.5">
          <Tooltip delay={0}>
            <Button
              variant="outline"
              size="sm"
              onPress={onCopyMapping}
              className="gap-1.5"
            >
              <Copy className="size-3 shrink-0" aria-hidden />
              Copy SDL
            </Button>
            <Tooltip.Content>
              Copy SDL_GAMECONTROLLERCONFIG mapping to clipboard
            </Tooltip.Content>
          </Tooltip>
        </div>
      </Widget.Header>

      <Widget.Content className="space-y-3">
        {/* KPI strip */}
        <KPIGroup className="flex-wrap gap-0">
          <KPI className="min-w-[140px] flex-1 border-0 shadow-none">
            <KPI.Header>
              <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                <Hash className="text-neon-cyan size-3 shrink-0" />
                Vendor:Product
              </KPI.Title>
            </KPI.Header>
            <KPI.Content>
              <span className="text-foreground font-mono text-sm tabular-nums">
                {formatHexId(ctrl.vendor_id)}:{formatHexId(ctrl.product_id)}
              </span>
            </KPI.Content>
          </KPI>
          <KPIGroup.Separator className="hidden h-8 sm:block" />
          <KPI className="min-w-[100px] flex-1 border-0 shadow-none">
            <KPI.Header>
              <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                <BusIcon className="text-neon-cyan size-3 shrink-0" />
                Bus
              </KPI.Title>
            </KPI.Header>
            <KPI.Content>
              <span className="text-foreground text-sm tabular-nums">
                {bus.label}
              </span>
            </KPI.Content>
          </KPI>
          <KPIGroup.Separator className="hidden h-8 sm:block" />
          <KPI className="min-w-[100px] flex-1 border-0 shadow-none">
            <KPI.Header>
              <KPI.Title className="text-muted flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide">
                <Tags className="text-neon-cyan size-3 shrink-0" />
                Version
              </KPI.Title>
            </KPI.Header>
            <KPI.Content>
              <span className="text-foreground font-mono text-sm tabular-nums">
                {formatHexId(ctrl.version)}
              </span>
            </KPI.Content>
          </KPI>
        </KPIGroup>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px]">
          <span className="text-muted flex items-center gap-1.5">
            <MapPin className="size-3 shrink-0" aria-hidden />
            Device
            <Text.Code className="text-foreground text-[11px]">
              {ctrl.device_path}
            </Text.Code>
          </span>
          <span className="text-muted flex items-center gap-1.5">
            <Fingerprint className="size-3 shrink-0" aria-hidden />
            GUID
            <Text.Code
              className="text-neon-cyan max-w-[260px] truncate text-[11px]"
              title={guid}
            >
              {guid}
            </Text.Code>
            <Tooltip delay={0}>
              <Button
                size="sm"
                variant="ghost"
                isIconOnly
                aria-label="Copy GUID"
                className="-my-1 size-6 min-h-6"
                onPress={onCopyGuid}
              >
                <Copy className="size-3" aria-hidden />
              </Button>
              <Tooltip.Content>Copy SDL2 GUID</Tooltip.Content>
            </Tooltip>
          </span>
        </div>

        {/* Live tester */}
        <Disclosure
          isExpanded={testerOpen}
          onExpandedChange={onToggleTester}
        >
          <Disclosure.Heading>
            <Button
              slot="trigger"
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 px-2 text-xs"
            >
              <Activity className="size-3.5 shrink-0" aria-hidden />
              Live input test
              <Disclosure.Indicator />
            </Button>
          </Disclosure.Heading>
          <Disclosure.Content>
            <Disclosure.Body className="pt-2">
              <GamepadTester matchId={ctrl.id} active={testerOpen} />
            </Disclosure.Body>
          </Disclosure.Content>
        </Disclosure>

        {/* SDL mapping disclosure */}
        <Disclosure
          onExpandedChange={(expanded) => {
            if (expanded) onRevealMapping();
          }}
        >
          <Disclosure.Heading>
            <Button
              slot="trigger"
              variant="ghost"
              size="sm"
              className="h-8 gap-1.5 px-2 text-xs"
            >
              <ChevronDown className="size-3.5 shrink-0" aria-hidden />
              SDL mapping
              <Disclosure.Indicator />
              {isLoadingMapping && <Spinner size="sm" className="ml-1" />}
            </Button>
          </Disclosure.Heading>
          <Disclosure.Content>
            <Disclosure.Body className="space-y-2 pt-2">
              {mapping ? (
                <>
                  <pre className="border-border bg-surface-deep text-foreground overflow-x-auto whitespace-pre-wrap break-all rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
                    {mapping}
                  </pre>
                  <div className="flex flex-wrap gap-1.5">
                    <Button
                      size="sm"
                      variant="outline"
                      onPress={onCopyMapping}
                      className="h-7 min-h-7 gap-1.5 px-2 text-xs"
                    >
                      <Copy className="size-3 shrink-0" aria-hidden />
                      Copy mapping
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onPress={onCopyEnv}
                      className="h-7 min-h-7 gap-1.5 px-2 text-xs"
                    >
                      <Copy className="size-3 shrink-0" aria-hidden />
                      Copy as env var
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onPress={onDownload}
                      className="h-7 min-h-7 gap-1.5 px-2 text-xs"
                    >
                      <Download className="size-3 shrink-0" aria-hidden />
                      Download .txt
                    </Button>
                  </div>
                </>
              ) : isLoadingMapping ? (
                <div className="text-muted flex items-center gap-2 text-xs">
                  <Spinner size="sm" />
                  Generating mapping…
                </div>
              ) : (
                <Text.Paragraph size="xs" color="muted">
                  Could not load mapping.
                </Text.Paragraph>
              )}
            </Disclosure.Body>
          </Disclosure.Content>
        </Disclosure>
      </Widget.Content>
    </Widget>
  );
}
