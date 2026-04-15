"use client";

import { Cog, RefreshCw, MonitorPlay, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Switch,
  Label,
  Description,
  Spinner,
  Fieldset,
  Separator,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { HeroicGameConfig, HeroicTogglesPayload } from "@/lib/api";
import { useSetHeroicToggles } from "@/hooks/use-games";
import { appShowToast } from "@/lib/app-toast";

interface HeroicTogglesProps {
  appId: string;
  config: HeroicGameConfig;
}

interface ToggleGroupDef {
  title: string;
  icon: LucideIcon;
  toggles: {
    key: keyof HeroicTogglesPayload;
    label: string;
    description: string;
  }[];
}

const TOGGLE_GROUPS: ToggleGroupDef[] = [
  {
    title: "Synchronization",
    icon: RefreshCw,
    toggles: [
      { key: "enable_esync", label: "Esync", description: "Eventfd-based synchronization for better CPU performance in multi-threaded games" },
      { key: "enable_fsync", label: "Fsync", description: "Futex-based synchronization — faster than Esync but requires kernel 5.16+" },
    ],
  },
  {
    title: "Rendering",
    icon: MonitorPlay,
    toggles: [
      { key: "auto_install_dxvk", label: "DXVK", description: "Auto-install DXVK for DirectX 9/10/11 to Vulkan translation" },
      { key: "auto_install_vkd3d", label: "VKD3D", description: "Auto-install VKD3D-Proton for DirectX 12 to Vulkan translation" },
      { key: "show_mangohud", label: "MangoHud", description: "Show the MangoHud performance overlay (FPS, frametime, CPU/GPU stats)" },
    ],
  },
  {
    title: "Performance",
    icon: Zap,
    toggles: [
      { key: "use_game_mode", label: "GameMode", description: "Enable Feral GameMode for CPU governor, scheduler, and GPU clock optimizations" },
      { key: "nvidia_prime", label: "NVIDIA Prime", description: "Use NVIDIA Prime render offload for hybrid GPU laptops (Intel/AMD + NVIDIA)" },
    ],
  },
];

export function HeroicToggles({ appId, config }: HeroicTogglesProps) {
  const setToggles = useSetHeroicToggles();

  async function handleToggle(key: keyof HeroicTogglesPayload, currentValue: boolean) {
    const label = TOGGLE_GROUPS
      .flatMap((g) => g.toggles)
      .find((t) => t.key === key)?.label ?? key;
    try {
      await setToggles.mutateAsync({
        appId,
        toggles: { [key]: !currentValue },
      });
      appShowToast(`${label} ${!currentValue ? "enabled" : "disabled"}`);
    } catch {
      appShowToast("Failed to update toggle", "error");
    }
  }

  return (
    <GlowCard className="p-5 space-y-4">
      <Fieldset>
        <Fieldset.Legend className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
          <Cog className="size-4 text-neon-cyan" />
          Heroic Settings
        </Fieldset.Legend>
        <Description>
          Heroic-managed Wine prefix toggles. Changes are saved immediately.
        </Description>
      </Fieldset>

      {TOGGLE_GROUPS.map((group, groupIdx) => {
        const GroupIcon = group.icon;
        return (
          <div key={group.title}>
            {groupIdx > 0 && <Separator className="mb-4" />}
            <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted mb-3">
              <GroupIcon className="size-3.5" />
              {group.title}
            </label>
            <div className="flex flex-col gap-2">
              {group.toggles.map((toggle) => {
                const value = config[toggle.key as keyof HeroicGameConfig] as boolean;
                return (
                  <Switch
                    key={toggle.key}
                    isSelected={value}
                    onChange={() => handleToggle(toggle.key, value)}
                    isDisabled={setToggles.isPending}
                    className="w-full flex-row-reverse justify-between gap-3 p-3 rounded-lg border border-separator hover:border-border transition-colors data-[selected]:border-neon-cyan/40 data-[selected]:bg-neon-cyan/5"
                  >
                    <Switch.Control className="data-[selected]:bg-neon-cyan/30">
                      <Switch.Thumb className="data-[selected]:bg-neon-cyan" />
                    </Switch.Control>
                    <Switch.Content>
                      <Label className="text-sm font-medium cursor-pointer flex items-center gap-1.5">
                        {setToggles.isPending && <Spinner size="sm" className="inline" />}
                        {toggle.label}
                      </Label>
                      <Description className="text-xs text-text-muted">
                        {toggle.description}
                      </Description>
                    </Switch.Content>
                  </Switch>
                );
              })}
            </div>
          </div>
        );
      })}
    </GlowCard>
  );
}
