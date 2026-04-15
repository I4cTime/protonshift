"use client";

import { Wrench, Grape } from "lucide-react";
import { Select, Label, ListBox, Description } from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { HeroicWineVersionData, HeroicGameConfig } from "@/lib/api";

interface SteamCompatToolProps {
  mode: "steam";
  selectedTool: string;
  onToolChange: (v: string) => void;
  tools: string[];
}

interface HeroicCompatToolProps {
  mode: "heroic";
  selectedTool: string;
  onToolChange: (v: string) => void;
  wineVersions: HeroicWineVersionData[];
  heroicConfig: HeroicGameConfig | undefined;
}

type GameCompatToolProps = SteamCompatToolProps | HeroicCompatToolProps;

export function GameCompatTool(props: GameCompatToolProps) {
  if (props.mode === "steam") {
    return (
      <GlowCard className="p-5 space-y-2">
        <div className="flex items-center gap-1.5 mb-1">
          <Wrench className="size-4 text-neon-cyan" />
          <span className="text-sm font-medium text-text-secondary">Proton / Compatibility Tool</span>
        </div>
        <Description>
          Select which Proton or Wine compatibility layer Steam uses for this title. Leave empty for the Steam default.
        </Description>
        <Select
          className="w-full"
          value={props.selectedTool}
          onChange={(v) => props.onToolChange(String(v ?? ""))}
          placeholder="Select compatibility tool"
        >
          <Label className="sr-only">Proton / Compatibility Tool</Label>
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {props.tools.map((tool) => (
                <ListBox.Item key={tool || "__none__"} id={tool} textValue={tool || "(None / Steam default)"}>
                  {tool || "(None / Steam default)"}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
      </GlowCard>
    );
  }

  const { selectedTool, onToolChange, wineVersions, heroicConfig } = props;

  return (
    <GlowCard className="p-5 space-y-2">
      <div className="flex items-center gap-1.5 mb-1">
        <Grape className="size-4 text-neon-cyan" />
        <span className="text-sm font-medium text-text-secondary">Wine / Proton Version</span>
      </div>
      <Description>
        Choose the Wine or Proton version Heroic uses. The current version is shown even if not in the available list.
      </Description>
      <Select
        className="w-full"
        value={selectedTool}
        onChange={(v) => onToolChange(String(v ?? ""))}
        placeholder="Select wine/proton version"
      >
        <Label className="sr-only">Wine / Proton Version</Label>
        <Select.Trigger>
          <Select.Value />
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox>
            {heroicConfig?.wine_version?.name && !wineVersions.some((v) => v.name === heroicConfig.wine_version.name) && (
              <ListBox.Item key={heroicConfig.wine_version.name} id={heroicConfig.wine_version.name} textValue={`${heroicConfig.wine_version.name} (current)`}>
                {heroicConfig.wine_version.name} (current)
                <ListBox.ItemIndicator />
              </ListBox.Item>
            )}
            {wineVersions.map((v) => (
              <ListBox.Item key={v.name} id={v.name} textValue={`${v.name} (${v.wine_type})`}>
                {v.name} ({v.wine_type})
                <ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
    </GlowCard>
  );
}
