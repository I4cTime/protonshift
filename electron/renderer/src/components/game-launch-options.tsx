"use client";

import { useMemo, useCallback } from "react";
import type { Key } from "react-aria-components";
import { Terminal, Layers } from "lucide-react";
import {
  TextArea,
  Description,
  Separator,
  Label,
  Chip,
  Text,
} from "@heroui/react";
import { CheckboxButtonGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import type { LaunchPreset } from "@/lib/api";

interface GameLaunchOptionsProps {
  launchOptions: string;
  setLaunchOptions: (v: string) => void;
  isSteam: boolean;
  presets: LaunchPreset[] | undefined;
}

/** Remove every preset snippet so we can rebuild from checkbox selection (longest values first). */
function stripPresetValues(line: string, presetList: LaunchPreset[]): string {
  const byLen = [...presetList].sort((a, b) => b.value.length - a.value.length);
  let s = line;
  for (const p of byLen) {
    const v = p.value.trim();
    if (!v) continue;
    s = s.split(v).join(" ");
  }
  return s.replace(/\s+/g, " ").trim();
}

export function GameLaunchOptions({
  launchOptions,
  setLaunchOptions,
  isSteam,
  presets,
}: GameLaunchOptionsProps) {
  const selectedPresetNames = useMemo(
    () =>
      presets?.filter((p) => launchOptions.includes(p.value)).map((p) => p.name) ?? [],
    [presets, launchOptions],
  );

  const activePresetCount = selectedPresetNames.length;

  const handlePresetsChange = useCallback(
    (keys: Iterable<Key>) => {
      if (!presets?.length) return;
      const selected = new Set([...keys].map(String));
      const base = stripPresetValues(launchOptions, presets);
      const orderedValues = presets
        .filter((p) => selected.has(p.name))
        .map((p) => p.value.trim())
        .filter(Boolean);
      const merged = [orderedValues.join(" "), base].filter(Boolean).join(" ").trim();
      setLaunchOptions(merged);
    },
    [presets, launchOptions, setLaunchOptions],
  );

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Terminal className="size-4 shrink-0 text-neon-cyan" aria-hidden />
          Launch options
          {presets && presets.length > 0 && activePresetCount > 0 && (
            <Chip size="sm" variant="secondary" className="text-[10px]">
              {activePresetCount} quick preset{activePresetCount === 1 ? "" : "s"}
            </Chip>
          )}
        </Widget.Title>
        <InfoHint label="About launch options">
          {isSteam
            ? "Arguments prepended to %command%. Put environment variables, gamemoderun, MangoHud, or gamescope before %command%."
            : "Extra arguments and environment variables for the game process. Put env vars before the runner or executable."}
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        <div className="space-y-1">
          <Label
            id="launch-options-line-label"
            className="text-muted text-[10px] font-semibold uppercase tracking-wide"
          >
            Command line
          </Label>
          <TextArea
            value={launchOptions}
            onChange={(e) => setLaunchOptions(e.target.value)}
            placeholder={
              isSteam
                ? "e.g. gamemoderun MANGOHUD=1 %command%"
                : "e.g. MANGOHUD=1 gamemoderun"
            }
            rows={3}
            variant="secondary"
            aria-labelledby="launch-options-line-label"
            className="w-full resize-none font-mono text-xs"
          />
        </div>

        {presets && presets.length > 0 && (
          <>
            <Separator />
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Layers className="text-neon-cyan size-3.5 shrink-0" aria-hidden />
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                  Quick presets
                </Label>
              </div>
              <Text.Paragraph size="xs" color="muted">
                Toggle snippets merged at the start of the line. Items marked not installed are
                disabled until the tool is available on this system.
              </Text.Paragraph>
              <CheckboxButtonGroup
                aria-label="Launch option quick presets"
                className="grid w-full grid-cols-1 gap-1.5 min-[380px]:grid-cols-2 min-[560px]:grid-cols-3"
                layout="grid"
                name="launch-option-presets"
                value={selectedPresetNames}
                variant="secondary"
                onChange={(keys) => handlePresetsChange(keys)}
              >
                {presets.map((preset) => {
                  const snippetInLine = launchOptions.includes(preset.value);
                  return (
                  <CheckboxButtonGroup.Item
                    key={preset.name}
                    value={preset.name}
                    isDisabled={!preset.is_installed && !snippetInLine}
                    className="min-h-[5.25rem] min-w-0"
                  >
                    <CheckboxButtonGroup.Indicator />
                    <CheckboxButtonGroup.ItemContent className="min-w-0 gap-1 py-1">
                      <CheckboxButtonGroup.ItemIcon className="text-neon-cyan">
                        <Layers className="size-3.5 shrink-0" aria-hidden />
                      </CheckboxButtonGroup.ItemIcon>
                      <div className="flex min-w-0 flex-wrap items-center gap-1">
                        <Label className="truncate text-[11px] font-semibold leading-tight">
                          {preset.name}
                        </Label>
                        {!preset.is_installed && (
                          <Chip
                            size="sm"
                            color="warning"
                            variant="soft"
                            className="shrink-0 text-[9px]"
                          >
                            Missing
                          </Chip>
                        )}
                      </div>
                      <Description className="text-muted line-clamp-2 text-[10px] leading-snug">
                        {preset.description}
                      </Description>
                    </CheckboxButtonGroup.ItemContent>
                  </CheckboxButtonGroup.Item>
                  );
                })}
              </CheckboxButtonGroup>
            </div>
          </>
        )}
      </Widget.Content>
    </Widget>
  );
}
