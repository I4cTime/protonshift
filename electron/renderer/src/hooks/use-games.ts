"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type GameFixCreateData, type HeroicTogglesPayload } from "@/lib/api";

export function useGames() {
  return useQuery({
    queryKey: ["games"],
    queryFn: api.getGames,
    staleTime: 30_000,
  });
}

export function useLaunchOptions(appId: string | null) {
  return useQuery({
    queryKey: ["launch-options", appId],
    queryFn: () => api.getLaunchOptions(appId!),
    enabled: !!appId,
  });
}

export function useSetLaunchOptions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, options }: { appId: string; options: string }) =>
      api.setLaunchOptions(appId, options),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["launch-options", vars.appId] });
    },
  });
}

export function useProtonTools(appId: string | null) {
  return useQuery({
    queryKey: ["proton-tools", appId],
    queryFn: () => api.getProtonTools(appId!),
    enabled: !!appId,
  });
}

export function useSetCompatTool() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, toolName }: { appId: string; toolName: string }) =>
      api.setCompatTool(appId, toolName),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["proton-tools", vars.appId] });
    },
  });
}

export function useRunProtontricks() {
  return useMutation({
    mutationFn: ({ appId, verb }: { appId: string; verb?: string }) =>
      api.runProtontricks(appId, verb),
  });
}

export function usePresets() {
  return useQuery({
    queryKey: ["presets"],
    queryFn: api.getPresets,
    staleTime: 60_000,
  });
}

export function useProtontricksVerbs() {
  return useQuery({
    queryKey: ["protontricks-verbs"],
    queryFn: api.getProtontricksVerbs,
    staleTime: 60_000,
  });
}

export function usePrefixInfo(appId: string | null, prefixPath?: string) {
  return useQuery({
    queryKey: ["prefix-info", appId, prefixPath],
    queryFn: () => api.getPrefixInfo(appId!, prefixPath),
    enabled: !!appId,
  });
}

export function useDeletePrefix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, prefixPath }: { appId: string; prefixPath?: string }) =>
      api.deletePrefix(appId, prefixPath),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["prefix-info", vars.appId] });
      qc.invalidateQueries({ queryKey: ["games"] });
    },
  });
}

export function useShaderCache(appId: string | null) {
  return useQuery({
    queryKey: ["shader-cache", appId],
    queryFn: () => api.getShaderCache(appId!),
    enabled: !!appId,
  });
}

export function useClearShaderCache() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (appId: string) => api.clearShaderCache(appId),
    onSuccess: (_data, appId) => {
      qc.invalidateQueries({ queryKey: ["shader-cache", appId] });
      qc.invalidateQueries({ queryKey: ["shader-cache-total"] });
    },
  });
}

export function useTotalShaderCache() {
  return useQuery({
    queryKey: ["shader-cache-total"],
    queryFn: api.getTotalShaderCache,
    staleTime: 30_000,
  });
}

export function useGameFixes(appId: string | null) {
  return useQuery({
    queryKey: ["game-fixes", appId],
    queryFn: () => api.getGameFixes(appId!),
    enabled: !!appId,
  });
}

export function useAddGameFix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, fix }: { appId: string; fix: GameFixCreateData }) =>
      api.addGameFix(appId, fix),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["game-fixes", vars.appId] });
    },
  });
}

export function useGameSaves(appId: string | null, prefixPath?: string) {
  return useQuery({
    queryKey: ["game-saves", appId, prefixPath],
    queryFn: () => api.getGameSaves(appId!, prefixPath),
    enabled: !!appId,
  });
}

export function useGameBackups(appId: string | null) {
  return useQuery({
    queryKey: ["game-backups", appId],
    queryFn: () => api.listGameBackups(appId!),
    enabled: !!appId,
  });
}

export function useBackupSaves() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, paths }: { appId: string; paths: string[] }) =>
      api.backupGameSaves(appId, paths),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["game-backups", vars.appId] });
    },
  });
}

export function useRestoreSaves() {
  return useMutation({
    mutationFn: ({
      appId,
      backupPath,
      targetDir,
    }: {
      appId: string;
      backupPath: string;
      targetDir: string;
    }) => api.restoreGameSaves(appId, backupPath, targetDir),
  });
}

// ---------------------------------------------------------------------------
// Heroic-specific hooks
// ---------------------------------------------------------------------------

export function useHeroicGameConfig(appId: string | null) {
  return useQuery({
    queryKey: ["heroic-config", appId],
    queryFn: () => api.getHeroicGameConfig(appId!),
    enabled: !!appId,
  });
}

export function useSetHeroicLaunchOptions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, options }: { appId: string; options: string }) =>
      api.setHeroicLaunchOptions(appId, options),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["heroic-config", vars.appId] });
    },
  });
}

export function useSetHeroicWineVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      appId,
      name,
      bin,
      wineType,
    }: {
      appId: string;
      name: string;
      bin: string;
      wineType: string;
    }) => api.setHeroicWineVersion(appId, name, bin, wineType),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["heroic-config", vars.appId] });
    },
  });
}

export function useSetHeroicToggles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ appId, toggles }: { appId: string; toggles: HeroicTogglesPayload }) =>
      api.setHeroicToggles(appId, toggles),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["heroic-config", vars.appId] });
    },
  });
}

export function useHeroicWineVersions() {
  return useQuery({
    queryKey: ["heroic-wine-versions"],
    queryFn: api.getHeroicWineVersions,
    staleTime: 60_000,
  });
}

export function useLaunchHeroicGame() {
  return useMutation({
    mutationFn: (appId: string) => api.launchHeroicGame(appId),
  });
}
