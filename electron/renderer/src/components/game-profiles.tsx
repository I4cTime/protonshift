"use client";

import { Bookmark, Trash2 } from "lucide-react";
import {
  Button,
  Chip,
  Description,
  Disclosure,
  Input,
  Spinner,
  TextField,
  Label,
} from "@heroui/react";
import { GlowCard } from "./glow-card";
import type { ProfileData } from "@/lib/api";
import { api } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";
import { useState } from "react";

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
        } catch { /* ignore */ }
      }

      if (profile.power_profile) {
        try {
          await api.setPowerProfile(profile.power_profile);
          applied.push("power profile");
        } catch { /* ignore */ }
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

  return (
    <GlowCard className="p-5 space-y-3">
      <div>
        <label className="flex items-center gap-1.5 text-sm font-medium text-text-secondary">
          <Bookmark className="size-4 text-neon-cyan" />
          Profiles
        </label>
        <Description>
          Save or load full launch configurations: launch options, compat tool, env vars, and power profile.
        </Description>
      </div>

      <Disclosure isExpanded={isExpanded} onExpandedChange={(v) => {
        setIsExpanded(v);
        if (v && !profileName) setProfileName(gameName);
      }}>
        <Disclosure.Heading>
          <Button slot="trigger" variant="ghost" size="sm" className="gap-1.5">
            <Bookmark className="size-3" />
            Save Current
            <Disclosure.Indicator />
          </Button>
        </Disclosure.Heading>
        <Disclosure.Content>
          <Disclosure.Body className="pt-3">
            <div className="flex items-end gap-2">
              <TextField
                value={profileName}
                onChange={setProfileName}
                className="flex-1"
              >
                <Label>Profile name</Label>
                <Input
                  placeholder="Enter a name..."
                  variant="secondary"
                  onKeyDown={(e) => e.key === "Enter" && handleSaveProfile()}
                />
              </TextField>
              <Button
                size="sm"
                onPress={handleSaveProfile}
                isDisabled={!profileName.trim() || saveProfileMut.isPending}
              >
                {saveProfileMut.isPending ? <Spinner size="sm" /> : "Save"}
              </Button>
            </div>
          </Disclosure.Body>
        </Disclosure.Content>
      </Disclosure>

      {profileNames && profileNames.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {profileNames.map((name) => {
            const isMatch =
              name.toLowerCase() === gameName.toLowerCase() ||
              name.toLowerCase() === gameAppId.toLowerCase();
            return (
              <div key={name} className="flex items-center gap-0.5">
                <Chip
                  color={isMatch ? "accent" : "default"}
                  variant={isMatch ? "primary" : "secondary"}
                  className="cursor-pointer rounded-r-none"
                  onClick={() => handleLoadProfile(name)}
                >
                  {isMatch && <Bookmark className="size-3" />}
                  {name}
                </Chip>
                <Button
                  isIconOnly
                  variant="ghost"
                  size="sm"
                  onPress={() => handleDeleteProfile(name)}
                  aria-label={`Delete profile ${name}`}
                  className="rounded-l-none border-l-0 h-auto min-w-6"
                >
                  <Trash2 className="size-3" />
                </Button>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-xs text-text-muted">No saved profiles yet.</p>
      )}
    </GlowCard>
  );
}
