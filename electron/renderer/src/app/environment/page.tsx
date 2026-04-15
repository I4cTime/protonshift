"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "motion/react";
import {
  Plus,
  Trash2,
  Save,
  Terminal,
  Layers,
  List,
  Code,
  Search,
  Info,
  FileText,
} from "lucide-react";
import { Button, Input, Chip, Spinner, Tooltip } from "@heroui/react";
import { PageShell } from "@/components/page-shell";
import { GlowCard } from "@/components/glow-card";
import { EnvPresets } from "@/components/env-presets";
import { useEnvVars, useSetEnvVars, useEnvPresets } from "@/hooks/use-env";
import { appShowToast } from "@/lib/app-toast";

/** Known Linux gaming env vars with short explanations. */
const KNOWN_VARS: Record<string, string> = {
  PROTON_ENABLE_WAYLAND: "Wayland rendering in Proton (1 = on)",
  PROTON_LOG: "Enable Proton debug logging",
  WINEDEBUG: "Wine debug channels (+tid, +err, etc.)",
  __GL_SHADER_DISK_CACHE: "NVIDIA shader disk cache (1 = on)",
  __GL_SHADER_DISK_CACHE_SKIP_CLEANUP: "Skip NVIDIA cache cleanup (1 = on)",
  RADV_PERFTEST: "RADV perf flags (gpl, ngg_streamout, etc.)",
  AMD_VULKAN_ICD: "Vulkan ICD on AMD (RADV or AMDVLK)",
  DXVK_ASYNC: "DXVK async shader compilation (1 = on)",
  DXVK_STATE_CACHE: "DXVK pipeline state cache (1 = on)",
  DXVK_LOG_LEVEL: "DXVK log verbosity (none/error/warn/info/debug)",
  VKD3D_CONFIG: "VKD3D feature flags (dxr, etc.)",
  VKD3D_DEBUG: "VKD3D debug level (none/err/warn/trace)",
  MESA_SHADER_CACHE_DISABLE: "Disable Mesa shader cache (true/false)",
  MESA_SHADER_CACHE_MAX_SIZE: "Mesa shader cache size limit (e.g. 4G)",
  SDL_VIDEODRIVER: "SDL video backend (wayland, x11)",
  GDK_BACKEND: "GTK display backend (wayland, x11)",
  QT_QPA_PLATFORM: "Qt platform plugin (wayland, xcb)",
  STEAM_GAMEMODE: "Feral GameMode via Steam (1 = on)",
  MANGOHUD: "Enable MangoHud overlay (1 = on)",
  ENABLE_VKBASALT: "Enable vkBasalt post-processing (1 = on)",
  STEAM_COMPAT_DATA_PATH: "Custom Proton prefix path",
  STEAM_COMPAT_CLIENT_INSTALL_PATH: "Steam install root for Proton lookup",
};

export default function EnvironmentPage() {
  const { data: envVars, isLoading } = useEnvVars();
  const { data: envPresets } = useEnvPresets();
  const setEnvVars = useSetEnvVars();

  const [vars, setVars] = useState<[string, string][]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (envVars) {
      setVars(Object.entries(envVars));
    }
  }, [envVars]);

  function addVar() {
    setVars((prev) => [...prev, ["", ""]]);
  }

  function removeVar(index: number) {
    setVars((prev) => prev.filter((_, i) => i !== index));
  }

  function updateVar(index: number, field: 0 | 1, value: string) {
    setVars((prev) =>
      prev.map((v, i) =>
        i === index ? (field === 0 ? [value, v[1]] : [v[0], value]) : v,
      ),
    );
  }

  async function handleSave() {
    const obj: Record<string, string> = {};
    for (const [k, v] of vars) {
      if (k.trim()) obj[k.trim()] = v;
    }
    try {
      await setEnvVars.mutateAsync(obj);
      appShowToast("Environment saved");
    } catch {
      appShowToast("Failed to save", "error");
    }
  }

  function applyPreset(presetVars: Record<string, string>) {
    setVars((prev) => {
      const existing = new Map(prev);
      for (const [k, v] of Object.entries(presetVars)) {
        existing.set(k, v);
      }
      return Array.from(existing.entries());
    });
    appShowToast("Preset applied — save to write to disk");
  }

  const filteredIndices = useMemo(() => {
    if (!filter.trim()) return null;
    const q = filter.toLowerCase();
    const matches: number[] = [];
    vars.forEach(([key, value], i) => {
      if (
        key.toLowerCase().includes(q) ||
        value.toLowerCase().includes(q)
      ) {
        matches.push(i);
      }
    });
    return new Set(matches);
  }, [filter, vars]);

  const visibleCount =
    filteredIndices !== null ? filteredIndices.size : vars.length;

  return (
    <PageShell>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
              <Terminal className="size-5" />
              Environment Variables
            </h2>
            <p className="flex items-center gap-1.5 text-sm text-text-muted mt-1">
              <FileText className="size-3.5" />
              ~/.config/environment.d/70-protonshift.conf
            </p>
          </div>
          <Button
            onPress={handleSave}
            isDisabled={setEnvVars.isPending}
            className="gap-2"
          >
            {setEnvVars.isPending ? (
              <Spinner size="sm" />
            ) : (
              <Save className="size-4" />
            )}
            Save
          </Button>
        </div>

        {/* Info banner */}
        <GlowCard className="p-4">
          <div className="flex gap-3">
            <Info className="mt-0.5 size-4 shrink-0 text-neon-cyan" />
            <div className="text-xs leading-relaxed text-text-muted">
              <p>
                Variables set here are written to{" "}
                <code className="text-neon-cyan">
                  ~/.config/environment.d/70-protonshift.conf
                </code>{" "}
                and loaded by systemd on login. They apply to{" "}
                <strong className="text-text-secondary">
                  every application
                </strong>{" "}
                in your session — Steam, Lutris, Heroic, and terminal-launched
                games all inherit them.
              </p>
              <p className="mt-1.5">
                Changes take effect after your next{" "}
                <strong className="text-text-secondary">
                  logout and login
                </strong>
                . Per-game overrides can be set in Steam&apos;s launch options
                or in the Games page.
              </p>
            </div>
          </div>
        </GlowCard>

        {/* Presets */}
        {envPresets && Object.keys(envPresets).length > 0 && (
          <GlowCard className="p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-3">
              <Layers className="size-4 text-neon-cyan" />
              Quick Presets
            </label>
            <EnvPresets presets={envPresets} onApply={applyPreset} />
          </GlowCard>
        )}

        {/* Variables editor */}
        <GlowCard className="p-5">
          <div className="flex items-center justify-between mb-4">
            <label className="flex items-center gap-2 text-sm font-medium text-text-secondary">
              <List className="size-4 text-neon-cyan" />
              Variables
              {vars.length > 0 && (
                <Chip size="sm" variant="secondary" className="text-[10px]">
                  {vars.length}
                </Chip>
              )}
            </label>
          </div>

          {vars.length > 3 && (
            <div className="relative mb-4">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-text-muted" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter variables…"
                aria-label="Filter variables"
                variant="secondary"
                className="w-full pl-9 font-mono text-xs"
              />
            </div>
          )}

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : vars.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
              <Terminal className="size-8 text-text-muted/50" />
              <div>
                <p className="text-sm font-medium text-text-secondary">
                  No variables yet
                </p>
                <p className="mt-1 text-xs text-text-muted">
                  Add a variable manually or apply a preset above to get
                  started.
                </p>
              </div>
              <Button variant="outline" onPress={addVar} className="gap-2">
                <Plus className="size-4" />
                Add first variable
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {vars.map(([key, value], index) => {
                if (filteredIndices !== null && !filteredIndices.has(index))
                  return null;

                const hint = key.trim() ? KNOWN_VARS[key.trim()] : undefined;

                return (
                  <motion.div
                    key={index}
                    className="group flex items-start gap-2"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.02 }}
                  >
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <Input
                          value={key}
                          onChange={(e) => updateVar(index, 0, e.target.value)}
                          placeholder="KEY"
                          aria-label={`Variable key ${index + 1}`}
                          variant="secondary"
                          className="flex-1 font-mono"
                        />
                        <span className="shrink-0 text-text-muted">=</span>
                        <Input
                          value={value}
                          onChange={(e) => updateVar(index, 1, e.target.value)}
                          placeholder="value"
                          aria-label={`Variable value ${index + 1}`}
                          variant="secondary"
                          className="flex-[2] font-mono"
                        />
                        <Tooltip delay={0}>
                          <Button
                            isIconOnly
                            variant="ghost"
                            size="sm"
                            onPress={() => removeVar(index)}
                            aria-label="Remove variable"
                            className="shrink-0 opacity-50 transition-opacity group-hover:opacity-100"
                          >
                            <Trash2 className="size-4" />
                          </Button>
                          <Tooltip.Content>Remove</Tooltip.Content>
                        </Tooltip>
                      </div>
                      {hint && (
                        <p className="ml-0.5 text-[11px] leading-snug text-text-muted">
                          {hint}
                        </p>
                      )}
                    </div>
                  </motion.div>
                );
              })}

              {filteredIndices !== null && visibleCount === 0 && (
                <p className="py-4 text-center text-xs text-text-muted">
                  No variables match &ldquo;{filter}&rdquo;
                </p>
              )}

              <Button
                variant="outline"
                onPress={addVar}
                className="w-full gap-2"
              >
                <Plus className="size-4" />
                Add Variable
              </Button>
            </div>
          )}
        </GlowCard>

        {/* Preview */}
        {vars.length > 0 && (
          <GlowCard className="p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-text-secondary mb-2">
              <Code className="size-4 text-neon-cyan" />
              Preview (70-protonshift.conf)
            </label>
            <pre className="rounded-lg border border-border bg-surface-deep p-3 font-mono text-xs text-neon-cyan max-h-48 overflow-auto whitespace-pre-wrap">
              {vars
                .filter(([k]) => k.trim())
                .map(([k, v]) => `${k.trim()}="${v}"`)
                .join("\n") || "# (empty)"}
            </pre>
          </GlowCard>
        )}
      </div>
    </PageShell>
  );
}
