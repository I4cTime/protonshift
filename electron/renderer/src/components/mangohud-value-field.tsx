"use client";

import { useMemo, type Dispatch, type SetStateAction } from "react";
import {
  Button,
  Description,
  Fieldset,
  FieldGroup,
  Input,
  Label,
  ListBox,
  NumberField,
  Select,
  Slider,
  Tooltip,
} from "@heroui/react";
import {
  FolderOpen,
  Gauge,
  Paintbrush,
  Keyboard,
  ScrollText,
  LayoutGrid,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

export interface MangoHudValueParam {
  key: string;
  label: string;
  type: "value";
}

export interface MangoHudParamRowItem {
  key: string;
  label: string;
  type: string;
}

/* ---------------------------------------------------------------------------
 * Constants
 * -------------------------------------------------------------------------*/

const MANGOHUD_POSITIONS: { id: string; label: string }[] = [
  { id: "top-left", label: "Top left" },
  { id: "top-center", label: "Top center" },
  { id: "top-right", label: "Top right" },
  { id: "middle-left", label: "Middle left" },
  { id: "middle-right", label: "Middle right" },
  { id: "bottom-left", label: "Bottom left" },
  { id: "bottom-center", label: "Bottom center" },
  { id: "bottom-right", label: "Bottom right" },
];

const TOGGLE_HOTKEY_PRESETS = [
  "F12",
  "Shift_R+F12",
  "Control_L+m",
  "Alt_L+F12",
] as const;

const OUTPUT_FOLDER_PRESETS = [
  "~/mangohud_logs",
  "~/.local/state/mangohud",
  "/tmp/mangohud_logs",
] as const;

/** Logical groups for MangoHud value parameters with descriptions. */
const VALUE_GROUPS: readonly {
  title: string;
  description: string;
  icon: LucideIcon;
  keys: readonly string[];
}[] = [
  {
    title: "Frame limiting",
    icon: Gauge,
    description:
      "Cap the maximum frame rate to reduce power consumption, heat, and fan noise. Set to 0 or leave empty for unlimited. Common targets: 30 (battery), 60, 120, 144, 165 — match your display refresh rate for tear-free output.",
    keys: ["fps_limit"],
  },
  {
    title: "Overlay appearance",
    icon: Paintbrush,
    description:
      "Control where the HUD appears and how it looks. Position anchors to a screen corner or edge, font size scales all overlay text, and background opacity lets you balance readability against gameplay visibility.",
    keys: ["position", "font_size", "background_alpha"],
  },
  {
    title: "Controls",
    icon: Keyboard,
    description:
      "Bind a hotkey to show/hide the overlay at runtime. Uses X11 key tokens — combine modifiers with '+' (e.g. Shift_R+F12). Handy for screenshots or when the overlay covers important UI.",
    keys: ["toggle_hud"],
  },
  {
    title: "Logging",
    icon: ScrollText,
    description:
      "When a log output folder is set, MangoHud writes CSV frame-time logs on each session. Use these for post-session analysis with tools like MangoPlot or custom scripts. If no folder is set, logging is disabled.",
    keys: ["output_folder"],
  },
];

/* ---------------------------------------------------------------------------
 * Individual field renderers
 * -------------------------------------------------------------------------*/

interface FieldProps {
  value: string;
  onChange: (next: string) => void;
}

function FpsLimitField({ value, onChange }: FieldProps) {
  const numVal = value === "" ? undefined : Number(value);

  return (
    <NumberField
      minValue={0}
      step={1}
      value={numVal}
      onChange={(v) => onChange(v === undefined ? "" : String(v))}
      aria-label="FPS Limit"
      variant="secondary"
      fullWidth
    >
      <Label>FPS Limit</Label>
      <NumberField.Group>
        <NumberField.DecrementButton />
        <NumberField.Input />
        <NumberField.IncrementButton />
      </NumberField.Group>
      <Description>
        0 or empty = unlimited. Match your display refresh rate for tear-free
        output.
      </Description>
    </NumberField>
  );
}

function PositionField({ value, onChange }: FieldProps) {
  const selectValue = value.trim() === "" ? "__default__" : value;

  return (
    <Select
      className="w-full"
      value={selectValue}
      onChange={(v) => {
        const id = String(v ?? "");
        onChange(id === "__default__" ? "" : id);
      }}
      placeholder="Overlay position on screen"
    >
      <Label>Position</Label>
      <Select.Trigger>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox>
          <ListBox.Item
            id="__default__"
            textValue="Default (use MangoHud / preset default)"
          >
            Default (preset / MangoHud default)
            <ListBox.ItemIndicator />
          </ListBox.Item>
          {MANGOHUD_POSITIONS.map((p) => (
            <ListBox.Item key={p.id} id={p.id} textValue={p.label}>
              {p.label}
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
      <Description>
        Where the HUD is anchored — corners and edges of the screen.
      </Description>
    </Select>
  );
}

function FontSizeField({ value, onChange }: FieldProps) {
  const numVal = value === "" ? undefined : Number(value);

  return (
    <NumberField
      minValue={8}
      maxValue={96}
      step={1}
      value={numVal}
      onChange={(v) => onChange(v === undefined ? "" : String(v))}
      aria-label="Font Size"
      variant="secondary"
      fullWidth
    >
      <Label>Font Size</Label>
      <NumberField.Group>
        <NumberField.DecrementButton />
        <NumberField.Input />
        <NumberField.IncrementButton />
      </NumberField.Group>
      <Description>Typical range 18–32 px. Scales all overlay text.</Description>
    </NumberField>
  );
}

function BackgroundAlphaField({ value, onChange }: FieldProps) {
  const parsed = value.trim() === "" ? undefined : parseFloat(value);
  const hasValue = parsed !== undefined && Number.isFinite(parsed);
  const sliderVal = hasValue ? Math.min(1, Math.max(0, parsed)) : 0.35;

  return (
    <div className="space-y-3">
      <Slider
        minValue={0}
        maxValue={1}
        step={0.05}
        value={sliderVal}
        onChange={(v) => onChange(String((v as number).toFixed(2)))}
        aria-label="Background Opacity"
        className="w-full"
      >
        <div className="flex items-center justify-between">
          <Label>Background Opacity</Label>
          <Slider.Output className="text-xs tabular-nums font-mono" />
        </div>
        <Slider.Track>
          <Slider.Fill />
          <Slider.Thumb />
        </Slider.Track>
      </Slider>
      <Input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0.0 – 1.0 (e.g. 0.35 = 35%)"
        aria-label="Background Opacity exact value"
        variant="secondary"
        className="w-full font-mono text-xs"
      />
      <p className="text-[11px] text-text-muted">
        0 = fully transparent, 1 = solid background. Type an exact value or drag
        the slider.
      </p>
    </div>
  );
}

function ToggleHudField({ value, onChange }: FieldProps) {
  return (
    <div className="space-y-2">
      <Label className="text-xs text-text-muted">Toggle Hotkey</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. F12 or Shift_R+F12"
        aria-label="Toggle Hotkey"
        variant="secondary"
        className="w-full font-mono text-sm"
      />
      <div className="flex flex-wrap gap-1.5">
        {TOGGLE_HOTKEY_PRESETS.map((preset) => (
          <Button
            key={preset}
            size="sm"
            variant="secondary"
            className="h-7 min-h-7 px-2 text-xs font-mono"
            onPress={() => onChange(preset)}
          >
            {preset}
          </Button>
        ))}
      </div>
      <Description>
        Uses MangoHud key tokens (Shift_R, Control_L, Alt_L). Combine with +.
      </Description>
    </div>
  );
}

function OutputFolderField({ value, onChange }: FieldProps) {
  const trimmed = value.trim();

  return (
    <div className="space-y-2">
      <Label className="text-xs text-text-muted">Log Output Folder</Label>
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. ~/mangohud_logs"
          aria-label="Log Output Folder"
          variant="secondary"
          className="min-w-0 flex-1 font-mono text-xs"
        />
        <Tooltip delay={0}>
          <Button
            isIconOnly
            variant="outline"
            size="sm"
            className="shrink-0"
            aria-label="Open folder in file manager"
            isDisabled={!trimmed}
            onPress={async () => {
              try {
                await api.openPath(trimmed);
              } catch {
                appShowToast("Could not open that path", "error");
              }
            }}
          >
            <FolderOpen className="size-4" />
          </Button>
          <Tooltip.Content>Open in file manager</Tooltip.Content>
        </Tooltip>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {OUTPUT_FOLDER_PRESETS.map((preset) => (
          <Button
            key={preset}
            size="sm"
            variant="secondary"
            className="h-7 min-h-7 px-2 text-xs font-mono"
            onPress={() => onChange(preset)}
          >
            {preset}
          </Button>
        ))}
      </div>
      <Description>
        Folder for MangoHud CSV frame-time logs. Leave empty to disable logging.
      </Description>
    </div>
  );
}

function GenericValueField({
  paramKey,
  label,
  value,
  onChange,
}: FieldProps & { paramKey: string; label: string }) {
  return (
    <div className="space-y-1">
      <Label className="text-xs text-text-muted">{label}</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Value for ${paramKey}`}
        aria-label={label}
        variant="secondary"
        className="w-full font-mono"
      />
    </div>
  );
}

const FIELD_RENDERERS: Record<
  string,
  (props: FieldProps) => React.ReactNode
> = {
  fps_limit: (p) => <FpsLimitField {...p} />,
  position: (p) => <PositionField {...p} />,
  font_size: (p) => <FontSizeField {...p} />,
  background_alpha: (p) => <BackgroundAlphaField {...p} />,
  toggle_hud: (p) => <ToggleHudField {...p} />,
  output_folder: (p) => <OutputFolderField {...p} />,
};

/* ---------------------------------------------------------------------------
 * Grouped layout component
 * -------------------------------------------------------------------------*/

interface MangoHudValueFieldsGridProps {
  valueParams: MangoHudParamRowItem[];
  values: Record<string, string>;
  onParamChange: (key: string, next: string) => void;
}

/**
 * MangoHud value fields organised into logical `Fieldset` groups with descriptions,
 * using HeroUI `NumberField`, `Slider`, `Select`, and `Fieldset` compounds.
 */
export function MangoHudValueFieldsGrid({
  valueParams,
  values,
  onParamChange,
}: MangoHudValueFieldsGridProps) {
  const byKey = useMemo(
    () => new Map(valueParams.map((p) => [p.key, p])),
    [valueParams],
  );

  const grouped = useMemo(
    () => new Set(VALUE_GROUPS.flatMap((g) => [...g.keys])),
    [],
  );

  const orphans = useMemo(
    () => valueParams.filter((p) => p.type === "value" && !grouped.has(p.key)),
    [valueParams, grouped],
  );

  return (
    <div className="flex flex-col gap-5">
      {VALUE_GROUPS.map((group) => {
        const groupParams = group.keys
          .map((k) => byKey.get(k))
          .filter((p): p is MangoHudParamRowItem => !!p && p.type === "value");
        if (groupParams.length === 0) return null;

        const GroupIcon = group.icon;
        return (
          <div
            key={group.title}
            className="rounded-xl border border-border bg-surface-secondary/30 p-4"
          >
            <Fieldset className="w-full">
              <Fieldset.Legend className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                <GroupIcon className="size-3.5 text-neon-cyan" />
                {group.title}
              </Fieldset.Legend>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                {group.description}
              </p>
              <FieldGroup className="mt-4">
                {groupParams.map((param) => {
                  const renderer = FIELD_RENDERERS[param.key];
                  if (renderer) {
                    return (
                      <div key={param.key}>
                        {renderer({
                          value: values[param.key] ?? "",
                          onChange: (next) => onParamChange(param.key, next),
                        })}
                      </div>
                    );
                  }
                  return (
                    <GenericValueField
                      key={param.key}
                      paramKey={param.key}
                      label={param.label}
                      value={values[param.key] ?? ""}
                      onChange={(next) => onParamChange(param.key, next)}
                    />
                  );
                })}
              </FieldGroup>
            </Fieldset>
          </div>
        );
      })}

      {orphans.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-secondary/30 p-4">
          <Fieldset className="w-full">
            <Fieldset.Legend className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
              <LayoutGrid className="size-3.5 text-neon-cyan" />
              Other
            </Fieldset.Legend>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">
              Additional value parameters not assigned to a specific category.
            </p>
            <FieldGroup className="mt-4">
              {orphans.map((param) => {
                const renderer = FIELD_RENDERERS[param.key];
                if (renderer) {
                  return (
                    <div key={param.key}>
                      {renderer({
                        value: values[param.key] ?? "",
                        onChange: (next) => onParamChange(param.key, next),
                      })}
                    </div>
                  );
                }
                return (
                  <GenericValueField
                    key={param.key}
                    paramKey={param.key}
                    label={param.label}
                    value={values[param.key] ?? ""}
                    onChange={(next) => onParamChange(param.key, next)}
                  />
                );
              })}
            </FieldGroup>
          </Fieldset>
        </div>
      )}
    </div>
  );
}
