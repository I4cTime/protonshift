"use client";

import { Sparkles, Trash2 } from "lucide-react";
import {
  Button,
  Chip,
  AlertDialog,
  Description,
  Spinner,
  Meter,
  Label,
  Text,
} from "@heroui/react";
import { Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import type { ShaderCacheInfo } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GameShaderCacheProps {
  shaderData: ShaderCacheInfo;
  appId: string;
  clearShaderMut: {
    mutateAsync: (appId: string) => Promise<unknown>;
    isPending: boolean;
  };
}

const MAX_CACHE_BYTES = 5 * 1024 * 1024 * 1024;

export function GameShaderCache({
  shaderData,
  appId,
  clearShaderMut,
}: GameShaderCacheProps) {
  async function handleClear() {
    try {
      await clearShaderMut.mutateAsync(appId);
      appShowToast("Shader cache cleared");
    } catch {
      appShowToast("Failed to clear shader cache", "error");
    }
  }

  const meterValue = Math.min((shaderData.size_bytes / MAX_CACHE_BYTES) * 100, 100);

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Sparkles className="text-neon-blue size-4 shrink-0" aria-hidden />
          Shader cache
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {shaderData.size_human}
          </Chip>
        </Widget.Title>
        <div className="flex shrink-0 items-center gap-1">
          <InfoHint label="About shader cache">
            Pre-compiled pipelines for this Steam title. Clearing forces recompilation on next launch
            (possible stutter).
          </InfoHint>
          <AlertDialog>
            <Button variant="danger-soft" size="sm" className="gap-1.5">
              <Trash2 className="size-3" />
              Clear
            </Button>
            <AlertDialog.Backdrop>
              <AlertDialog.Container>
                <AlertDialog.Dialog className="sm:max-w-[400px]">
                  <AlertDialog.CloseTrigger />
                  <AlertDialog.Header>
                    <AlertDialog.Icon status="warning" />
                    <AlertDialog.Heading>Clear shader cache?</AlertDialog.Heading>
                  </AlertDialog.Header>
                  <AlertDialog.Body>
                    <Description className="text-sm">
                      Deletes cached shaders for this game. The next launch will recompile shaders,
                      which may cause temporary stutter.
                    </Description>
                  </AlertDialog.Body>
                  <AlertDialog.Footer>
                    <Button slot="close" variant="tertiary">
                      Cancel
                    </Button>
                    <Button
                      variant="danger"
                      onPress={handleClear}
                      isDisabled={clearShaderMut.isPending}
                    >
                      {clearShaderMut.isPending ? <Spinner size="sm" /> : "Clear cache"}
                    </Button>
                  </AlertDialog.Footer>
                </AlertDialog.Dialog>
              </AlertDialog.Container>
            </AlertDialog.Backdrop>
          </AlertDialog>
        </div>
      </Widget.Header>
      <Widget.Content className="space-y-2">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <Label
            id="shader-cache-meter-label"
            className="text-muted text-[10px] font-semibold uppercase tracking-wide"
          >
            Relative size
          </Label>
          <Text.Paragraph
            size="xs"
            color="muted"
            className="text-[10px] tabular-nums"
          >
            cap ref. 5 GB
          </Text.Paragraph>
        </div>
        <Meter
          aria-labelledby="shader-cache-meter-label"
          value={meterValue}
          className="w-full"
          color={meterValue > 80 ? "warning" : "accent"}
        >
          <Meter.Track>
            <Meter.Fill />
          </Meter.Track>
        </Meter>
      </Widget.Content>
    </Widget>
  );
}
