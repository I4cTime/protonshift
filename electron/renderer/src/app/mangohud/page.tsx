"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "motion/react";
import {
  Gauge,
  Save,
  FileText,
  ChevronDown,
  ChevronRight,
  Plus,
  Layers,
  LayoutGrid,
  SlidersHorizontal,
  Code,
  Pencil,
  FilePlus2,
  Search,
  FolderOpen,
} from "lucide-react";
import {
  Button,
  Card,
  Chip,
  Input,
  Label,
  Link as HeroLink,
  ListBox,
  Select,
  Spinner,
  Text,
  TextField,
} from "@heroui/react";
import { EmptyState, ListView, Widget } from "@heroui-pro/react";
import type { Selection } from "react-aria-components";
import { PageShell } from "@/components/page-shell";
import { MangoHudOverlayMetrics } from "@/components/mangohud-overlay-metrics";
import { MangoHudPresets } from "@/components/mangohud-presets";
import { MangoHudValueFieldsGrid } from "@/components/mangohud-value-field";
import { api } from "@/lib/api";
import { mangohudPerGameSlug, mangohudSuggestedSlugForGame } from "@/lib/mangohud-naming";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useGames } from "@/hooks/use-games";
import { appShowToast } from "@/lib/app-toast";

type MangoHudGamePick = { id: string; label: string; suggestedSlug: string };

const INSTALL_HINTS: { distro: string; cmd: string }[] = [
  { distro: "Bazzite / SteamOS", cmd: "Pre-installed — restart app or check PATH" },
  { distro: "Ubuntu / Pop!_OS / Mint", cmd: "sudo apt install mangohud" },
  { distro: "Fedora / Fedora Atomic", cmd: "sudo dnf install mangohud" },
  { distro: "Arch / Manjaro / EndeavourOS", cmd: "sudo pacman -S mangohud" },
  { distro: "openSUSE", cmd: "sudo zypper install mangohud" },
  {
    distro: "Flatpak (Steam)",
    cmd: "flatpak install flathub org.freedesktop.Platform.VulkanLayer.MangoHud",
  },
  { distro: "NixOS", cmd: "nix-env -iA nixpkgs.mangohud" },
];

export default function MangoHudPage() {
  const qc = useQueryClient();
  const { data: availData } = useQuery({
    queryKey: ["mangohud-available"],
    queryFn: api.getMangoHudAvailable,
    staleTime: 60_000,
  });
  const { data: configData, isLoading } = useQuery({
    queryKey: ["mangohud-config"],
    queryFn: api.getMangoHudConfig,
  });
  const { data: presets } = useQuery({
    queryKey: ["mangohud-presets"],
    queryFn: api.getMangoHudPresets,
  });

  const { data: perGameList } = useQuery({
    queryKey: ["mangohud-per-game-list"],
    queryFn: api.listMangoHudPerGame,
    staleTime: 30_000,
  });

  const { data: gamesData } = useGames();

  const mangohudGamePicks = useMemo((): MangoHudGamePick[] => {
    if (!gamesData) return [];
    const picks: MangoHudGamePick[] = [];
    for (const g of gamesData.steam) {
      picks.push({
        id: `steam:${g.app_id}`,
        label: `[Steam] ${g.name}`,
        suggestedSlug: mangohudSuggestedSlugForGame(g),
      });
    }
    for (const g of gamesData.heroic) {
      picks.push({
        id: `heroic:${g.app_id}`,
        label: `[${g.store === "gog" ? "GOG" : "Epic"}] ${g.name}`,
        suggestedSlug: mangohudSuggestedSlugForGame(g),
      });
    }
    for (const g of gamesData.lutris) {
      picks.push({
        id: `lutris:${g.app_id}`,
        label: `[Lutris] ${g.name}`,
        suggestedSlug: mangohudSuggestedSlugForGame(g),
      });
    }
    picks.sort((a, b) =>
      a.label.localeCompare(b.label, undefined, { sensitivity: "base" }),
    );
    return picks;
  }, [gamesData]);

  const [config, setConfig] = useState<Record<string, string>>({});
  const [editingGame, setEditingGame] = useState<string | null>(null);
  const [gameConfig, setGameConfig] = useState<Record<string, string>>({});
  const [showPerGame, setShowPerGame] = useState(false);
  const [newPerGameName, setNewPerGameName] = useState("");
  const [selectedGamePickId, setSelectedGamePickId] = useState<string>("");

  const saveMut = useMutation({
    mutationFn: (cfg: Record<string, string>) => api.setMangoHudConfig(cfg),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mangohud-config"] });
      appShowToast("Global config saved");
    },
    onError: () => appShowToast("Failed to save", "error"),
  });

  const savePerGameMut = useMutation({
    mutationFn: ({ name, cfg }: { name: string; cfg: Record<string, string> }) =>
      api.setMangoHudPerGameConfig(name, cfg),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mangohud-per-game-list"] });
      appShowToast("Per-game config saved");
    },
    onError: () => appShowToast("Failed to save per-game config", "error"),
  });

  const createPerGameMut = useMutation({
    mutationFn: ({ name, cfg }: { name: string; cfg: Record<string, string> }) =>
      api.setMangoHudPerGameConfig(name, cfg),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["mangohud-per-game-list"] });
      const slug = mangohudPerGameSlug(vars.name);
      appShowToast(`Created wine-${slug}.conf`);
      setNewPerGameName("");
      setSelectedGamePickId("");
      setGameConfig(vars.cfg);
      setEditingGame(slug);
    },
    onError: () => appShowToast("Failed to create per-game config", "error"),
  });

  async function loadPerGameConfig(name: string) {
    try {
      const data = await api.getMangoHudPerGameConfig(name);
      setGameConfig(data.config);
      setEditingGame(mangohudPerGameSlug(name));
    } catch {
      appShowToast("Failed to load per-game config", "error");
    }
  }

  function handleCreatePerGame(initial: "global" | "empty") {
    const raw = newPerGameName.trim();
    if (!raw) {
      appShowToast(
        "Enter a config name (often the game .exe stem, e.g. eldenring)",
        "error",
      );
      return;
    }
    const slug = mangohudPerGameSlug(raw);
    const exists = perGameList?.some((p) => p.name === slug);
    if (exists) {
      appShowToast(
        "That config already exists — pick it in the list below",
        "error",
      );
      return;
    }
    const cfg = initial === "global" ? { ...config } : {};
    createPerGameMut.mutate({ name: raw, cfg });
  }

  useEffect(() => {
    if (!configData) return;
    queueMicrotask(() => setConfig(configData.config));
  }, [configData]);

  /** Deep-link from Games page: /mangohud?slug=…&pick=steam:… */
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const url = new URL(window.location.href);
      const slug = url.searchParams.get("slug");
      const pick = url.searchParams.get("pick");
      if (!slug && !pick) return;
      queueMicrotask(() => {
        if (slug) setNewPerGameName(slug);
        if (pick) setSelectedGamePickId(pick);
        setShowPerGame(true);
      });
      url.searchParams.delete("slug");
      url.searchParams.delete("pick");
      const rest = url.searchParams.toString();
      const path = url.pathname + url.hash;
      window.history.replaceState(null, "", rest ? `${path}?${rest}` : path);
    } catch {
      /* ignore */
    }
  }, []);

  function setParamValue(key: string, value: string) {
    setConfig((prev) => ({ ...prev, [key]: value }));
  }

  function applyPreset(presetName: string) {
    if (!presets) return;
    const preset = presets[presetName];
    if (!preset) return;
    setConfig(preset);
    appShowToast(`Applied "${presetName}" preset`);
  }

  /* ------------------------------ Not installed ----------------------------- */
  if (!availData?.available) {
    return (
      <PageShell>
        <div className="mx-auto max-w-4xl space-y-5">
          <div className="space-y-1">
            <Text.Heading
              level={2}
              className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
            >
              <Gauge className="size-5 shrink-0" aria-hidden />
              MangoHud
            </Text.Heading>
            <Text.Paragraph size="xs" color="muted">
              Vulkan/OpenGL overlay for FPS, GPU/CPU usage, temperatures, and
              frame timing.
            </Text.Paragraph>
          </div>

          <Widget>
            <Widget.Header>
              <Widget.Title className="flex items-center gap-1.5">
                <Gauge
                  className="text-neon-cyan size-4 shrink-0"
                  aria-hidden
                />
                MangoHud
                <Chip size="sm" color="warning" variant="soft" className="ml-1 text-[10px]">
                  Not installed
                </Chip>
              </Widget.Title>
            </Widget.Header>
            <Widget.Content className="space-y-4">
              <Text.Paragraph size="sm" color="muted" className="leading-relaxed">
                MangoHud is the go-to performance overlay for Linux gaming. Once
                installed, restart this app to detect it.
              </Text.Paragraph>

              <div className="space-y-2">
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                  Install via your package manager
                </Label>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {INSTALL_HINTS.map((item) => (
                    <Card
                      key={item.distro}
                      className="border-border bg-surface-secondary/40 p-2.5"
                    >
                      <Card.Header className="p-0 pb-1">
                        <Card.Title className="text-muted text-[11px] font-medium">
                          {item.distro}
                        </Card.Title>
                      </Card.Header>
                      <Card.Content className="p-0">
                        <Text.Code className="text-neon-cyan block break-all text-xs">
                          {item.cmd}
                        </Text.Code>
                      </Card.Content>
                    </Card>
                  ))}
                </div>
              </div>

              <Card className="border-border bg-surface-secondary/40 p-3">
                <Card.Header className="p-0 pb-1">
                  <Card.Title className="text-muted text-[11px] font-semibold uppercase tracking-wide">
                    Usage
                  </Card.Title>
                </Card.Header>
                <Card.Content className="p-0">
                  <Text.Paragraph size="xs" color="muted" className="leading-relaxed">
                    Add{" "}
                    <Text.Code className="text-neon-cyan text-[11px]">
                      MANGOHUD=1 %command%
                    </Text.Code>{" "}
                    to a game&apos;s launch options, or enable the MangoHud
                    preset on the Games page.
                  </Text.Paragraph>
                </Card.Content>
              </Card>

              <Text.Paragraph size="xs" color="muted" className="leading-relaxed">
                After installing, restart the app to detect MangoHud.{" "}
                <HeroLink
                  href="https://github.com/flightlessmango/MangoHud"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-neon-cyan text-xs"
                >
                  GitHub →
                </HeroLink>
              </Text.Paragraph>
            </Widget.Content>
          </Widget>
        </div>
      </PageShell>
    );
  }

  /* -------------------------------- Configured -------------------------------- */
  const toggleParams = configData?.params.filter((p) => p.type === "toggle") ?? [];
  const valueParams = configData?.params.filter((p) => p.type === "value") ?? [];
  const presetCount = presets ? Object.keys(presets).length : 0;
  const previewBody =
    Object.entries(config)
      .map(([k, v]) => (v ? `${k}=${v}` : k))
      .join("\n") || "# (empty config)";

  return (
    <PageShell>
      <div className="mx-auto max-w-4xl space-y-5">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <Text.Heading
              level={2}
              className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
            >
              <Gauge className="size-5 shrink-0" aria-hidden />
              MangoHud config
            </Text.Heading>
            <Text.Paragraph
              size="xs"
              color="muted"
              className="flex items-center gap-1.5"
            >
              <FileText className="size-3.5 shrink-0" aria-hidden />
              <Text.Code className="text-[11px]">
                ~/.config/MangoHud/MangoHud.conf
              </Text.Code>
            </Text.Paragraph>
          </div>
          <Button
            onPress={() => saveMut.mutate(config)}
            isDisabled={saveMut.isPending}
            className="gap-1.5"
          >
            {saveMut.isPending ? (
              <Spinner size="sm" />
            ) : (
              <Save className="size-3.5 shrink-0" aria-hidden />
            )}
            Save
          </Button>
        </div>

        {/* Quick presets */}
        {presets && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex items-center gap-1.5">
                <Layers
                  className="text-neon-cyan size-4 shrink-0"
                  aria-hidden
                />
                Quick presets
                {presetCount > 0 && (
                  <Chip
                    size="sm"
                    variant="secondary"
                    className="ml-1 text-[10px]"
                  >
                    {presetCount}
                  </Chip>
                )}
              </Widget.Title>
            </Widget.Header>
            <Widget.Content>
              <MangoHudPresets presets={presets} onApply={applyPreset} />
            </Widget.Content>
          </Widget>
        )}

        {isLoading ? (
          <Widget>
            <Widget.Content>
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            </Widget.Content>
          </Widget>
        ) : (
          <>
            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <LayoutGrid
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Overlay metrics
                  {toggleParams.length > 0 && (
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="ml-1 text-[10px]"
                    >
                      {toggleParams.length}
                    </Chip>
                  )}
                </Widget.Title>
              </Widget.Header>
              <Widget.Content>
                <MangoHudOverlayMetrics
                  toggleParams={toggleParams}
                  config={config}
                  setConfig={setConfig}
                />
              </Widget.Content>
            </Widget>

            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <SlidersHorizontal
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Configuration values
                  {valueParams.length > 0 && (
                    <Chip
                      size="sm"
                      variant="secondary"
                      className="ml-1 text-[10px]"
                    >
                      {valueParams.length}
                    </Chip>
                  )}
                </Widget.Title>
              </Widget.Header>
              <Widget.Content>
                <MangoHudValueFieldsGrid
                  valueParams={valueParams}
                  values={config}
                  onParamChange={setParamValue}
                />
              </Widget.Content>
            </Widget>

            <Widget>
              <Widget.Header>
                <Widget.Title className="flex items-center gap-1.5">
                  <Code
                    className="text-neon-cyan size-4 shrink-0"
                    aria-hidden
                  />
                  Preview
                  <Text.Code className="text-muted ml-1 text-[10px]">
                    MangoHud.conf
                  </Text.Code>
                </Widget.Title>
              </Widget.Header>
              <Widget.Content>
                <pre className="border-border bg-surface-deep text-neon-cyan max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border p-3 font-mono text-xs leading-relaxed">
                  {previewBody}
                </pre>
              </Widget.Content>
            </Widget>
          </>
        )}

        {/* Per-game configs (collapsible) */}
        <Widget>
          <Widget.Header>
            <Widget.Title className="flex items-center gap-1.5">
              <FileText
                className="text-neon-cyan size-4 shrink-0"
                aria-hidden
              />
              Per-game configs
              {perGameList && perGameList.length > 0 && (
                <Chip
                  size="sm"
                  variant="secondary"
                  className="ml-1 text-[10px]"
                >
                  {perGameList.length}
                </Chip>
              )}
            </Widget.Title>
            <Button
              variant="ghost"
              size="sm"
              onPress={() => setShowPerGame((v) => !v)}
              aria-expanded={showPerGame}
              className="shrink-0 gap-1 text-xs"
            >
              {showPerGame ? "Hide" : "Show"}
              {showPerGame ? (
                <ChevronDown className="size-3.5 shrink-0" aria-hidden />
              ) : (
                <ChevronRight className="size-3.5 shrink-0" aria-hidden />
              )}
            </Button>
          </Widget.Header>
          {showPerGame && (
            <Widget.Content className="space-y-3">
              <motion.div
                className="space-y-3"
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                {/* New per-game config */}
                <Card className="border-neon-cyan/20 bg-surface-deep p-3">
                  <Card.Header className="p-0 pb-2">
                    <Card.Title className="flex items-center gap-1.5 text-sm font-semibold">
                      <Plus
                        className="text-neon-cyan size-4 shrink-0"
                        aria-hidden
                      />
                      New per-game config
                    </Card.Title>
                  </Card.Header>
                  <Card.Content className="space-y-3 p-0">
                    <Text.Paragraph
                      size="xs"
                      color="muted"
                      className="leading-relaxed"
                    >
                      MangoHud loads{" "}
                      <Text.Code className="text-neon-cyan text-[11px]">
                        ~/.config/MangoHud/wine-&lt;name&gt;.conf
                      </Text.Code>{" "}
                      for Wine games — often{" "}
                      <Text.Code className="text-neon-cyan text-[11px]">
                        &lt;name&gt;
                      </Text.Code>{" "}
                      matches the game{" "}
                      <Text.Code className="text-neon-cyan text-[11px]">
                        .exe
                      </Text.Code>{" "}
                      stem (e.g.{" "}
                      <Text.Code className="text-neon-cyan text-[11px]">
                        eldenring
                      </Text.Code>
                      ). For Steam we suggest the library{" "}
                      <strong className="text-foreground font-semibold">
                        install folder
                      </strong>{" "}
                      name; for Heroic/Lutris the game title. Edit the field if
                      your overlay still doesn&apos;t load. You can also set{" "}
                      <Text.Code className="text-neon-cyan text-[11px]">
                        MANGOHUD_CONFIGFILE=~/.config/MangoHud/wine-…conf
                      </Text.Code>{" "}
                      in launch options.
                    </Text.Paragraph>

                    {mangohudGamePicks.length > 0 && (
                      <Select
                        className="w-full"
                        value={selectedGamePickId}
                        onChange={(v) => {
                          const id = String(v ?? "");
                          if (!id) {
                            setSelectedGamePickId("");
                            return;
                          }
                          const pick = mangohudGamePicks.find(
                            (p) => p.id === id,
                          );
                          if (pick) {
                            setSelectedGamePickId(id);
                            setNewPerGameName(pick.suggestedSlug);
                          }
                        }}
                        placeholder="Choose an installed game to fill the config name…"
                      >
                        <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                          Known games (auto-fill)
                        </Label>
                        <Select.Trigger>
                          <Select.Value />
                          <Select.Indicator />
                        </Select.Trigger>
                        <Select.Popover className="max-h-72 min-w-[var(--trigger-width)]">
                          <ListBox className="max-h-64 overflow-y-auto">
                            {mangohudGamePicks.map((pick) => (
                              <ListBox.Item
                                key={pick.id}
                                id={pick.id}
                                textValue={`${pick.label} → ${pick.suggestedSlug}`}
                              >
                                <span className="flex flex-col gap-0.5 text-left">
                                  <span className="truncate">{pick.label}</span>
                                  <span className="text-muted truncate font-mono text-xs">
                                    {pick.suggestedSlug}
                                  </span>
                                </span>
                                <ListBox.ItemIndicator />
                              </ListBox.Item>
                            ))}
                          </ListBox>
                        </Select.Popover>
                      </Select>
                    )}

                    <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                      <TextField
                        value={newPerGameName}
                        onChange={(v) => {
                          setNewPerGameName(v);
                          setSelectedGamePickId("");
                        }}
                        variant="secondary"
                        fullWidth
                        className="min-w-0 flex-1"
                      >
                        <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                          Config name
                        </Label>
                        <Input
                          placeholder="e.g. eldenring or My_Game"
                          className="font-mono text-xs"
                        />
                      </TextField>
                      <div className="flex shrink-0 flex-wrap gap-2">
                        <Button
                          size="sm"
                          onPress={() => handleCreatePerGame("global")}
                          isDisabled={
                            createPerGameMut.isPending ||
                            !newPerGameName.trim()
                          }
                          className="gap-1.5"
                        >
                          {createPerGameMut.isPending ? (
                            <Spinner size="sm" />
                          ) : (
                            <Plus className="size-3.5 shrink-0" aria-hidden />
                          )}
                          Copy from global
                        </Button>
                        <Button
                          size="sm"
                          variant="secondary"
                          onPress={() => handleCreatePerGame("empty")}
                          isDisabled={
                            createPerGameMut.isPending ||
                            !newPerGameName.trim()
                          }
                          className="gap-1.5"
                        >
                          <FilePlus2 className="size-3.5 shrink-0" aria-hidden />
                          Create empty
                        </Button>
                      </div>
                    </div>
                  </Card.Content>
                </Card>

                {/* Existing per-game configs */}
                {!perGameList || perGameList.length === 0 ? (
                  <EmptyState size="sm">
                    <EmptyState.Header>
                      <EmptyState.Media variant="icon">
                        <FolderOpen className="size-5" aria-hidden />
                      </EmptyState.Media>
                      <EmptyState.Title>
                        No per-game configs yet
                      </EmptyState.Title>
                      <EmptyState.Description>
                        Use the form above to create a wine-&lt;name&gt;.conf
                        in ~/.config/MangoHud/.
                      </EmptyState.Description>
                    </EmptyState.Header>
                  </EmptyState>
                ) : (
                  <ListView
                    aria-label="Per-game MangoHud configs"
                    variant="secondary"
                    selectionMode="single"
                    selectionBehavior="replace"
                    items={perGameList.map((p) => ({ id: p.name, ...p }))}
                    selectedKeys={
                      editingGame
                        ? new Set([editingGame])
                        : new Set<string>()
                    }
                    onSelectionChange={(keys: Selection) => {
                      if (keys === "all") return;
                      const id = [...keys][0];
                      if (id != null) loadPerGameConfig(String(id));
                    }}
                    onAction={(key) => loadPerGameConfig(String(key))}
                    className="border-0 bg-transparent p-0 shadow-none"
                  >
                    {(pg) => (
                      <ListView.Item id={pg.name} textValue={pg.name}>
                        <ListView.ItemContent>
                          <FileText
                            className={`size-4 shrink-0 ${
                              editingGame === pg.name
                                ? "text-neon-cyan"
                                : "text-muted"
                            }`}
                            aria-hidden
                          />
                          <div className="flex min-w-0 flex-col">
                            <ListView.Title
                              className={
                                editingGame === pg.name
                                  ? "text-neon-cyan font-medium"
                                  : undefined
                              }
                            >
                              {pg.name}
                            </ListView.Title>
                            <ListView.Description className="font-mono">
                              {pg.path}
                            </ListView.Description>
                          </div>
                        </ListView.ItemContent>
                        {editingGame === pg.name && (
                          <ListView.ItemAction>
                            <Chip size="sm" color="accent" variant="soft">
                              Editing
                            </Chip>
                          </ListView.ItemAction>
                        )}
                      </ListView.Item>
                    )}
                  </ListView>
                )}

                {editingGame && (
                  <motion.div
                    className="border-border space-y-3 border-t pt-3"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <Text.Heading
                        level={3}
                        className="text-neon-cyan flex items-center gap-1.5 text-sm font-semibold"
                      >
                        <Pencil className="size-3.5 shrink-0" aria-hidden />
                        Editing:{" "}
                        <Text.Code className="text-neon-cyan text-[12px]">
                          {editingGame}
                        </Text.Code>
                      </Text.Heading>
                      <Button
                        size="sm"
                        onPress={() =>
                          savePerGameMut.mutate({
                            name: editingGame,
                            cfg: gameConfig,
                          })
                        }
                        isDisabled={savePerGameMut.isPending}
                        className="gap-1.5"
                      >
                        {savePerGameMut.isPending ? (
                          <Spinner size="sm" />
                        ) : (
                          <Save className="size-3 shrink-0" aria-hidden />
                        )}
                        Save
                      </Button>
                    </div>

                    <div className="space-y-1.5">
                      <Label className="text-muted flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
                        <LayoutGrid
                          className="text-neon-cyan size-3 shrink-0"
                          aria-hidden
                        />
                        Overlay metrics
                      </Label>
                      <MangoHudOverlayMetrics
                        toggleParams={toggleParams}
                        config={gameConfig}
                        setConfig={setGameConfig}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label className="text-muted flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
                        <SlidersHorizontal
                          className="text-neon-cyan size-3 shrink-0"
                          aria-hidden
                        />
                        Configuration values
                      </Label>
                      <MangoHudValueFieldsGrid
                        valueParams={valueParams}
                        values={gameConfig}
                        onParamChange={(key, next) =>
                          setGameConfig((prev) => ({
                            ...prev,
                            [key]: next,
                          }))
                        }
                      />
                    </div>

                    <div className="space-y-1.5">
                      <Label className="text-muted flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
                        <Search
                          className="text-neon-cyan size-3 shrink-0"
                          aria-hidden
                        />
                        Preview
                      </Label>
                      <pre className="border-border bg-surface-deep text-neon-cyan max-h-32 overflow-auto whitespace-pre-wrap rounded-lg border p-3 font-mono text-xs leading-relaxed">
                        {Object.entries(gameConfig)
                          .map(([k, v]) => (v ? `${k}=${v}` : k))
                          .join("\n") || "# (empty config)"}
                      </pre>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            </Widget.Content>
          )}
        </Widget>
      </div>
    </PageShell>
  );
}
