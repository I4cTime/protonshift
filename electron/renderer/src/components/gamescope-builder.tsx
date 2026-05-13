"use client";

import { useState, useEffect, useMemo } from "react";
import type { Key } from "react-aria-components";
import {
  Monitor,
  Copy,
  Plus,
  Check,
  Maximize2,
  Sparkles,
  Grid3x3,
  Sun,
  RectangleHorizontal,
  Square,
  RefreshCw,
  Gauge,
  Zap,
  type LucideIcon,
} from "lucide-react";
import {
  Button,
  ButtonGroup,
  Chip,
  Description,
  Disclosure,
  Label,
  Link as HeroLink,
  ListBox,
  NumberField,
  Separator,
  Switch,
  Text,
  TextArea,
  TextField,
  Tooltip,
  Card,
} from "@heroui/react";
import {
  CellSlider,
  CheckboxButtonGroup,
  InlineSelect,
  NumberStepper,
  Segment,
  Sheet,
  Widget,
} from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import { api, type GamescopeOptions, type ScopeBuddyAutoCaps } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

interface GamescopeBuilderProps {
  onInsert: (cmd: string) => void;
  /** Latest raw ``gamescope … --`` preview (not ScopeBuddy wrap) for per-game scb.conf helpers. */
  onBuiltLineChange?: (line: string) => void;
}

const DEFAULT_OPTS: GamescopeOptions = {
  output_width: 1920,
  output_height: 1080,
  game_width: 1920,
  game_height: 1080,
  fps_limit: 0,
  fsr: false,
  fsr_sharpness: 5,
  integer_scale: false,
  hdr: false,
  nested: true,
  borderless: true,
  fullscreen: true,
  extra_args: "",
  wrap_with_scopebuddy: false,
  scb_auto_res: false,
  scb_auto_hdr: false,
  scb_auto_vrr: false,
  scb_auto_refresh: false,
  scb_auto_frame_limit: false,
  scb_noscope: false,
};

const RESOLUTION_PRESETS = [
  { label: "720p", w: 1280, h: 720 },
  { label: "1080p", w: 1920, h: 1080 },
  { label: "1440p", w: 2560, h: 1440 },
  { label: "4K", w: 3840, h: 2160 },
] as const;

const FEATURE_DEFS: {
  id: keyof Pick<GamescopeOptions, "fsr" | "integer_scale" | "hdr" | "fullscreen" | "borderless">;
  label: string;
  short: string;
  Icon: LucideIcon;
}[] = [
  { id: "fsr", label: "FSR upscale", short: "FSR", Icon: Sparkles },
  { id: "integer_scale", label: "Integer scale", short: "1:1", Icon: Grid3x3 },
  { id: "hdr", label: "HDR output", short: "HDR", Icon: Sun },
  { id: "fullscreen", label: "Fullscreen", short: "FS", Icon: Square },
  { id: "borderless", label: "Borderless", short: "BL", Icon: RectangleHorizontal },
];

const SCB_AUTO_DEFS: {
  id: keyof Pick<
    GamescopeOptions,
    | "scb_auto_res"
    | "scb_auto_hdr"
    | "scb_auto_vrr"
    | "scb_auto_refresh"
    | "scb_auto_frame_limit"
  >;
  label: string;
  short: string;
  Icon: LucideIcon;
}[] = [
  { id: "scb_auto_res", label: "Auto resolution (-W/-H)", short: "RES", Icon: Maximize2 },
  { id: "scb_auto_hdr", label: "Auto HDR if display supports it", short: "HDR", Icon: Sun },
  { id: "scb_auto_vrr", label: "Adaptive sync if active", short: "VRR", Icon: Zap },
  { id: "scb_auto_refresh", label: "Explicit refresh (-r)", short: "Hz", Icon: RefreshCw },
  { id: "scb_auto_frame_limit", label: "Match framerate limiter to display", short: "Cap", Icon: Gauge },
];

const SCOPEBUDDY_INSTALL_ROWS: { distro: string; cmd: string }[] = [
  { distro: "Bazzite / SteamOS", cmd: "Often pre-installed — check PATH for scb / scopebuddy" },
  { distro: "Fedora (Terra)", cmd: "sudo dnf install ScopeBuddy" },
  { distro: "Arch / AUR", cmd: "yay -S scopebuddy-git" },
  {
    distro: "Any distro",
    cmd: "curl -fsSL …/scopebuddy | sudo tee /usr/local/bin/scopebuddy && sudo chmod +x /usr/local/bin/scopebuddy",
  },
  { distro: "NixOS / Home Manager", cmd: "inputs.scopebuddy.url = github:HikariKnight/ScopeBuddy" },
];

function presetKeyFromOpts(o: GamescopeOptions): string {
  for (const p of RESOLUTION_PRESETS) {
    if (
      o.output_width === p.w &&
      o.output_height === p.h &&
      o.game_width === p.w &&
      o.game_height === p.h
    ) {
      return p.label;
    }
  }
  return "custom";
}

function canUseScbAutoDetect(caps: ScopeBuddyAutoCaps | undefined): boolean {
  if (!caps?.jq) return false;
  return caps.kde || caps.gnome_gdctl || caps.gnome_randr || caps.wlroots;
}

function autoDetectTooltip(caps: ScopeBuddyAutoCaps | undefined): string {
  if (!caps?.jq) return "Install jq for SCB_AUTO_* display probing.";
  if (!caps.kde && !caps.gnome_gdctl && !caps.gnome_randr && !caps.wlroots) {
    return "No KDE (kscreen-doctor), GNOME (gdctl / gnome-randr), or wlr-randr probe available.";
  }
  const bits: string[] = [];
  if (caps.kde) bits.push("KDE (kscreen-doctor)");
  if (caps.gnome_gdctl) bits.push("GNOME (gdctl JSON)");
  if (caps.gnome_randr && !caps.gnome_gdctl) bits.push("GNOME (gnome-randr)");
  if (caps.wlroots) bits.push("wlroots (wlr-randr)");
  return `Auto-detect may use: ${bits.join(", ")}.`;
}

export function GamescopeBuilder({ onInsert, onBuiltLineChange }: GamescopeBuilderProps) {
  const qc = useQueryClient();

  const { data: availData } = useQuery({
    queryKey: ["gamescope-available"],
    queryFn: api.getGamescopeAvailable,
    staleTime: 60_000,
  });

  const { data: scbAvail } = useQuery({
    queryKey: ["scopebuddy-available"],
    queryFn: api.getScopeBuddyAvailable,
    staleTime: 60_000,
  });

  const rescanMut = useMutation({
    mutationFn: () => api.rescanScopeBuddy(),
    onSuccess: async (info) => {
      qc.setQueryData(["scopebuddy-available"], info);
      await qc.invalidateQueries({ queryKey: ["scopebuddy-auto-caps"] });
      if (info.available) {
        appShowToast(`ScopeBuddy found: ${info.binary}${info.version ? ` v${info.version}` : ""}`);
      } else {
        appShowToast("ScopeBuddy still not detected on PATH", "error");
      }
    },
    onError: () => appShowToast("Rescan failed", "error"),
  });

  const { data: scbCaps } = useQuery({
    queryKey: ["scopebuddy-auto-caps"],
    queryFn: api.getScopeBuddyAutoCaps,
    staleTime: 60_000,
    enabled: !!scbAvail?.available,
  });

  const [opts, setOpts] = useState<GamescopeOptions>(DEFAULT_OPTS);
  const [preview, setPreview] = useState("");
  const [copied, setCopied] = useState(false);
  const [commandSheetOpen, setCommandSheetOpen] = useState(false);

  const presetKey = useMemo(() => presetKeyFromOpts(opts), [opts]);

  const selectedFeatureKeys = useMemo(
    () => FEATURE_DEFS.filter((f) => opts[f.id]).map((f) => f.id),
    [opts],
  );

  const selectedScbAutoKeys = useMemo(
    () => SCB_AUTO_DEFS.filter((f) => opts[f.id]).map((f) => f.id),
    [opts],
  );

  const canAuto = useMemo(() => canUseScbAutoDetect(scbCaps), [scbCaps]);

  useEffect(() => {
    let cancelled = false;
    void api.buildGamescopeCmd(opts).then(
      (res) => {
        if (!cancelled) setPreview(res.command);
      },
      () => {
        if (!cancelled) setPreview(opts.wrap_with_scopebuddy ? "scb --" : "gamescope --");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [opts]);

  useEffect(() => {
    if (!opts.wrap_with_scopebuddy && preview && !preview.startsWith("SCB_")) {
      onBuiltLineChange?.(preview);
    }
  }, [preview, opts.wrap_with_scopebuddy, onBuiltLineChange]);

  function update(patch: Partial<GamescopeOptions>) {
    setOpts((prev) => ({ ...prev, ...patch }));
  }

  function handleCopy() {
    navigator.clipboard.writeText(preview);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handlePresetChange(k: Key | null) {
    const id = String(k ?? "");
    if (id === "custom") return;
    const p = RESOLUTION_PRESETS.find((x) => x.label === id);
    if (p) {
      update({
        output_width: p.w,
        output_height: p.h,
        game_width: p.w,
        game_height: p.h,
      });
    }
  }

  function handleFeaturesChange(keys: Iterable<Key>) {
    const set = new Set([...keys].map(String));
    const patch: Partial<GamescopeOptions> = {};
    for (const f of FEATURE_DEFS) {
      patch[f.id] = set.has(f.id);
    }
    update(patch);
  }

  function handleScbAutoChange(keys: Iterable<Key>) {
    const set = new Set([...keys].map(String));
    const patch: Partial<GamescopeOptions> = {};
    for (const f of SCB_AUTO_DEFS) {
      patch[f.id] = set.has(f.id);
    }
    update(patch);
  }

  function handleBuildModeChange(k: Key) {
    const id = String(k);
    update({ wrap_with_scopebuddy: id === "scopebuddy" });
  }

  const activeGsCount = FEATURE_DEFS.filter((f) => opts[f.id]).length;
  const activeScbCount =
    SCB_AUTO_DEFS.filter((f) => opts[f.id]).length + (opts.scb_noscope ? 1 : 0);
  const activeCount = opts.wrap_with_scopebuddy ? activeScbCount : activeGsCount;

  const wrapMode = opts.wrap_with_scopebuddy;

  /* ---------- Not installed ---------- */
  if (!availData?.available) {
    return (
      <Widget>
        <Widget.Header>
          <Widget.Title className="flex items-center gap-1.5">
            <Monitor className="size-4 text-neon-cyan" />
            Gamescope
            <Chip size="sm" color="warning" variant="soft" className="ml-1 text-[10px]">
              Not installed
            </Chip>
          </Widget.Title>
          <InfoHint label="About Gamescope">
            Micro-compositor for per-game resolution, FPS cap, FSR, and HDR. ScopeBuddy also requires
            gamescope at runtime.
          </InfoHint>
        </Widget.Header>
        <Widget.Content className="space-y-2">
          <Text.Paragraph size="xs" color="muted">
            Install gamescope, then restart this app.{" "}
            <HeroLink
              href="https://github.com/ValveSoftware/gamescope"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neon-cyan text-xs"
            >
              Valve gamescope
            </HeroLink>
          </Text.Paragraph>
          <Disclosure defaultExpanded={false}>
            <Disclosure.Heading>
              <Button slot="trigger" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
                <Maximize2 className="size-3.5 shrink-0" />
                Install hints by distro
                <Disclosure.Indicator />
              </Button>
            </Disclosure.Heading>
            <Disclosure.Content>
              <Disclosure.Body className="space-y-2 pt-1">
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {[
                    { distro: "Bazzite / SteamOS", cmd: "Pre-installed — check PATH" },
                    { distro: "Arch / Manjaro", cmd: "sudo pacman -S gamescope" },
                    { distro: "Fedora", cmd: "sudo dnf install gamescope" },
                    { distro: "openSUSE", cmd: "sudo zypper install gamescope" },
                    { distro: "NixOS", cmd: "nix-env -iA nixpkgs.gamescope" },
                    { distro: "Steam Flatpak", cmd: "Bundled with Steam" },
                  ].map((item) => (
                    <Card key={item.distro} className="border-border bg-surface-secondary/40 p-2.5">
                      <Card.Header className="p-0 pb-1">
                        <Card.Title className="text-muted text-[11px] font-medium">{item.distro}</Card.Title>
                      </Card.Header>
                      <Card.Content className="p-0">
                        <Text.Code className="text-neon-cyan block truncate text-xs">{item.cmd}</Text.Code>
                      </Card.Content>
                    </Card>
                  ))}
                </div>
                <Card className="border-border bg-surface-secondary/40 p-2.5">
                  <Card.Header className="p-0 pb-1">
                    <Card.Title className="text-muted text-[11px] font-medium">Ubuntu / Pop!_OS</Card.Title>
                  </Card.Header>
                  <Card.Content className="p-0">
                    <Text.Paragraph size="xs">
                      <HeroLink
                        href="https://github.com/akdor1154/gamescope-pkg/releases/latest"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-neon-cyan"
                      >
                        .deb release
                      </HeroLink>{" "}
                      or PPA <Text.Code className="text-neon-cyan">ppa:kgraefe/gamescope</Text.Code>
                    </Text.Paragraph>
                  </Card.Content>
                </Card>
              </Disclosure.Body>
            </Disclosure.Content>
          </Disclosure>
        </Widget.Content>
      </Widget>
    );
  }

  /* ---------- Builder (compact) ---------- */
  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Monitor className="size-4 text-neon-cyan" />
          Gamescope
          <Chip size="sm" variant="secondary" className="ml-1 text-[10px]">
            {activeCount} on
          </Chip>
        </Widget.Title>
        <InfoHint label="About this builder">
          Build a raw gamescope prefix, or a short ScopeBuddy line (scb --) with SCB_AUTO_* flags. Put
          detailed gamescope args in ~/.config/scopebuddy/scb.conf or the per-game override below.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        <div className="rounded-xl border border-border bg-surface-secondary/30 p-1">
          <Segment
            aria-label="Gamescope build mode"
            variant="ghost"
            size="sm"
            selectedKey={wrapMode ? "scopebuddy" : "gamescope"}
            onSelectionChange={(k) => handleBuildModeChange(k)}
            className="flex w-full min-w-0 gap-0"
          >
            <Segment.Item id="gamescope" className="min-w-0 flex-1 basis-0 justify-center">
              Raw gamescope
            </Segment.Item>
            <Segment.Separator />
            <Tooltip delay={0} isDisabled={!!scbAvail?.available}>
              <Segment.Item
                id="scopebuddy"
                isDisabled={!scbAvail?.available}
                className="min-w-0 flex-1 basis-0 justify-center"
              >
                ScopeBuddy
              </Segment.Item>
              <Tooltip.Content>Install ScopeBuddy (scb) to enable this mode.</Tooltip.Content>
            </Tooltip>
          </Segment>
        </div>

        {availData?.available && !scbAvail?.available && (
          <Card className="border-border bg-surface-secondary/40 p-2.5">
            <Card.Header className="p-0 pb-1">
              <Card.Title className="text-muted flex flex-wrap items-center gap-2 text-[11px] font-medium">
                <span>ScopeBuddy not found</span>
                <Tooltip delay={0}>
                  <Button
                    size="sm"
                    variant="outline"
                    className="ml-auto h-7 gap-1 px-2 text-[10px]"
                    onPress={() => rescanMut.mutate()}
                    isDisabled={rescanMut.isPending}
                    aria-label="Rescan for scopebuddy on PATH"
                  >
                    <RefreshCw
                      className={`size-3 shrink-0 ${rescanMut.isPending ? "animate-spin" : ""}`}
                      aria-hidden
                    />
                    Rescan
                  </Button>
                  <Tooltip.Content className="max-w-xs text-xs">
                    Re-check PATH for scb / scopebuddy without restarting the app.
                  </Tooltip.Content>
                </Tooltip>
              </Card.Title>
            </Card.Header>
            <Card.Content className="space-y-2 p-0">
              <Text.Paragraph size="xs" color="muted">
                Optional wrapper for nested gamescope, Steam overlay fixes, and SCB_AUTO_* display
                detection.{" "}
                <HeroLink
                  href="https://github.com/OpenGamingCollective/ScopeBuddy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-neon-cyan"
                >
                  ScopeBuddy
                </HeroLink>
              </Text.Paragraph>
              <Disclosure defaultExpanded={false}>
                <Disclosure.Heading>
                  <Button slot="trigger" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
                    Install hints
                    <Disclosure.Indicator />
                  </Button>
                </Disclosure.Heading>
                <Disclosure.Content>
                  <Disclosure.Body className="grid grid-cols-1 gap-2 pt-1 sm:grid-cols-2">
                    {SCOPEBUDDY_INSTALL_ROWS.map((row) => (
                      <Card key={row.distro} className="border-border bg-surface-deep/50 p-2">
                        <Card.Title className="text-muted mb-1 text-[10px] font-medium">{row.distro}</Card.Title>
                        <Text.Code className="text-neon-cyan block text-[10px] leading-snug break-all">
                          {row.cmd}
                        </Text.Code>
                      </Card>
                    ))}
                  </Disclosure.Body>
                </Disclosure.Content>
              </Disclosure>
            </Card.Content>
          </Card>
        )}

        {/* Preset + preview line */}
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
          {!wrapMode && (
            <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
              <Label className="text-muted shrink-0 text-[10px] font-semibold uppercase tracking-wide">
                Preset
              </Label>
              <InlineSelect
                aria-label="Resolution preset"
                value={presetKey}
                onChange={(v) => handlePresetChange(v)}
              >
                <InlineSelect.Trigger className="min-h-8 gap-1.5 text-sm">
                  <InlineSelect.Value />
                  <InlineSelect.Indicator />
                </InlineSelect.Trigger>
                <InlineSelect.Popover className="min-w-[9rem]" placement="bottom start">
                  <ListBox>
                    {RESOLUTION_PRESETS.map((p) => (
                      <ListBox.Item key={p.label} id={p.label} textValue={p.label}>
                        {p.label}
                        <ListBox.ItemIndicator />
                      </ListBox.Item>
                    ))}
                    <ListBox.Item id="custom" textValue="Custom">
                      Custom
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  </ListBox>
                </InlineSelect.Popover>
              </InlineSelect>
            </div>
          )}
          {wrapMode && (
            <Text.Paragraph size="xs" color="muted" className="min-w-0 flex-1 leading-snug">
              Use the per-game ScopeBuddy override widget for <Text.Code className="text-neon-cyan">SCB_GAMESCOPE_ARGS</Text.Code>{" "}
              (resolution, FSR, etc.). This line only sets env flags and invokes{" "}
              <Text.Code className="text-neon-cyan">{scbAvail?.binary || "scb"}</Text.Code>.
            </Text.Paragraph>
          )}
          <Tooltip delay={0}>
            <Text.Code className="text-muted bg-surface-deep border-border block max-w-full truncate rounded-md border px-2 py-1 text-[11px] leading-tight">
              {preview}
            </Text.Code>
            <Tooltip.Content className="max-w-md font-mono text-xs">{preview}</Tooltip.Content>
          </Tooltip>
        </div>

        <Separator />

        {!wrapMode ? (
          <>
            <div className="space-y-1.5">
              <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">Features</Label>
              <CheckboxButtonGroup
                aria-label="Gamescope features"
                className="grid w-full grid-cols-2 gap-1.5 min-[420px]:grid-cols-3 min-[560px]:grid-cols-5"
                layout="grid"
                name="gamescope-features"
                value={selectedFeatureKeys}
                variant="secondary"
                onChange={(keys) => handleFeaturesChange(keys)}
              >
                {FEATURE_DEFS.map((feat) => {
                  const Icon = feat.Icon;
                  return (
                    <CheckboxButtonGroup.Item key={feat.id} value={feat.id} className="min-h-[5.25rem]">
                      <CheckboxButtonGroup.Indicator />
                      <CheckboxButtonGroup.ItemContent className="gap-1 py-1">
                        <CheckboxButtonGroup.ItemIcon className="text-neon-cyan">
                          <Icon className="size-3.5 shrink-0" aria-hidden />
                        </CheckboxButtonGroup.ItemIcon>
                        <Label className="text-[11px] font-semibold leading-tight">{feat.short}</Label>
                        <Description className="text-muted line-clamp-2 text-[10px] leading-snug">
                          {feat.label}
                        </Description>
                      </CheckboxButtonGroup.ItemContent>
                    </CheckboxButtonGroup.Item>
                  );
                })}
              </CheckboxButtonGroup>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:gap-4">
              <div className="min-w-0 shrink-0 space-y-1">
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">FPS cap</Label>
                <Text.Paragraph size="xs" color="muted" className="text-[10px]">
                  0 = off
                </Text.Paragraph>
                <NumberStepper
                  aria-label="FPS limit"
                  minValue={0}
                  maxValue={360}
                  step={1}
                  value={opts.fps_limit}
                  onChange={(v) => update({ fps_limit: v })}
                >
                  <NumberStepper.Group>
                    <NumberStepper.DecrementButton />
                    <NumberStepper.Value className="min-w-[2.75rem] font-mono text-sm tabular-nums" />
                    <NumberStepper.IncrementButton />
                  </NumberStepper.Group>
                </NumberStepper>
              </div>
              {opts.fsr && (
                <div className="min-w-0 flex-1">
                  <CellSlider
                    aria-label="FSR sharpness"
                    minValue={0}
                    maxValue={20}
                    step={1}
                    value={opts.fsr_sharpness}
                    variant="secondary"
                    onChange={(v) => update({ fsr_sharpness: v as number })}
                  >
                    <CellSlider.Track>
                      <CellSlider.Fill />
                      <CellSlider.Thumb />
                      <CellSlider.Label>FSR sharpness</CellSlider.Label>
                      <CellSlider.Output />
                    </CellSlider.Track>
                  </CellSlider>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                  SCB_AUTO_* (display)
                </Label>
                <Tooltip delay={0}>
                  <Chip size="sm" variant="secondary" className="text-[9px]">
                    {canAuto ? "Probe OK" : "Limited"}
                  </Chip>
                  <Tooltip.Content className="max-w-xs text-xs">{autoDetectTooltip(scbCaps)}</Tooltip.Content>
                </Tooltip>
              </div>
              <CheckboxButtonGroup
                aria-label="ScopeBuddy auto flags"
                className="grid w-full grid-cols-2 gap-1.5 min-[420px]:grid-cols-3 min-[560px]:grid-cols-5"
                layout="grid"
                name="scopebuddy-auto"
                value={selectedScbAutoKeys}
                variant="secondary"
                onChange={(keys) => handleScbAutoChange(keys)}
              >
                {SCB_AUTO_DEFS.map((feat) => {
                  const Icon = feat.Icon;
                  const disabled = !canAuto;
                  const item = (
                    <CheckboxButtonGroup.Item
                      key={feat.id}
                      value={feat.id}
                      isDisabled={disabled}
                      className="min-h-[5.25rem]"
                    >
                      <CheckboxButtonGroup.Indicator />
                      <CheckboxButtonGroup.ItemContent className="gap-1 py-1">
                        <CheckboxButtonGroup.ItemIcon className="text-neon-cyan">
                          <Icon className="size-3.5 shrink-0" aria-hidden />
                        </CheckboxButtonGroup.ItemIcon>
                        <Label className="text-[11px] font-semibold leading-tight">{feat.short}</Label>
                        <Description className="text-muted line-clamp-2 text-[10px] leading-snug">
                          {feat.label}
                        </Description>
                      </CheckboxButtonGroup.ItemContent>
                    </CheckboxButtonGroup.Item>
                  );
                  return disabled ? (
                    <Tooltip key={feat.id} delay={0}>
                      {item}
                      <Tooltip.Content className="max-w-xs text-xs">{autoDetectTooltip(scbCaps)}</Tooltip.Content>
                    </Tooltip>
                  ) : (
                    item
                  );
                })}
              </CheckboxButtonGroup>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface-secondary/30 px-3 py-2">
              <div className="min-w-0 space-y-0.5">
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">SCB_NOSCOPE</Label>
                <Text.Paragraph size="xs" color="muted" className="text-[10px] leading-snug">
                  Skip gamescope (experimental HDR path with Proton 10+ Wayland).
                </Text.Paragraph>
              </div>
              <Switch
                isSelected={opts.scb_noscope}
                onChange={() => update({ scb_noscope: !opts.scb_noscope })}
                aria-label="SCB_NOSCOPE experimental no-gamescope mode"
              >
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch>
            </div>
          </div>
        )}

        <Separator />

        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <ButtonGroup className="w-full sm:w-auto">
            <Tooltip delay={0}>
              <Button size="sm" onPress={() => onInsert(preview)} className="gap-1.5">
                <Plus className="size-3.5 shrink-0" />
                Insert
              </Button>
              <Tooltip.Content>Prepend to launch options</Tooltip.Content>
            </Tooltip>
            <Tooltip delay={0}>
              <Button variant="outline" size="sm" onPress={handleCopy} className="gap-1.5">
                {copied ? <Check className="size-3.5 shrink-0" /> : <Copy className="size-3.5 shrink-0" />}
                {copied ? "Copied" : "Copy"}
              </Button>
              <Tooltip.Content>Copy full command</Tooltip.Content>
            </Tooltip>
            <Button size="sm" variant="secondary" onPress={() => setCommandSheetOpen(true)}>
              Full command
            </Button>
          </ButtonGroup>
        </div>

        <Sheet isOpen={commandSheetOpen} onOpenChange={setCommandSheetOpen}>
          <Sheet.Backdrop variant="blur">
            <Sheet.Content className="mx-auto max-h-[90vh] max-w-[min(100vw-1rem,520px)]">
              <Sheet.Dialog>
                <Sheet.Handle />
                <Sheet.CloseTrigger />
                <Sheet.Header>
                  <Sheet.Heading>{wrapMode ? "Launch prefix" : "Gamescope command"}</Sheet.Heading>
                </Sheet.Header>
                <Sheet.Body>
                  <pre className="text-muted max-h-[55vh] overflow-auto rounded-lg border border-border bg-surface-deep p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all text-neon-cyan">
                    {preview}
                  </pre>
                </Sheet.Body>
                <Sheet.Footer className="flex flex-wrap gap-2">
                  <Sheet.Close>
                    <Button variant="secondary" size="sm">
                      Close
                    </Button>
                  </Sheet.Close>
                  <Button
                    size="sm"
                    onPress={() => {
                      handleCopy();
                      setCommandSheetOpen(false);
                    }}
                    className="gap-1.5"
                  >
                    {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </Sheet.Footer>
              </Sheet.Dialog>
            </Sheet.Content>
          </Sheet.Backdrop>
        </Sheet>

        {!wrapMode && (
          <Disclosure defaultExpanded={false}>
            <Disclosure.Heading>
              <Button slot="trigger" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
                <Maximize2 className="size-3.5 shrink-0" />
                Custom resolution and extra args
                <Disclosure.Indicator />
              </Button>
            </Disclosure.Heading>
            <Disclosure.Content>
              <Disclosure.Body className="space-y-3 border-t border-separator pt-3">
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(
                    [
                      { key: "output_width", label: "Out W" },
                      { key: "output_height", label: "Out H" },
                      { key: "game_width", label: "Game W" },
                      { key: "game_height", label: "Game H" },
                    ] as const
                  ).map(({ key, label }) => (
                    <NumberField
                      key={key}
                      minValue={0}
                      step={8}
                      value={opts[key]}
                      onChange={(v) => update({ [key]: v ?? 0 } as Partial<GamescopeOptions>)}
                      formatOptions={{ useGrouping: false }}
                      aria-label={label}
                      variant="secondary"
                      fullWidth
                    >
                      <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                        {label}
                      </Label>
                      <NumberField.Group>
                        <NumberField.DecrementButton />
                        <NumberField.Input className="font-mono text-xs" />
                        <NumberField.IncrementButton />
                      </NumberField.Group>
                    </NumberField>
                  ))}
                </div>
                <TextField
                  value={opts.extra_args}
                  onChange={(v) => update({ extra_args: v })}
                  variant="secondary"
                  fullWidth
                >
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Extra gamescope args
                  </Label>
                  <TextArea
                    placeholder="e.g. --hdr-itm-enable"
                    rows={2}
                    className="resize-none font-mono text-xs"
                  />
                </TextField>
              </Disclosure.Body>
            </Disclosure.Content>
          </Disclosure>
        )}
      </Widget.Content>
    </Widget>
  );
}
