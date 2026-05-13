"use client";

import { useMemo } from "react";
import { Wrench } from "lucide-react";
import { Button, Chip, Label, Separator, Text, Tooltip } from "@heroui/react";
import { Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";

interface GameProtontricksVerb {
  id: string;
  label: string;
  category?: string;
}

interface GameProtontricksProps {
  appId: string;
  verbs: GameProtontricksVerb[];
  onRunVerb: (appId: string, verb?: string) => void;
  isPending: boolean;
}

const UNCATEGORISED = "Other";

export function GameProtontricks({ appId, verbs, onRunVerb, isPending }: GameProtontricksProps) {
  const grouped = useMemo(() => {
    const order: string[] = [];
    const buckets = new Map<string, GameProtontricksVerb[]>();
    for (const verb of verbs) {
      const key = verb.category && verb.category.trim() ? verb.category : UNCATEGORISED;
      if (!buckets.has(key)) {
        buckets.set(key, []);
        order.push(key);
      }
      buckets.get(key)!.push(verb);
    }
    return order.map((category) => ({ category, items: buckets.get(category)! }));
  }, [verbs]);

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Wrench className="text-neon-cyan size-4 shrink-0" aria-hidden />
          Protontricks
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {verbs.length} verb{verbs.length === 1 ? "" : "s"}
          </Chip>
        </Widget.Title>
        <InfoHint label="About Protontricks">
          Run verbs or open the GUI for this Steam prefix. Installs Windows components (VC++, .NET,
          etc.) into the Wine prefix.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        <Text.Paragraph size="xs" color="muted">
          GUI runs winetricks against the game&apos;s Proton prefix. Quick verbs run without
          opening the full UI. Hover any verb for its full description.
        </Text.Paragraph>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-stretch">
          <Button
            variant="outline"
            size="sm"
            onPress={() => onRunVerb(appId)}
            isDisabled={isPending}
            className="w-full shrink-0 gap-1.5 sm:w-auto sm:self-start"
          >
            <Wrench className="size-3.5 shrink-0" />
            Open GUI
          </Button>
          <Separator orientation="vertical" className="hidden shrink-0 sm:block" />
          <div className="min-w-0 flex-1 space-y-2">
            {grouped.map(({ category, items }) => {
              const slug = category.toLowerCase().replace(/[^a-z0-9]+/g, "-");
              const labelId = `protontricks-verbs-${slug}`;
              return (
                <div key={category} className="space-y-1">
                  <Label
                    id={labelId}
                    className="text-muted flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide"
                  >
                    {category}
                    <Chip size="sm" variant="secondary" className="text-[9px]">
                      {items.length}
                    </Chip>
                  </Label>
                  <div
                    role="group"
                    aria-labelledby={labelId}
                    className="flex flex-wrap gap-1.5"
                  >
                    {items.map((verb) => (
                      <Tooltip key={verb.id} delay={0}>
                        <Button
                          variant="secondary"
                          size="sm"
                          className="h-8 min-h-8 px-2.5 font-mono text-[11px]"
                          onPress={() => onRunVerb(appId, verb.id)}
                          isDisabled={isPending}
                        >
                          {verb.id}
                        </Button>
                        <Tooltip.Content>{verb.label}</Tooltip.Content>
                      </Tooltip>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Widget.Content>
    </Widget>
  );
}
