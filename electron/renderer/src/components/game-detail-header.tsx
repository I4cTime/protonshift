"use client";

import type { ReactNode } from "react";
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
  /** Quick profile apply + save (rendered before Launch / Save) */
  profilesMenu: ReactNode;
}

function SourceIconGlyph({
  source,
  className,
}: {
  source: string;
  className?: string;
}) {
  switch (source) {
    case "steam":
      return <Gamepad2 className={className} aria-hidden />;
    case "heroic":
      return <Swords className={className} aria-hidden />;
    case "lutris":
      return <Joystick className={className} aria-hidden />;
    default:
      return <Gamepad2 className={className} aria-hidden />;
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
  profilesMenu,
}: GameDetailHeaderProps) {
  function handleCopyAppId() {
    navigator.clipboard.writeText(game.app_id);
    appShowToast("App ID copied");
  }

  const showLaunchSave = isSteam || isHeroic || hasLaunchOptions;

  return (
    <header className="sticky top-0 z-20 -mx-2 mb-3 space-y-3 border-b border-separator bg-background/85 px-2 py-2 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
      {isSteam && steamRunning && (
        <Alert status="warning">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Steam client is active</Alert.Title>
            <Alert.Description>
              The app detected a running <code className="text-xs">steam</code> process (including
              when Steam is only in the system tray, not in the foreground). Fully quit Steam
              before saving launch options to avoid conflicts.
            </Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="flex items-center gap-2 text-xl font-bold text-neon-cyan">
            <SourceIconGlyph source={game.source} className="size-5 shrink-0" />
            <span className="truncate">{game.name}</span>
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-text-secondary">
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
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {profilesMenu}
          {showLaunchSave && (
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
    </header>
  );
}
