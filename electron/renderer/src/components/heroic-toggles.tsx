"use client";

import { Cog, RefreshCw, MonitorPlay, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Switch,
  Label,
  Spinner,
  Text,
} from "@heroui/react";
import { ItemCard, ItemCardGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
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
      {
        key: "enable_esync",
        label: "Esync",
        description:
          "Eventfd-based synchronization for better CPU performance in multi-threaded games.",
      },
      {
        key: "enable_fsync",
        label: "Fsync",
        description:
          "Futex-based synchronization — faster than Esync but requires kernel 5.16+.",
      },
    ],
  },
  {
    title: "Rendering",
    icon: MonitorPlay,
    toggles: [
      {
        key: "auto_install_dxvk",
        label: "DXVK",
        description: "Auto-install DXVK for DirectX 9/10/11 → Vulkan translation.",
      },
      {
        key: "auto_install_vkd3d",
        label: "VKD3D",
        description: "Auto-install VKD3D-Proton for DirectX 12 → Vulkan translation.",
      },
      {
        key: "show_mangohud",
        label: "MangoHud",
        description: "Show the MangoHud performance overlay (FPS, frametime, CPU/GPU stats).",
      },
    ],
  },
  {
    title: "Performance",
    icon: Zap,
    toggles: [
      {
        key: "use_game_mode",
        label: "GameMode",
        description: "Enable Feral GameMode CPU governor, scheduler, and GPU clock optimizations.",
      },
      {
        key: "nvidia_prime",
        label: "NVIDIA Prime",
        description: "Use NVIDIA Prime render offload for hybrid GPU laptops (Intel/AMD + NVIDIA).",
      },
    ],
  },
];

export function HeroicToggles({ appId, config }: HeroicTogglesProps) {
  const setToggles = useSetHeroicToggles();

  const enabledCount = TOGGLE_GROUPS.flatMap((g) => g.toggles).filter(
    (t) => Boolean(config[t.key as keyof HeroicGameConfig]),
  ).length;

  async function handleToggle(key: keyof HeroicTogglesPayload, currentValue: boolean) {
    const label =
      TOGGLE_GROUPS.flatMap((g) => g.toggles).find((t) => t.key === key)?.label ?? key;
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
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Cog className="text-neon-cyan size-4 shrink-0" aria-hidden />
          Heroic settings
          <span
            className="text-muted text-[10px] font-normal normal-case"
            aria-label={`${enabledCount} enabled`}
          >
            ({enabledCount} on)
          </span>
        </Widget.Title>
        <InfoHint label="About Heroic settings">
          Heroic-managed Wine prefix toggles. Changes save immediately.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-4">
        {TOGGLE_GROUPS.map((group) => {
          const GroupIcon = group.icon;
          return (
            <section key={group.title} className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <GroupIcon className="text-neon-cyan size-3.5 shrink-0" aria-hidden />
                <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                  {group.title}
                </Label>
              </div>
              <ItemCardGroup
                variant="outline"
                layout="list"
                className="overflow-hidden rounded-xl"
              >
                {group.toggles.map((toggle) => {
                  const value = Boolean(config[toggle.key as keyof HeroicGameConfig]);
                  return (
                    <ItemCard key={toggle.key} className="py-2">
                      <ItemCard.Content className="min-w-0 gap-0.5">
                        <ItemCard.Title className="text-foreground text-sm font-medium">
                          {toggle.label}
                        </ItemCard.Title>
                        <Text.Paragraph
                          size="xs"
                          color="muted"
                          className="leading-snug"
                        >
                          {toggle.description}
                        </Text.Paragraph>
                      </ItemCard.Content>
                      <ItemCard.Action>
                        <div className="flex items-center gap-2">
                          {setToggles.isPending && <Spinner size="sm" />}
                          <Switch
                            isSelected={value}
                            onChange={() => handleToggle(toggle.key, value)}
                            isDisabled={setToggles.isPending}
                            aria-label={toggle.label}
                          >
                            <Switch.Control>
                              <Switch.Thumb />
                            </Switch.Control>
                          </Switch>
                        </div>
                      </ItemCard.Action>
                    </ItemCard>
                  );
                })}
              </ItemCardGroup>
            </section>
          );
        })}
      </Widget.Content>
    </Widget>
  );
}
