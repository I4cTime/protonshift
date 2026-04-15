"use client";

import { Lightbulb } from "lucide-react";
import { Button, Description } from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { GameFixData } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GameKnownFixesProps {
  fixes: GameFixData[];
  isSteam: boolean;
  hasLaunchOptions: boolean;
  launchOptions: string;
  setLaunchOptions: (v: string) => void;
}

export function GameKnownFixes({
  fixes,
  isSteam,
  hasLaunchOptions,
  launchOptions,
  setLaunchOptions,
}: GameKnownFixesProps) {
  function handleApplyFix(fix: GameFixData) {
    if (fix.fix_type === "env") {
      const envStr = `${fix.key}=${fix.value}`;
      const current = launchOptions.trim();
      if (current.includes(envStr)) {
        appShowToast("Already applied");
        return;
      }
      if (isSteam) {
        const hasCmd = current.includes("%command%");
        if (hasCmd) {
          setLaunchOptions(current.replace("%command%", `${envStr} %command%`));
        } else {
          setLaunchOptions(current ? `${envStr} ${current}` : `${envStr} %command%`);
        }
      } else {
        setLaunchOptions(current ? `${envStr} ${current}` : envStr);
      }
    } else {
      const current = launchOptions.trim();
      if (current.includes(fix.value)) {
        appShowToast("Already applied");
        return;
      }
      setLaunchOptions(current ? `${current} ${fix.value}` : fix.value);
    }
    appShowToast(`Applied: ${fix.title}`);
  }

  return (
    <GlowCard className="p-5 space-y-3">
      <div>
        <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
          <Lightbulb className="size-4 text-amber-400" />
          Known Fixes &amp; Tweaks
        </label>
        <Description>
          Community-sourced fixes for common issues. Click Apply to insert into launch options.
        </Description>
      </div>

      <div className="space-y-2">
        {fixes.map((fix, i) => (
          <div
            key={`${fix.title}-${i}`}
            className="flex items-center justify-between p-3 rounded-lg bg-surface-deep border border-separator hover:border-border transition-all"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary">{fix.title}</p>
              <p className="text-xs text-text-muted truncate">{fix.description}</p>
              <code className="text-xs font-mono text-neon-cyan mt-0.5 block">
                {fix.fix_type === "env" ? `${fix.key}=${fix.value}` : fix.value}
              </code>
            </div>
            {hasLaunchOptions && (
              <Button
                variant="ghost"
                size="sm"
                className="ml-3 shrink-0"
                onPress={() => handleApplyFix(fix)}
              >
                Apply
              </Button>
            )}
          </div>
        ))}
      </div>
    </GlowCard>
  );
}
