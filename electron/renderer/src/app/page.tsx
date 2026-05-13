"use client";

import { useState, useMemo } from "react";
import { Gamepad2, Swords, Joystick, Settings } from "lucide-react";
import { Alert, Skeleton } from "@heroui/react";
import { EmptyState } from "@heroui-pro/react";
import { PageShell } from "@/components/page-shell";
import { GameList } from "@/components/game-list";
import { GameDetail } from "@/components/game-detail";
import { useGames } from "@/hooks/use-games";
import type { AnyGame } from "@/lib/api";

function gameListKey(game: AnyGame): string {
  return `${game.source}:${game.app_id}`;
}

export default function GamesPage() {
  const { data, isLoading, error } = useGames();
  const [selected, setSelected] = useState<AnyGame | null>(null);

  const selectedListKey = useMemo(
    () => (selected ? gameListKey(selected) : null),
    [selected],
  );

  return (
    <PageShell>
      {isLoading ? (
        <div className="flex gap-6 h-[calc(100vh-4.5rem-3rem)]">
          <div className="w-80 shrink-0 h-full flex flex-col gap-3 p-3 rounded-xl border border-neon-cyan/20 bg-surface-elevated">
            <Skeleton className="h-10 w-full rounded-lg" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
              <Skeleton className="h-6 w-16 rounded-full" />
            </div>
            <div className="flex flex-col gap-1">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full rounded-lg" />
              ))}
            </div>
          </div>
          <div className="flex-1 flex flex-col gap-4">
            <Skeleton className="h-16 w-full rounded-2xl" />
            <Skeleton className="h-32 w-full rounded-2xl" />
            <Skeleton className="h-24 w-full rounded-2xl" />
            <Skeleton className="h-24 w-full rounded-2xl" />
          </div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-full">
          <Alert status="danger" className="max-w-lg">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Title>Failed to load games</Alert.Title>
              <Alert.Description>
                {String(error)}. Make sure the backend is running and Steam, Heroic, or Lutris is installed.
              </Alert.Description>
            </Alert.Content>
          </Alert>
        </div>
      ) : (
        <div className="flex gap-6 h-[calc(100vh-4.5rem-3rem)]">
          <div className="w-80 shrink-0 h-full">
            <GameList
              steam={data?.steam ?? []}
              heroic={data?.heroic ?? []}
              lutris={data?.lutris ?? []}
              selectedListKey={selectedListKey}
              onSelect={setSelected}
            />
          </div>
          <div className="flex-1 overflow-y-auto -mr-6 pr-6">
            {selected ? (
              <GameDetail game={selected} />
            ) : (
              <div className="flex h-full min-h-[280px] items-center justify-center">
                <EmptyState className="max-w-md border-border rounded-2xl border border-dashed px-4 py-8">
                  <EmptyState.Header>
                    <EmptyState.Media variant="icon">
                      <Gamepad2 className="size-8 text-neon-cyan opacity-80" aria-hidden />
                    </EmptyState.Media>
                    <EmptyState.Title>Select a game</EmptyState.Title>
                    <EmptyState.Description className="text-center">
                      Choose a game from the list to configure launch options, compatibility tools, and performance
                      settings.
                    </EmptyState.Description>
                  </EmptyState.Header>
                  <EmptyState.Content className="flex flex-col items-center gap-3 pt-2">
                    <div className="text-muted flex flex-wrap items-center justify-center gap-4 text-xs">
                      <span className="flex items-center gap-1.5">
                        <Gamepad2 className="size-3.5" aria-hidden />
                        Steam
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Swords className="size-3.5" aria-hidden />
                        Heroic
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Joystick className="size-3.5" aria-hidden />
                        Lutris
                      </span>
                    </div>
                    <div className="text-muted flex items-center gap-1.5 text-xs opacity-70">
                      <Settings className="size-3" aria-hidden />
                      <span>Proton, MangoHud, Gamescope, env vars, profiles and more</span>
                    </div>
                  </EmptyState.Content>
                </EmptyState>
              </div>
            )}
          </div>
        </div>
      )}
    </PageShell>
  );
}
