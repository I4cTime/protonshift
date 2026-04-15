"use client";

import { useState, useMemo } from "react";
import { Gamepad2, Swords, Joystick, SearchX, FolderOpen } from "lucide-react";
import { SearchField, Surface, Chip, Separator, Description } from "@heroui/react";
import { motion, AnimatePresence } from "motion/react";
import type { AnyGame, SteamGame, HeroicGame, LutrisGame } from "@/lib/api";

interface GameListProps {
  steam: SteamGame[];
  heroic: HeroicGame[];
  lutris: LutrisGame[];
  selectedId: string | null;
  onSelect: (game: AnyGame) => void;
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

function getSourceLabel(game: AnyGame): string {
  if (game.source === "heroic") return `Heroic (${(game as HeroicGame).store})`;
  return game.source.charAt(0).toUpperCase() + game.source.slice(1);
}

export function GameList({ steam, heroic, lutris, selectedId, onSelect }: GameListProps) {
  const [search, setSearch] = useState("");
  const totalCount = steam.length + heroic.length + lutris.length;

  const allGames = useMemo(() => {
    const games: AnyGame[] = [...steam, ...heroic, ...lutris];
    if (!search.trim()) return games;
    const q = search.toLowerCase();
    return games.filter((g) => g.name.toLowerCase().includes(q));
  }, [steam, heroic, lutris, search]);

  const isSearching = search.trim().length > 0;

  return (
    <Surface variant="secondary" className="flex flex-col h-full backdrop-blur-xl border border-neon-cyan/20 rounded-xl overflow-hidden shadow-card">
      <div className="p-3 flex flex-col gap-2">
        <SearchField
          value={search}
          onChange={setSearch}
          onClear={() => setSearch("")}
          aria-label="Search games"
        >
          <SearchField.Group className="w-full">
            <SearchField.SearchIcon />
            <SearchField.Input
              placeholder="Search games..."
              className="w-full"
            />
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
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence>
          {allGames.map((game, index) => {
            const Icon = getSourceIcon(game.source);
            const active = game.app_id === selectedId;
            const isHeroicGame = game.source === "heroic";
            return (
              <motion.button
                key={`${game.source}-${game.app_id}`}
                onClick={() => onSelect(game)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 text-left
                  transition-colors cursor-pointer
                  ${active ? "bg-neon-cyan/[0.18]" : "hover:bg-neon-cyan/[0.08]"}
                `}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ delay: Math.min(index * 0.02, 0.5), duration: 0.25 }}
                layout
              >
                <Icon className={`size-4 shrink-0 ${active ? "text-neon-cyan" : "text-text-muted"}`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm truncate ${active ? "text-neon-cyan font-medium" : "text-text-primary"}`}>
                    {game.name}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <p className="text-xs text-text-muted truncate">
                      {getSourceLabel(game)}
                    </p>
                    {isHeroicGame && (
                      <Chip size="sm" variant="soft" color="accent" className="text-[10px] h-4 px-1.5">
                        {(game as HeroicGame).store}
                      </Chip>
                    )}
                  </div>
                </div>
              </motion.button>
            );
          })}
        </AnimatePresence>
        {allGames.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-text-muted px-4">
            {isSearching ? (
              <>
                <SearchX className="size-10 mb-3 opacity-50" />
                <p className="text-sm font-medium">No matches</p>
                <Description className="text-center mt-1">
                  No games match &ldquo;{search}&rdquo;. Try a different search term.
                </Description>
              </>
            ) : (
              <>
                <FolderOpen className="size-10 mb-3 opacity-50" />
                <p className="text-sm font-medium">No games discovered</p>
                <Description className="text-center mt-1">
                  Install games via Steam, Heroic, or Lutris, then restart the app to detect them.
                </Description>
              </>
            )}
          </div>
        )}
      </div>
    </Surface>
  );
}
