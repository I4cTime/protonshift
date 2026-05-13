"use client";

import { useState } from "react";
import { Bookmark, Save, Trash2, Sparkles } from "lucide-react";
import {
  AlertDialog,
  Button,
  Chip,
  Description,
  Disclosure,
  Input,
  Label,
  Spinner,
  Text,
  TextField,
  Tooltip,
} from "@heroui/react";
import { EmptyState, ItemCard, ItemCardGroup, Widget } from "@heroui-pro/react";
import { InfoHint } from "./info-hint";
import type { ProfileData } from "@/lib/api";
import { api } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

interface GameProfilesProps {
  gameName: string;
  gameAppId: string;
  isSteam: boolean;
  isHeroic: boolean;
  launchOptions: string;
  selectedTool: string;
  selectedHeroicWine: string;
  profileNames: string[] | undefined;
  setLaunchOptions: (v: string) => void;
  setSelectedTool: (v: string) => void;
  setSelectedHeroicWine: (v: string) => void;
  saveProfileMut: { mutateAsync: (p: ProfileData) => Promise<unknown>; isPending: boolean };
  deleteProfileMut: { mutateAsync: (name: string) => Promise<unknown> };
}

export function GameProfiles({
  gameName,
  gameAppId,
  isSteam,
  isHeroic,
  launchOptions,
  selectedTool,
  selectedHeroicWine,
  profileNames,
  setLaunchOptions,
  setSelectedTool,
  setSelectedHeroicWine,
  saveProfileMut,
  deleteProfileMut,
}: GameProfilesProps) {
  const [profileName, setProfileName] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  async function handleSaveProfile() {
    if (!profileName.trim()) return;
    try {
      const [envVars, systemInfo] = await Promise.all([
        api.getEnvVars().catch(() => ({} as Record<string, string>)),
        api.getSystemInfo().catch(() => null),
      ]);
      const profile: ProfileData = {
        name: profileName.trim(),
        launch_options: launchOptions,
        compat_tool: isSteam ? selectedTool : selectedHeroicWine,
        env_vars: envVars,
        power_profile: systemInfo?.current_power_profile ?? "",
      };
      await saveProfileMut.mutateAsync(profile);
      appShowToast(`Profile "${profileName}" saved`);
      setProfileName("");
      setIsExpanded(false);
    } catch {
      appShowToast("Failed to save profile", "error");
    }
  }

  async function handleLoadProfile(name: string) {
    try {
      const profile = await api.getProfile(name);
      setLaunchOptions(profile.launch_options);
      if (isSteam && profile.compat_tool) setSelectedTool(profile.compat_tool);
      if (isHeroic && profile.compat_tool) setSelectedHeroicWine(profile.compat_tool);

      const applied: string[] = ["launch options"];
      if (profile.compat_tool) applied.push("compat tool");

      if (profile.env_vars && Object.keys(profile.env_vars).length > 0) {
        try {
          await api.setEnvVars(profile.env_vars);
          applied.push("env vars");
        } catch {
          /* ignore */
        }
      }

      if (profile.power_profile) {
        try {
          await api.setPowerProfile(profile.power_profile);
          applied.push("power profile");
        } catch {
          /* ignore */
        }
      }

      appShowToast(`Profile "${name}" loaded (${applied.join(", ")})`);
    } catch {
      appShowToast("Failed to load profile", "error");
    }
  }

  async function handleDeleteProfile(name: string) {
    try {
      await deleteProfileMut.mutateAsync(name);
      appShowToast(`Profile "${name}" deleted`);
    } catch {
      appShowToast("Failed to delete profile", "error");
    }
  }

  const profileCount = profileNames?.length ?? 0;

  return (
    <Widget>
      <Widget.Header>
        <Widget.Title className="flex flex-wrap items-center gap-1.5">
          <Bookmark className="text-neon-cyan size-4 shrink-0" aria-hidden />
          Profiles
          <Chip size="sm" variant="secondary" className="text-[10px]">
            {profileCount}
          </Chip>
        </Widget.Title>
        <InfoHint label="About profiles">
          Save or load full launch configurations: launch options, compat tool, env vars, and
          power profile.
        </InfoHint>
      </Widget.Header>
      <Widget.Content className="space-y-3">
        <Disclosure
          isExpanded={isExpanded}
          onExpandedChange={(v) => {
            setIsExpanded(v);
            if (v && !profileName) setProfileName(gameName);
          }}
        >
          <Disclosure.Heading>
            <Button
              slot="trigger"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 px-2 text-xs"
            >
              <Save className="size-3.5 shrink-0" aria-hidden />
              Save current configuration
              <Disclosure.Indicator />
            </Button>
          </Disclosure.Heading>
          <Disclosure.Content>
            <Disclosure.Body className="pt-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <TextField
                  value={profileName}
                  onChange={setProfileName}
                  className="min-w-0 flex-1"
                >
                  <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
                    Profile name
                  </Label>
                  <Input
                    placeholder="e.g. Performance"
                    variant="secondary"
                    onKeyDown={(e) => e.key === "Enter" && void handleSaveProfile()}
                  />
                </TextField>
                <Button
                  size="sm"
                  onPress={() => void handleSaveProfile()}
                  isDisabled={!profileName.trim() || saveProfileMut.isPending}
                  className="shrink-0 gap-1.5 sm:self-end"
                >
                  {saveProfileMut.isPending ? (
                    <Spinner size="sm" />
                  ) : (
                    <Save className="size-3.5 shrink-0" aria-hidden />
                  )}
                  Save profile
                </Button>
              </div>
              <Text.Paragraph size="xs" color="muted" className="mt-2">
                Snapshots launch options, compat tool, environment variables, and the active
                power profile.
              </Text.Paragraph>
            </Disclosure.Body>
          </Disclosure.Content>
        </Disclosure>

        {profileNames && profileNames.length > 0 ? (
          <div className="space-y-1.5">
            <Label className="text-muted text-[10px] font-semibold uppercase tracking-wide">
              Saved profiles
            </Label>
            <ItemCardGroup
              variant="outline"
              layout="list"
              className="overflow-hidden rounded-xl"
            >
              {profileNames.map((name) => {
                const isMatch =
                  name.toLowerCase() === gameName.toLowerCase() ||
                  name.toLowerCase() === gameAppId.toLowerCase();
                return (
                  <ItemCard key={name} className="py-2">
                    <ItemCard.Icon>
                      {isMatch ? (
                        <Sparkles className="text-neon-cyan size-4" aria-hidden />
                      ) : (
                        <Bookmark className="text-muted size-4" aria-hidden />
                      )}
                    </ItemCard.Icon>
                    <ItemCard.Content className="min-w-0 gap-0.5">
                      <ItemCard.Title className="flex min-w-0 flex-wrap items-center gap-1.5 text-sm">
                        <span className="truncate" title={name}>
                          {name}
                        </span>
                        {isMatch && (
                          <Chip size="sm" color="accent" variant="soft" className="text-[10px]">
                            Matches game
                          </Chip>
                        )}
                      </ItemCard.Title>
                      <Text.Paragraph
                        size="xs"
                        color="muted"
                        className="leading-snug"
                      >
                        Loads launch options, compat tool, env vars, and power profile.
                      </Text.Paragraph>
                    </ItemCard.Content>
                    <ItemCard.Action>
                      <div className="flex shrink-0 items-center gap-1.5">
                        <Tooltip delay={0}>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-8 px-2 text-xs"
                            onPress={() => void handleLoadProfile(name)}
                          >
                            Load
                          </Button>
                          <Tooltip.Content>Apply this profile to the game</Tooltip.Content>
                        </Tooltip>
                        <AlertDialog>
                          <Tooltip delay={0}>
                            <Button
                              isIconOnly
                              variant="danger-soft"
                              size="sm"
                              aria-label={`Delete profile ${name}`}
                              className="h-8 w-8 min-w-8"
                            >
                              <Trash2 className="size-3.5" />
                            </Button>
                            <Tooltip.Content>Delete profile</Tooltip.Content>
                          </Tooltip>
                          <AlertDialog.Backdrop>
                            <AlertDialog.Container>
                              <AlertDialog.Dialog className="sm:max-w-[400px]">
                                <AlertDialog.CloseTrigger />
                                <AlertDialog.Header>
                                  <AlertDialog.Icon status="warning" />
                                  <AlertDialog.Heading>Delete profile?</AlertDialog.Heading>
                                </AlertDialog.Header>
                                <AlertDialog.Body>
                                  <Description className="text-sm">
                                    Permanently remove the profile{" "}
                                    <code className="bg-surface-secondary text-foreground rounded px-1 py-0.5 font-mono text-[12px]">
                                      {name}
                                    </code>
                                    . This cannot be undone.
                                  </Description>
                                </AlertDialog.Body>
                                <AlertDialog.Footer>
                                  <Button slot="close" variant="tertiary">
                                    Cancel
                                  </Button>
                                  <Button
                                    variant="danger"
                                    onPress={() => void handleDeleteProfile(name)}
                                  >
                                    Delete
                                  </Button>
                                </AlertDialog.Footer>
                              </AlertDialog.Dialog>
                            </AlertDialog.Container>
                          </AlertDialog.Backdrop>
                        </AlertDialog>
                      </div>
                    </ItemCard.Action>
                  </ItemCard>
                );
              })}
            </ItemCardGroup>
          </div>
        ) : (
          <EmptyState className="border-border rounded-xl border border-dashed px-4 py-6">
            <EmptyState.Header>
              <EmptyState.Media variant="icon">
                <Bookmark className="text-neon-cyan size-7 opacity-80" aria-hidden />
              </EmptyState.Media>
              <EmptyState.Title>No saved profiles yet</EmptyState.Title>
              <EmptyState.Description className="text-center">
                Configure the game on the Setup tab, then save the current state as a reusable
                profile.
              </EmptyState.Description>
            </EmptyState.Header>
          </EmptyState>
        )}
      </Widget.Content>
    </Widget>
  );
}
