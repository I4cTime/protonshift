"use client";

import { Archive, FolderOpen, RotateCcw } from "lucide-react";
import {
  Button,
  Chip,
  Disclosure,
  Label,
  Separator,
  Spinner,
  Text,
  Tooltip,
} from "@heroui/react";
import { ItemCard, ItemCardGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
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
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Archive className="text-neon-blue size-4 shrink-0" aria-hidden />
          Save data
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {savesData.length} location{savesData.length === 1 ? "" : "s"}
          </Chip>
        </Widget.Title>
        <div className="flex shrink-0 items-center gap-1">
          <InfoHint label="About save data">
            Detected save locations and backup history. Backup creates a timestamped archive
            (.tar.gz).
          </InfoHint>
          <Button
            variant="outline"
            size="sm"
            onPress={handleBackupAll}
            isDisabled={backupSavesMut.isPending}
            className="gap-1.5"
          >
            {backupSavesMut.isPending ? <Spinner size="sm" /> : <Archive className="size-3" />}
            Backup all
          </Button>
        </div>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        <Text.Paragraph size="xs" color="muted">
          Paths below are scanned from the prefix. Backup before risky changes.
        </Text.Paragraph>

        <ItemCardGroup variant="outline" layout="list" className="overflow-hidden rounded-xl">
          {savesData.map((save) => (
            <ItemCard key={save.path} className="py-2">
              <ItemCard.Icon>
                <FolderOpen className="text-muted size-4" aria-hidden />
              </ItemCard.Icon>
              <ItemCard.Content className="min-w-0">
                <ItemCard.Title className="truncate text-sm">{save.label}</ItemCard.Title>
                <ItemCard.Description className="min-w-0">
                  <Text.Code
                    className="text-muted block truncate text-[11px]"
                    title={save.path}
                  >
                    {save.path}
                  </Text.Code>
                </ItemCard.Description>
              </ItemCard.Content>
              <ItemCard.Action>
                <Chip size="sm" variant="secondary" className="shrink-0 text-[10px]">
                  {save.size_human}
                </Chip>
              </ItemCard.Action>
            </ItemCard>
          ))}
        </ItemCardGroup>

        {backupsData && backupsData.length > 0 && (
          <>
            <Separator />
            <Disclosure defaultExpanded={false}>
              <Disclosure.Heading>
                <Button slot="trigger" variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs">
                  <Archive className="size-3.5 shrink-0" />
                  Backups
                  <Chip size="sm" variant="secondary" className="text-[10px]">
                    {backupsData.length}
                  </Chip>
                  <Disclosure.Indicator />
                </Button>
              </Disclosure.Heading>
              <Disclosure.Content>
                <Disclosure.Body className="space-y-2 pt-2">
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Recent archives
                  </Label>
                  <ItemCardGroup variant="outline" layout="list" className="overflow-hidden rounded-xl">
                    {backupsData.slice(0, 5).map((backup) => (
                      <ItemCard key={backup.path} className="py-2">
                        <ItemCard.Icon>
                          <Archive className="text-muted size-4" aria-hidden />
                        </ItemCard.Icon>
                        <ItemCard.Content className="min-w-0">
                          <ItemCard.Title className="truncate text-xs font-medium">
                            {backup.filename}
                          </ItemCard.Title>
                          <ItemCard.Description className="text-muted text-[10px]">
                            {backup.size_human}
                          </ItemCard.Description>
                        </ItemCard.Content>
                        <ItemCard.Action>
                          <Tooltip delay={0}>
                            <Button
                              isIconOnly
                              variant="outline"
                              size="sm"
                              onPress={() => handleRestore(backup.path)}
                              aria-label="Restore this backup"
                              isDisabled={restoreSavesMut.isPending}
                            >
                              {restoreSavesMut.isPending ? (
                                <Spinner size="sm" />
                              ) : (
                                <RotateCcw className="size-3.5" />
                              )}
                            </Button>
                            <Tooltip.Content>Restore into primary save folder</Tooltip.Content>
                          </Tooltip>
                        </ItemCard.Action>
                      </ItemCard>
                    ))}
                  </ItemCardGroup>
                </Disclosure.Body>
              </Disclosure.Content>
            </Disclosure>
          </>
        )}
      </Widget.Content>
    </Widget>
  );
}
