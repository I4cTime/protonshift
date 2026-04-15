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
} from "lucide-react";
import { Button, Input, Chip, Spinner, Link as HeroLink, Select, Label, ListBox } from "@heroui/react";
import { PageShell } from "@/components/page-shell";
import { GlowCard } from "@/components/glow-card";
import { MangoHudOverlayMetrics } from "@/components/mangohud-overlay-metrics";
import { MangoHudPresets } from "@/components/mangohud-presets";
import { MangoHudValueFieldsGrid } from "@/components/mangohud-value-field";
import { api } from "@/lib/api";
import { mangohudPerGameSlug, mangohudSuggestedSlugForGame } from "@/lib/mangohud-naming";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useGames } from "@/hooks/use-games";
import { appShowToast } from "@/lib/app-toast";

type MangoHudGamePick = { id: string; label: string; suggestedSlug: string };

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
    picks.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: "base" }));
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
      appShowToast("Enter a config name (often the game .exe stem, e.g. eldenring)", "error");
      return;
    }
    const slug = mangohudPerGameSlug(raw);
    const exists = perGameList?.some((p) => p.name === slug);
    if (exists) {
      appShowToast("That config already exists — pick it in the list below", "error");
      return;
    }
    const cfg = initial === "global" ? { ...config } : {};
    createPerGameMut.mutate({ name: raw, cfg });
  }

  useEffect(() => {
    if (configData) setConfig(configData.config);
  }, [configData]);

  /** Deep-link from Games page: /mangohud?slug=…&pick=steam:… */
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const url = new URL(window.location.href);
      const slug = url.searchParams.get("slug");
      const pick = url.searchParams.get("pick");
      if (!slug && !pick) return;
      if (slug) setNewPerGameName(slug);
      if (pick) setSelectedGamePickId(pick);
      setShowPerGame(true);
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

  if (!availData?.available) {
    return (
      <PageShell>
        <div className="max-w-4xl mx-auto space-y-6">
          <h2 className="text-xl font-bold text-neon-cyan">MangoHud</h2>
          <GlowCard className="p-6 space-y-4">
            <div className="flex items-center gap-3 text-text-secondary text-sm font-medium">
              <Gauge className="size-5 text-neon-cyan" />
              MangoHud — Not Installed
            </div>
            <p className="text-sm text-text-muted">
              MangoHud is a Vulkan/OpenGL overlay that shows FPS, GPU/CPU usage, temperatures, frame timing, and more. It&apos;s the go-to performance overlay for Linux gaming.
            </p>
            <div className="space-y-2">
              <p className="text-xs text-text-secondary font-medium">Install via your package manager:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { distro: "Ubuntu / Pop!_OS / Mint", cmd: "sudo apt install mangohud" },
                  { distro: "Fedora", cmd: "sudo dnf install mangohud" },
                  { distro: "Arch / Manjaro / EndeavourOS", cmd: "sudo pacman -S mangohud" },
                  { distro: "openSUSE", cmd: "sudo zypper install mangohud" },
                  { distro: "Flatpak (Steam)", cmd: "flatpak install flathub org.freedesktop.Platform.VulkanLayer.MangoHud" },
                  { distro: "NixOS", cmd: "nix-env -iA nixpkgs.mangohud" },
                ].map((item) => (
                  <div key={item.distro} className="p-3 rounded-lg bg-surface-deep border border-separator">
                    <p className="text-xs text-text-muted mb-0.5">{item.distro}</p>
                    <code className="text-xs text-neon-cyan font-mono break-all">{item.cmd}</code>
                  </div>
                ))}
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface-deep border border-separator">
              <p className="text-xs text-text-secondary font-medium mb-1">Usage</p>
              <p className="text-xs text-text-muted">
                Add <code className="text-neon-cyan">MANGOHUD=1 %command%</code> to a game&apos;s launch options, or enable the MangoHud preset on the Games page.
              </p>
            </div>
            <p className="text-xs text-text-muted">
              After installing, restart the app to detect MangoHud.{" "}
              <HeroLink
                href="https://github.com/flightlessmango/MangoHud"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-neon-cyan"
              >
                GitHub &rarr;
              </HeroLink>
            </p>
          </GlowCard>
        </div>
      </PageShell>
    );
  }

  const toggleParams = configData?.params.filter((p) => p.type === "toggle") ?? [];
  const valueParams = configData?.params.filter((p) => p.type === "value") ?? [];

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
            <Gauge className="size-5" />
            MangoHud Config
          </h2>
          <Button
            onPress={() => saveMut.mutate(config)}
            isDisabled={saveMut.isPending}
            className="gap-2"
          >
            {saveMut.isPending ? <Spinner size="sm" /> : <Save className="size-4" />}
            Save
          </Button>
        </div>

        {presets && (
          <GlowCard className="p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
              <Layers className="size-4 text-neon-cyan" />
              Quick Presets
            </label>
            <MangoHudPresets presets={presets} onApply={applyPreset} />
          </GlowCard>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <>
            <GlowCard className="p-5">
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
                <LayoutGrid className="size-4 text-neon-cyan" />
                Overlay Metrics
              </label>
              <MangoHudOverlayMetrics
                toggleParams={toggleParams}
                config={config}
                setConfig={setConfig}
              />
            </GlowCard>

            <GlowCard className="p-5">
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
                <SlidersHorizontal className="size-4 text-neon-cyan" />
                Configuration Values
              </label>
              <MangoHudValueFieldsGrid
                valueParams={valueParams}
                values={config}
                onParamChange={setParamValue}
              />
            </GlowCard>

            <GlowCard className="p-5">
              <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
                <Code className="size-4 text-neon-cyan" />
                Preview (MangoHud.conf)
              </label>
              <pre className="p-3 rounded-lg bg-surface-deep border border-border font-mono text-xs text-neon-cyan max-h-48 overflow-auto whitespace-pre-wrap">
                {Object.entries(config)
                  .map(([k, v]) => (v ? `${k}=${v}` : k))
                  .join("\n") || "# (empty config)"}
              </pre>
            </GlowCard>
          </>
        )}

        <GlowCard className="p-5">
          <Button
            variant="ghost"
            onPress={() => setShowPerGame(!showPerGame)}
            className="w-full justify-start gap-2 text-sm font-medium text-text-secondary"
          >
            {showPerGame ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
            <FileText className="size-4" />
            Per-Game Configs
            {perGameList && perGameList.length > 0 && (
              <Chip size="sm" variant="secondary" className="ml-auto">{perGameList.length} found</Chip>
            )}
          </Button>
          {showPerGame && (
            <motion.div
              className="mt-4 space-y-3"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
            >
              <div className="p-4 rounded-lg bg-surface-deep border border-neon-cyan/20 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium text-text-secondary">
                  <Plus className="size-4 text-neon-cyan" />
                  New per-game config
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  MangoHud loads <code className="text-neon-cyan">~/.config/MangoHud/wine-&lt;name&gt;.conf</code> for
                  Wine games—often <code className="text-neon-cyan">&lt;name&gt;</code> matches the game{" "}
                  <code className="text-neon-cyan">.exe</code> stem (e.g.{" "}
                  <code className="text-neon-cyan">eldenring</code>). For Steam we suggest the library{" "}
                  <strong className="text-text-secondary">install folder</strong> name; for Heroic/Lutris the game
                  title. Edit the field if your overlay still doesn&apos;t load. You can also set{" "}
                  <code className="text-neon-cyan">MANGOHUD_CONFIGFILE=~/.config/MangoHud/wine-…conf</code> in launch
                  options.
                </p>
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
                      const pick = mangohudGamePicks.find((p) => p.id === id);
                      if (pick) {
                        setSelectedGamePickId(id);
                        setNewPerGameName(pick.suggestedSlug);
                      }
                    }}
                    placeholder="Choose an installed game to fill the config name…"
                  >
                    <Label>Known games (auto-fill)</Label>
                    <Select.Trigger>
                      <Select.Value />
                      <Select.Indicator />
                    </Select.Trigger>
                    <Select.Popover className="max-h-72">
                      <ListBox className="max-h-64 overflow-y-auto">
                        {mangohudGamePicks.map((pick) => (
                          <ListBox.Item
                            key={pick.id}
                            id={pick.id}
                            textValue={`${pick.label} → ${pick.suggestedSlug}`}
                          >
                            <span className="flex flex-col gap-0.5 text-left">
                              <span>{pick.label}</span>
                              <span className="text-xs font-mono text-text-muted">{pick.suggestedSlug}</span>
                            </span>
                            <ListBox.ItemIndicator />
                          </ListBox.Item>
                        ))}
                      </ListBox>
                    </Select.Popover>
                  </Select>
                )}
                <div className="flex flex-col sm:flex-row gap-2 sm:items-end">
                  <div className="flex-1 space-y-1">
                    <Label className="text-xs text-text-muted">Config name</Label>
                    <Input
                      value={newPerGameName}
                      onChange={(e) => {
                        setNewPerGameName(e.target.value);
                        setSelectedGamePickId("");
                      }}
                      placeholder="e.g. eldenring or My_Game"
                      variant="secondary"
                      className="w-full font-mono"
                      aria-label="Per-game MangoHud config name"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <Button
                      onPress={() => handleCreatePerGame("global")}
                      isDisabled={createPerGameMut.isPending || !newPerGameName.trim()}
                      className="gap-1.5"
                    >
                      {createPerGameMut.isPending ? <Spinner size="sm" /> : <Plus className="size-4" />}
                      Copy from global
                    </Button>
                    <Button
                      variant="secondary"
                      onPress={() => handleCreatePerGame("empty")}
                      isDisabled={createPerGameMut.isPending || !newPerGameName.trim()}
                      className="gap-1.5"
                    >
                      <FilePlus2 className="size-4" />
                      Create empty
                    </Button>
                  </div>
                </div>
              </div>

              {!perGameList || perGameList.length === 0 ? (
                <p className="text-xs text-text-muted">
                  No per-game configs on disk yet. Use the form above to create{" "}
                  <code className="text-neon-cyan">wine-&lt;name&gt;.conf</code> in{" "}
                  <code className="text-neon-cyan">~/.config/MangoHud/</code>.
                </p>
              ) : (
                <div className="space-y-2">
                  {perGameList.map((pg) => (
                    <div
                      key={pg.name}
                      className={`flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer ${
                        editingGame === pg.name
                          ? "bg-neon-cyan/10 border-neon-cyan/30"
                          : "bg-surface-deep border-separator hover:border-border"
                      }`}
                      onClick={() => loadPerGameConfig(pg.name)}
                    >
                      <div>
                        <p className="text-sm font-medium text-text-primary">{pg.name}</p>
                        <p className="text-xs text-text-muted font-mono truncate">{pg.path}</p>
                      </div>
                      {editingGame === pg.name && (
                        <Chip size="sm" color="accent" variant="soft">Editing</Chip>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {editingGame && (
                <motion.div
                  className="space-y-3 pt-3 border-t border-border"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <div className="flex items-center justify-between">
                    <p className="flex items-center gap-2 text-sm font-medium text-neon-cyan">
                      <Pencil className="size-3.5" />
                      Editing: {editingGame}
                    </p>
                    <Button
                      size="sm"
                      onPress={() => savePerGameMut.mutate({ name: editingGame, cfg: gameConfig })}
                      isDisabled={savePerGameMut.isPending}
                      className="gap-1.5"
                    >
                      {savePerGameMut.isPending ? <Spinner size="sm" /> : <Save className="size-3" />}
                      Save
                    </Button>
                  </div>
                  <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
                    <LayoutGrid className="size-4 text-neon-cyan" />
                    Overlay Metrics
                  </label>
                  <MangoHudOverlayMetrics
                    toggleParams={toggleParams}
                    config={gameConfig}
                    setConfig={setGameConfig}
                  />
                  <div className="mt-4 space-y-3">
                    <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-text-secondary">
                      <SlidersHorizontal className="size-3.5 text-neon-cyan" />
                      Configuration Values
                    </p>
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
                  <pre className="p-3 rounded-lg bg-surface-deep border border-border font-mono text-xs text-neon-cyan max-h-32 overflow-auto whitespace-pre-wrap">
                    {Object.entries(gameConfig)
                      .map(([k, v]) => (v ? `${k}=${v}` : k))
                      .join("\n") || "# (empty config)"}
                  </pre>
                </motion.div>
              )}
            </motion.div>
          )}
        </GlowCard>
      </div>
    </PageShell>
  );
}
