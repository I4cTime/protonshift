"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Key } from "react-aria-components";
import {
  Telescope,
  Save,
  Trash2,
  FolderOpen,
  Layers,
  Maximize2,
  Sun,
  Zap,
  RefreshCw,
  Gauge,
  type LucideIcon,
} from "lucide-react";
import {
  Button,
  ButtonGroup,
  Chip,
  Description,
  Label,
  Switch,
  Text,
  TextArea,
  TextField,
  Tooltip,
} from "@heroui/react";
import { CheckboxButtonGroup, Sheet, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import { api, type GamescopeOptions, type ScopeBuddyAutoCaps } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { appShowToast } from "@/lib/app-toast";

const SCB_AUTO_DEFS: {
  id: keyof Pick<
    GamescopeOptions,
    | "scb_auto_res"
    | "scb_auto_hdr"
    | "scb_auto_vrr"
    | "scb_auto_refresh"
    | "scb_auto_frame_limit"
  >;
  cfgKey: string;
  label: string;
  short: string;
  Icon: LucideIcon;
}[] = [
  { id: "scb_auto_res", cfgKey: "SCB_AUTO_RES", label: "Auto resolution", short: "RES", Icon: Maximize2 },
  { id: "scb_auto_hdr", cfgKey: "SCB_AUTO_HDR", label: "Auto HDR", short: "HDR", Icon: Sun },
  { id: "scb_auto_vrr", cfgKey: "SCB_AUTO_VRR", label: "Auto VRR", short: "VRR", Icon: Zap },
  { id: "scb_auto_refresh", cfgKey: "SCB_AUTO_REFRESH", label: "Auto refresh (-r)", short: "Hz", Icon: RefreshCw },
  {
    id: "scb_auto_frame_limit",
    cfgKey: "SCB_AUTO_FRAME_LIMIT",
    label: "Auto frame limit",
    short: "Cap",
    Icon: Gauge,
  },
];

function canUseScbAutoDetect(caps: ScopeBuddyAutoCaps | undefined): boolean {
  if (!caps?.jq) return false;
  return caps.kde || caps.gnome_gdctl || caps.gnome_randr || caps.wlroots;
}

function autoDetectTooltip(caps: ScopeBuddyAutoCaps | undefined): string {
  if (!caps?.jq) return "Install jq for SCB_AUTO_* display probing.";
  if (!caps.kde && !caps.gnome_gdctl && !caps.gnome_randr && !caps.wlroots) {
    return "No KDE, GNOME, or wlr-randr probe available for auto-detect.";
  }
  const bits: string[] = [];
  if (caps.kde) bits.push("KDE");
  if (caps.gnome_gdctl) bits.push("gdctl");
  if (caps.gnome_randr) bits.push("gnome-randr");
  if (caps.wlroots) bits.push("wlr-randr");
  return `May use: ${bits.join(", ")}.`;
}

/** Strip ``gamescope`` and trailing ``--`` from the builder preview for ``SCB_GAMESCOPE_ARGS``. */
export function gamescopeArgsFromBuilderPreview(line: string): string {
  const t = line.trim();
  if (!t) return "";
  let rest = t;
  if (rest.startsWith("gamescope")) {
    rest = rest.slice("gamescope".length).trim();
  }
  rest = rest.replace(/\s+--\s*$/, "").trim();
  return rest;
}

interface GameScopeBuddyOverrideProps {
  scopeBuddyKey: string;
  keyLabel: string;
  gamescopeBuilderPreview?: string;
}

function configToBool(cfg: Record<string, string>, k: string): boolean {
  const v = (cfg[k] ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}

function patchCfg(
  prev: Record<string, string>,
  patch: Record<string, string>,
): Record<string, string> {
  const next = { ...prev };
  for (const [k, v] of Object.entries(patch)) {
    if (v === "" || v === undefined) {
      delete next[k];
    } else {
      next[k] = v;
    }
  }
  return next;
}

export function GameScopeBuddyOverride({
  scopeBuddyKey,
  keyLabel,
  gamescopeBuilderPreview = "",
}: GameScopeBuddyOverrideProps) {
  const qc = useQueryClient();

  const { data: avail } = useQuery({
    queryKey: ["scopebuddy-available"],
    queryFn: api.getScopeBuddyAvailable,
    staleTime: 60_000,
  });

  const { data: caps } = useQuery({
    queryKey: ["scopebuddy-auto-caps"],
    queryFn: api.getScopeBuddyAutoCaps,
    staleTime: 60_000,
    enabled: !!avail?.available,
  });

  const { data: perApp, isLoading } = useQuery({
    queryKey: ["scopebuddy-per-app", scopeBuddyKey],
    queryFn: () => api.getScopeBuddyPerApp(scopeBuddyKey),
    enabled: !!avail?.available && !!scopeBuddyKey,
  });

  const { data: presets } = useQuery({
    queryKey: ["scopebuddy-presets"],
    queryFn: api.getScopeBuddyPresets,
    enabled: !!avail?.available,
  });

  const [local, setLocal] = useState<Record<string, string>>({});
  const [presetOpen, setPresetOpen] = useState(false);

  useEffect(() => {
    if (perApp?.config) {
      setLocal({ ...perApp.config });
    } else if (perApp && !perApp.exists) {
      setLocal({});
    }
  }, [perApp?.exists, perApp?.config, perApp]);

  const canAuto = useMemo(() => canUseScbAutoDetect(caps), [caps]);

  const selectedAutoKeys = useMemo(() => {
    return SCB_AUTO_DEFS.filter((d) => configToBool(local, d.cfgKey)).map((d) => d.id);
  }, [local]);

  const noscopeOn = useMemo(() => configToBool(local, "SCB_NOSCOPE"), [local]);

  const saveMut = useMutation({
    mutationFn: () => api.setScopeBuddyPerApp(scopeBuddyKey, local),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["scopebuddy-per-app", scopeBuddyKey] });
      await qc.invalidateQueries({ queryKey: ["scopebuddy-per-app"] });
      appShowToast("ScopeBuddy override saved");
    },
    onError: () => appShowToast("Failed to save ScopeBuddy override", "error"),
  });

  const deleteMut = useMutation({
    mutationFn: () => api.deleteScopeBuddyPerApp(scopeBuddyKey),
    onSuccess: async () => {
      setLocal({});
      await qc.invalidateQueries({ queryKey: ["scopebuddy-per-app", scopeBuddyKey] });
      await qc.invalidateQueries({ queryKey: ["scopebuddy-per-app"] });
      appShowToast("Override removed");
    },
    onError: () => appShowToast("Failed to delete override", "error"),
  });

  const handleAutoChange = useCallback((keys: Iterable<Key>) => {
    const set = new Set([...keys].map(String));
    setLocal((prev) => {
      let next = { ...prev };
      for (const d of SCB_AUTO_DEFS) {
        if (set.has(d.id)) {
          next[d.cfgKey] = "1";
        } else {
          next = patchCfg(next, { [d.cfgKey]: "" });
        }
      }
      return next;
    });
  }, []);

  const applyBuilderArgs = useCallback(() => {
    const args = gamescopeArgsFromBuilderPreview(gamescopeBuilderPreview);
    if (!args) {
      appShowToast("Build a raw gamescope line in the builder first", "error");
      return;
    }
    setLocal((prev) => ({ ...prev, SCB_GAMESCOPE_ARGS: args }));
    appShowToast("Copied gamescope args into SCB_GAMESCOPE_ARGS (save to write)");
  }, [gamescopeBuilderPreview]);

  const openConfDir = useCallback(async () => {
    try {
      const p = perApp?.path ?? "";
      const dir = p.replace(/\/[^/]+$/, "") || avail?.config_dir;
      if (dir) await api.openPath(dir);
    } catch {
      appShowToast("Could not open folder", "error");
    }
  }, [perApp?.path, avail?.config_dir]);

  if (!avail?.available) {
    return null;
  }

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Telescope className="size-4 shrink-0 text-neon-cyan" aria-hidden />
          ScopeBuddy override
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {keyLabel}
          </Chip>
        </Widget.Title>
        <InfoHint label="Per-game ScopeBuddy">
          Writes ~/.config/scopebuddy/AppID/&lt;key&gt;.conf. Steam uses the numeric app id; Heroic/Lutris use a
          slug matching MangoHud per-game naming.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        {isLoading ? (
          <Text.Paragraph size="xs" color="muted">
            Loading…
          </Text.Paragraph>
        ) : (
          <>
            <TextField
              value={local.SCB_GAMESCOPE_ARGS ?? ""}
              onChange={(v) => setLocal((p) => ({ ...p, SCB_GAMESCOPE_ARGS: v }))}
              variant="secondary"
              fullWidth
            >
              <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                SCB_GAMESCOPE_ARGS
              </Label>
              <TextArea
                placeholder="e.g. -W 2560 -H 1440 -w 1920 -h 1080 -f -b --hdr-enabled"
                rows={3}
                className="resize-none font-mono text-xs"
              />
            </TextField>

            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" onPress={applyBuilderArgs} className="gap-1.5">
                <Layers className="size-3.5 shrink-0" aria-hidden />
                From Gamescope builder
              </Button>
              <Button size="sm" variant="secondary" onPress={() => setPresetOpen(true)} className="gap-1.5">
                <Layers className="size-3.5 shrink-0" aria-hidden />
                Apply preset…
              </Button>
            </div>

            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                  SCB_AUTO_* in this file
                </Label>
                <Tooltip delay={0}>
                  <Chip size="sm" variant="secondary" className="text-[9px]">
                    {canAuto ? "Probe OK" : "Limited"}
                  </Chip>
                  <Tooltip.Content className="max-w-xs text-xs">{autoDetectTooltip(caps)}</Tooltip.Content>
                </Tooltip>
              </div>
              <CheckboxButtonGroup
                aria-label="ScopeBuddy per-app auto flags"
                className="grid w-full grid-cols-2 gap-1.5 min-[380px]:grid-cols-3"
                layout="grid"
                name="scopebuddy-per-app-auto"
                value={selectedAutoKeys}
                variant="secondary"
                onChange={(keys) => handleAutoChange(keys)}
              >
                {SCB_AUTO_DEFS.map((feat) => {
                  const Icon = feat.Icon;
                  const disabled = !canAuto;
                  const item = (
                    <CheckboxButtonGroup.Item
                      key={feat.id}
                      value={feat.id}
                      isDisabled={disabled}
                      className="min-h-[4.5rem]"
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
                      <Tooltip.Content className="max-w-xs text-xs">{autoDetectTooltip(caps)}</Tooltip.Content>
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
                  Skip gamescope for this title (experimental).
                </Text.Paragraph>
              </div>
              <Switch
                isSelected={noscopeOn}
                onChange={() =>
                  setLocal((p) =>
                    noscopeOn ? patchCfg(p, { SCB_NOSCOPE: "" }) : { ...p, SCB_NOSCOPE: "1" },
                  )
                }
                aria-label="SCB_NOSCOPE in per-app config"
              >
                <Switch.Control>
                  <Switch.Thumb />
                </Switch.Control>
              </Switch>
            </div>

            <ButtonGroup className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onPress={() => saveMut.mutate()}
                isDisabled={saveMut.isPending}
                className="gap-1.5"
              >
                <Save className="size-3.5 shrink-0" aria-hidden />
                Save
              </Button>
              <Button
                size="sm"
                variant="outline"
                onPress={() => deleteMut.mutate()}
                isDisabled={deleteMut.isPending || !perApp?.exists}
                className="gap-1.5"
              >
                <Trash2 className="size-3.5 shrink-0" aria-hidden />
                Delete override
              </Button>
              <Button size="sm" variant="secondary" onPress={() => void openConfDir()} className="gap-1.5">
                <FolderOpen className="size-3.5 shrink-0" aria-hidden />
                Open folder
              </Button>
            </ButtonGroup>

            <Text.Paragraph size="xs" color="muted" className="font-mono text-[10px] leading-tight break-all">
              {perApp?.path ?? ""}
            </Text.Paragraph>
          </>
        )}

        <Sheet isOpen={presetOpen} onOpenChange={setPresetOpen}>
          <Sheet.Backdrop variant="blur">
            <Sheet.Content className="mx-auto max-h-[90vh] max-w-[min(100vw-1rem,420px)]">
              <Sheet.Dialog>
                <Sheet.Handle />
                <Sheet.CloseTrigger />
                <Sheet.Header>
                  <Sheet.Heading>ScopeBuddy presets</Sheet.Heading>
                </Sheet.Header>
                <Sheet.Body className="space-y-2">
                  {presets &&
                    Object.entries(presets).map(([name, vars]) => (
                      <Button
                        key={name}
                        variant="secondary"
                        size="sm"
                        className="h-auto w-full justify-start py-2"
                        onPress={() => {
                          setLocal((prev) => ({ ...prev, ...vars }));
                          setPresetOpen(false);
                          appShowToast(`Merged preset: ${name}`);
                        }}
                      >
                        <span className="text-left text-xs font-semibold">{name}</span>
                      </Button>
                    ))}
                </Sheet.Body>
                <Sheet.Footer>
                  <Sheet.Close>
                    <Button variant="secondary" size="sm">
                      Close
                    </Button>
                  </Sheet.Close>
                </Sheet.Footer>
              </Sheet.Dialog>
            </Sheet.Content>
          </Sheet.Backdrop>
        </Sheet>
      </Widget.Content>
    </Widget>
  );
}
