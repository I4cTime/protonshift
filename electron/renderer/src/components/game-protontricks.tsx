"use client";

import { Wrench } from "lucide-react";
import { Button, Tooltip, Toolbar, Separator, Description, Chip } from "@heroui/react";
import { GlowCard } from "./glow-card";

interface GameProtontricksProps {
  appId: string;
  verbs: { id: string; label: string }[];
  onRunVerb: (appId: string, verb?: string) => void;
  isPending: boolean;
}

export function GameProtontricks({ appId, verbs, onRunVerb, isPending }: GameProtontricksProps) {
  return (
    <GlowCard className="p-5 space-y-3">
      <div>
        <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
          <Wrench className="size-4 text-neon-cyan" />
          Protontricks
        </label>
        <Description>
          Run Protontricks verbs or open the GUI for this prefix. Installs Windows components (vcrun, dotnet, etc.) into the Wine prefix.
        </Description>
      </div>

      <Toolbar aria-label="Protontricks actions" className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onPress={() => onRunVerb(appId)}
          isDisabled={isPending}
          className="gap-1.5"
        >
          <Wrench className="size-3" />
          Open GUI
        </Button>
        <Separator orientation="vertical" className="h-6 mx-1" />
        {verbs.map((verb) => (
          <Tooltip key={verb.id} delay={0}>
            <Chip
              variant="secondary"
              className="cursor-pointer"
              onClick={() => onRunVerb(appId, verb.id)}
            >
              {verb.id}
            </Chip>
            <Tooltip.Content>{verb.label}</Tooltip.Content>
          </Tooltip>
        ))}
      </Toolbar>
    </GlowCard>
  );
}
