"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import type { Key, Selection } from "react-aria-components";
import { Gamepad2, Swords, Joystick, SearchX, FolderOpen } from "lucide-react";
import { SearchField, Surface, Chip, Separator } from "@heroui/react";
import { ListView, EmptyState } from "@heroui-pro/react";
import type { AnyGame, SteamGame, HeroicGame, LutrisGame } from "@/lib/api";
import { FOCUS_GAME_SEARCH_EVENT } from "@/lib/command-palette-events";

interface GameListProps {
  steam: SteamGame[];
  heroic: HeroicGame[];
  lutris: LutrisGame[];
  selectedListKey: string | null;
  onSelect: (game: AnyGame) => void;
}

function gameKey(game: AnyGame): string {
  return `${game.source}:${game.app_id}`;
}

/** ListView `items` must carry a top-level `id` for collection keys (HeroUI / RAC). */
type GameListRow = { id: string; game: AnyGame };

function GameSourceGlyph({
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

function getSourceLabel(game: AnyGame): string {
  if (game.source === "heroic") return `Heroic (${(game as HeroicGame).store})`;
  return game.source.charAt(0).toUpperCase() + game.source.slice(1);
}

export function GameList({ steam, heroic, lutris, selectedListKey, onSelect }: GameListProps) {
  const [search, setSearch] = useState("");
  const totalCount = steam.length + heroic.length + lutris.length;

  const allGames = useMemo(() => {
    const games: AnyGame[] = [...steam, ...heroic, ...lutris];
    if (!search.trim()) return games;
    const q = search.toLowerCase();
    return games.filter((g) => g.name.toLowerCase().includes(q));
  }, [steam, heroic, lutris, search]);

  const listRows = useMemo(
    (): GameListRow[] => allGames.map((g) => ({ id: gameKey(g), game: g })),
    [allGames],
  );

  const gameByKey = useMemo(
    () => new Map(listRows.map((r) => [r.id, r.game])),
    [listRows],
  );

  const isSearching = search.trim().length > 0;

  const selectedKeys = useMemo((): Selection => {
    if (!selectedListKey) return new Set<Key>();
    return new Set<Key>([selectedListKey]);
  }, [selectedListKey]);

  const onSelectionChange = useCallback(
    (keys: Selection) => {
      if (keys === "all") return;
      const id = [...keys][0];
      if (id == null) return;
      const g = gameByKey.get(String(id));
      if (g) onSelect(g);
    },
    [gameByKey, onSelect],
  );

  const onListAction = useCallback(
    (key: string | number) => {
      const g = gameByKey.get(String(key));
      if (g) onSelect(g);
    },
    [gameByKey, onSelect],
  );

  useEffect(() => {
    function focusSearch() {
      const input = document.querySelector<HTMLInputElement>(
        '[aria-label="Search games"] input, input[placeholder="Search games..."]',
      );
      input?.focus();
      input?.select?.();
    }
    window.addEventListener(FOCUS_GAME_SEARCH_EVENT, focusSearch);
    return () => window.removeEventListener(FOCUS_GAME_SEARCH_EVENT, focusSearch);
  }, []);

  return (
    <Surface
      variant="secondary"
      className="flex flex-col h-full backdrop-blur-xl border border-neon-cyan/20 rounded-xl overflow-hidden shadow-card"
    >
      <div className="p-3 flex flex-col gap-2">
        <SearchField
          value={search}
          onChange={setSearch}
          onClear={() => setSearch("")}
          aria-label="Search games"
        >
          <SearchField.Group className="w-full">
            <SearchField.SearchIcon />
            <SearchField.Input placeholder="Search games..." className="w-full" />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
        {totalCount > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {steam.length > 0 && (
              <Chip size="sm" variant="secondary" className="gap-1">
                <Gamepad2 className="size-3" />
                {steam.length}
              </Chip>
            )}
            {heroic.length > 0 && (
              <Chip size="sm" variant="secondary" className="gap-1">
                <Swords className="size-3" />
                {heroic.length}
              </Chip>
            )}
            {lutris.length > 0 && (
              <Chip size="sm" variant="secondary" className="gap-1">
                <Joystick className="size-3" />
                {lutris.length}
              </Chip>
            )}
            {isSearching && (
              <Chip size="sm" variant="soft" color="accent" className="ml-auto">
                {allGames.length} match{allGames.length !== 1 ? "es" : ""}
              </Chip>
            )}
          </div>
        )}
      </div>
      <Separator />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {allGames.length > 0 ? (
          <ListView
            aria-label="Games"
            variant="secondary"
            selectionMode="single"
            selectionBehavior="replace"
            items={listRows}
            selectedKeys={selectedKeys}
            onSelectionChange={onSelectionChange}
            onAction={onListAction}
            className="min-h-0 border-0 bg-transparent p-0 shadow-none"
          >
            {(row) => {
              const { id: gk, game } = row;
              const isHeroicGame = game.source === "heroic";
              const isActive = selectedListKey === gk;
              return (
                <ListView.Item id={gk} textValue={game.name} className="rounded-lg">
                  <ListView.ItemContent>
                    <GameSourceGlyph
                      source={game.source}
                      className={`size-4 shrink-0 ${isActive ? "text-neon-cyan" : "text-muted"}`}
                    />
                    <div className="flex min-w-0 flex-col">
                      <ListView.Title className={isActive ? "text-neon-cyan font-medium" : undefined}>
                        {game.name}
                      </ListView.Title>
                      <div className="flex items-center gap-1.5">
                        <ListView.Description>{getSourceLabel(game)}</ListView.Description>
                        {isHeroicGame && (
                          <Chip size="sm" variant="soft" color="accent" className="h-4 px-1.5 text-[10px]">
                            {(game as HeroicGame).store}
                          </Chip>
                        )}
                      </div>
                    </div>
                  </ListView.ItemContent>
                </ListView.Item>
              );
            }}
          </ListView>
        ) : isSearching ? (
          <div className="flex min-h-[180px] items-center justify-center p-4">
            <EmptyState size="sm" className="max-w-sm border-border rounded-xl border border-dashed">
              <EmptyState.Header>
                <EmptyState.Media variant="icon">
                  <SearchX className="size-5 text-muted" aria-hidden />
                </EmptyState.Media>
                <EmptyState.Title>No matches</EmptyState.Title>
                <EmptyState.Description className="text-center">
                  No games match &ldquo;{search}&rdquo;. Try a different search term.
                </EmptyState.Description>
              </EmptyState.Header>
            </EmptyState>
          </div>
        ) : (
          <div className="flex min-h-[180px] items-center justify-center p-4">
            <EmptyState size="sm" className="max-w-sm border-border rounded-xl border border-dashed">
              <EmptyState.Header>
                <EmptyState.Media variant="icon">
                  <FolderOpen className="size-5 text-muted" aria-hidden />
                </EmptyState.Media>
                <EmptyState.Title>No games discovered</EmptyState.Title>
                <EmptyState.Description className="text-center">
                  Install games via Steam, Heroic, or Lutris, then restart the app to detect them.
                </EmptyState.Description>
              </EmptyState.Header>
            </EmptyState>
          </div>
        )}
      </div>
    </Surface>
  );
}
