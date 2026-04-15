"use client";

import { Terminal, Layers } from "lucide-react";
import {
  TextArea,
  Description,
  Separator,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { LaunchPreset } from "@/lib/api";

interface GameLaunchOptionsProps {
  launchOptions: string;
  setLaunchOptions: (v: string) => void;
  isSteam: boolean;
  presets: LaunchPreset[] | undefined;
}

export function GameLaunchOptions({
  launchOptions,
  setLaunchOptions,
  isSteam,
  presets,
}: GameLaunchOptionsProps) {
  function handlePresetToggle(value: string) {
    const current = launchOptions.trim();
    if (current.includes(value)) {
      setLaunchOptions(current.replace(value, "").replace(/\s+/g, " ").trim());
    } else {
      setLaunchOptions(current ? `${value} ${current}` : value);
    }
  }

  const activePresetIds = presets
    ?.filter((p) => launchOptions.includes(p.value))
    .map((p) => p.name) ?? [];

  return (
    <GlowCard className="p-5 space-y-4">
      <div>
        <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary mb-1">
          <Terminal className="size-4 text-neon-cyan" />
          Launch Options
        </label>
        <Description>
          {isSteam
            ? "Command-line arguments prepended to %command%. Use environment variables, gamemoderun, mangohud, or gamescope before %command%."
            : "Extra arguments and environment variables passed to the game process. Place env vars before the executable."}
        </Description>
      </div>

      <TextArea
        value={launchOptions}
        onChange={(e) => setLaunchOptions(e.target.value)}
        placeholder={isSteam ? "e.g. gamemoderun MANGOHUD=1 %command%" : "e.g. MANGOHUD=1 gamemoderun"}
        rows={3}
        aria-label="Launch options"
        className="w-full font-mono resize-none"
        variant="secondary"
      />

      {presets && presets.length > 0 && (
        <>
          <Separator />
          <div>
            <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary mb-1">
              <Layers className="size-3.5 text-neon-cyan" />
              Quick Presets
            </label>
            <Description className="mb-3">
              Toggle launch-option snippets. Active presets are highlighted. Greyed-out presets are not installed.
            </Description>
            <ToggleButtonGroup
              selectionMode="multiple"
              selectedKeys={new Set(activePresetIds)}
              className="flex flex-wrap gap-2"
              aria-label="Launch option presets"
            >
              {presets.map((preset) => (
                <Tooltip key={preset.name} delay={0}>
                  <ToggleButton
                    id={preset.name}
                    onPress={() => handlePresetToggle(preset.value)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
                      launchOptions.includes(preset.value)
                        ? "bg-neon-cyan/20 border-neon-cyan text-neon-cyan shadow-glow-sm"
                        : "border-border-secondary text-text-muted hover:border-neon-cyan hover:text-neon-cyan"
                    } ${!preset.is_installed ? "opacity-50" : ""}`}
                  >
                    {preset.name}
                  </ToggleButton>
                  <Tooltip.Content>
                    <p>{preset.description}</p>
                    {!preset.is_installed && (
                      <p className="text-xs text-text-muted mt-1">Not installed</p>
                    )}
                  </Tooltip.Content>
                </Tooltip>
              ))}
            </ToggleButtonGroup>
          </div>
        </>
      )}
    </GlowCard>
  );
}
