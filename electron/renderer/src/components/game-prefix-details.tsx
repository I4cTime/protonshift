"use client";

import { HardDrive, Calendar, Box, Trash2 } from "lucide-react";
import {
  Button,
  Description,
  Separator,
  AlertDialog,
  Spinner,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { PrefixInfo } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GamePrefixDetailsProps {
  prefixData: PrefixInfo;
  appId: string;
  isSteam: boolean;
  prefixPath: string | null;
  deletePrefixMut: {
    mutateAsync: (args: { appId: string; prefixPath?: string }) => Promise<unknown>;
    isPending: boolean;
  };
}

export function GamePrefixDetails({
  prefixData,
  appId,
  isSteam,
  prefixPath,
  deletePrefixMut,
}: GamePrefixDetailsProps) {
  async function handleDelete() {
    try {
      await deletePrefixMut.mutateAsync({
        appId,
        prefixPath: !isSteam && prefixPath ? prefixPath : undefined,
      });
      appShowToast("Prefix deleted");
    } catch {
      appShowToast("Failed to delete prefix", "error");
    }
  }

  const stats = [
    { icon: HardDrive, color: "text-neon-cyan", label: "Size", value: prefixData.size_human },
    prefixData.created
      ? { icon: Calendar, color: "text-neon-blue", label: "Created", value: new Date(prefixData.created).toLocaleDateString() }
      : null,
    prefixData.dxvk_version
      ? { icon: Box, color: "text-neon-purple", label: "DXVK", value: prefixData.dxvk_version }
      : null,
    prefixData.vkd3d_version
      ? { icon: Box, color: "text-neon-pink", label: "VKD3D", value: prefixData.vkd3d_version }
      : null,
  ].filter(Boolean) as { icon: typeof HardDrive; color: string; label: string; value: string }[];

  return (
    <GlowCard className="p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
            <HardDrive className="size-4 text-neon-cyan" />
            Prefix Details
          </label>
          <Description>
            Wine prefix info: disk size, creation date, DXVK and VKD3D-Proton versions detected.
          </Description>
        </div>
        <AlertDialog>
          <Button variant="danger-soft" size="sm" className="gap-1.5">
            <Trash2 className="size-3" />
            Delete Prefix
          </Button>
          <AlertDialog.Backdrop>
            <AlertDialog.Container>
              <AlertDialog.Dialog className="sm:max-w-[400px]">
                <AlertDialog.CloseTrigger />
                <AlertDialog.Header>
                  <AlertDialog.Icon status="danger" />
                  <AlertDialog.Heading>Delete Wine Prefix?</AlertDialog.Heading>
                </AlertDialog.Header>
                <AlertDialog.Body>
                  <p>This will permanently remove the Wine prefix and all its contents including save data, configuration, and installed components. This cannot be undone.</p>
                </AlertDialog.Body>
                <AlertDialog.Footer>
                  <Button slot="close" variant="tertiary">Cancel</Button>
                  <Button
                    variant="danger"
                    onPress={handleDelete}
                    isDisabled={deletePrefixMut.isPending}
                  >
                    {deletePrefixMut.isPending ? <Spinner size="sm" /> : "Yes, Delete"}
                  </Button>
                </AlertDialog.Footer>
              </AlertDialog.Dialog>
            </AlertDialog.Container>
          </AlertDialog.Backdrop>
        </AlertDialog>
      </div>

      <Separator />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {stats.map((stat) => {
          const StatIcon = stat.icon;
          return (
            <div key={stat.label} className="flex items-center gap-2 p-3 rounded-lg bg-surface-deep border border-separator">
              <StatIcon className={`size-4 shrink-0 ${stat.color}`} />
              <div>
                <p className="text-xs text-text-muted">{stat.label}</p>
                <p className="text-sm font-medium text-text-primary">{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>
    </GlowCard>
  );
}
