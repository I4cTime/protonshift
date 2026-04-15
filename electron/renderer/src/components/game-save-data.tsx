"use client";

import { Archive, RotateCcw } from "lucide-react";
import {
  Button,
  Chip,
  Description,
  Disclosure,
  Separator,
  Spinner,
  Tooltip,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { SaveLocationData, BackupInfoData } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GameSaveDataProps {
  savesData: SaveLocationData[];
  backupsData: BackupInfoData[] | undefined;
  appId: string;
  backupSavesMut: {
    mutateAsync: (args: { appId: string; paths: string[] }) => Promise<unknown>;
    isPending: boolean;
  };
  restoreSavesMut: {
    mutateAsync: (args: { appId: string; backupPath: string; targetDir: string }) => Promise<unknown>;
    isPending: boolean;
  };
}

export function GameSaveData({
  savesData,
  backupsData,
  appId,
  backupSavesMut,
  restoreSavesMut,
}: GameSaveDataProps) {
  async function handleBackupAll() {
    try {
      await backupSavesMut.mutateAsync({
        appId,
        paths: savesData.map((s) => s.path),
      });
      appShowToast("Backup created");
    } catch {
      appShowToast("Failed to create backup", "error");
    }
  }

  async function handleRestore(backupPath: string) {
    if (!savesData.length) return;
    try {
      await restoreSavesMut.mutateAsync({
        appId,
        backupPath,
        targetDir: savesData[0].path,
      });
      appShowToast("Backup restored");
    } catch {
      appShowToast("Failed to restore", "error");
    }
  }

  return (
    <GlowCard className="p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
            <Archive className="size-4 text-neon-blue" />
            Save Data
          </label>
          <Description>
            Detected save game locations and backup history. Backup creates a timestamped .tar.gz archive.
          </Description>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onPress={handleBackupAll}
          isDisabled={backupSavesMut.isPending}
          className="gap-1.5"
        >
          {backupSavesMut.isPending ? <Spinner size="sm" /> : <Archive className="size-3" />}
          Backup All
        </Button>
      </div>

      <div className="space-y-2">
        {savesData.map((save) => (
          <div key={save.path} className="flex items-center justify-between p-2.5 rounded-lg bg-surface-deep border border-separator">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-text-primary">{save.label}</p>
              <p className="text-xs text-text-muted font-mono truncate">{save.path}</p>
            </div>
            <Chip size="sm" variant="secondary" className="ml-2 shrink-0">{save.size_human}</Chip>
          </div>
        ))}
      </div>

      {backupsData && backupsData.length > 0 && (
        <>
          <Separator />
          <Disclosure defaultExpanded={false}>
            <Disclosure.Heading>
              <Button slot="trigger" variant="ghost" size="sm" className="gap-1.5 text-xs">
                <Archive className="size-3" />
                Backups ({backupsData.length})
                <Disclosure.Indicator />
              </Button>
            </Disclosure.Heading>
            <Disclosure.Content>
              <Disclosure.Body className="pt-2">
                <div className="space-y-1">
                  {backupsData.slice(0, 5).map((backup) => (
                    <div key={backup.path} className="flex items-center justify-between text-xs p-2 rounded-lg bg-surface-deep border border-separator">
                      <span className="text-text-secondary">{backup.filename}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-text-muted">{backup.size_human}</span>
                        <Tooltip delay={0}>
                          <Button
                            isIconOnly
                            variant="ghost"
                            size="sm"
                            onPress={() => handleRestore(backup.path)}
                            aria-label="Restore backup"
                            isDisabled={restoreSavesMut.isPending}
                          >
                            {restoreSavesMut.isPending ? <Spinner size="sm" /> : <RotateCcw className="size-3" />}
                          </Button>
                          <Tooltip.Content>Restore this backup</Tooltip.Content>
                        </Tooltip>
                      </div>
                    </div>
                  ))}
                </div>
              </Disclosure.Body>
            </Disclosure.Content>
          </Disclosure>
        </>
      )}
    </GlowCard>
  );
}
