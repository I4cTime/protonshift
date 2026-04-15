"use client";

import { useState, useEffect, useCallback } from "react";
import { Monitor, Copy, Plus, Check, Maximize2, Gauge, Sparkles, Info } from "lucide-react";
import {
  Button,
  Chip,
  Description,
  Fieldset,
  FieldGroup,
  Label,
  NumberField,
  Separator,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Link as HeroLink,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import { api, type GamescopeOptions } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";

interface GamescopeBuilderProps {
  onInsert: (cmd: string) => void;
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
};

const FEATURE_DEFS = [
  { id: "fsr" as const, label: "FSR", description: "AMD FidelityFX Super Resolution — upscale lower game resolution to output resolution" },
  { id: "integer_scale" as const, label: "Integer Scale", description: "Pixel-perfect scaling — best for retro/pixel-art games" },
  { id: "hdr" as const, label: "HDR", description: "High Dynamic Range output — requires HDR-capable display and driver support" },
  { id: "fullscreen" as const, label: "Fullscreen", description: "Run the nested compositor in exclusive fullscreen mode" },
  { id: "borderless" as const, label: "Borderless", description: "Borderless window mode — easier Alt+Tab, slight input latency trade-off" },
];

const RESOLUTION_PRESETS = [
  { label: "720p", w: 1280, h: 720 },
  { label: "1080p", w: 1920, h: 1080 },
  { label: "1440p", w: 2560, h: 1440 },
  { label: "4K", w: 3840, h: 2160 },
];

export function GamescopeBuilder({ onInsert }: GamescopeBuilderProps) {
  const { data: availData } = useQuery({
    queryKey: ["gamescope-available"],
    queryFn: api.getGamescopeAvailable,
    staleTime: 60_000,
  });

  const [opts, setOpts] = useState<GamescopeOptions>(DEFAULT_OPTS);
  const [preview, setPreview] = useState("");
  const [copied, setCopied] = useState(false);

  const updatePreview = useCallback(async (o: GamescopeOptions) => {
    try {
      const res = await api.buildGamescopeCmd(o);
      setPreview(res.command);
    } catch {
      setPreview("gamescope --");
    }
  }, []);

  useEffect(() => {
    updatePreview(opts);
  }, [opts, updatePreview]);

  function update(patch: Partial<GamescopeOptions>) {
    setOpts((prev) => ({ ...prev, ...patch }));
  }

  function handleCopy() {
    navigator.clipboard.writeText(preview);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const featureKeys = ["fsr", "integer_scale", "hdr", "fullscreen", "borderless"] as const;
  const activeFeatures = new Set(featureKeys.filter((k) => opts[k]));
  const activeCount = activeFeatures.size;

  /* ---------- Not installed ---------- */
  if (!availData?.available) {
    return (
      <GlowCard className="p-5 space-y-3">
        <div>
          <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
            <Monitor className="size-4 text-neon-cyan" />
            Gamescope Builder
            <Chip size="sm" color="warning" variant="soft" className="text-[10px]">
              Not Installed
            </Chip>
          </label>
          <Description className="mt-1">
            Gamescope is a SteamOS micro-compositor for controlling resolution, FPS limits, FSR upscaling, and HDR per game.
          </Description>
        </div>
        <Separator />
        <div className="space-y-1.5">
          <p className="text-xs text-text-secondary font-medium">Install via your package manager:</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {[
              { distro: "Arch / Manjaro / EndeavourOS", cmd: "sudo pacman -S gamescope" },
              { distro: "Fedora", cmd: "sudo dnf install gamescope" },
              { distro: "openSUSE", cmd: "sudo zypper install gamescope" },
              { distro: "NixOS", cmd: "nix-env -iA nixpkgs.gamescope" },
              { distro: "Flatpak (Steam)", cmd: "Bundled with Steam Flatpak" },
            ].map((item) => (
              <div key={item.distro} className="p-2 rounded-lg bg-surface-deep border border-separator">
                <p className="text-xs text-text-muted">{item.distro}</p>
                <code className="text-xs text-neon-cyan font-mono">{item.cmd}</code>
              </div>
            ))}
          </div>
          <div className="p-2 rounded-lg bg-surface-deep border border-separator">
            <p className="text-xs text-text-muted">Ubuntu / Pop!_OS / Mint</p>
            <p className="text-xs text-text-muted mt-0.5 italic">
              Not in default repos — install the{" "}
              <HeroLink
                href="https://github.com/akdor1154/gamescope-pkg/releases/latest"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-neon-cyan"
              >
                .deb package
              </HeroLink>{" "}
              or add the{" "}
              <code className="text-neon-cyan font-mono not-italic">ppa:kgraefe/gamescope</code> PPA
            </p>
          </div>
        </div>
        <Description>
          After installing, restart the app to detect gamescope.{" "}
          <HeroLink href="https://github.com/ValveSoftware/gamescope" target="_blank" rel="noopener noreferrer" className="text-xs text-neon-cyan">
            GitHub &rarr;
          </HeroLink>
        </Description>
      </GlowCard>
    );
  }

  /* ---------- Builder ---------- */
  return (
    <GlowCard className="p-5 space-y-4">
      {/* Header */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
          <Monitor className="size-4 text-neon-cyan" />
          Gamescope Builder
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {activeCount} feature{activeCount !== 1 ? "s" : ""} active
          </Chip>
        </label>
        <Description className="mt-1">
          Build a Gamescope launch command with resolution, FPS limits, FSR upscaling, and display options.
        </Description>
      </div>

      {/* Resolution */}
      <div className="rounded-xl border border-border bg-surface-secondary/30 p-3">
        <Fieldset className="w-full">
          <Fieldset.Legend className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
            <Maximize2 className="size-3.5 text-neon-cyan" />
            Resolution
          </Fieldset.Legend>
          <p className="mt-1 text-xs leading-relaxed text-text-muted">
            Output resolution is the display target. Game resolution is what the game renders internally — set lower than output to enable upscaling via FSR or integer scale.
          </p>

          {/* Quick presets */}
          <div className="mt-3 flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] uppercase tracking-wide text-text-muted font-medium mr-1">Quick:</span>
            {RESOLUTION_PRESETS.map((p) => (
              <Tooltip key={p.label} delay={0}>
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-6 min-h-6 px-2 text-[10px] font-mono"
                  onPress={() =>
                    update({
                      output_width: p.w,
                      output_height: p.h,
                      game_width: p.w,
                      game_height: p.h,
                    })
                  }
                >
                  {p.label}
                </Button>
                <Tooltip.Content>{p.w}&times;{p.h} — sets both output and game resolution</Tooltip.Content>
              </Tooltip>
            ))}
          </div>

          <FieldGroup className="mt-3 space-y-3">
            {/* Output resolution */}
            <div>
              <p className="text-[11px] font-medium text-text-muted mb-1.5">Output (display target)</p>
              <div className="grid grid-cols-2 gap-3">
                <NumberField
                  minValue={0}
                  step={10}
                  value={opts.output_width}
                  onChange={(v) => update({ output_width: v ?? 0 })}
                  formatOptions={{ useGrouping: false }}
                  aria-label="Output Width"
                  variant="secondary"
                  fullWidth
                >
                  <Label>Width</Label>
                  <NumberField.Group>
                    <NumberField.DecrementButton />
                    <NumberField.Input className="font-mono" />
                    <NumberField.IncrementButton />
                  </NumberField.Group>
                </NumberField>
                <NumberField
                  minValue={0}
                  step={10}
                  value={opts.output_height}
                  onChange={(v) => update({ output_height: v ?? 0 })}
                  formatOptions={{ useGrouping: false }}
                  aria-label="Output Height"
                  variant="secondary"
                  fullWidth
                >
                  <Label>Height</Label>
                  <NumberField.Group>
                    <NumberField.DecrementButton />
                    <NumberField.Input className="font-mono" />
                    <NumberField.IncrementButton />
                  </NumberField.Group>
                </NumberField>
              </div>
            </div>
            {/* Game resolution */}
            <div>
              <p className="text-[11px] font-medium text-text-muted mb-1.5">Game (internal render)</p>
              <div className="grid grid-cols-2 gap-3">
                <NumberField
                  minValue={0}
                  step={10}
                  value={opts.game_width}
                  onChange={(v) => update({ game_width: v ?? 0 })}
                  formatOptions={{ useGrouping: false }}
                  aria-label="Game Width"
                  variant="secondary"
                  fullWidth
                >
                  <Label>Width</Label>
                  <NumberField.Group>
                    <NumberField.DecrementButton />
                    <NumberField.Input className="font-mono" />
                    <NumberField.IncrementButton />
                  </NumberField.Group>
                </NumberField>
                <NumberField
                  minValue={0}
                  step={10}
                  value={opts.game_height}
                  onChange={(v) => update({ game_height: v ?? 0 })}
                  formatOptions={{ useGrouping: false }}
                  aria-label="Game Height"
                  variant="secondary"
                  fullWidth
                >
                  <Label>Height</Label>
                  <NumberField.Group>
                    <NumberField.DecrementButton />
                    <NumberField.Input className="font-mono" />
                    <NumberField.IncrementButton />
                  </NumberField.Group>
                </NumberField>
              </div>
            </div>
          </FieldGroup>
        </Fieldset>
      </div>

      {/* Limits */}
      <div className="rounded-xl border border-border bg-surface-secondary/30 p-3">
        <Fieldset className="w-full">
          <Fieldset.Legend className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
            <Gauge className="size-3.5 text-neon-cyan" />
            Limits
          </Fieldset.Legend>
          <p className="mt-1 text-xs leading-relaxed text-text-muted">
            Cap the maximum frame rate to reduce power draw, heat, and fan noise. Match your display refresh rate for tear-free output.
          </p>
          <FieldGroup className="mt-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <NumberField
                minValue={0}
                step={1}
                value={opts.fps_limit}
                onChange={(v) => update({ fps_limit: v ?? 0 })}
                aria-label="FPS Limit"
                variant="secondary"
                fullWidth
              >
                <Label>FPS Limit</Label>
                <NumberField.Group>
                  <NumberField.DecrementButton />
                  <NumberField.Input className="font-mono min-w-0" />
                  <NumberField.IncrementButton />
                </NumberField.Group>
                <Description>0 = unlimited</Description>
              </NumberField>
              {opts.fsr && (
                <NumberField
                  minValue={0}
                  maxValue={20}
                  step={1}
                  value={opts.fsr_sharpness}
                  onChange={(v) => update({ fsr_sharpness: v ?? 5 })}
                  aria-label="FSR Sharpness"
                  variant="secondary"
                  fullWidth
                >
                  <Label>FSR Sharpness</Label>
                  <NumberField.Group>
                    <NumberField.DecrementButton />
                    <NumberField.Input className="font-mono min-w-0" />
                    <NumberField.IncrementButton />
                  </NumberField.Group>
                  <Description>0 = sharpest, 20 = softest</Description>
                </NumberField>
              )}
            </div>
          </FieldGroup>
        </Fieldset>
      </div>

      {/* Features */}
      <div className="rounded-xl border border-border bg-surface-secondary/30 p-3">
        <Fieldset className="w-full">
          <Fieldset.Legend className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
            <Sparkles className="size-3.5 text-neon-cyan" />
            Features
          </Fieldset.Legend>
          <p className="mt-1 text-xs leading-relaxed text-text-muted">
            Toggle compositor features. FSR requires game resolution to be lower than output. HDR needs driver and display support.
          </p>
          <ToggleButtonGroup
            selectionMode="multiple"
            selectedKeys={activeFeatures}
            className="flex flex-wrap gap-2 mt-3"
            aria-label="Gamescope features"
          >
            {FEATURE_DEFS.map((feat) => (
              <Tooltip key={feat.id} delay={0}>
                <ToggleButton
                  id={feat.id}
                  onPress={() => update({ [feat.id]: !opts[feat.id] })}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
                    opts[feat.id]
                      ? "bg-neon-cyan/20 border-neon-cyan text-neon-cyan shadow-glow-sm"
                      : "border-border-secondary text-text-muted hover:border-neon-cyan hover:text-neon-cyan"
                  }`}
                >
                  {feat.label}
                </ToggleButton>
                <Tooltip.Content className="max-w-xs text-xs">{feat.description}</Tooltip.Content>
              </Tooltip>
            ))}
          </ToggleButtonGroup>
        </Fieldset>
      </div>

      {/* Command Preview */}
      <div className="rounded-xl border border-border bg-surface-secondary/30 p-3 space-y-2.5">
        <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          <Info className="size-3.5 text-neon-cyan" />
          Command Preview
        </label>
        <pre className="text-xs font-mono text-neon-cyan bg-surface-deep border border-border rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
          {preview}
        </pre>
        <div className="flex items-center gap-2">
          <Tooltip delay={0}>
            <Button size="sm" onPress={() => onInsert(preview)} className="gap-1.5">
              <Plus className="size-3" />
              Insert into Launch Options
            </Button>
            <Tooltip.Content>Append this command to the game&apos;s launch options</Tooltip.Content>
          </Tooltip>
          <Tooltip delay={0}>
            <Button variant="outline" size="sm" onPress={handleCopy} className="gap-1.5">
              {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
              {copied ? "Copied" : "Copy"}
            </Button>
            <Tooltip.Content>Copy command to clipboard</Tooltip.Content>
          </Tooltip>
        </div>
      </div>
    </GlowCard>
  );
}
