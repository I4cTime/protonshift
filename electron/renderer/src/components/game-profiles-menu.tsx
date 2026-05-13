"use client";

import { useState } from "react";
import { ChevronDown, Bookmark } from "lucide-react";
import {
  Button,
  Dropdown,
  Modal,
  TextField,
  Input,
  Label,
  Spinner,
  useOverlayState,
} from "@heroui/react";
import type { ProfileData } from "@/lib/api";
import { api } from "@/lib/api";
import { appShowToast } from "@/lib/app-toast";

const SAVE_ACTION = "__save_profile__";

export interface GameProfilesMenuProps {
  gameName: string;
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
}

export function GameProfilesMenu({
  gameName,
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
}: GameProfilesMenuProps) {
  const saveModal = useOverlayState();
  const [profileName, setProfileName] = useState("");

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
      saveModal.close();
    } catch {
      appShowToast("Failed to save profile", "error");
    }
  }

  function openSaveModal() {
    setProfileName(gameName);
    saveModal.open();
  }

  return (
    <>
      <Dropdown>
        <Button variant="outline" size="sm" className="gap-1.5 min-w-0">
          <Bookmark className="size-4 shrink-0" aria-hidden />
          Profiles
          <ChevronDown className="size-3.5 shrink-0 opacity-70" aria-hidden />
        </Button>
        <Dropdown.Popover placement="bottom start" className="min-w-[12rem]">
          <Dropdown.Menu
            aria-label="Profiles"
            onAction={(key) => {
              const id = String(key);
              if (id === SAVE_ACTION) {
                openSaveModal();
                return;
              }
              void handleLoadProfile(id);
            }}
          >
            {profileNames?.map((name) => (
              <Dropdown.Item key={name} id={name} textValue={name}>
                {name}
              </Dropdown.Item>
            ))}
            <Dropdown.Item id={SAVE_ACTION} textValue="Save current configuration">
              Save current…
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown.Popover>
      </Dropdown>

      <Modal state={saveModal}>
        <Modal.Backdrop>
          <Modal.Container className="max-w-md">
            <Modal.Dialog>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Heading>Save profile</Modal.Heading>
              </Modal.Header>
              <Modal.Body className="space-y-3">
                <TextField value={profileName} onChange={setProfileName}>
                  <Label>Profile name</Label>
                  <Input
                    placeholder="Enter a name…"
                    variant="secondary"
                    onKeyDown={(e) => e.key === "Enter" && void handleSaveProfile()}
                  />
                </TextField>
              </Modal.Body>
              <Modal.Footer className="gap-2">
                <Button variant="tertiary" onPress={() => saveModal.close()}>
                  Cancel
                </Button>
                <Button
                  onPress={() => void handleSaveProfile()}
                  isDisabled={!profileName.trim() || saveProfileMut.isPending}
                >
                  {saveProfileMut.isPending ? <Spinner size="sm" /> : "Save"}
                </Button>
              </Modal.Footer>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </>
  );
}
