"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { EmptyState } from "@heroui-pro/react";
import { Joystick } from "lucide-react";
import type { AnyGame, SteamGame, HeroicGame } from "@/lib/api";
import { api } from "@/lib/api";
import {
  useLaunchOptions,
  useSetLaunchOptions,
  useProtonTools,
  useSetCompatTool,
  useRunProtontricks,
  usePresets,
  useProtontricksVerbs,
  useGames,
  usePrefixInfo,
  useDeletePrefix,
  useShaderCache,
  useClearShaderCache,
  useGameFixes,
  useGameSaves,
  useGameBackups,
  useBackupSaves,
  useRestoreSaves,
  useHeroicGameConfig,
  useSetHeroicLaunchOptions,
  useHeroicWineVersions,
  useSetHeroicWineVersion,
  useLaunchHeroicGame,
} from "@/hooks/use-games";
import {
  useProfiles,
  useSaveProfile,
  useDeleteProfile,
} from "@/hooks/use-profiles";
import { mangohudSuggestedSlugForGame } from "@/lib/mangohud-naming";
import { appShowToast } from "@/lib/app-toast";
import { GameDetailHeader } from "./game-detail-header";
import { GameDetailKpiStrip } from "./game-detail-kpi-strip";
import { GameDetailTabs, type GameDetailTabKey } from "./game-detail-tabs";
import { GameProfilesMenu } from "./game-profiles-menu";
import { GameLaunchOptions } from "./game-launch-options";
import { GameCompatTool } from "./game-compat-tool";
import { GameProtontricks } from "./game-protontricks";
import { GameKnownFixes } from "./game-known-fixes";
import { GameProfiles } from "./game-profiles";
import { GamePrefixDetails } from "./game-prefix-details";
import { GameShaderCache } from "./game-shader-cache";
import { GameSaveData } from "./game-save-data";
import { GamePaths } from "./game-paths";
import { HeroicToggles } from "./heroic-toggles";
import { GamescopeBuilder } from "./gamescope-builder";
import { GameScopeBuddyOverride } from "./game-scopebuddy-override";

interface GameDetailProps {
  game: AnyGame;
}

function isSteamGame(game: AnyGame): game is SteamGame {
  return game.source === "steam";
}
function isHeroicGame(game: AnyGame): game is HeroicGame {
  return game.source === "heroic";
}

export function GameDetail({ game }: GameDetailProps) {
  const isSteam = isSteamGame(game);
  const isHeroic = isHeroicGame(game);
  const isLutris = game.source === "lutris";

  const prefixPath = isSteam
    ? game.compatdata_path
    : "prefix_path" in game
      ? game.prefix_path
      : null;

  const hasLaunchOptions = isSteam || isHeroic;
  const hasPrefix = !!prefixPath;

  const mangohudPickId = isSteam
    ? `steam:${game.app_id}`
    : isHeroic
      ? `heroic:${game.app_id}`
      : `lutris:${game.app_id}`;
  const mangohudSlug = mangohudSuggestedSlugForGame(game);
  const scopeBuddyKey = isSteam ? game.app_id : mangohudSlug;
  const scopeBuddyKeyLabel = isSteam
    ? `Steam ${game.app_id}`
    : `${game.source} · ${mangohudSlug}`;

  // ── Data hooks ──
  const { data: gamesData } = useGames();
  const { data: presets } = usePresets();
  const { data: profileNames } = useProfiles();
  const { data: fixesData } = useGameFixes(game.app_id);
  const { data: launchData } = useLaunchOptions(isSteam ? game.app_id : null);
  const { data: protonData } = useProtonTools(isSteam ? game.app_id : null);
  const { data: verbsData } = useProtontricksVerbs();
  const { data: shaderData } = useShaderCache(isSteam ? game.app_id : null);
  const { data: heroicConfig } = useHeroicGameConfig(isHeroic ? game.app_id : null);
  const { data: heroicWineVersions } = useHeroicWineVersions();
  const { data: prefixData } = usePrefixInfo(
    hasPrefix ? game.app_id : null,
    !isSteam && prefixPath ? prefixPath : undefined,
  );
  const { data: savesData } = useGameSaves(
    game.app_id,
    !isSteam && prefixPath ? prefixPath : undefined,
  );
  const { data: backupsData } = useGameBackups(game.app_id);

  // ── Mutation hooks ──
  const saveLaunchOpts = useSetLaunchOptions();
  const saveCompatTool = useSetCompatTool();
  const runProtontricks = useRunProtontricks();
  const saveProfile = useSaveProfile();
  const deleteProfileMut = useDeleteProfile();
  const deletePrefixMut = useDeletePrefix();
  const clearShaderMut = useClearShaderCache();
  const backupSavesMut = useBackupSaves();
  const restoreSavesMut = useRestoreSaves();
  const setHeroicLaunchOpts = useSetHeroicLaunchOptions();
  const setHeroicWine = useSetHeroicWineVersion();
  const launchHeroicMut = useLaunchHeroicGame();

  // ── Local state ──
  const [launchOptions, setLaunchOptions] = useState("");
  const [gamescopeBuilderPreview, setGamescopeBuilderPreview] = useState("");
  const [selectedTool, setSelectedTool] = useState("");
  const [selectedHeroicWine, setSelectedHeroicWine] = useState("");
  const [tabKey, setTabKey] = useState<GameDetailTabKey>("setup");
  const [tabMotionEpoch, setTabMotionEpoch] = useState(0);
  const prevAppIdRef = useRef(game.app_id);

  const steamRunning = gamesData?.steam_running ?? false;

  useEffect(() => {
    if (prevAppIdRef.current === game.app_id) return;
    prevAppIdRef.current = game.app_id;
    setTabKey("setup");
    setTabMotionEpoch((e) => e + 1);
  }, [game.app_id]);

  useEffect(() => {
    if (!isSteam || !launchData) return;
    queueMicrotask(() => setLaunchOptions(launchData.options));
  }, [isSteam, launchData]);

  useEffect(() => {
    if (!isHeroic || !heroicConfig) return;
    queueMicrotask(() => setLaunchOptions(heroicConfig.other_options));
  }, [isHeroic, heroicConfig]);

  useEffect(() => {
    if (!isSteam || !protonData) return;
    queueMicrotask(() => setSelectedTool(protonData.current));
  }, [isSteam, protonData]);

  useEffect(() => {
    if (!isHeroic || !heroicConfig?.wine_version?.name) return;
    queueMicrotask(() =>
      setSelectedHeroicWine(heroicConfig.wine_version.name),
    );
  }, [isHeroic, heroicConfig]);

  // ── Handlers ──
  async function handleSave() {
    try {
      if (isSteam) {
        await saveLaunchOpts.mutateAsync({ appId: game.app_id, options: launchOptions });
        if (selectedTool !== protonData?.current) {
          await saveCompatTool.mutateAsync({ appId: game.app_id, toolName: selectedTool });
        }
      } else if (isHeroic) {
        await setHeroicLaunchOpts.mutateAsync({ appId: game.app_id, options: launchOptions });
        if (heroicWineVersions && selectedHeroicWine !== heroicConfig?.wine_version?.name) {
          const wv = heroicWineVersions.find((v) => v.name === selectedHeroicWine);
          if (wv) {
            await setHeroicWine.mutateAsync({
              appId: game.app_id,
              name: wv.name,
              bin: wv.bin,
              wineType: wv.wine_type,
            });
          }
        }
      }
      appShowToast("Saved successfully");
    } catch {
      appShowToast("Failed to save", "error");
    }
  }

  async function handleLaunch() {
    try {
      if (isSteam) {
        await api.openUri(`steam://rungameid/${game.app_id}`);
      } else if (isHeroic) {
        await launchHeroicMut.mutateAsync(game.app_id);
      }
    } catch {
      appShowToast("Failed to launch", "error");
    }
  }

  function handleTabSelectionChange(key: GameDetailTabKey) {
    setTabKey(key);
    setTabMotionEpoch((e) => e + 1);
  }

  const isSaving = saveLaunchOpts.isPending || setHeroicLaunchOpts.isPending;

  const setupHasContent =
    hasLaunchOptions ||
    (isSteam && !!protonData) ||
    (isHeroic && !!heroicWineVersions && heroicWineVersions.length > 0) ||
    (isHeroic && !!heroicConfig?.exists) ||
    !!(fixesData && fixesData.length > 0);

  const lutrisSetupPlaceholder = isLutris && !setupHasContent;

  const profilesMenu = (
    <GameProfilesMenu
      gameName={game.name}
      isSteam={isSteam}
      isHeroic={isHeroic}
      launchOptions={launchOptions}
      selectedTool={selectedTool}
      selectedHeroicWine={selectedHeroicWine}
      profileNames={profileNames}
      setLaunchOptions={setLaunchOptions}
      setSelectedTool={setSelectedTool}
      setSelectedHeroicWine={setSelectedHeroicWine}
      saveProfileMut={saveProfile}
    />
  );

  const setupPanel = (
    <>
      {lutrisSetupPlaceholder && (
        <EmptyState className="border-border rounded-2xl border border-dashed px-4 py-8">
          <EmptyState.Header>
            <EmptyState.Media variant="icon">
              <Joystick className="size-8 text-neon-cyan opacity-80" aria-hidden />
            </EmptyState.Media>
            <EmptyState.Title>Lutris game</EmptyState.Title>
            <EmptyState.Description className="text-center">
              Launch options and compatibility tools are managed in Lutris. Use the Prefix tab for paths
              and save data when available, and Profiles for quick configuration presets.
            </EmptyState.Description>
          </EmptyState.Header>
        </EmptyState>
      )}
      {hasLaunchOptions && (
        <GameLaunchOptions
          launchOptions={launchOptions}
          setLaunchOptions={setLaunchOptions}
          isSteam={isSteam}
          presets={presets}
        />
      )}
      {isSteam && protonData && (
        <GameCompatTool
          mode="steam"
          selectedTool={selectedTool}
          onToolChange={setSelectedTool}
          tools={protonData.tools}
        />
      )}
      {isHeroic && heroicWineVersions && heroicWineVersions.length > 0 && (
        <GameCompatTool
          mode="heroic"
          selectedTool={selectedHeroicWine}
          onToolChange={setSelectedHeroicWine}
          wineVersions={heroicWineVersions}
          heroicConfig={heroicConfig}
        />
      )}
      {isHeroic && heroicConfig?.exists && <HeroicToggles appId={game.app_id} config={heroicConfig} />}
      {hasLaunchOptions && (
        <GamescopeBuilder
          onBuiltLineChange={setGamescopeBuilderPreview}
          onInsert={(cmd) => {
            const current = launchOptions.trim();
            if (current.includes(cmd)) return;
            setLaunchOptions(current ? `${cmd} ${current}` : cmd);
            appShowToast("Gamescope command inserted");
          }}
        />
      )}
      {hasLaunchOptions && (
        <GameScopeBuddyOverride
          scopeBuddyKey={scopeBuddyKey}
          keyLabel={scopeBuddyKeyLabel}
          gamescopeBuilderPreview={gamescopeBuilderPreview}
        />
      )}
      {fixesData && fixesData.length > 0 && (
        <GameKnownFixes
          fixes={fixesData}
          isSteam={isSteam}
          hasLaunchOptions={hasLaunchOptions}
          launchOptions={launchOptions}
          setLaunchOptions={setLaunchOptions}
        />
      )}
    </>
  );

  const prefixPanel = (
    <>
      {savesData && savesData.length > 0 && (
        <GameSaveData
          savesData={savesData}
          backupsData={backupsData}
          appId={game.app_id}
          backupSavesMut={backupSavesMut}
          restoreSavesMut={restoreSavesMut}
        />
      )}
      {prefixData?.exists && (
        <GamePrefixDetails
          prefixData={prefixData}
          appId={game.app_id}
          isSteam={isSteam}
          prefixPath={prefixPath}
          deletePrefixMut={deletePrefixMut}
        />
      )}
      {isSteam && verbsData?.available && (
        <GameProtontricks
          appId={game.app_id}
          verbs={verbsData.verbs}
          onRunVerb={(appId, verb) => runProtontricks.mutate({ appId, verb })}
          isPending={runProtontricks.isPending}
        />
      )}
      {isSteam && shaderData?.exists && (
        <GameShaderCache
          shaderData={shaderData}
          appId={game.app_id}
          clearShaderMut={clearShaderMut}
        />
      )}
      <GamePaths
        installPath={game.install_path ?? null}
        prefixPath={prefixPath}
        mangohudSlug={mangohudSlug}
        mangohudPickId={mangohudPickId}
      />
    </>
  );

  const profilesPanel = (
    <GameProfiles
      gameName={game.name}
      gameAppId={game.app_id}
      isSteam={isSteam}
      isHeroic={isHeroic}
      launchOptions={launchOptions}
      selectedTool={selectedTool}
      selectedHeroicWine={selectedHeroicWine}
      profileNames={profileNames}
      setLaunchOptions={setLaunchOptions}
      setSelectedTool={setSelectedTool}
      setSelectedHeroicWine={setSelectedHeroicWine}
      saveProfileMut={saveProfile}
      deleteProfileMut={deleteProfileMut}
    />
  );

  return (
    <motion.div
      key={game.app_id}
      className="relative space-y-4 pr-2"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <GameDetailHeader
        game={game}
        steamRunning={steamRunning}
        isSteam={isSteam}
        isHeroic={isHeroic}
        hasLaunchOptions={hasLaunchOptions}
        isSaving={isSaving}
        isLaunching={launchHeroicMut.isPending}
        onSave={handleSave}
        onLaunch={handleLaunch}
        profilesMenu={profilesMenu}
      />

      <GameDetailKpiStrip
        isSteam={isSteam}
        isHeroic={isHeroic}
        protonCurrent={protonData?.current}
        heroicWineName={heroicConfig?.wine_version?.name ?? null}
        prefixData={prefixData}
        shaderData={shaderData}
        backupsData={backupsData}
      />

      <GameDetailTabs
        selectedKey={tabKey}
        onSelectionChange={handleTabSelectionChange}
        setupPanel={setupPanel}
        prefixPanel={prefixPanel}
        profilesPanel={profilesPanel}
        gameKey={game.app_id}
        motionEpoch={tabMotionEpoch}
      />
    </motion.div>
  );
}
