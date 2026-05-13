"use client";

import { useMemo } from "react";
import type { Key } from "@heroui/react";
import {
  Button,
  Description,
  Fieldset,
  FieldGroup,
  Input,
  Label,
  ListBox,
  Text,
  Tooltip,
} from "@heroui/react";
import { CellSlider, InlineSelect, NumberStepper } from "@heroui-pro/react";
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

/** Logical groups for MangoHud value parameters with concise descriptions. */
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
      "Cap the maximum frame rate. Match your display refresh for tear-free output.",
    keys: ["fps_limit"],
  },
  {
    title: "Overlay appearance",
    icon: Paintbrush,
    description:
      "Where the HUD is anchored, how large it is, and how transparent its background looks.",
    keys: ["position", "font_size", "background_alpha"],
  },
  {
    title: "Controls",
    icon: Keyboard,
    description:
      "Hotkeys for showing or hiding the overlay at runtime, using X11 key tokens.",
    keys: ["toggle_hud"],
  },
  {
    title: "Logging",
    icon: ScrollText,
    description:
      "MangoHud writes CSV frame-time logs to this folder. Leave empty to disable.",
    keys: ["output_folder"],
  },
];

/* ---------------------------------------------------------------------------
 * Shared field shell
 * -------------------------------------------------------------------------*/

const FIELD_LABEL_CLASS =
  "text-muted text-[10px] font-semibold uppercase tracking-wide";

/* ---------------------------------------------------------------------------
 * Individual field renderers
 * -------------------------------------------------------------------------*/

interface FieldProps {
  value: string;
  onChange: (next: string) => void;
}

function FpsLimitField({ value, onChange }: FieldProps) {
  const numVal = value === "" ? 0 : Number(value);
  const safe = Number.isFinite(numVal) ? numVal : 0;

  return (
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>FPS limit</Label>
      <NumberStepper
        aria-label="FPS limit"
        minValue={0}
        maxValue={360}
        step={1}
        value={safe}
        onChange={(v) => onChange(v === 0 ? "" : String(v))}
      >
        <NumberStepper.Group>
          <NumberStepper.DecrementButton />
          <NumberStepper.Value className="min-w-[3rem] font-mono text-sm" />
          <NumberStepper.IncrementButton />
        </NumberStepper.Group>
      </NumberStepper>
      <Description className="leading-snug">
        0 = unlimited. Common targets: 30, 60, 120, 144, 165 Hz.
      </Description>
    </div>
  );
}

function PositionField({ value, onChange }: FieldProps) {
  const selectValue: Key = (value.trim() === "" ? "__default__" : value) as Key;

  return (
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>Position</Label>
      <InlineSelect
        aria-label="Overlay position"
        value={selectValue}
        onChange={(k) => {
          const id = String(k ?? "");
          onChange(id === "__default__" ? "" : id);
        }}
      >
        <InlineSelect.Trigger className="font-medium">
          <InlineSelect.Value />
          <InlineSelect.Indicator />
        </InlineSelect.Trigger>
        <InlineSelect.Popover className="min-w-[200px]">
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
        </InlineSelect.Popover>
      </InlineSelect>
    </div>
  );
}

function FontSizeField({ value, onChange }: FieldProps) {
  const numVal = value === "" ? 24 : Number(value);
  const safe = Number.isFinite(numVal) ? Math.min(96, Math.max(8, numVal)) : 24;

  return (
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>Font size</Label>
      <NumberStepper
        aria-label="Font size"
        minValue={8}
        maxValue={96}
        step={1}
        value={safe}
        onChange={(v) => onChange(String(v))}
      >
        <NumberStepper.Group>
          <NumberStepper.DecrementButton />
          <NumberStepper.Value className="min-w-[3rem] font-mono text-sm" />
          <NumberStepper.IncrementButton />
        </NumberStepper.Group>
      </NumberStepper>
      <Description className="leading-snug">
        Typical: 18–32 px.
      </Description>
    </div>
  );
}

function BackgroundAlphaField({ value, onChange }: FieldProps) {
  const parsed = value.trim() === "" ? undefined : parseFloat(value);
  const hasValue = parsed !== undefined && Number.isFinite(parsed);
  const sliderVal = hasValue ? Math.min(1, Math.max(0, parsed)) : 0.35;

  return (
    <div className="space-y-2">
      <CellSlider
        aria-label="Background opacity"
        minValue={0}
        maxValue={1}
        step={0.05}
        value={sliderVal}
        formatOptions={{ maximumFractionDigits: 2, minimumFractionDigits: 2 }}
        onChange={(v) => onChange(String((v as number).toFixed(2)))}
      >
        <CellSlider.Track>
          <CellSlider.Fill />
          <CellSlider.Thumb />
          <CellSlider.Label>Background opacity</CellSlider.Label>
          <CellSlider.Output />
        </CellSlider.Track>
      </CellSlider>
      <Input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="0.0 – 1.0 (e.g. 0.35)"
        aria-label="Background opacity exact value"
        variant="secondary"
        className="w-full font-mono text-xs"
      />
      <Text.Paragraph size="xs" color="muted" className="leading-snug">
        0 = transparent · 1 = solid. Drag the slider or type an exact value.
      </Text.Paragraph>
    </div>
  );
}

function ToggleHudField({ value, onChange }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>Toggle hotkey</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="e.g. F12 or Shift_R+F12"
        aria-label="Toggle hotkey"
        variant="secondary"
        className="w-full font-mono text-sm"
      />
      <div className="flex flex-wrap gap-1.5">
        {TOGGLE_HOTKEY_PRESETS.map((preset) => (
          <Button
            key={preset}
            size="sm"
            variant="secondary"
            className="h-7 min-h-7 px-2 font-mono text-xs"
            onPress={() => onChange(preset)}
          >
            {preset}
          </Button>
        ))}
      </div>
    </div>
  );
}

function OutputFolderField({ value, onChange }: FieldProps) {
  const trimmed = value.trim();

  return (
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>Log output folder</Label>
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. ~/mangohud_logs"
          aria-label="Log output folder"
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
            className="h-7 min-h-7 px-2 font-mono text-xs"
            onPress={() => onChange(preset)}
          >
            {preset}
          </Button>
        ))}
      </div>
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
    <div className="space-y-1.5">
      <Label className={FIELD_LABEL_CLASS}>{label}</Label>
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

interface ValueGroupCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  children: React.ReactNode;
}

function ValueGroupCard({
  title,
  description,
  icon: Icon,
  children,
}: ValueGroupCardProps) {
  return (
    <div className="border-border bg-surface-secondary/30 rounded-lg border p-3">
      <Fieldset className="w-full gap-2">
        <Fieldset.Legend className="text-muted flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide">
          <Icon className="text-neon-cyan size-3.5 shrink-0" aria-hidden />
          {title}
        </Fieldset.Legend>
        <Text.Paragraph size="xs" color="muted" className="leading-snug">
          {description}
        </Text.Paragraph>
        <FieldGroup className="space-y-3">{children}</FieldGroup>
      </Fieldset>
    </div>
  );
}

function renderField(
  param: MangoHudParamRowItem,
  values: Record<string, string>,
  onParamChange: (key: string, next: string) => void,
) {
  const renderer = FIELD_RENDERERS[param.key];
  const fieldProps: FieldProps = {
    value: values[param.key] ?? "",
    onChange: (next) => onParamChange(param.key, next),
  };
  if (renderer) {
    return <div key={param.key}>{renderer(fieldProps)}</div>;
  }
  return (
    <GenericValueField
      key={param.key}
      paramKey={param.key}
      label={param.label}
      {...fieldProps}
    />
  );
}

/**
 * MangoHud value fields organised into logical `Fieldset` groups with descriptions,
 * using HeroUI `Fieldset` / `Input` plus Pro `NumberStepper`, `CellSlider`, and `InlineSelect`.
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
    <div className="flex flex-col gap-3">
      {VALUE_GROUPS.map((group) => {
        const groupParams = group.keys
          .map((k) => byKey.get(k))
          .filter((p): p is MangoHudParamRowItem => !!p && p.type === "value");
        if (groupParams.length === 0) return null;

        return (
          <ValueGroupCard
            key={group.title}
            title={group.title}
            description={group.description}
            icon={group.icon}
          >
            {groupParams.map((p) => renderField(p, values, onParamChange))}
          </ValueGroupCard>
        );
      })}

      {orphans.length > 0 && (
        <ValueGroupCard
          title="Other"
          description="Additional value parameters not assigned to a specific category."
          icon={LayoutGrid}
        >
          {orphans.map((p) => renderField(p, values, onParamChange))}
        </ValueGroupCard>
      )}
    </div>
  );
}
