interface ApiResponse {
  ok: boolean;
  status: number;
  body: string;
}

interface ElectronApi {
  getApiPort: () => Promise<number | null>;
  fetch: (path: string, init?: RequestInit) => Promise<ApiResponse>;
}

declare global {
  interface Window {
    api: ElectronApi;
  }
}

async function apiFetch<T = unknown>(
  path: string,
  options?: { method?: string; body?: unknown }
): Promise<T> {
  const init: RequestInit = {};
  if (options?.method) init.method = options.method;
  if (options?.body) init.body = JSON.stringify(options.body);

  let response: ApiResponse;

  if (typeof window !== "undefined" && window.api) {
    response = await window.api.fetch(path, init);
  } else {
    const port = 8000;
    const res = await fetch(`http://127.0.0.1:${port}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json" },
    });
    response = {
      ok: res.ok,
      status: res.status,
      body: await res.text(),
    };
  }

  const data = JSON.parse(response.body);
  if (!response.ok) {
    throw new Error(data.detail || `API error ${response.status}`);
  }
  return data as T;
}

export const api = {
  getGames: () =>
    apiFetch<{
      steam: SteamGame[];
      heroic: HeroicGame[];
      lutris: LutrisGame[];
      steam_running: boolean;
    }>("/games"),

  getLaunchOptions: (appId: string) =>
    apiFetch<{ options: string }>(`/games/${appId}/launch-options`),

  setLaunchOptions: (appId: string, options: string) =>
    apiFetch<StatusResponse>(`/games/${appId}/launch-options`, {
      method: "PUT",
      body: { options },
    }),

  getCompatTool: (appId: string) =>
    apiFetch<{ tool: string }>(`/games/${appId}/compat-tool`),

  setCompatTool: (appId: string, toolName: string) =>
    apiFetch<StatusResponse>(`/games/${appId}/compat-tool`, {
      method: "PUT",
      body: { tool_name: toolName },
    }),

  getProtonTools: (appId: string) =>
    apiFetch<{ tools: string[]; current: string }>(`/games/${appId}/proton-tools`),

  runProtontricks: (appId: string, verb?: string) =>
    apiFetch<StatusResponse>(`/games/${appId}/protontricks`, {
      method: "POST",
      body: { verb: verb ?? null },
    }),

  getProtontricksVerbs: () =>
    apiFetch<{ available: boolean; verbs: { id: string; label: string }[] }>(
      "/protontricks/verbs"
    ),

  getPresets: () => apiFetch<LaunchPreset[]>("/presets"),

  getEnvPresets: () => apiFetch<Record<string, Record<string, string>>>("/env-presets"),

  getEnvVars: () => apiFetch<Record<string, string>>("/env-vars"),

  setEnvVars: (vars: Record<string, string>) =>
    apiFetch<StatusResponse>("/env-vars", { method: "PUT", body: { vars } }),

  getSystemInfo: () => apiFetch<SystemInfo>("/system"),

  setPowerProfile: (profile: string) =>
    apiFetch<StatusResponse>("/system/power-profile", {
      method: "PUT",
      body: { profile },
    }),

  getProfiles: () => apiFetch<string[]>("/profiles"),

  getProfile: (name: string) => apiFetch<ProfileData>(`/profiles/${encodeURIComponent(name)}`),

  saveProfile: (profile: ProfileData) =>
    apiFetch<StatusResponse>("/profiles", { method: "POST", body: profile }),

  deleteProfile: (name: string) =>
    apiFetch<StatusResponse>(`/profiles/${encodeURIComponent(name)}`, { method: "DELETE" }),

  getSteamStatus: () =>
    apiFetch<{ running: boolean; root: string | null; config_path: string | null }>(
      "/steam/status"
    ),

  openPath: (path: string) =>
    apiFetch<StatusResponse>("/open-path", { method: "POST", body: { path } }),

  openUri: (uri: string) =>
    apiFetch<StatusResponse>("/open-uri", { method: "POST", body: { uri } }),

  getPrefixInfo: (appId: string, prefixPath?: string) =>
    apiFetch<PrefixInfo>(
      `/games/${appId}/prefix-info${prefixPath ? `?prefix_path=${encodeURIComponent(prefixPath)}` : ""}`
    ),

  deletePrefix: (appId: string, prefixPath?: string) =>
    apiFetch<StatusResponse>(
      `/games/${appId}/prefix${prefixPath ? `?prefix_path=${encodeURIComponent(prefixPath)}` : ""}`,
      { method: "DELETE" }
    ),

  getShaderCache: (appId: string) =>
    apiFetch<ShaderCacheInfo>(`/games/${appId}/shader-cache`),

  clearShaderCache: (appId: string) =>
    apiFetch<StatusResponse>(`/games/${appId}/shader-cache`, { method: "DELETE" }),

  getTotalShaderCache: () =>
    apiFetch<{ size_bytes: number; size_human: string }>("/shader-cache/total"),

  getGamescopeAvailable: () =>
    apiFetch<{ available: boolean }>("/gamescope/available"),

  buildGamescopeCmd: (opts: GamescopeOptions) =>
    apiFetch<{ command: string }>("/gamescope/build-cmd", { method: "POST", body: opts }),

  getGameFixes: (appId: string) =>
    apiFetch<GameFixData[]>(`/games/${appId}/fixes`),

  addGameFix: (appId: string, fix: GameFixCreateData) =>
    apiFetch<StatusResponse>(`/games/${appId}/fixes`, { method: "POST", body: fix }),

  getMangoHudAvailable: () =>
    apiFetch<{ available: boolean }>("/mangohud/available"),

  getMangoHudConfig: () =>
    apiFetch<MangoHudConfigResponse>("/mangohud/config"),

  setMangoHudConfig: (config: Record<string, string>) =>
    apiFetch<StatusResponse>("/mangohud/config", { method: "PUT", body: { config } }),

  getMangoHudPresets: () =>
    apiFetch<Record<string, Record<string, string>>>("/mangohud/presets"),

  listMangoHudPerGame: () =>
    apiFetch<{ name: string; path: string }[]>("/mangohud/per-game"),

  getMangoHudPerGameConfig: (gameName: string) =>
    apiFetch<MangoHudConfigResponse & { path: string; exists: boolean }>(
      `/mangohud/per-game/${encodeURIComponent(gameName)}`
    ),

  setMangoHudPerGameConfig: (gameName: string, config: Record<string, string>) =>
    apiFetch<StatusResponse>(`/mangohud/per-game/${encodeURIComponent(gameName)}`, {
      method: "PUT",
      body: { config },
    }),

  getGameSaves: (appId: string, prefixPath?: string) =>
    apiFetch<SaveLocationData[]>(
      `/games/${appId}/saves${prefixPath ? `?prefix_path=${encodeURIComponent(prefixPath)}` : ""}`
    ),

  backupGameSaves: (appId: string, paths: string[]) =>
    apiFetch<{ path: string }>(`/games/${appId}/saves/backup`, { method: "POST", body: { paths } }),

  listGameBackups: (appId: string) =>
    apiFetch<BackupInfoData[]>(`/games/${appId}/saves/backups`),

  restoreGameSaves: (appId: string, backupPath: string, targetDir: string) =>
    apiFetch<StatusResponse>(`/games/${appId}/saves/restore`, {
      method: "POST",
      body: { backup_path: backupPath, target_dir: targetDir },
    }),

  getMonitors: () =>
    apiFetch<DisplayInfoResponse>("/display/monitors"),

  setResolution: (monitor: string, width: number, height: number, refresh?: number) =>
    apiFetch<StatusResponse>("/display/resolution", {
      method: "PUT",
      body: { monitor, width, height, refresh: refresh ?? 0 },
    }),

  getControllers: () =>
    apiFetch<ControllerData[]>("/controllers"),

  getControllerSdlMapping: (controllerId: string) =>
    apiFetch<{ mapping: string }>(`/controllers/${encodeURIComponent(controllerId)}/sdl-mapping`),

  getHeroicGameConfig: (appId: string) =>
    apiFetch<HeroicGameConfig>(`/heroic/games/${appId}/config`),

  setHeroicLaunchOptions: (appId: string, options: string) =>
    apiFetch<StatusResponse>(`/heroic/games/${appId}/launch-options`, {
      method: "PUT",
      body: { options },
    }),

  setHeroicWineVersion: (appId: string, name: string, bin: string, wineType: string) =>
    apiFetch<StatusResponse>(`/heroic/games/${appId}/wine-version`, {
      method: "PUT",
      body: { name, bin, wine_type: wineType },
    }),

  setHeroicToggles: (appId: string, toggles: HeroicTogglesPayload) =>
    apiFetch<StatusResponse>(`/heroic/games/${appId}/toggles`, {
      method: "PUT",
      body: toggles,
    }),

  getHeroicWineVersions: () =>
    apiFetch<HeroicWineVersionData[]>("/heroic/wine-versions"),

  launchHeroicGame: (appId: string) =>
    apiFetch<StatusResponse>(`/heroic/games/${appId}/launch`, { method: "POST" }),
};

// Type definitions matching Python Pydantic models

export interface SteamGame {
  app_id: string;
  name: string;
  install_dir: string;
  last_played: number;
  library_path: string;
  compatdata_path: string | null;
  has_compatdata: boolean;
  install_path: string | null;
  source: "steam";
}

export interface HeroicGame {
  app_id: string;
  name: string;
  store: string;
  install_path: string | null;
  prefix_path: string | null;
  source: "heroic";
}

export interface LutrisGame {
  app_id: string;
  name: string;
  install_path: string | null;
  prefix_path: string | null;
  source: "lutris";
}

export type AnyGame = SteamGame | HeroicGame | LutrisGame;

export interface GPUInfo {
  name: string;
  driver: string;
  vram_mb: number | null;
  temperature: number | null;
}

export interface SystemInfo {
  gpus: GPUInfo[];
  power_profiles: string[];
  current_power_profile: string | null;
}

export interface LaunchPreset {
  name: string;
  value: string;
  description: string;
  install_command: string;
  install_url: string;
  is_installed: boolean;
}

export interface ProfileData {
  name: string;
  launch_options: string;
  compat_tool: string;
  env_vars: Record<string, string>;
  power_profile: string;
}

export interface ShaderCacheInfo {
  app_id: string;
  path: string;
  exists: boolean;
  size_bytes: number;
  size_human: string;
}

export interface PrefixInfo {
  path: string;
  exists: boolean;
  size_bytes: number;
  size_human: string;
  created: string;
  dxvk_version: string;
  vkd3d_version: string;
}

export interface ControllerData {
  id: string;
  name: string;
  device_path: string;
  controller_type: string;
  vendor_id: string;
  product_id: string;
}

export interface MonitorData {
  name: string;
  connected: boolean;
  resolution: string;
  refresh_rate: string;
  primary: boolean;
  position: string;
}

export interface DisplayInfoResponse {
  session_type: string;
  monitors: MonitorData[];
}

export interface SaveLocationData {
  path: string;
  exists: boolean;
  size_bytes: number;
  size_human: string;
  label: string;
}

export interface BackupInfoData {
  path: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  created: string;
}

export interface MangoHudParam {
  key: string;
  label: string;
  type: "toggle" | "value";
}

export interface MangoHudConfigResponse {
  config: Record<string, string>;
  params: MangoHudParam[];
}

export interface GameFixData {
  title: string;
  description: string;
  fix_type: string;
  key: string;
  value: string;
  source: string;
}

export interface GameFixCreateData {
  title: string;
  description?: string;
  fix_type?: string;
  key?: string;
  value?: string;
}

export interface GamescopeOptions {
  output_width: number;
  output_height: number;
  game_width: number;
  game_height: number;
  fps_limit: number;
  fsr: boolean;
  fsr_sharpness: number;
  integer_scale: boolean;
  hdr: boolean;
  nested: boolean;
  borderless: boolean;
  fullscreen: boolean;
  extra_args: string;
}

export interface HeroicWineVersionData {
  name: string;
  bin: string;
  wine_type: string;
}

export interface HeroicGameConfig {
  app_id: string;
  exists: boolean;
  wine_prefix: string;
  wine_version: HeroicWineVersionData;
  other_options: string;
  enable_esync: boolean;
  enable_fsync: boolean;
  auto_install_dxvk: boolean;
  auto_install_vkd3d: boolean;
  show_fps: boolean;
  show_mangohud: boolean;
  use_game_mode: boolean;
  nvidia_prime: boolean;
  saves_path: string;
  target_exe: string;
}

export interface HeroicTogglesPayload {
  enable_esync?: boolean;
  enable_fsync?: boolean;
  auto_install_dxvk?: boolean;
  auto_install_vkd3d?: boolean;
  show_mangohud?: boolean;
  use_game_mode?: boolean;
  nvidia_prime?: boolean;
}

export interface StatusResponse {
  success: boolean;
  message: string;
}
