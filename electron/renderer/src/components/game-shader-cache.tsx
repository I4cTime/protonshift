"use client";

import { Sparkles, Trash2 } from "lucide-react";
import {
  Button,
  Chip,
  Description,
  AlertDialog,
  Spinner,
  Meter,
  Label,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
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

const MAX_CACHE_BYTES = 5 * 1024 * 1024 * 1024; // 5 GB for scale

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
    <GlowCard className="p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
            <Sparkles className="size-4 text-neon-blue" />
            Shader Cache
          </label>
          <Description>
            Pre-compiled shader pipelines for this game. Clearing forces recompilation on next launch.
          </Description>
        </div>
        <div className="flex items-center gap-3">
          <Chip size="sm" variant="secondary">{shaderData.size_human}</Chip>
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
                    <AlertDialog.Heading>Clear Shader Cache?</AlertDialog.Heading>
                  </AlertDialog.Header>
                  <AlertDialog.Body>
                    <p>This will delete all cached shaders for this game. The game will need to recompile shaders on next launch, which may cause temporary stuttering.</p>
                  </AlertDialog.Body>
                  <AlertDialog.Footer>
                    <Button slot="close" variant="tertiary">Cancel</Button>
                    <Button
                      variant="danger"
                      onPress={handleClear}
                      isDisabled={clearShaderMut.isPending}
                    >
                      {clearShaderMut.isPending ? <Spinner size="sm" /> : "Clear Cache"}
                    </Button>
                  </AlertDialog.Footer>
                </AlertDialog.Dialog>
              </AlertDialog.Container>
            </AlertDialog.Backdrop>
          </AlertDialog>
        </div>
      </div>

      <Meter aria-label="Shader cache size" value={meterValue} className="w-full" color={meterValue > 80 ? "warning" : "accent"}>
        <Label className="sr-only">Cache size</Label>
        <Meter.Track>
          <Meter.Fill />
        </Meter.Track>
      </Meter>
    </GlowCard>
  );
}
