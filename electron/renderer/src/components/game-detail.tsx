"use client";

import { useState, useEffect } from "react";
import { motion } from "motion/react";
import type { AnyGame, SteamGame, HeroicGame, LutrisGame } from "@/lib/api";
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
import { RevealSection } from "./reveal-section";
import { GameDetailHeader } from "./game-detail-header";
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
  const [selectedTool, setSelectedTool] = useState("");
  const [selectedHeroicWine, setSelectedHeroicWine] = useState("");

  const steamRunning = gamesData?.steam_running ?? false;

  useEffect(() => {
    if (isSteam && launchData) setLaunchOptions(launchData.options);
  }, [isSteam, launchData]);

  useEffect(() => {
    if (isHeroic && heroicConfig) setLaunchOptions(heroicConfig.other_options);
  }, [isHeroic, heroicConfig]);

  useEffect(() => {
    if (isSteam && protonData) setSelectedTool(protonData.current);
  }, [isSteam, protonData]);

  useEffect(() => {
    if (isHeroic && heroicConfig?.wine_version?.name) {
      setSelectedHeroicWine(heroicConfig.wine_version.name);
    }
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

  const isSaving = saveLaunchOpts.isPending || setHeroicLaunchOpts.isPending;

  return (
    <motion.div
      key={game.app_id}
      className="space-y-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Header */}
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
      />

      {/* Launch Options + Quick Presets */}
      {hasLaunchOptions && (
        <RevealSection>
          <GameLaunchOptions
            launchOptions={launchOptions}
            setLaunchOptions={setLaunchOptions}
            isSteam={isSteam}
            presets={presets}
          />
        </RevealSection>
      )}

      {/* Steam Proton/Compat Tool */}
      {isSteam && protonData && (
        <RevealSection delay={0.1}>
          <GameCompatTool
            mode="steam"
            selectedTool={selectedTool}
            onToolChange={setSelectedTool}
            tools={protonData.tools}
          />
        </RevealSection>
      )}

      {/* Heroic Wine/Proton */}
      {isHeroic && heroicWineVersions && heroicWineVersions.length > 0 && (
        <RevealSection delay={0.1}>
          <GameCompatTool
            mode="heroic"
            selectedTool={selectedHeroicWine}
            onToolChange={setSelectedHeroicWine}
            wineVersions={heroicWineVersions}
            heroicConfig={heroicConfig}
          />
        </RevealSection>
      )}

      {/* Heroic Toggles */}
      {isHeroic && heroicConfig?.exists && (
        <RevealSection delay={0.15}>
          <HeroicToggles appId={game.app_id} config={heroicConfig} />
        </RevealSection>
      )}

      {/* Protontricks */}
      {isSteam && verbsData?.available && (
        <RevealSection delay={0.15}>
          <GameProtontricks
            appId={game.app_id}
            verbs={verbsData.verbs}
            onRunVerb={(appId, verb) => runProtontricks.mutate({ appId, verb })}
            isPending={runProtontricks.isPending}
          />
        </RevealSection>
      )}

      {/* Gamescope */}
      {hasLaunchOptions && (
        <RevealSection delay={0.2}>
          <GamescopeBuilder
            onInsert={(cmd) => {
              const current = launchOptions.trim();
              if (current.includes(cmd)) return;
              setLaunchOptions(current ? `${cmd} ${current}` : cmd);
              appShowToast("Gamescope command inserted");
            }}
          />
        </RevealSection>
      )}

      {/* Known Fixes */}
      {fixesData && fixesData.length > 0 && (
        <RevealSection delay={0.25}>
          <GameKnownFixes
            fixes={fixesData}
            isSteam={isSteam}
            hasLaunchOptions={hasLaunchOptions}
            launchOptions={launchOptions}
            setLaunchOptions={setLaunchOptions}
          />
        </RevealSection>
      )}

      {/* Profiles */}
      <RevealSection delay={0.3}>
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
      </RevealSection>

      {/* Prefix Details */}
      {prefixData?.exists && (
        <RevealSection delay={0.35}>
          <GamePrefixDetails
            prefixData={prefixData}
            appId={game.app_id}
            isSteam={isSteam}
            prefixPath={prefixPath}
            deletePrefixMut={deletePrefixMut}
          />
        </RevealSection>
      )}

      {/* Shader Cache */}
      {isSteam && shaderData?.exists && (
        <RevealSection delay={0.4}>
          <GameShaderCache
            shaderData={shaderData}
            appId={game.app_id}
            clearShaderMut={clearShaderMut}
          />
        </RevealSection>
      )}

      {/* Save Data */}
      {savesData && savesData.length > 0 && (
        <RevealSection delay={0.45}>
          <GameSaveData
            savesData={savesData}
            backupsData={backupsData}
            appId={game.app_id}
            backupSavesMut={backupSavesMut}
            restoreSavesMut={restoreSavesMut}
          />
        </RevealSection>
      )}

      {/* Paths */}
      <RevealSection delay={0.5}>
        <GamePaths
          installPath={game.install_path ?? null}
          prefixPath={prefixPath}
          mangohudSlug={mangohudSlug}
          mangohudPickId={mangohudPickId}
        />
      </RevealSection>
    </motion.div>
  );
}
