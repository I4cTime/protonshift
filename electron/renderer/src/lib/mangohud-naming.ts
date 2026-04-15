import type { AnyGame, SteamGame } from "@/lib/api";

/** Matches `get_per_game_config_path` slug (see `mangohud.py`). */
export function mangohudPerGameSlug(name: string): string {
  return name
    .trim()
    .replace(/\\/g, "_")
    .replace(/\s+/g, "_")
    .replace(/\//g, "_");
}

/** Best-effort base string for wine-<name>.conf before slugging. */
export function mangohudNameCandidateFromGame(game: AnyGame): string {
  if (game.source === "steam") {
    const s = game as SteamGame;
    const dir = s.install_dir?.trim();
    if (dir) return dir;
  }
  return game.name.trim();
}

export function mangohudSuggestedSlugForGame(game: AnyGame): string {
  return mangohudPerGameSlug(mangohudNameCandidateFromGame(game));
}
