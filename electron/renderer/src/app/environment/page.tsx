"use client";

import { useState, useMemo } from "react";
import { motion } from "motion/react";
import {
  Plus,
  Trash2,
  Save,
  Terminal,
  Layers,
  List,
  Code,
  Info,
  FileText,
} from "lucide-react";
import {
  Button,
  Chip,
  Input,
  Label,
  SearchField,
  Spinner,
  Text,
  Tooltip,
} from "@heroui/react";
import { EmptyState, Widget } from "@heroui-pro/react";
import { PageShell } from "@/components/page-shell";
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

const ENV_FILE_PATH = "~/.config/environment.d/70-protonshift.conf";

function entriesFromEnv(env: Record<string, string>): [string, string][] {
  return Object.entries(env);
}

function EnvironmentVarsBody({
  initialEntries,
  isLoading,
  envPresets,
  setEnvVars,
}: {
  initialEntries: [string, string][];
  isLoading: boolean;
  envPresets: Record<string, Record<string, string>> | undefined;
  setEnvVars: ReturnType<typeof useSetEnvVars>;
}) {
  const [vars, setVars] = useState<[string, string][]>(initialEntries);
  const [filter, setFilter] = useState("");

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

  const previewBody = useMemo(
    () =>
      vars
        .filter(([k]) => k.trim())
        .map(([k, v]) => `${k.trim()}="${v}"`)
        .join("\n") || "# (empty)",
    [vars],
  );

  return (
    <PageShell>
      <div className="mx-auto max-w-3xl space-y-5">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <Text.Heading
              level={2}
              className="text-neon-cyan flex items-center gap-2 text-xl font-bold"
            >
              <Terminal className="size-5 shrink-0" aria-hidden />
              Environment Variables
            </Text.Heading>
            <Text.Paragraph
              size="xs"
              color="muted"
              className="flex items-center gap-1.5"
            >
              <FileText className="size-3.5 shrink-0" aria-hidden />
              <Text.Code className="text-[11px]">{ENV_FILE_PATH}</Text.Code>
            </Text.Paragraph>
          </div>
          <Button
            onPress={() => void handleSave()}
            isDisabled={setEnvVars.isPending}
            className="gap-1.5"
          >
            {setEnvVars.isPending ? (
              <Spinner size="sm" />
            ) : (
              <Save className="size-3.5 shrink-0" aria-hidden />
            )}
            Save
          </Button>
        </div>

        {/* Info banner */}
        <Widget>
          <Widget.Content className="py-3">
            <div className="flex items-start gap-3">
              <Info className="text-neon-cyan mt-0.5 size-4 shrink-0" aria-hidden />
              <div className="min-w-0 flex-1 space-y-1.5">
                <Text.Paragraph size="xs" color="muted" className="leading-relaxed">
                  Variables set here are written to{" "}
                  <Text.Code className="text-neon-cyan text-[11px]">
                    {ENV_FILE_PATH}
                  </Text.Code>{" "}
                  and loaded by systemd on login. They apply to{" "}
                  <strong className="text-foreground font-semibold">
                    every application
                  </strong>{" "}
                  in your session — Steam, Lutris, Heroic, and terminal-launched
                  games all inherit them.
                </Text.Paragraph>
                <Text.Paragraph size="xs" color="muted" className="leading-relaxed">
                  Changes take effect after your next{" "}
                  <strong className="text-foreground font-semibold">
                    logout and login
                  </strong>
                  . Per-game overrides can be set in Steam&apos;s launch options
                  or in the Games page.
                </Text.Paragraph>
              </div>
            </div>
          </Widget.Content>
        </Widget>

        {/* Presets */}
        {envPresets && Object.keys(envPresets).length > 0 && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex items-center gap-1.5">
                <Layers className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Quick presets
                <Chip size="sm" variant="secondary" className="ml-1 text-[10px]">
                  {Object.keys(envPresets).length}
                </Chip>
              </Widget.Title>
            </Widget.Header>
            <Widget.Content>
              <EnvPresets presets={envPresets} onApply={applyPreset} />
            </Widget.Content>
          </Widget>
        )}

        {/* Variables editor */}
        <Widget>
          <Widget.Header>
            <Widget.Title className="flex items-center gap-1.5">
              <List className="text-neon-cyan size-4 shrink-0" aria-hidden />
              Variables
              {vars.length > 0 && (
                <Chip size="sm" variant="secondary" className="ml-1 text-[10px]">
                  {vars.length}
                </Chip>
              )}
            </Widget.Title>
          </Widget.Header>
          <Widget.Content className="space-y-3">
            {vars.length > 3 && (
              <SearchField
                value={filter}
                onChange={setFilter}
                onClear={() => setFilter("")}
                aria-label="Filter variables"
                variant="secondary"
                fullWidth
              >
                <SearchField.Group className="w-full">
                  <SearchField.SearchIcon />
                  <SearchField.Input
                    placeholder="Filter variables…"
                    className="font-mono text-xs"
                  />
                  <SearchField.ClearButton />
                </SearchField.Group>
              </SearchField>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            ) : vars.length === 0 ? (
              <EmptyState size="md">
                <EmptyState.Header>
                  <EmptyState.Media variant="icon">
                    <Terminal className="size-5" aria-hidden />
                  </EmptyState.Media>
                  <EmptyState.Title>No variables yet</EmptyState.Title>
                  <EmptyState.Description>
                    Add a variable manually or apply a preset above to get
                    started.
                  </EmptyState.Description>
                </EmptyState.Header>
                <EmptyState.Content>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={addVar}
                    className="gap-1.5"
                  >
                    <Plus className="size-3.5 shrink-0" aria-hidden />
                    Add first variable
                  </Button>
                </EmptyState.Content>
              </EmptyState>
            ) : (
              <div className="space-y-2">
                {vars.map(([key, value], index) => {
                  if (filteredIndices !== null && !filteredIndices.has(index))
                    return null;

                  const hint = key.trim() ? KNOWN_VARS[key.trim()] : undefined;

                  return (
                    <motion.div
                      key={index}
                      className="group flex min-w-0 flex-col gap-1"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.02 }}
                    >
                      <div className="flex items-center gap-2">
                        <Label
                          id={`env-key-${index}`}
                          className="sr-only"
                        >
                          {`Variable key ${index + 1}`}
                        </Label>
                        <Input
                          value={key}
                          onChange={(e) => updateVar(index, 0, e.target.value)}
                          placeholder="KEY"
                          aria-labelledby={`env-key-${index}`}
                          variant="secondary"
                          className="flex-1 font-mono text-xs"
                        />
                        <span
                          aria-hidden
                          className="text-muted shrink-0 select-none font-mono text-xs"
                        >
                          =
                        </span>
                        <Label
                          id={`env-value-${index}`}
                          className="sr-only"
                        >
                          {`Variable value ${index + 1}`}
                        </Label>
                        <Input
                          value={value}
                          onChange={(e) => updateVar(index, 1, e.target.value)}
                          placeholder="value"
                          aria-labelledby={`env-value-${index}`}
                          variant="secondary"
                          className="flex-[2] font-mono text-xs"
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
                            <Trash2 className="size-3.5 shrink-0" aria-hidden />
                          </Button>
                          <Tooltip.Content>Remove</Tooltip.Content>
                        </Tooltip>
                      </div>
                      {hint && (
                        <Text.Paragraph
                          size="xs"
                          color="muted"
                          className="ml-0.5 leading-snug"
                        >
                          {hint}
                        </Text.Paragraph>
                      )}
                    </motion.div>
                  );
                })}

                {filteredIndices !== null && visibleCount === 0 && (
                  <Text.Paragraph
                    size="xs"
                    color="muted"
                    align="center"
                    className="py-4"
                  >
                    No variables match &ldquo;{filter}&rdquo;
                  </Text.Paragraph>
                )}

                <Button
                  variant="outline"
                  onPress={addVar}
                  className="w-full gap-1.5"
                >
                  <Plus className="size-3.5 shrink-0" aria-hidden />
                  Add variable
                </Button>
              </div>
            )}
          </Widget.Content>
        </Widget>

        {/* Preview */}
        {vars.length > 0 && (
          <Widget>
            <Widget.Header>
              <Widget.Title className="flex items-center gap-1.5">
                <Code className="text-neon-cyan size-4 shrink-0" aria-hidden />
                Preview
                <Text.Code className="text-muted ml-1 text-[10px]">
                  70-protonshift.conf
                </Text.Code>
              </Widget.Title>
            </Widget.Header>
            <Widget.Content>
              <pre className="border-border bg-surface-deep text-neon-cyan max-h-48 overflow-auto whitespace-pre-wrap rounded-lg border p-3 font-mono text-xs leading-relaxed">
                {previewBody}
              </pre>
            </Widget.Content>
          </Widget>
        )}
      </div>
    </PageShell>
  );
}

export default function EnvironmentPage() {
  const { data: envVars, isLoading } = useEnvVars();
  const { data: envPresets } = useEnvPresets();
  const setEnvVars = useSetEnvVars();

  return (
    <EnvironmentVarsBody
      key={envVars != null ? JSON.stringify(envVars) : "pending"}
      initialEntries={envVars != null ? entriesFromEnv(envVars) : []}
      isLoading={isLoading}
      envPresets={envPresets}
      setEnvVars={setEnvVars}
    />
  );
}
