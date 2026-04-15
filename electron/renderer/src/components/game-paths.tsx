"use client";

import Link from "next/link";
import { FolderOpen, ExternalLink, Gauge } from "lucide-react";
import { Button, Description, Separator, Tooltip } from "@heroui/react";
import { GlowCard } from "./glow-card";
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

  return (
    <GlowCard className="p-5 space-y-3">
      <div>
        <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
          <FolderOpen className="size-4 text-neon-cyan" />
          Paths
        </label>
        <Description>
          Install and prefix directories. Open in file manager or jump to per-game MangoHud config.
        </Description>
      </div>

      <div className="space-y-2 text-sm">
        {installPath && (
          <div className="flex items-center gap-2">
            <FolderOpen className="size-4 text-text-muted shrink-0" />
            <span className="text-text-secondary">Install:</span>
            <span className="text-text-primary font-mono text-xs truncate flex-1">{installPath}</span>
            <Tooltip delay={0}>
              <Button isIconOnly variant="ghost" size="sm" onPress={() => handleOpenPath(installPath)} aria-label="Open install folder">
                <ExternalLink className="size-3.5" />
              </Button>
              <Tooltip.Content>Open folder</Tooltip.Content>
            </Tooltip>
          </div>
        )}
        {prefixPath && (
          <div className="flex items-center gap-2">
            <FolderOpen className="size-4 text-text-muted shrink-0" />
            <span className="text-text-secondary">Prefix:</span>
            <span className="text-text-primary font-mono text-xs truncate flex-1">{prefixPath}</span>
            <Tooltip delay={0}>
              <Button isIconOnly variant="ghost" size="sm" onPress={() => handleOpenPath(prefixPath)} aria-label="Open prefix folder">
                <ExternalLink className="size-3.5" />
              </Button>
              <Tooltip.Content>Open folder</Tooltip.Content>
            </Tooltip>
          </div>
        )}

        <Separator />

        <div>
          <Link
            href={`/mangohud?slug=${encodeURIComponent(mangohudSlug)}&pick=${encodeURIComponent(mangohudPickId)}`}
            className="inline-flex items-center gap-2 text-xs font-medium text-neon-cyan hover:text-neon-cyan/90 hover:underline"
          >
            <Gauge className="size-3.5 shrink-0" />
            Per-game MangoHud
          </Link>
          <p className="text-[11px] text-text-muted mt-1">
            Opens the MangoHud page with this title suggested as <code className="text-neon-cyan/80">wine-{mangohudSlug}.conf</code>
          </p>
        </div>
      </div>
    </GlowCard>
  );
}
