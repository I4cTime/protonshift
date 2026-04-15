"use client";

import { Gamepad2, Swords, Joystick, Copy, Play, Save } from "lucide-react";
import { Button, ButtonGroup, Chip, Tooltip, Spinner, Alert } from "@heroui/react";
import type { AnyGame, HeroicGame } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GameDetailHeaderProps {
  game: AnyGame;
  steamRunning: boolean;
  isSteam: boolean;
  isHeroic: boolean;
  hasLaunchOptions: boolean;
  isSaving: boolean;
  isLaunching: boolean;
  onSave: () => void;
  onLaunch: () => void;
}

function getSourceIcon(source: string) {
  switch (source) {
    case "steam":
      return Gamepad2;
    case "heroic":
      return Swords;
    case "lutris":
      return Joystick;
    default:
      return Gamepad2;
  }
}

export function GameDetailHeader({
  game,
  steamRunning,
  isSteam,
  isHeroic,
  hasLaunchOptions,
  isSaving,
  isLaunching,
  onSave,
  onLaunch,
}: GameDetailHeaderProps) {
  const SourceIcon = getSourceIcon(game.source);

  function handleCopyAppId() {
    navigator.clipboard.writeText(game.app_id);
    appShowToast("App ID copied");
  }

  return (
    <div className="space-y-3">
      {isSteam && steamRunning && (
        <Alert status="warning">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Steam is running</Alert.Title>
            <Alert.Description>
              Close Steam before saving launch options to avoid conflicts.
            </Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
            <SourceIcon className="size-5 shrink-0" />
            {game.name}
          </h2>
          <div className="flex items-center gap-3 mt-1 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5">
              {isHeroic && (
                <Chip size="sm" variant="soft" color="accent" className="mr-1">
                  {(game as HeroicGame).store.toUpperCase()}
                </Chip>
              )}
              {game.source === "lutris" && (
                <Chip size="sm" variant="soft" color="accent" className="mr-1">
                  Lutris
                </Chip>
              )}
              App ID: {game.app_id}
            </span>
            <Tooltip delay={0}>
              <Button isIconOnly variant="ghost" size="sm" onPress={handleCopyAppId} aria-label="Copy App ID">
                <Copy className="size-3.5" />
              </Button>
              <Tooltip.Content>Copy App ID</Tooltip.Content>
            </Tooltip>
          </div>
        </div>
        {(isSteam || isHeroic || hasLaunchOptions) && (
          <ButtonGroup>
            {(isSteam || isHeroic) && (
              <Button
                variant="outline"
                size="sm"
                onPress={onLaunch}
                isDisabled={isLaunching}
                className="gap-2"
              >
                <Play className="size-4" />
                Launch
              </Button>
            )}
            {hasLaunchOptions && (
              <Button
                size="sm"
                onPress={onSave}
                isDisabled={isSaving}
                className="gap-2"
              >
                {isSaving ? <Spinner size="sm" /> : <Save className="size-4" />}
                {isSteam ? "Save to Steam" : "Save to Heroic"}
              </Button>
            )}
          </ButtonGroup>
        )}
      </div>
    </div>
  );
}
