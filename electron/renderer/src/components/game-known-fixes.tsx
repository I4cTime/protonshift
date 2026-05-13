"use client";

import { Lightbulb, Terminal, Variable } from "lucide-react";
import { Button, Chip, Text, Tooltip } from "@heroui/react";
import { ItemCard, ItemCardGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
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
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Lightbulb className="size-4 shrink-0 text-amber-400" />
          Known fixes and tweaks
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {fixes.length}
          </Chip>
        </Widget.Title>
        <InfoHint label="About known fixes">
          Community-sourced fixes. Apply inserts into launch options (env vars before
          %command% on Steam).
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-2">
        <Text.Paragraph size="xs" color="muted">
          One tap merges the snippet into your launch line if it is not already there.
        </Text.Paragraph>
        <ItemCardGroup variant="outline" layout="list" className="overflow-hidden rounded-xl">
          {fixes.map((fix, i) => {
            const snippet =
              fix.fix_type === "env" ? `${fix.key}=${fix.value}` : fix.value;
            const RowIcon = fix.fix_type === "env" ? Variable : Terminal;
            return (
              <ItemCard key={`${fix.title}-${i}`} className="py-2">
                <ItemCard.Icon>
                  <RowIcon className="text-muted size-4" aria-hidden />
                </ItemCard.Icon>
                <ItemCard.Content className="min-w-0 gap-1">
                  <ItemCard.Title className="flex min-w-0 flex-wrap items-center gap-2 text-sm">
                    <span className="min-w-0 truncate">{fix.title}</span>
                    <Chip size="sm" variant="soft" className="text-[10px] lowercase">
                      {fix.fix_type}
                    </Chip>
                  </ItemCard.Title>
                  <Text.Paragraph
                    size="xs"
                    color="muted"
                    className="line-clamp-2 leading-snug"
                  >
                    {fix.description}
                  </Text.Paragraph>
                  <Text.Code
                    className="text-neon-cyan block truncate text-[11px]"
                    title={snippet}
                  >
                    {snippet}
                  </Text.Code>
                </ItemCard.Content>
                <ItemCard.Action>
                  {hasLaunchOptions ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="shrink-0"
                      onPress={() => handleApplyFix(fix)}
                    >
                      Apply
                    </Button>
                  ) : (
                    <Tooltip delay={0}>
                      <span className="inline-flex">
                        <Button size="sm" variant="outline" isDisabled className="shrink-0">
                          Apply
                        </Button>
                      </span>
                      <Tooltip.Content>
                        Launch options are not available for this launcher.
                      </Tooltip.Content>
                    </Tooltip>
                  )}
                </ItemCard.Action>
              </ItemCard>
            );
          })}
        </ItemCardGroup>
      </Widget.Content>
    </Widget>
  );
}
