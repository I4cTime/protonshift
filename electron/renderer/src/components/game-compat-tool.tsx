"use client";

import { Wrench, Grape } from "lucide-react";
import { Chip, Label, ListBox, Select, Text } from "@heroui/react";
import { Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
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
    const count = props.tools.length;
    return (
      <Widget>
        <Widget.Header>
          <Widget.Title className="flex flex-wrap items-center gap-1.5">
            <Wrench className="text-neon-cyan size-4 shrink-0" aria-hidden />
            Proton / compatibility tool
            <Chip size="sm" variant="secondary" className="text-[10px]">
              {count} option{count === 1 ? "" : "s"}
            </Chip>
          </Widget.Title>
          <InfoHint label="About compatibility tool">
            Choose which Proton or Wine layer Steam uses for this title. Leave empty for the
            Steam default.
          </InfoHint>
        </Widget.Header>
        <Widget.Content className="space-y-1.5">
          <Label
            id="steam-compat-tool-label"
            className="text-muted text-[10px] font-semibold uppercase tracking-wide"
          >
            Compatibility tool
          </Label>
          <Select
            className="w-full"
            value={props.selectedTool}
            onChange={(v) => props.onToolChange(String(v ?? ""))}
            placeholder="Select compatibility tool"
            aria-labelledby="steam-compat-tool-label"
          >
            <Select.Trigger className="w-full">
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover className="min-w-[var(--trigger-width)]">
              <ListBox>
                {props.tools.map((tool) => (
                  <ListBox.Item
                    key={tool || "__none__"}
                    id={tool}
                    textValue={tool || "(None / Steam default)"}
                  >
                    {tool || "(None / Steam default)"}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
          <Text.Paragraph size="xs" color="muted">
            Steam restarts may be required for changes to take effect.
          </Text.Paragraph>
        </Widget.Content>
      </Widget>
    );
  }

  const { selectedTool, onToolChange, wineVersions, heroicConfig } = props;
  const currentName = heroicConfig?.wine_version?.name ?? null;
  const currentInList = currentName
    ? wineVersions.some((v) => v.name === currentName)
    : false;

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Grape className="text-neon-cyan size-4 shrink-0" aria-hidden />
          Wine / Proton version
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {wineVersions.length} version{wineVersions.length === 1 ? "" : "s"}
          </Chip>
        </Widget.Title>
        <InfoHint label="About Wine / Proton version">
          Choose the Wine or Proton version Heroic uses. The current selection is shown even
          if it is no longer in the available list.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-1.5">
        <Label
          id="heroic-wine-version-label"
          className="text-muted text-[10px] font-semibold uppercase tracking-wide"
        >
          Wine / Proton version
        </Label>
        <Select
          className="w-full"
          value={selectedTool}
          onChange={(v) => onToolChange(String(v ?? ""))}
          placeholder="Select Wine or Proton version"
          aria-labelledby="heroic-wine-version-label"
        >
          <Select.Trigger className="w-full">
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover className="min-w-[var(--trigger-width)]">
            <ListBox>
              {currentName && !currentInList && (
                <ListBox.Item
                  key={currentName}
                  id={currentName}
                  textValue={`${currentName} (current)`}
                >
                  {currentName} (current)
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              )}
              {wineVersions.map((v) => (
                <ListBox.Item
                  key={v.name}
                  id={v.name}
                  textValue={`${v.name} (${v.wine_type})`}
                >
                  <span className="truncate">{v.name}</span>
                  <span className="text-muted ml-2 shrink-0 text-[11px]">{v.wine_type}</span>
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
        {currentName && (
          <Text.Paragraph size="xs" color="muted">
            Current: <Text.Code>{currentName}</Text.Code>
          </Text.Paragraph>
        )}
      </Widget.Content>
    </Widget>
  );
}
