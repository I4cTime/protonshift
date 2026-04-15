"use client";

import { Button, Tooltip } from "@heroui/react";
import { Minus, Square, X } from "lucide-react";

export function WindowControls() {
  if (typeof window === "undefined" || !window.electron) {
    return null;
  }

  const { minimizeWindow, toggleMaximize, closeWindow } = window.electron;

  return (
    <div className="flex items-center gap-0.5 shrink-0 app-region-no-drag">
      <Tooltip delay={0}>
        <Button
          isIconOnly
          variant="ghost"
          size="sm"
          className="size-8 min-w-8 rounded-lg text-foreground hover:bg-surface-secondary"
          aria-label="Minimize window"
          onPress={() => void minimizeWindow()}
        >
          <Minus className="size-4" strokeWidth={2.5} />
        </Button>
        <Tooltip.Content>Minimize</Tooltip.Content>
      </Tooltip>
      <Tooltip delay={0}>
        <Button
          isIconOnly
          variant="ghost"
          size="sm"
          className="size-8 min-w-8 rounded-lg text-foreground hover:bg-surface-secondary"
          aria-label="Maximize or restore window"
          onPress={() => void toggleMaximize()}
        >
          <Square className="size-3.5" strokeWidth={2.25} />
        </Button>
        <Tooltip.Content>Maximize</Tooltip.Content>
      </Tooltip>
      <Tooltip delay={0}>
        <Button
          isIconOnly
          variant="ghost"
          size="sm"
          className="size-8 min-w-8 rounded-lg text-foreground hover:bg-danger/15 hover:text-danger"
          aria-label="Quit application"
          onPress={() => void closeWindow()}
        >
          <X className="size-4" strokeWidth={2.5} />
        </Button>
        <Tooltip.Content>Quit</Tooltip.Content>
      </Tooltip>
    </div>
  );
}
