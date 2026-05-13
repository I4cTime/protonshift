"use client";

import Link from "next/link";
import { FolderOpen, ExternalLink, Gauge } from "lucide-react";
import { Button, Label, Separator, Tooltip } from "@heroui/react";
import { ItemCard, ItemCardGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import { appShowToast } from "@/lib/app-toast";
import { api } from "@/lib/api";

interface GamePathsProps {
  installPath: string | null;
  prefixPath: string | null;
  mangohudSlug: string;
  mangohudPickId: string;
}

export function GamePaths({
  installPath,
  prefixPath,
  mangohudSlug,
  mangohudPickId,
}: GamePathsProps) {
  async function handleOpenPath(path: string) {
    try {
      await api.openPath(path);
    } catch {
      appShowToast("Failed to open folder", "error");
    }
  }

  const rows: { kind: "install" | "prefix"; label: string; path: string }[] = [];
  if (installPath) rows.push({ kind: "install", label: "Install", path: installPath });
  if (prefixPath) rows.push({ kind: "prefix", label: "Prefix", path: prefixPath });

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <FolderOpen className="text-neon-cyan size-4 shrink-0" aria-hidden />
          Paths
          {rows.length > 0 && (
            <span className="text-muted text-[10px] font-normal normal-case">
              ({rows.length})
            </span>
          )}
        </Widget.Title>
        <InfoHint label="About paths">
          Game install and Wine prefix folders. Open in the file manager or jump to per-game MangoHud
          settings.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        {rows.length > 0 ? (
          <>
            <p className="text-muted text-xs">
              Use open actions to reveal these locations in your file manager.
            </p>
            <ItemCardGroup variant="outline" layout="list" className="overflow-hidden rounded-xl">
              {rows.map((row) => (
                <ItemCard key={row.kind} className="py-2">
                  <ItemCard.Icon>
                    <FolderOpen className="text-muted size-4" aria-hidden />
                  </ItemCard.Icon>
                  <ItemCard.Content className="min-w-0">
                    <ItemCard.Title>
                      <code
                        className="text-foreground block break-all font-mono text-[11px] font-semibold leading-snug"
                        title={row.path}
                      >
                        <span className="line-clamp-2">{row.path}</span>
                      </code>
                    </ItemCard.Title>
                    <ItemCard.Description className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                      {row.label}
                    </ItemCard.Description>
                  </ItemCard.Content>
                  <ItemCard.Action>
                    <Tooltip delay={0}>
                      <Button
                        isIconOnly
                        variant="outline"
                        size="sm"
                        onPress={() => handleOpenPath(row.path)}
                        aria-label={`Open ${row.label.toLowerCase()} folder`}
                      >
                        <ExternalLink className="size-3.5" />
                      </Button>
                      <Tooltip.Content>Open folder</Tooltip.Content>
                    </Tooltip>
                  </ItemCard.Action>
                </ItemCard>
              ))}
            </ItemCardGroup>
          </>
        ) : (
          <p className="text-muted text-xs">
            No install or prefix paths are available for this launcher entry.
          </p>
        )}

        <Separator />

        <div className="space-y-1.5">
          <Label className="text-muted flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
            <Gauge className="text-neon-cyan size-3.5 shrink-0" aria-hidden />
            MangoHud
          </Label>
          <Link
            href={`/mangohud?slug=${encodeURIComponent(mangohudSlug)}&pick=${encodeURIComponent(mangohudPickId)}`}
            className="text-neon-cyan inline-flex items-center gap-1.5 text-xs font-medium hover:underline"
          >
            Per-game MangoHud
            <ExternalLink className="size-3 shrink-0 opacity-70" aria-hidden />
          </Link>
          <p className="text-muted text-[11px]">
            Opens MangoHud with this title suggested as{" "}
            <code className="text-neon-cyan/90 font-mono text-[10px]">
              wine-{mangohudSlug}.conf
            </code>
          </p>
        </div>
      </Widget.Content>
    </Widget>
  );
}
