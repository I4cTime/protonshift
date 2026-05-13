"use client";

import type { ReactNode } from "react";
import type { Key } from "react-aria-components";
import { motion } from "motion/react";
import { Segment } from "@heroui-pro/react";

export type GameDetailTabKey = "setup" | "prefix" | "profiles";

export interface GameDetailTabsProps {
  selectedKey: GameDetailTabKey;
  onSelectionChange: (key: GameDetailTabKey) => void;
  setupPanel: ReactNode;
  prefixPanel: ReactNode;
  profilesPanel: ReactNode;
  /** Stable per-game id (e.g. app id) for layout keys */
  gameKey: string;
  /** Increment when the selected tab changes to replay enter motion */
  motionEpoch: number;
}

function toTabKey(k: Key): GameDetailTabKey {
  const s = String(k);
  if (s === "prefix" || s === "profiles") return s;
  return "setup";
}

const TABS: { id: GameDetailTabKey; label: string }[] = [
  { id: "setup", label: "Setup" },
  { id: "prefix", label: "Prefix" },
  { id: "profiles", label: "Profiles" },
];

export function GameDetailTabs({
  selectedKey,
  onSelectionChange,
  setupPanel,
  prefixPanel,
  profilesPanel,
  gameKey,
  motionEpoch,
}: GameDetailTabsProps) {
  const panel =
    selectedKey === "setup" ? setupPanel : selectedKey === "prefix" ? prefixPanel : profilesPanel;

  return (
    <div className="w-full min-w-0 space-y-3">
      <div className="rounded-xl border border-border bg-surface/90 p-1 shadow-sm">
        <Segment
          aria-label="Game settings"
          variant="ghost"
          size="sm"
          selectedKey={selectedKey}
          onSelectionChange={(k) => onSelectionChange(toTabKey(k))}
          className="flex w-full min-w-0 gap-0"
        >
          {TABS.map((tab, i) => (
            <Segment.Item key={tab.id} id={tab.id} className="min-w-0 flex-1 basis-0 justify-center">
              {i > 0 ? <Segment.Separator /> : null}
              {tab.label}
            </Segment.Item>
          ))}
        </Segment>
      </div>

      <motion.div
        key={`${gameKey}-${selectedKey}-${motionEpoch}`}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="space-y-4"
      >
        {panel}
      </motion.div>
    </div>
  );
}
