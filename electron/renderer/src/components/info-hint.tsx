"use client";

import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { Button, Tooltip } from "@heroui/react";

interface InfoHintProps {
  /** Accessible label such as "About Paths" — describes what the tooltip explains. */
  label: string;
  /** Tooltip body. Plain text is recommended; long content stays readable thanks to max-w-xs. */
  children: ReactNode;
  /** Optional extra classes for the trigger button. */
  className?: string;
}

/**
 * Compact info-icon trigger that reveals a tooltip on hover/focus. Designed
 * to live in a `Widget.Header` so that descriptive help text doesn't push
 * the body content downward.
 */
export function InfoHint({ label, children, className = "" }: InfoHintProps) {
  return (
    <Tooltip delay={0}>
      <Button
        isIconOnly
        variant="ghost"
        size="sm"
        aria-label={label}
        className={`text-muted shrink-0 ${className}`}
      >
        <Info className="size-4" />
      </Button>
      <Tooltip.Content className="max-w-xs text-xs leading-relaxed">
        {children}
      </Tooltip.Content>
    </Tooltip>
  );
}
