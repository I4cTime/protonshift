"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Telescope,
  RefreshCw,
  FolderOpen,
  Layers,
  Save,
  Trash2,
  Plus,
  FilePlus2,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  type LucideIcon,
} from "lucide-react";
import {
  Alert,
  Button,
  ButtonGroup,
  Card,
  Chip,
  Input,
  Label,
  Link as HeroLink,
  Spinner,
  Text,
  TextField,
  Tooltip,
} from "@heroui/react";
import { EmptyState, ItemCard, ItemCardGroup, Sheet, Widget } from "@heroui-pro/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageShell } from "@/components/page-shell";
import { ScbKvEditor } from "@/components/scb-kv-editor";
import { api, type ScopeBuddyAutoCaps } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

const SCB_KNOWN_KEYS = [
  "SCB_GAMESCOPE_ARGS",
  "SCB_AUTO_RES",
  "SCB_AUTO_HDR",
  "SCB_AUTO_VRR",
  "SCB_AUTO_REFRESH",
  "SCB_AUTO_FRAME_LIMIT",
  "SCB_NOSCOPE",
  "SCB_NESTEDFIX",
  "SCB_APPENDMODE",
  "SCB_DEBUG",
] as const;

const SCOPEBUDDY_INSTALL_ROWS: { distro: string; cmd: string }[] = [
  { distro: "Bazzite / SteamOS", cmd: "Often pre-installed — check PATH" },
  { distro: "Fedora (Terra)", cmd: "sudo dnf install ScopeBuddy" },
  { distro: "Arch / AUR", cmd: "yay -S scopebuddy-git" },
  {
    distro: "curl (any distro)",
    cmd: "curl -fsSL https://raw.githubusercontent.com/HikariKnight/ScopeBuddy/refs/heads/main/bin/scopebuddy | sudo tee /usr/local/bin/scopebuddy && sudo chmod +x /usr/local/bin/scopebuddy",
  },
  { distro: "NixOS / Home Manager", cmd: "inputs.scopebuddy.url = github:HikariKnight/ScopeBuddy" },
];

interface CapRow {
  id: keyof ScopeBuddyAutoCaps;
  label: string;
  hint: string;
}

const CAP_ROWS: CapRow[] = [
  { id: "kde", label: "KDE Plasma", hint: "kscreen-doctor + jq" },
  { id: "gnome_gdctl", label: "GNOME (gdctl JSON)", hint: "upstream gdctl with --format=json + jq" },
  { id: "gnome_randr", label: "GNOME (gnome-randr)", hint: "fallback when gdctl JSON missing" },
  { id: "wlroots", label: "wlroots compositor", hint: "wlr-randr + jq" },
  { id: "jq", label: "jq", hint: "required for all SCB_AUTO_* probes" },
];

interface KvSheetState {
  kind: "per-app" | "envvars";
  key: string;
  isNew: boolean;
}

interface ScbConfFile {
  path: string;
  exists: boolean;
  config: Record<string, string>;
}

function presetButtons(presets: Record<string, Record<string, string>> | undefined) {
  if (!presets) return null;
  return Object.entries(presets).map(([name, vars]) => ({
    name,
    vars,
    summary: Object.keys(vars).join(", "),
  }));
}

export default function ScopeBuddyPage() {
  const qc = useQueryClient();
  const [globalCfg, setGlobalCfg] = useState<Record<string, string>>({});
  const [globalDirty, setGlobalDirty] = useState(false);
  const [editorState, setEditorState] = useState<KvSheetState | null>(null);
  const [editorCfg, setEditorCfg] = useState<Record<string, string>>({});
  const [editorDirty, setEditorDirty] = useState(false);
  const [newKeyInput, setNewKeyInput] = useState("");

  const { data: avail, isLoading: availLoading } = useQuery({
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

  const { data: globalConfig } = useQuery({
    queryKey: ["scopebuddy-config"],
    queryFn: api.getScopeBuddyConfig,
    enabled: !!avail?.available,
  });

  const { data: presets } = useQuery({
    queryKey: ["scopebuddy-presets"],
    queryFn: api.getScopeBuddyPresets,
    enabled: !!avail?.available,
  });

  const { data: perAppList } = useQuery({
    queryKey: ["scopebuddy-per-app"],
    queryFn: api.listScopeBuddyPerApp,
    enabled: !!avail?.available,
  });

  const { data: envVarsList } = useQuery({
    queryKey: ["scopebuddy-envvars"],
    queryFn: api.listScopeBuddyEnvVars,
    enabled: !!avail?.available,
  });

  const { data: openItem } = useQuery<ScbConfFile>({
    queryKey: ["scopebuddy-open", editorState?.kind, editorState?.key],
    enabled: !!editorState && !editorState.isNew,
    queryFn: async (): Promise<ScbConfFile> => {
      if (!editorState) throw new Error("no editor");
      const r =
        editorState.kind === "per-app"
          ? await api.getScopeBuddyPerApp(editorState.key)
          : await api.getScopeBuddyEnvVars(editorState.key);
      return { path: r.path, exists: r.exists, config: r.config };
    },
  });

  useEffect(() => {
    if (!globalConfig?.config) return;
    queueMicrotask(() => {
      setGlobalCfg({ ...globalConfig.config });
      setGlobalDirty(false);
    });
  }, [globalConfig?.exists, globalConfig?.config]);

  useEffect(() => {
    if (!editorState) {
      queueMicrotask(() => {
        setEditorCfg({});
        setEditorDirty(false);
      });
      return;
    }
    if (editorState.isNew) {
      queueMicrotask(() => {
        setEditorCfg({});
        setEditorDirty(false);
      });
      return;
    }
    if (openItem?.config) {
      const next = { ...openItem.config };
      queueMicrotask(() => {
        setEditorCfg(next);
        setEditorDirty(false);
      });
    }
  }, [editorState, openItem?.config]);

  const rescanMut = useMutation({
    mutationFn: () => api.rescanScopeBuddy(),
    onSuccess: async (info) => {
      qc.setQueryData(["scopebuddy-available"], info);
      await qc.invalidateQueries({ queryKey: ["scopebuddy-auto-caps"] });
      appShowToast(
        info.available
          ? `ScopeBuddy detected: ${info.binary}${info.version ? ` v${info.version}` : ""}`
          : "ScopeBuddy still not on PATH",
        info.available ? "success" : "error",
      );
    },
    onError: () => appShowToast("Rescan failed", "error"),
  });

  const saveGlobalMut = useMutation({
    mutationFn: () => api.setScopeBuddyConfig(globalCfg),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["scopebuddy-config"] });
      setGlobalDirty(false);
      appShowToast("Saved global scb.conf");
    },
    onError: () => appShowToast("Failed to save global config", "error"),
  });

  const saveEditorMut = useMutation({
    mutationFn: () => {
      if (!editorState) return Promise.reject(new Error("no editor"));
      return editorState.kind === "per-app"
        ? api.setScopeBuddyPerApp(editorState.key, editorCfg)
        : api.setScopeBuddyEnvVars(editorState.key, editorCfg);
    },
    onSuccess: async () => {
      if (!editorState) return;
      await qc.invalidateQueries({ queryKey: ["scopebuddy-open", editorState.kind, editorState.key] });
      await qc.invalidateQueries({
        queryKey: editorState.kind === "per-app" ? ["scopebuddy-per-app"] : ["scopebuddy-envvars"],
      });
      setEditorDirty(false);
      appShowToast("Saved");
    },
    onError: () => appShowToast("Save failed", "error"),
  });

  const deleteEditorMut = useMutation({
    mutationFn: () => {
      if (!editorState) return Promise.reject(new Error("no editor"));
      return editorState.kind === "per-app"
        ? api.deleteScopeBuddyPerApp(editorState.key)
        : api.deleteScopeBuddyEnvVars(editorState.key);
    },
    onSuccess: async () => {
      if (!editorState) return;
      await qc.invalidateQueries({
        queryKey: editorState.kind === "per-app" ? ["scopebuddy-per-app"] : ["scopebuddy-envvars"],
      });
      setEditorState(null);
      appShowToast("Removed");
    },
    onError: () => appShowToast("Delete failed", "error"),
  });

  const presetRows = useMemo(() => presetButtons(presets), [presets]);

  const openConfigDir = async () => {
    try {
      await api.openPath(avail?.config_dir || "~/.config/scopebuddy");
    } catch {
      appShowToast("Could not open ScopeBuddy config folder", "error");
    }
  };

  const openItemPath = async (path: string | undefined) => {
    if (!path) return;
    try {
      await api.openPath(path);
    } catch {
      appShowToast("Could not open file", "error");
    }
  };

  function startNewEditor(kind: "per-app" | "envvars") {
    setNewKeyInput("");
    setEditorState({ kind, key: "", isNew: true });
  }

  function commitNewKey() {
    const trimmed = newKeyInput.trim();
    if (!trimmed) {
      appShowToast("Pick a name first", "error");
      return;
    }
    if (!editorState) return;
    setEditorState({ ...editorState, key: trimmed, isNew: false });
  }

  return (
    <PageShell>
      <div className="mx-auto max-w-4xl space-y-5">
        {/* Header */}
        <div className="space-y-1">
          <Text.Heading
            level={2}
            className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
          >
            <Telescope className="size-5 shrink-0" aria-hidden />
            ScopeBuddy
          </Text.Heading>
          <Text.Paragraph size="xs" color="muted">
            Manage <Text.Code className="text-neon-cyan text-[11px]">~/.config/scopebuddy/scb.conf</Text.Code>,
            per-app overrides, and shared envvars snippets.{" "}
            <HeroLink
              href="https://github.com/OpenGamingCollective/ScopeBuddy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-neon-cyan"
            >
              Project
            </HeroLink>
          </Text.Paragraph>
        </div>

        {/* Status / rescan / open dir */}
        <Widget>
          <Widget.Header>
            <Widget.Title className="flex flex-wrap items-center gap-1.5">
              <Telescope className="text-neon-cyan size-4 shrink-0" aria-hidden />
              Status
            </Widget.Title>
          </Widget.Header>
          <Widget.Content className="space-y-2">
            {availLoading ? (
              <div className="flex items-center justify-center py-6">
                <Spinner size="sm" />
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2">
                <Chip
                  size="sm"
                  variant="secondary"
                  className="text-[10px] font-mono"
                  color={avail?.available ? "success" : "warning"}
                >
                  {avail?.available
                    ? `${avail.binary}${avail.version ? ` · v${avail.version}` : ""}`
                    : "scb · missing"}
                </Chip>
                <Chip size="sm" variant="secondary" className="text-[10px] font-mono">
                  {avail?.config_dir || "~/.config/scopebuddy"}
                </Chip>
                <ButtonGroup className="ml-auto">
                  <Tooltip delay={0}>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-8 gap-1.5 px-2 text-xs"
                      onPress={() => rescanMut.mutate()}
                      isDisabled={rescanMut.isPending}
                    >
                      <RefreshCw
                        className={`size-3.5 shrink-0 ${rescanMut.isPending ? "animate-spin" : ""}`}
                        aria-hidden
                      />
                      Rescan
                    </Button>
                    <Tooltip.Content>Re-detect scb / scopebuddy on PATH</Tooltip.Content>
                  </Tooltip>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1.5 px-2 text-xs"
                    onPress={() => void openConfigDir()}
                  >
                    <FolderOpen className="size-3.5 shrink-0" aria-hidden />
                    Open folder
                  </Button>
                </ButtonGroup>
              </div>
            )}
            {!availLoading && !avail?.available && (
              <Alert status="warning">
                <Alert.Indicator />
                <Alert.Content>
                  <Alert.Title>ScopeBuddy is not installed</Alert.Title>
                  <Alert.Description>
                    Install one of the options below, then click Rescan — no app restart needed.
                  </Alert.Description>
                </Alert.Content>
              </Alert>
            )}
            {!availLoading && !avail?.available && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {SCOPEBUDDY_INSTALL_ROWS.map((row) => (
                  <Card key={row.distro} className="border-border bg-surface-deep/50 p-2">
                    <Card.Title className="text-muted mb-1 text-[10px] font-medium">{row.distro}</Card.Title>
                    <Text.Code className="text-neon-cyan block text-[10px] leading-snug break-all">
                      {row.cmd}
                    </Text.Code>
                  </Card>
                ))}
              </div>
            )}
          </Widget.Content>
        </Widget>

        {/* Auto-detect capabilities */}
        {avail?.available && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex items-center gap-1.5">
                <Layers className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Auto-detect probes
              </Widget.Title>
            </Widget.Header>
            <Widget.Content>
              <Text.Paragraph size="xs" color="muted" className="mb-2 leading-snug">
                ScopeBuddy infers display settings via these backends. Greys out flags that won&apos;t actually
                fire on your session.
              </Text.Paragraph>
              <ItemCardGroup variant="secondary" layout="list" className="overflow-hidden rounded-xl">
                {CAP_ROWS.map((row) => {
                  const ok = !!caps?.[row.id];
                  const Icon: LucideIcon = ok ? CheckCircle2 : AlertCircle;
                  return (
                    <ItemCard key={row.id} className="py-2.5">
                      <ItemCard.Icon
                        className={`bg-surface-secondary ${ok ? "text-success" : "text-warning"}`}
                      >
                        <Icon className="size-4 shrink-0" aria-hidden />
                      </ItemCard.Icon>
                      <ItemCard.Content className="min-w-0 gap-0.5">
                        <ItemCard.Title className="flex items-center gap-2">
                          <span className="truncate">{row.label}</span>
                          <Chip
                            size="sm"
                            variant="secondary"
                            color={ok ? "success" : "warning"}
                            className="text-[9px]"
                          >
                            {ok ? "available" : "missing"}
                          </Chip>
                        </ItemCard.Title>
                        <Text.Paragraph size="xs" color="muted" className="leading-snug">
                          {row.hint}
                        </Text.Paragraph>
                      </ItemCard.Content>
                    </ItemCard>
                  );
                })}
              </ItemCardGroup>
            </Widget.Content>
          </Widget>
        )}

        {/* Global scb.conf */}
        {avail?.available && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex flex-wrap items-center gap-1.5">
                <Telescope className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Global scb.conf
                {globalConfig?.exists ? (
                  <Chip size="sm" variant="secondary" color="success" className="text-[10px]">
                    exists
                  </Chip>
                ) : (
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    new file
                  </Chip>
                )}
                {globalDirty && (
                  <Chip size="sm" variant="secondary" color="warning" className="text-[10px]">
                    unsaved
                  </Chip>
                )}
              </Widget.Title>
            </Widget.Header>
            <Widget.Content className="space-y-3">
              <Text.Paragraph size="xs" color="muted" className="font-mono text-[10px] break-all leading-tight">
                {globalConfig?.path}
              </Text.Paragraph>
              <ScbKvEditor
                value={globalCfg}
                onChange={(next) => {
                  setGlobalCfg(next);
                  setGlobalDirty(true);
                }}
                knownKeys={SCB_KNOWN_KEYS}
                ariaLabel="Global ScopeBuddy config keys"
              />
              {presetRows && presetRows.length > 0 && (
                <div className="space-y-1.5">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Apply preset (merges into current keys)
                  </Label>
                  <div className="flex flex-wrap gap-1.5">
                    {presetRows.map((p) => (
                      <Tooltip key={p.name} delay={0}>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 gap-1 px-2 text-[10px]"
                          onPress={() => {
                            setGlobalCfg((prev) => ({ ...prev, ...p.vars }));
                            setGlobalDirty(true);
                            appShowToast(`Merged preset: ${p.name}`);
                          }}
                        >
                          <Plus className="size-3 shrink-0" aria-hidden />
                          {p.name}
                        </Button>
                        <Tooltip.Content className="max-w-xs text-xs">{p.summary}</Tooltip.Content>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              )}
              <ButtonGroup className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onPress={() => saveGlobalMut.mutate()}
                  isDisabled={saveGlobalMut.isPending || !globalDirty}
                  className="gap-1.5"
                >
                  <Save className="size-3.5 shrink-0" aria-hidden />
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onPress={() => void openItemPath(globalConfig?.path)}
                  isDisabled={!globalConfig?.path}
                  className="gap-1.5"
                >
                  <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                  Open in editor
                </Button>
              </ButtonGroup>
            </Widget.Content>
          </Widget>
        )}

        {/* Per-app overrides */}
        {avail?.available && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex flex-wrap items-center gap-1.5">
                <Layers className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Per-app overrides
                <Chip size="sm" variant="secondary" className="text-[10px]">
                  {perAppList?.length ?? 0}
                </Chip>
              </Widget.Title>
            </Widget.Header>
            <Widget.Content className="space-y-3">
              <Text.Paragraph size="xs" color="muted" className="leading-snug">
                Files under <Text.Code className="text-neon-cyan text-[11px]">AppID/&lt;key&gt;.conf</Text.Code>.
                Steam uses the numeric app id; Heroic and Lutris use the same slug as MangoHud per-game configs.
              </Text.Paragraph>
              {perAppList && perAppList.length > 0 ? (
                <ItemCardGroup variant="secondary" layout="list" className="overflow-hidden rounded-xl">
                  {perAppList.map((row) => (
                    <ItemCard key={row.key} className="py-2.5">
                      <ItemCard.Icon className="bg-surface-secondary text-neon-cyan">
                        <Telescope className="size-4 shrink-0" aria-hidden />
                      </ItemCard.Icon>
                      <ItemCard.Content className="min-w-0 gap-0.5">
                        <ItemCard.Title className="truncate font-mono text-xs">{row.key}</ItemCard.Title>
                        <Text.Code className="text-muted/80 mt-0.5 block truncate text-[10px]" title={row.path}>
                          {row.path}
                        </Text.Code>
                      </ItemCard.Content>
                      <ItemCard.Action>
                        <ButtonGroup>
                          <Button
                            size="sm"
                            variant="secondary"
                            onPress={() => setEditorState({ kind: "per-app", key: row.key, isNew: false })}
                          >
                            Edit
                          </Button>
                          <Tooltip delay={0}>
                            <Button
                              isIconOnly
                              size="sm"
                              variant="outline"
                              aria-label={`Open ${row.key} in editor`}
                              onPress={() => void openItemPath(row.path)}
                            >
                              <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                            </Button>
                            <Tooltip.Content>Open in system editor</Tooltip.Content>
                          </Tooltip>
                        </ButtonGroup>
                      </ItemCard.Action>
                    </ItemCard>
                  ))}
                </ItemCardGroup>
              ) : (
                <EmptyState size="sm">
                  <EmptyState.Header>
                    <EmptyState.Media variant="icon">
                      <Telescope className="size-5" aria-hidden />
                    </EmptyState.Media>
                    <EmptyState.Title>No per-app overrides yet</EmptyState.Title>
                    <EmptyState.Description className="text-center">
                      Create one for a game from the Games tab, or use the button below to add one by raw key.
                    </EmptyState.Description>
                  </EmptyState.Header>
                </EmptyState>
              )}
              <Button
                size="sm"
                variant="secondary"
                onPress={() => startNewEditor("per-app")}
                className="gap-1.5"
              >
                <FilePlus2 className="size-3.5 shrink-0" aria-hidden />
                New override by app id / slug
              </Button>
            </Widget.Content>
          </Widget>
        )}

        {/* Envvars snippets */}
        {avail?.available && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex flex-wrap items-center gap-1.5">
                <Layers className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Envvars snippets
                <Chip size="sm" variant="secondary" className="text-[10px]">
                  {envVarsList?.length ?? 0}
                </Chip>
              </Widget.Title>
            </Widget.Header>
            <Widget.Content className="space-y-3">
              <Text.Paragraph size="xs" color="muted" className="leading-snug">
                Reusable env-var bundles under <Text.Code className="text-neon-cyan text-[11px]">envvars/&lt;name&gt;.conf</Text.Code>.
                Activate from a game by setting <Text.Code className="text-neon-cyan text-[11px]">SCB_ENV=&lt;name&gt;</Text.Code>{" "}
                in launch options.
              </Text.Paragraph>
              {envVarsList && envVarsList.length > 0 ? (
                <ItemCardGroup variant="secondary" layout="list" className="overflow-hidden rounded-xl">
                  {envVarsList.map((row) => (
                    <ItemCard key={row.name} className="py-2.5">
                      <ItemCard.Icon className="bg-surface-secondary text-neon-cyan">
                        <Layers className="size-4 shrink-0" aria-hidden />
                      </ItemCard.Icon>
                      <ItemCard.Content className="min-w-0 gap-0.5">
                        <ItemCard.Title className="truncate font-mono text-xs">{row.name}</ItemCard.Title>
                        <Text.Code className="text-muted/80 mt-0.5 block truncate text-[10px]" title={row.path}>
                          {row.path}
                        </Text.Code>
                      </ItemCard.Content>
                      <ItemCard.Action>
                        <ButtonGroup>
                          <Button
                            size="sm"
                            variant="secondary"
                            onPress={() => setEditorState({ kind: "envvars", key: row.name, isNew: false })}
                          >
                            Edit
                          </Button>
                          <Tooltip delay={0}>
                            <Button
                              isIconOnly
                              size="sm"
                              variant="outline"
                              aria-label={`Open ${row.name} in editor`}
                              onPress={() => void openItemPath(row.path)}
                            >
                              <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                            </Button>
                            <Tooltip.Content>Open in system editor</Tooltip.Content>
                          </Tooltip>
                        </ButtonGroup>
                      </ItemCard.Action>
                    </ItemCard>
                  ))}
                </ItemCardGroup>
              ) : (
                <EmptyState size="sm">
                  <EmptyState.Header>
                    <EmptyState.Media variant="icon">
                      <Layers className="size-5" aria-hidden />
                    </EmptyState.Media>
                    <EmptyState.Title>No envvars snippets yet</EmptyState.Title>
                    <EmptyState.Description className="text-center">
                      Create one to share Proton/DXVK tweaks across multiple games.
                    </EmptyState.Description>
                  </EmptyState.Header>
                </EmptyState>
              )}
              <Button
                size="sm"
                variant="secondary"
                onPress={() => startNewEditor("envvars")}
                className="gap-1.5"
              >
                <FilePlus2 className="size-3.5 shrink-0" aria-hidden />
                New envvars snippet
              </Button>
            </Widget.Content>
          </Widget>
        )}

        {/* Editor sheet */}
        <Sheet
          isOpen={!!editorState}
          onOpenChange={(open) => {
            if (!open) {
              setEditorState(null);
            }
          }}
        >
          <Sheet.Backdrop variant="blur">
            <Sheet.Content className="mx-auto max-h-[92vh] max-w-[min(100vw-1rem,640px)]">
              <Sheet.Dialog>
                <Sheet.Handle />
                <Sheet.CloseTrigger />
                <Sheet.Header>
                  <Sheet.Heading className="flex flex-wrap items-center gap-2">
                    {editorState?.kind === "per-app" ? "Per-app override" : "Envvars snippet"}
                    {editorState?.key && (
                      <Chip size="sm" variant="secondary" className="text-[10px] font-mono">
                        {editorState.key}
                      </Chip>
                    )}
                    {editorDirty && (
                      <Chip size="sm" variant="secondary" color="warning" className="text-[10px]">
                        unsaved
                      </Chip>
                    )}
                  </Sheet.Heading>
                </Sheet.Header>
                <Sheet.Body className="space-y-3">
                  {editorState?.isNew ? (
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                      <TextField
                        value={newKeyInput}
                        onChange={setNewKeyInput}
                        className="min-w-0 flex-1"
                      >
                        <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                          {editorState.kind === "per-app"
                            ? "Steam app id or game slug"
                            : "Snippet name"}
                        </Label>
                        <Input
                          placeholder={
                            editorState.kind === "per-app"
                              ? "e.g. 12345 or My_Game_Name"
                              : "e.g. nvidia-wayland"
                          }
                          variant="secondary"
                          className="font-mono text-xs"
                          onKeyDown={(e) => e.key === "Enter" && commitNewKey()}
                        />
                      </TextField>
                      <Button size="sm" onPress={commitNewKey}>
                        Continue
                      </Button>
                    </div>
                  ) : openItem ? (
                    <>
                      <Text.Paragraph
                        size="xs"
                        color="muted"
                        className="font-mono text-[10px] break-all leading-tight"
                      >
                        {openItem.path}
                      </Text.Paragraph>
                      <ScbKvEditor
                        value={editorCfg}
                        onChange={(next) => {
                          setEditorCfg(next);
                          setEditorDirty(true);
                        }}
                        knownKeys={SCB_KNOWN_KEYS}
                        ariaLabel={`${editorState?.kind} editor`}
                      />
                    </>
                  ) : (
                    <div className="flex items-center justify-center py-6">
                      <Spinner size="sm" />
                    </div>
                  )}
                </Sheet.Body>
                <Sheet.Footer className="flex flex-wrap gap-2">
                  <Sheet.Close>
                    <Button variant="secondary" size="sm">
                      Close
                    </Button>
                  </Sheet.Close>
                  {editorState && !editorState.isNew && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onPress={() => deleteEditorMut.mutate()}
                        isDisabled={deleteEditorMut.isPending}
                        className="gap-1.5"
                      >
                        <Trash2 className="size-3.5 shrink-0" aria-hidden />
                        Delete
                      </Button>
                      <Button
                        size="sm"
                        onPress={() => saveEditorMut.mutate()}
                        isDisabled={saveEditorMut.isPending || !editorDirty}
                        className="gap-1.5"
                      >
                        <Save className="size-3.5 shrink-0" aria-hidden />
                        Save
                      </Button>
                    </>
                  )}
                </Sheet.Footer>
              </Sheet.Dialog>
            </Sheet.Content>
          </Sheet.Backdrop>
        </Sheet>
      </div>
    </PageShell>
  );
}
