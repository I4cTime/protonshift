"""ProtonShift — GTK4 application."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# GI must be imported before other modules that use it
import gi  # noqa: I001

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from .env_vars import ENV_PRESETS, read_gaming_env, write_gaming_env  # noqa: E402
from .gpu import get_current_power_profile, get_gpu_info, get_power_profiles, set_power_profile  # noqa: E402
from .presets import LAUNCH_PRESETS, LaunchPreset  # noqa: E402
from .heroic import HeroicGame, discover_heroic_games  # noqa: E402
from .lutris import LutrisGame, discover_lutris_games  # noqa: E402
from .protontricks import COMMON_VERBS, is_protontricks_available, run_protontricks  # noqa: E402
from .steam import (  # noqa: E402
    SteamGame,
    discover_games,
    get_available_proton_tools,
    get_localconfig_path,
    is_steam_running,
)
from .vdf_config import get_compat_tool, get_launch_options, set_compat_tool, set_launch_options  # noqa: E402
from .profiles_storage import (  # noqa: E402
    ApplicationProfile,
    list_profiles,
    load_profile,
    save_profile as save_profile_to_storage,
)


class GameDetailView(Gtk.Box):
    """Detail panel for a selected game."""

    def __init__(
        self,
        game: SteamGame,
        config_path: Path | None,
        window: Adw.ApplicationWindow | None = None,
        steam_root: Path | None = None,
        **kwargs,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.game = game
        self.config_path = config_path
        self._window = window
        self._steam_root = steam_root

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)

        # App ID + Copy
        id_row = Adw.ActionRow(title="App ID", subtitle=game.app_id)
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text("Copy App ID")
        copy_btn.connect("clicked", self._on_copy_app_id)
        id_row.add_suffix(copy_btn)
        content.append(id_row)

        # Install path
        if game.install_path and game.install_path.exists():
            install_row = Adw.ActionRow(title="Install path", subtitle=str(game.install_path))
            open_install_btn = Gtk.Button(label="Open")
            open_install_btn.connect("clicked", self._on_open_install_path)
            install_row.add_suffix(open_install_btn)
            content.append(install_row)

        # Proton version
        if config_path and steam_root:
            tools = get_available_proton_tools(steam_root)
            proton_row = Adw.ComboRow(title="Proton version", subtitle="Force compatibility tool")
            proton_model = Gtk.StringList()
            for t in tools:
                label = "Default" if not t else t.replace("proton_", "Proton ").replace("_", ".")
                proton_model.append(label)
            proton_row.set_model(proton_model)
            current = get_compat_tool(config_path, game.app_id)
            if current in tools:
                proton_row.set_selected(tools.index(current))
            else:
                proton_row.set_selected(0)
            proton_row.connect("notify::selected", self._on_proton_changed, config_path)
            self._proton_combo = proton_row
            content.append(proton_row)

        # Launch options
        opts_frame = Gtk.Frame()
        opts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        opts_label = Gtk.Label(label="Launch Options", xalign=0, margin_bottom=10)
        opts_label.add_css_class("title-4")
        opts_box.append(opts_label)

        self.launch_entry = Gtk.Entry(placeholder_text="e.g. MANGOHUD=1 gamemoderun %command%", hexpand=True)
        self.launch_entry.set_activates_default(True)
        opts_box.append(self.launch_entry)

        hint = Gtk.Label(
            label="Environment variables + %command%. Saved to Steam config.",
            wrap=True, xalign=0, margin_top=10,
        )
        hint.add_css_class("dim-label")
        hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        opts_box.append(hint)

        # Launch presets (Phase 4) — horizontal row
        preset_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for preset in LAUNCH_PRESETS:
            btn = Gtk.Button(label=preset.name)
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_launch_preset, preset)
            preset_box.append(btn)
        preset_box.set_hexpand(True)
        preset_row.append(preset_box)
        self._preset_info_btn = Gtk.Button(icon_name="help-about-symbolic")
        self._preset_info_btn.add_css_class("flat")
        self._preset_info_btn.set_tooltip_text("Preset help & install instructions")
        self._preset_info_btn.connect("clicked", self._on_preset_help)
        preset_row.append(self._preset_info_btn)
        opts_box.append(preset_row)

        opts_frame.set_child(opts_box)
        content.append(opts_frame)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        launch_btn = Gtk.Button(label="Launch in Steam")
        launch_btn.connect("clicked", self._on_launch_in_steam)
        btn_box.append(launch_btn)
        self.save_btn = Gtk.Button(label="Save", css_classes=["suggested-action"])
        self.save_btn.connect("clicked", self._on_save)
        btn_box.append(self.save_btn)

        if game.compatdata_path and game.compatdata_path.exists():
            open_btn = Gtk.Button(label="Open Prefix Folder")
            open_btn.connect("clicked", self._on_open_prefix)
            btn_box.append(open_btn)

        if is_protontricks_available():
            pt_btn = Gtk.Button(label="Run Protontricks")
            pt_btn.connect("clicked", self._on_run_protontricks)
            btn_box.append(pt_btn)

            # Quick install menu
            pt_menu = Gtk.MenuButton(label="Quick Install")
            popover = Gtk.Popover()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
            for verb, desc in COMMON_VERBS:
                row = Gtk.Button(label=f"{verb} — {desc}")
                row.connect("clicked", self._on_install_verb, verb, popover)
                box.append(row)
            popover.set_child(box)
            pt_menu.set_popover(popover)
            btn_box.append(pt_menu)

        profile_menu = Gtk.MenuButton(label="Profiles")
        profile_popover = Gtk.Popover()
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
        save_prof_btn = Gtk.Button(label="Save current as profile")
        save_prof_btn.connect("clicked", self._on_save_profile, profile_popover)
        load_prof_btn = Gtk.Button(label="Load profile")
        load_prof_btn.connect("clicked", self._on_load_profile, profile_popover)
        profile_box.append(save_prof_btn)
        profile_box.append(load_prof_btn)
        profile_popover.set_child(profile_box)
        profile_menu.set_popover(profile_popover)
        btn_box.append(profile_menu)

        content.append(btn_box)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(content)
        self.append(scroll)
        self._load_options()

    def _load_options(self):
        if self.config_path:
            opts = get_launch_options(self.config_path, self.game.app_id)
            self.launch_entry.set_text(opts)

    def _on_copy_app_id(self, _btn):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(self.game.app_id)
        self._toast("App ID copied")

    def _on_open_install_path(self, _btn):
        if self.game.install_path and self.game.install_path.exists():
            path = str(self.game.install_path)
            try:
                subprocess.run(["xdg-open", path], check=False)
            except FileNotFoundError:
                subprocess.run(["gio", "open", path], check=False)

    def _on_launch_in_steam(self, _btn):
        try:
            subprocess.run(["steam", f"steam://rungameid/{self.game.app_id}"], check=False)
        except FileNotFoundError:
            self._toast("Steam not found")

    def _on_proton_changed(self, row: Adw.ComboRow, _pspec, config_path: Path):
        idx = row.get_selected()
        tools = get_available_proton_tools(self._steam_root)
        if 0 <= idx < len(tools):
            tool = tools[idx]
            if set_compat_tool(config_path, self.game.app_id, tool):
                self._toast("Proton version saved")

    def _on_save(self, _btn):
        if not self.config_path:
            self._toast("No Steam config found")
            return
        if is_steam_running():
            dialog = Adw.MessageDialog(
                transient_for=self._window,
                heading="Steam is running",
                body="Editing localconfig.vdf while Steam is running may cause changes to be lost. Close Steam first for reliable saving, or save anyway.",
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("save", "Save anyway")
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            dialog.connect("response", self._on_save_dialog_response)
            dialog.present()
            return
        self._do_save()

    def _on_save_dialog_response(self, dialog: Adw.MessageDialog, response: str):
        dialog.destroy()
        if response == "save":
            self._do_save()

    def _do_save(self):
        if not self.config_path:
            return
        opts = self.launch_entry.get_text().strip()
        if set_launch_options(self.config_path, self.game.app_id, opts):
            self._toast("Saved")
        else:
            self._toast("Failed to save")

    def _on_open_prefix(self, _btn):
        if self.game.compatdata_path and self.game.compatdata_path.exists():
            path = str(self.game.compatdata_path)
            try:
                subprocess.run(["xdg-open", path], check=False)
            except FileNotFoundError:
                subprocess.run(["gio", "open", path], check=False)

    def _on_run_protontricks(self, _btn):
        ok, err = run_protontricks(self.game.app_id)
        if not ok:
            self._toast(err)

    def _on_install_verb(self, _btn, verb: str, popover: Gtk.Popover):
        popover.popdown()
        ok, err = run_protontricks(self.game.app_id, verb)
        if not ok:
            self._toast(err)
        else:
            self._toast(f"Installing {verb}…")

    def _on_launch_preset(self, _btn, preset: LaunchPreset):
        """Toggle preset in launch options: add if absent, remove if present."""
        current = self.launch_entry.get_text().strip()
        tokens = [t for t in current.split() if t]
        # Extract parts before %command%
        before_cmd: list[str] = []
        for t in tokens:
            if t == "%command%":
                break
            before_cmd.append(t)

        # Preset identifiers: match by VAR= prefix or exact token
        preset_atoms = preset.value.split()
        is_present = all(
            any(
                t.startswith(atom.split("=", 1)[0] + "=") if "=" in atom else t == atom
                for t in before_cmd
            )
            for atom in preset_atoms
        )

        if is_present:
            # Remove all tokens matching the preset
            keys_to_remove = {
                atom.split("=", 1)[0] + "=" if "=" in atom else atom
                for atom in preset_atoms
            }
            new_tokens = []
            for t in before_cmd:
                remove = False
                for k in keys_to_remove:
                    if "=" in k:
                        if t.startswith(k):
                            remove = True
                            break
                    elif t == k:
                        remove = True
                        break
                if not remove:
                    new_tokens.append(t)
            new_base = " ".join(new_tokens)
        else:
            # Adding preset — show install hint if tool not installed
            if not preset.is_installed() and preset.install_command:
                self._show_preset_install_hint(preset)
            # Add preset (dedupe: don't add if any atom already there)
            existing_keys = {t.split("=", 1)[0] + "=" for t in before_cmd if "=" in t}
            existing_words = {t for t in before_cmd if "=" not in t}
            to_add = []
            for atom in preset_atoms:
                if "=" in atom:
                    key = atom.split("=", 1)[0] + "="
                    if key not in existing_keys:
                        to_add.append(atom)
                        existing_keys.add(key)
                else:
                    if atom not in existing_words:
                        to_add.append(atom)
                        existing_words.add(atom)
            new_base = " ".join(before_cmd + to_add) if to_add else " ".join(before_cmd)

        result = f"{new_base} %command%".strip() if new_base else "%command%"
        self.launch_entry.set_text(result)

    def _show_preset_install_hint(self, preset: LaunchPreset):
        """Show install instructions for a preset that isn't installed."""
        msg = f"{preset.name} is not installed.\n\nInstall with:\n{preset.install_command}"
        if preset.install_url:
            msg += f"\n\nMore info: {preset.install_url}"
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Install required",
            body=msg,
        )
        dialog.add_response("copy", "Copy command")
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        dialog.connect("response", lambda d, r: self._on_install_dialog_response(d, r, preset))
        dialog.present()

    def _on_install_dialog_response(self, dialog: Adw.MessageDialog, response: str, preset: LaunchPreset):
        if response == "copy" and preset.install_command:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(preset.install_command)
            if self._window and hasattr(self._window, "add_toast"):
                self._window.add_toast(Adw.Toast.new("Command copied to clipboard"))
        dialog.destroy()

    def _get_current_compat_tool(self) -> str:
        if hasattr(self, "_proton_combo") and self._steam_root:
            tools = get_available_proton_tools(self._steam_root)
            idx = self._proton_combo.get_selected()
            if 0 <= idx < len(tools):
                return tools[idx]
        return ""

    def _on_save_profile(self, _btn, popover: Gtk.Popover):
        popover.popdown()
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Save profile",
            body="Enter a name for this profile:",
        )
        entry = Gtk.Entry(placeholder_text="Profile name")
        entry.set_hexpand(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.append(entry)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def on_response(d, response: str):
            if response == "save":
                name = entry.get_text().strip()
                if not name:
                    self._toast("Enter a profile name")
                    d.destroy()
                    return
                profile = ApplicationProfile(
                    name=name,
                    launch_options=self.launch_entry.get_text().strip(),
                    compat_tool=self._get_current_compat_tool(),
                    env_vars=read_gaming_env(),
                    power_profile=get_current_power_profile() or "",
                )
                if save_profile_to_storage(profile):
                    self._toast("Profile saved")
                else:
                    self._toast("Failed to save profile")
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _on_load_profile(self, _btn, popover: Gtk.Popover):
        popover.popdown()
        names = list_profiles()
        if not names:
            self._toast("No profiles saved")
            return
        dialog = Adw.MessageDialog(
            transient_for=self._window,
            heading="Load profile",
            body="Select a profile to apply:",
        )
        listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        for n in names:
            row = Adw.ActionRow(title=n)
            listbox.append(row)
        if names:
            listbox.select_row(listbox.get_row_at_index(0))
        scrolled = Gtk.ScrolledWindow(max_content_height=200)
        scrolled.set_child(listbox)
        dialog.set_extra_child(scrolled)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("load", "Load")
        dialog.set_default_response("load")
        dialog.set_close_response("cancel")

        def on_response(d, response: str):
            if response == "load":
                row = listbox.get_selected_row()
                if row and isinstance(row.get_child(), Adw.ActionRow):
                    name = row.get_child().get_title()
                    profile = load_profile(name)
                    if profile:
                        self.launch_entry.set_text(profile.launch_options)
                        if profile.compat_tool and hasattr(self, "_proton_combo") and self.config_path and self._steam_root:
                            tools = get_available_proton_tools(self._steam_root)
                            if profile.compat_tool in tools:
                                self._proton_combo.set_selected(tools.index(profile.compat_tool))
                            set_compat_tool(self.config_path, self.game.app_id, profile.compat_tool)
                        if profile.env_vars:
                            write_gaming_env(profile.env_vars)
                        if profile.power_profile:
                            set_power_profile(profile.power_profile)
                        self._toast("Profile applied. Save to persist launch options.")
                    else:
                        self._toast("Failed to load profile")
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def _on_preset_help(self, _btn):
        """Show preset help popover with descriptions and install instructions."""
        popover = Gtk.Popover()
        popover.set_has_arrow(True)
        popover.set_autohide(True)
        popover.set_parent(getattr(self, "_preset_info_btn", self))
        popover.add_css_class("preset-help-popover")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=16, margin_bottom=16, margin_start=20, margin_end=20)
        box.set_size_request(440, 380)
        title = Gtk.Label(label="Launch preset help")
        title.add_css_class("title-3")
        title.set_xalign(0)
        box.append(title)
        for preset in LAUNCH_PRESETS:
            frame = Gtk.Frame()
            frame.add_css_class("preset-help-card")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=10, margin_bottom=10, margin_start=12, margin_end=12)
            preset_title = Gtk.Label(label=preset.name)
            preset_title.add_css_class("title-4")
            preset_title.set_xalign(0)
            inner.append(preset_title)
            desc = Gtk.Label(label=preset.description or "No description.")
            desc.set_wrap(True)
            desc.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            desc.add_css_class("dim-label")
            desc.set_xalign(0)
            inner.append(desc)
            if preset.install_command:
                installed = preset.is_installed()
                hint = Gtk.Label(
                    label="✓ Installed" if installed else f"Install: {preset.install_command}",
                )
                hint.add_css_class("caption")
                hint.set_xalign(0)
                if not installed:
                    hint.add_css_class("dim-label")
                inner.append(hint)
            frame.set_child(inner)
            box.append(frame)
        scrolled = Gtk.ScrolledWindow(vexpand=True, min_content_height=320, max_content_height=480, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scrolled.set_child(box)
        popover.set_child(scrolled)
        popover.popup()

    def _toast(self, msg: str):
        toast = Adw.Toast.new(msg)
        toast.set_timeout(2)
        if self._window and hasattr(self._window, "add_toast"):
            self._window.add_toast(toast)


class EnvVarsView(Gtk.Box):
    """Phase 3: Environment variables editor."""

    def __init__(self, window: Adw.ApplicationWindow | None = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self._window = window

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
        content.set_hexpand(True)
        content.add_css_class("env-view-content")

        title = Gtk.Label(label="Global Environment Variables")
        title.add_css_class("title-1")
        title.set_halign(Gtk.Align.CENTER)
        content.append(title)

        hint = Gtk.Label(
            label="Stored in ~/.config/environment.d/70-protonshift.conf. Logout and login for changes.",
            wrap=True,
        )
        hint.add_css_class("env-hint")
        hint.set_halign(Gtk.Align.CENTER)
        hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        hint.set_justify(Gtk.Justification.CENTER)
        content.append(hint)

        # Presets: all 3 on same line, centered
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        preset_box.set_halign(Gtk.Align.CENTER)
        for name, vars_dict in ENV_PRESETS.items():
            btn = Gtk.Button(label=name)
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_preset, vars_dict)
            preset_box.append(btn)
        content.append(preset_box)

        # List of vars: full width
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        current_label = Gtk.Label(label="Current variables:")
        current_label.set_halign(Gtk.Align.CENTER)
        content.append(current_label)
        self._list_frame = Gtk.ScrolledWindow(vexpand=True, hexpand=True, max_content_height=200)
        self._list_frame.set_child(self.listbox)
        content.append(self._list_frame)

        # Add new + Delete selected
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        add_box.set_halign(Gtk.Align.CENTER)
        self.key_entry = Gtk.Entry(placeholder_text="KEY")
        self.val_entry = Gtk.Entry(placeholder_text="value")
        add_btn = Gtk.Button(label="Add")
        add_btn.connect("clicked", self._on_add)
        del_btn = Gtk.Button(label="Delete selected")
        del_btn.connect("clicked", self._on_delete_selected)
        add_box.append(self.key_entry)
        add_box.append(self.val_entry)
        add_box.append(add_btn)
        add_box.append(del_btn)
        content.append(add_box)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(content)
        self.append(scroll)
        self._refresh_list()

    def _refresh_list(self):
        while child := self.listbox.get_first_child():
            self.listbox.remove(child)
        for k, v in read_gaming_env().items():
            row = Adw.ActionRow(title=k, subtitle=v)
            self.listbox.append(row)

    def _on_preset(self, _btn, vars_dict: dict):
        current = read_gaming_env()
        current.update(vars_dict)
        if write_gaming_env(current):
            self._refresh_list()
            self._toast("Preset applied")
        else:
            self._toast("Failed to save")

    def _on_add(self, _btn):
        k = self.key_entry.get_text().strip()
        v = self.val_entry.get_text().strip()
        if not k:
            return
        current = read_gaming_env()
        current[k] = v
        if write_gaming_env(current):
            self.key_entry.set_text("")
            self.val_entry.set_text("")
            self._refresh_list()
            self._toast("Added. Logout/login to apply.")

    def _on_delete_selected(self, _btn):
        row = self.listbox.get_selected_row()
        if not row or not isinstance(row.get_child(), Adw.ActionRow):
            self._toast("Select a variable to delete")
            return
        key = row.get_child().get_title()
        current = read_gaming_env()
        if key in current:
            del current[key]
            if write_gaming_env(current):
                self._refresh_list()
                self._toast("Deleted. Logout/login to apply.")
            else:
                self._toast("Failed to save")

    def _toast(self, msg: str):
        if self._window and hasattr(self._window, "add_toast"):
            self._window.add_toast(Adw.Toast.new(msg))


class SystemView(Gtk.Box):
    """Phase 4: GPU info and power profile."""

    def __init__(self, window: Adw.ApplicationWindow | None = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self._window = window

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        content.add_css_class("system-view-content")

        title = Gtk.Label(label="System")
        title.add_css_class("title-1")
        title.set_halign(Gtk.Align.CENTER)
        content.append(title)

        # GPU card
        gpu_frame = Gtk.Frame()
        gpu_frame.add_css_class("system-card")
        gpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12, margin_bottom=12, margin_start=16, margin_end=16)
        gpu_title = Gtk.Label(label="GPU", css_classes=["title-4"])
        gpu_title.set_halign(Gtk.Align.CENTER)
        gpu_box.append(gpu_title)
        gpus = get_gpu_info()
        if gpus:
            for gpu in gpus:
                desc = f"{gpu.name}"
                if gpu.driver:
                    desc += f" (driver {gpu.driver})"
                if gpu.vram_mb:
                    desc += f" — {gpu.vram_mb} MiB"
                lbl = Gtk.Label(label=desc, wrap=True, justify=Gtk.Justification.CENTER)
                lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl.set_halign(Gtk.Align.CENTER)
                gpu_box.append(lbl)
        else:
            gpu_box.append(Gtk.Label(label="No GPU info available", css_classes=["dim-label"]))
        gpu_frame.set_child(gpu_box)
        content.append(gpu_frame)

        # Power profile card
        profile_frame = Gtk.Frame()
        profile_frame.add_css_class("system-card")
        profile_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=16, margin_bottom=16, margin_start=20, margin_end=20)
        profile_label = Gtk.Label(label="Power Profile", css_classes=["title-4"])
        profile_label.set_halign(Gtk.Align.CENTER)
        profile_inner.append(profile_label)
        current = get_current_power_profile()
        profiles = get_power_profiles()
        if not profiles:
            profiles = ["performance", "balanced", "power-saver"]
        profile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        profile_box.set_halign(Gtk.Align.CENTER)
        for p in profiles:
            btn = Gtk.Button(label=p.replace("-", " ").title())
            btn.add_css_class("pill")
            if current and p.lower() in current.lower():
                btn.add_css_class("suggested-action")
            btn.connect("clicked", self._on_power_profile, p)
            profile_box.append(btn)
        profile_inner.append(profile_box)
        profile_frame.set_child(profile_inner)
        content.append(profile_frame)

        # MangoHud config
        mangohud_btn = Gtk.Button(label="Open MangoHud config folder")
        mangohud_btn.connect("clicked", self._on_open_mangohud_config)
        mangohud_btn.set_halign(Gtk.Align.CENTER)
        content.append(mangohud_btn)

        center_box = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL)
        center_box.set_hexpand(True)
        center_box.set_vexpand(True)
        center_box.set_center_widget(content)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(center_box)
        self.append(scroll)

    def _on_power_profile(self, _btn, profile: str):
        ok, msg = set_power_profile(profile)
        if self._window and hasattr(self._window, "add_toast"):
            self._window.add_toast(Adw.Toast.new(msg if ok else f"Error: {msg}"))

    def _on_open_mangohud_config(self, _btn):
        path = Path.home() / ".config" / "MangoHud"
        path.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["xdg-open", str(path)], check=False)
        except FileNotFoundError:
            subprocess.run(["gio", "open", str(path)], check=False)


class HeroicDetailView(Gtk.Box):
    """Detail panel for a Heroic game (Epic/GOG)."""

    def __init__(self, game: HeroicGame, window: Adw.ApplicationWindow | None = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.game = game
        self._window = window

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)

        content.append(Adw.ActionRow(title="Store", subtitle=game.store.upper()))
        content.append(Adw.ActionRow(title="App ID", subtitle=game.app_id))

        if game.prefix_path and game.prefix_path.exists():
            open_btn = Gtk.Button(label="Open Prefix Folder", css_classes=["suggested-action"])
            open_btn.connect("clicked", self._on_open_prefix)
            content.append(open_btn)

        hint = Gtk.Label(
            label="Launch and configure this game from Heroic Games Launcher.",
            wrap=True, xalign=0, margin_top=10,
        )
        hint.add_css_class("dim-label")
        hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content.append(hint)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(content)
        self.append(scroll)

    def _on_open_prefix(self, _btn):
        if self.game.prefix_path and self.game.prefix_path.exists():
            path = str(self.game.prefix_path)
            try:
                subprocess.run(["xdg-open", path], check=False)
            except FileNotFoundError:
                subprocess.run(["gio", "open", path], check=False)


class LutrisDetailView(Gtk.Box):
    """Detail panel for a Lutris game."""

    def __init__(self, game: LutrisGame, window: Adw.ApplicationWindow | None = None, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.game = game
        self._window = window

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)

        content.append(Adw.ActionRow(title="Source", subtitle="Lutris"))
        content.append(Adw.ActionRow(title="Slug", subtitle=game.app_id))

        if game.install_path and game.install_path.exists():
            row = Adw.ActionRow(title="Install path", subtitle=str(game.install_path))
            open_btn = Gtk.Button(label="Open")
            open_btn.connect("clicked", self._on_open_install_path)
            row.add_suffix(open_btn)
            content.append(row)

        if game.prefix_path and game.prefix_path.exists():
            open_btn = Gtk.Button(label="Open Prefix Folder", css_classes=["suggested-action"])
            open_btn.connect("clicked", self._on_open_prefix)
            content.append(open_btn)

        hint = Gtk.Label(
            label="Launch and configure this game from Lutris.",
            wrap=True, xalign=0, margin_top=10,
        )
        hint.add_css_class("dim-label")
        hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content.append(hint)

        scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(content)
        self.append(scroll)

    def _on_open_install_path(self, _btn):
        if self.game.install_path and self.game.install_path.exists():
            path = str(self.game.install_path)
            try:
                subprocess.run(["xdg-open", path], check=False)
            except FileNotFoundError:
                subprocess.run(["gio", "open", path], check=False)

    def _on_open_prefix(self, _btn):
        if self.game.prefix_path and self.game.prefix_path.exists():
            path = str(self.game.prefix_path)
            try:
                subprocess.run(["xdg-open", path], check=False)
            except FileNotFoundError:
                subprocess.run(["gio", "open", path], check=False)


class GameRow(Gtk.ListBoxRow):
    """Row for game list."""

    def __init__(self, game: SteamGame | HeroicGame | LutrisGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        if isinstance(game, HeroicGame):
            subtitle = f"{game.store.upper()} · {game.app_id}"
        elif isinstance(game, LutrisGame):
            subtitle = f"Lutris · {game.app_id}"
        else:
            subtitle = f"Steam · App ID: {game.app_id}"
        row = Adw.ActionRow(title=game.name, subtitle=subtitle)
        row.set_activatable(True)
        self.set_child(row)


class GameSetupHubWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, app: Adw.Application, **kwargs):
        super().__init__(application=app, **kwargs)
        self.set_default_size(700, 500)
        self.set_title("ProtonShift")
        self.steam_root: Path | None = None
        self.config_path: Path | None = None
        self.games: list[SteamGame | HeroicGame | LutrisGame] = []
        self.toast_overlay = Adw.ToastOverlay()

        self._build_ui()

    def _build_ui(self):
        self.toast_overlay.set_child(self._build_main())
        self.set_content(self.toast_overlay)

    def _build_main(self) -> Gtk.Widget:
        self.top_stack = Gtk.Stack(vexpand=True)

        # Loading
        loading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        sp = Gtk.Spinner(spinning=True)
        sp.set_size_request(48, 48)
        loading.append(sp)
        load_label = Gtk.Label(label="Scanning libraries…")
        load_label.add_css_class("title-4")
        loading.append(load_label)
        self.top_stack.add_named(loading, "loading")

        self.view_stack = Adw.ViewStack(vexpand=True)

        # Games view
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)
        self.main_box.set_margin_top(10)
        self.main_box.set_margin_bottom(10)
        self.main_box.set_margin_start(10)
        self.main_box.set_margin_end(10)

        list_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_panel.set_size_request(280, -1)
        list_frame = Gtk.Frame()
        list_frame.add_css_class("game-list-frame")
        list_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        search = Gtk.SearchEntry(placeholder_text="Search games…")
        search.add_css_class("game-list-search")
        search.connect("search-changed", self._on_search_changed)
        list_inner.append(search)
        list_scroll = Gtk.ScrolledWindow(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, vexpand=True)
        self.listbox.connect("row-activated", self._on_game_selected)
        list_scroll.set_child(self.listbox)
        list_inner.append(list_scroll)
        list_frame.set_child(list_inner)
        list_panel.append(list_frame)

        self.main_box.append(list_panel)

        self.detail_stack = Gtk.Stack()
        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        placeholder.set_hexpand(True)
        placeholder.set_vexpand(True)
        ph_label = Gtk.Label(label="Select a game")
        ph_label.add_css_class("placeholder-title")
        placeholder.append(ph_label)
        self.detail_stack.add_named(placeholder, "placeholder")
        self.main_box.append(self.detail_stack)

        self.view_stack.add_titled_with_icon(
            self.main_box, "games", "Games", "applications-games-symbolic"
        )

        # Environment view (Phase 3)
        env_view = EnvVarsView(window=self)
        self.view_stack.add_titled_with_icon(
            env_view, "env", "Environment", "applications-science-symbolic"
        )

        # System view (Phase 4)
        sys_view = SystemView(window=self)
        self.view_stack.add_titled_with_icon(
            sys_view, "system", "System", "computer-symbolic"
        )

        # Toolbar with view switcher and menu
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher(stack=self.view_stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_tooltip_text("Menu")
        menu = Gio.Menu.new()
        menu.append("About", "app.about")
        menu.append("Keyboard Shortcuts", "win.shortcuts")
        popover = Gtk.PopoverMenu(menu_model=menu)
        menu_btn.set_popover(popover)
        header.pack_end(menu_btn)
        toolbar.add_top_bar(header)
        toolbar.set_content(self.view_stack)

        self.top_stack.add_named(toolbar, "main")

        GLib.idle_add(self._load_games)
        return self.top_stack

    def _load_games(self):
        steam_root, steam_games = discover_games()
        self.steam_root = steam_root
        if steam_root:
            self.config_path = get_localconfig_path(steam_root)
        heroic_games = discover_heroic_games()
        lutris_games = discover_lutris_games()
        # Steam by last_played; Heroic and Lutris by name
        heroic_sorted = sorted(heroic_games, key=lambda g: g.name.lower())
        lutris_sorted = sorted(lutris_games, key=lambda g: g.name.lower())
        self.games = list(steam_games) + heroic_sorted + lutris_sorted
        self._populate_list(self.games)
        self.top_stack.set_visible_child_name("main")

    def _populate_list(self, games: list[SteamGame | HeroicGame | LutrisGame]):
        # Clear
        while child := self.listbox.get_first_child():
            self.listbox.remove(child)
        for game in games:
            self.listbox.append(GameRow(game))

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().lower()
        if not query:
            self._populate_list(self.games)
        else:
            filtered = [g for g in self.games if query in g.name.lower() or query in g.app_id]
            self._populate_list(filtered)

    def _on_game_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow):
        if not isinstance(row, GameRow):
            return
        game = row.game
        if isinstance(game, HeroicGame):
            detail = HeroicDetailView(game, window=self)
            key = f"heroic-{game.app_id}"
        elif isinstance(game, LutrisGame):
            detail = LutrisDetailView(game, window=self)
            key = f"lutris-{game.app_id}"
        else:
            detail = GameDetailView(
                game, self.config_path, window=self, steam_root=self.steam_root
            )
            key = f"steam-{game.app_id}"
        if old := self.detail_stack.get_child_by_name(key):
            self.detail_stack.remove(old)
        self.detail_stack.add_named(detail, key)
        self.detail_stack.set_visible_child_name(key)

    def add_toast(self, toast: Adw.Toast):
        self.toast_overlay.add_toast(toast)

    def add_shortcuts(self):
        shortcut_action = Gio.SimpleAction.new("shortcuts", None)
        shortcut_action.connect("activate", self._on_shortcuts)
        self.add_action(shortcut_action)
        self.get_application().set_accels_for_action("win.shortcuts", ["<Primary>question"])
        self.get_application().set_accels_for_action("app.quit", ["<Primary>q"])

    def _on_shortcuts(self, _action, _param):
        try:
            sw = Adw.ShortcutsDialog(transient_for=self)
            section = Adw.ShortcutsSection(title="General")
            section.add(Adw.ShortcutsItem(title="Keyboard Shortcuts", accelerator="<Primary>question"))
            section.add(Adw.ShortcutsItem(title="Quit", accelerator="<Primary>q"))
            sw.add(section)
            sw.present()
        except (AttributeError, TypeError):
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Keyboard Shortcuts",
                body="Ctrl+? — Keyboard Shortcuts\nCtrl+Q — Quit",
            )
            dialog.add_response("ok", "OK")
            dialog.connect("response", lambda d, _: d.destroy())
            dialog.present()


def _load_theme():
    """Load futuristic theme CSS."""
    css_path = Path(__file__).resolve().parent / "theme.css"
    if not css_path.exists():
        return
    try:
        provider = Gtk.CssProvider()
        provider.load_from_path(str(css_path))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
    except Exception:
        pass


def main():
    app = Adw.Application(application_id="io.github.protonshift", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def on_about(_action, _param):
        win = app.get_active_window()
        about = Adw.AboutWindow(
            transient_for=win,
            application_name="ProtonShift",
            version="0.8.7",
            developer_name="ProtonShift",
            website="https://github.com/protonshift/protonshift",
            application_icon="io.github.protonshift",
        )
        about.present()

    def on_activate(a):
        _load_theme()
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        win = GameSetupHubWindow(a)
        win.add_shortcuts()
        win.present()

    about_action = Gio.SimpleAction.new("about", None)
    about_action.connect("activate", on_about)
    app.add_action(about_action)
    app.connect("activate", on_activate)
    return app.run(sys.argv)
