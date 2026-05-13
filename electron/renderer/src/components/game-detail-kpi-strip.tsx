"use client";

import { useMemo } from "react";
import { Box, HardDrive, Sparkles, Archive } from "lucide-react";
import { Surface } from "@heroui/react";
import type { BackupInfoData, PrefixInfo, ShaderCacheInfo } from "@/lib/api";

function formatRelativeTime(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return iso;
  const diffMs = Date.now() - t;
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 48) return `${hr}h ago`;
  const d = Math.floor(hr / 24);
  if (d < 14) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export interface GameDetailKpiStripProps {
  isSteam: boolean;
  isHeroic: boolean;
  /** Steam: current compat tool name */
  protonCurrent?: string | null;
  /** Heroic: wine version display name */
  heroicWineName?: string | null;
  prefixData?: PrefixInfo | null;
  shaderData?: ShaderCacheInfo | null;
  backupsData?: BackupInfoData[] | null;
}

type StatTile = {
  key: string;
  label: string;
  value: string;
  Icon: typeof Box;
};

export function GameDetailKpiStrip({
  isSteam,
  isHeroic,
  protonCurrent,
  heroicWineName,
  prefixData,
  shaderData,
  backupsData,
}: GameDetailKpiStripProps) {
  const wineLabel = isSteam ? "Proton" : isHeroic ? "Wine" : null;
  const wineValue = isSteam ? protonCurrent : isHeroic ? heroicWineName : null;

  const lastBackup = useMemo(() => {
    if (!backupsData?.length) return null;
    const sorted = [...backupsData].sort(
      (a, b) => new Date(b.created).getTime() - new Date(a.created).getTime(),
    );
    return sorted[0] ?? null;
  }, [backupsData]);

  const tiles: StatTile[] = [];

  if (wineLabel && wineValue) {
    tiles.push({
      key: "wine",
      label: wineLabel,
      value: wineValue,
      Icon: Box,
    });
  }

  if (prefixData?.exists) {
    tiles.push({
      key: "prefix",
      label: "Prefix",
      value: prefixData.size_human,
      Icon: HardDrive,
    });
  }

  if (isSteam && shaderData?.exists) {
    tiles.push({
      key: "shader",
      label: "Shaders",
      value: shaderData.size_human,
      Icon: Sparkles,
    });
  }

  if (lastBackup) {
    tiles.push({
      key: "backup",
      label: "Last backup",
      value: formatRelativeTime(lastBackup.created),
      Icon: Archive,
    });
  }

  if (tiles.length === 0) return null;

  const gridCols =
    tiles.length === 1
      ? "grid-cols-1"
      : tiles.length === 2
        ? "grid-cols-1 sm:grid-cols-2"
        : tiles.length === 3
          ? "grid-cols-1 sm:grid-cols-3"
          : "grid-cols-2 lg:grid-cols-4";

  return (
    <div className={`grid w-full min-w-0 gap-2 ${gridCols}`}>
      {tiles.map((t) => {
        const Icon = t.Icon;
        return (
          <Surface
            key={t.key}
            variant="secondary"
            className="flex min-h-[4.75rem] min-w-0 flex-col justify-between rounded-xl border border-border px-3 py-2.5 shadow-sm"
          >
            <div className="flex items-center gap-2 text-muted">
              <Icon className="size-4 shrink-0 text-accent" aria-hidden />
              <span className="truncate text-[11px] font-semibold uppercase tracking-wide">{t.label}</span>
            </div>
            <p className="mt-1 truncate text-sm font-semibold text-foreground" title={t.value}>
              {t.value}
            </p>
          </Surface>
        );
      })}
    </div>
  );
}
