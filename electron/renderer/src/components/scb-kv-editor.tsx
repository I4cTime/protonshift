"use client";

import { useCallback } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button, Input, Label, Text, TextField, Tooltip } from "@heroui/react";

export interface ScbKvEditorProps {
  /** Current key/value pairs. */
  value: Record<string, string>;
  /** Replace the full kv map. */
  onChange: (next: Record<string, string>) => void;
  /** Suggestion list shown when adding a new key. */
  knownKeys?: readonly string[];
  /** Optional aria label for the whole editor. */
  ariaLabel?: string;
}

interface RowItem {
  k: string;
  v: string;
}

function toRows(map: Record<string, string>): RowItem[] {
  return Object.entries(map).map(([k, v]) => ({ k, v }));
}

function fromRows(rows: RowItem[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const { k, v } of rows) {
    const key = k.trim();
    if (!key) continue;
    out[key] = v;
  }
  return out;
}

/**
 * Tiny key/value table for bash-style ``KEY=value`` config files.
 * Used by the per-game ScopeBuddy override widget and the dedicated /scopebuddy
 * page; values are surfaced as raw strings so the user keeps full control.
 */
export function ScbKvEditor({ value, onChange, knownKeys, ariaLabel }: ScbKvEditorProps) {
  const rows = toRows(value);

  const setRow = useCallback(
    (idx: number, patch: Partial<RowItem>) => {
      const next = rows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
      onChange(fromRows(next));
    },
    [rows, onChange],
  );

  const removeRow = useCallback(
    (idx: number) => {
      const next = rows.filter((_, i) => i !== idx);
      onChange(fromRows(next));
    },
    [rows, onChange],
  );

  const addRow = useCallback(
    (key?: string) => {
      const k = key ?? "";
      onChange(fromRows([...rows, { k, v: "" }]));
    },
    [rows, onChange],
  );

  const presentKeys = new Set(rows.map((r) => r.k));
  const remainingKnown = (knownKeys ?? []).filter((k) => !presentKeys.has(k));

  return (
    <div className="space-y-2" aria-label={ariaLabel}>
      <div className="grid grid-cols-[minmax(8rem,12rem)_1fr_auto] gap-2 px-1 pb-1">
        <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">Key</Label>
        <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">Value</Label>
        <span className="sr-only">Actions</span>
      </div>

      {rows.length === 0 ? (
        <Text.Paragraph size="xs" color="muted" className="px-1 italic">
          No keys yet — pick a known one below or add a custom row.
        </Text.Paragraph>
      ) : (
        <div className="space-y-1.5">
          {rows.map((row, idx) => (
            <div
              key={idx}
              className="grid grid-cols-[minmax(8rem,12rem)_1fr_auto] items-end gap-2"
            >
              <TextField
                value={row.k}
                onChange={(v) => setRow(idx, { k: v })}
                aria-label={`Key ${idx + 1}`}
                className="min-w-0"
              >
                <Input placeholder="SCB_…" variant="secondary" className="font-mono text-xs" />
              </TextField>
              <TextField
                value={row.v}
                onChange={(v) => setRow(idx, { v })}
                aria-label={`Value for ${row.k || "row"} ${idx + 1}`}
                className="min-w-0"
              >
                <Input placeholder="value" variant="secondary" className="font-mono text-xs" />
              </TextField>
              <Tooltip delay={0}>
                <Button
                  isIconOnly
                  size="sm"
                  variant="ghost"
                  className="h-9 w-9 text-danger hover:bg-danger/10"
                  onPress={() => removeRow(idx)}
                  aria-label={`Remove ${row.k || `row ${idx + 1}`}`}
                >
                  <Trash2 className="size-3.5 shrink-0" aria-hidden />
                </Button>
                <Tooltip.Content>Remove row</Tooltip.Content>
              </Tooltip>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-1.5 pt-1">
        {remainingKnown.length > 0 && (
          <>
            <Text.Paragraph size="xs" color="muted" className="text-[10px] mr-1 self-center">
              Add known:
            </Text.Paragraph>
            {remainingKnown.map((k) => (
              <Button
                key={k}
                size="sm"
                variant="secondary"
                className="h-7 gap-1 px-2 text-[10px] font-mono"
                onPress={() => addRow(k)}
              >
                <Plus className="size-3 shrink-0" aria-hidden />
                {k}
              </Button>
            ))}
          </>
        )}
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto h-7 gap-1 px-2 text-[10px]"
          onPress={() => addRow()}
        >
          <Plus className="size-3 shrink-0" aria-hidden />
          Custom row
        </Button>
      </div>
    </div>
  );
}
