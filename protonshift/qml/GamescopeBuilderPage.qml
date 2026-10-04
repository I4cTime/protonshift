import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Vertical slice: the gamescope command builder, wired to the real Python core
// (`gamescope` context property -> GamescopeController -> core.gamescope).
// Left: controls. Right: a live preview that rebuilds on every edit.
RowLayout {
    id: page
    spacing: Theme.spaceLg

    // The game this command can be added to: the Library's selection, when it
    // is a Steam game whose launch options are loaded.
    readonly property bool hasTarget: (library.selected.source || "") === "steam" && launch.loaded
    readonly property string targetName: library.selected.name || ""

    // ============================ CONTROLS =================================
    PsCard {
        Layout.preferredWidth: 560
        Layout.fillHeight: true

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.spaceLg

                // availability notice
                Rectangle {
                    Layout.fillWidth: true
                    visible: !gamescope.gamescopeAvailable
                    radius: Theme.radiusSm
                    color: Theme.warningSurface
                    border.color: Theme.warningBorder
                    border.width: 1
                    implicitHeight: notice.implicitHeight + 2 * Theme.spaceSm
                    Text {
                        id: notice
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        wrapMode: Text.WordWrap
                        color: Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                        text: "gamescope was not found on this system. You can still build a command to copy elsewhere."
                    }
                }

                // --- resolution ---
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Resolution"
                    subtitle: "Output is the window/display size, game is the internal render size."
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: Theme.space
                    rowSpacing: Theme.spaceSm
                    PsNumberField {
                        Layout.fillWidth: true
                        label: "Output width (-W)"
                        value: gamescope.outputWidth
                        onEdited: gamescope.outputWidth = value
                    }
                    PsNumberField {
                        Layout.fillWidth: true
                        label: "Output height (-H)"
                        value: gamescope.outputHeight
                        onEdited: gamescope.outputHeight = value
                    }
                    PsNumberField {
                        Layout.fillWidth: true
                        label: "Game width (-w)"
                        value: gamescope.gameWidth
                        onEdited: gamescope.gameWidth = value
                    }
                    PsNumberField {
                        Layout.fillWidth: true
                        label: "Game height (-h)"
                        value: gamescope.gameHeight
                        onEdited: gamescope.gameHeight = value
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                // --- performance ---
                PsSectionHeader { Layout.fillWidth: true; text: "Performance" }
                PsNumberField {
                    Layout.preferredWidth: 200
                    label: "FPS limit (-r)"
                    to: 1000
                    value: gamescope.fpsLimit
                    onEdited: gamescope.fpsLimit = value
                }
                PsSwitchRow {
                    text: "FSR upscaling"
                    subtitle: "AMD FidelityFX Super Resolution (-F fsr)"
                    checked: gamescope.fsr
                    onToggled: gamescope.fsr = value
                }
                PsSlider {
                    Layout.fillWidth: true
                    visible: gamescope.fsr
                    label: "FSR sharpness"
                    from: 0; to: 20
                    value: gamescope.fsrSharpness
                    onMoved: gamescope.fsrSharpness = Math.round(value)
                }
                PsSwitchRow {
                    text: "Integer scaling"
                    subtitle: "Sharp pixel-perfect upscaling (--integer-scale)"
                    checked: gamescope.integerScale
                    onToggled: gamescope.integerScale = value
                }
                PsSwitchRow {
                    text: "HDR"
                    subtitle: "--hdr-enabled"
                    checked: gamescope.hdr
                    onToggled: gamescope.hdr = value
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                // --- window ---
                PsSectionHeader { Layout.fillWidth: true; text: "Window" }
                PsSwitchRow {
                    text: "Fullscreen (-f)"
                    checked: gamescope.fullscreen
                    onToggled: gamescope.fullscreen = value
                }
                PsSwitchRow {
                    text: "Borderless (-b)"
                    checked: gamescope.borderless
                    onToggled: gamescope.borderless = value
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                // --- advanced ---
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Advanced"
                    subtitle: "Extra gamescope arguments, appended verbatim."
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: Theme.bgDeep
                    border.width: extra.activeFocus ? 2 : 1
                    border.color: extra.activeFocus ? Theme.primary : Theme.border
                    Behavior on border.color { ColorAnimation { duration: 120 } }
                    TextField {
                        id: extra
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        verticalAlignment: TextInput.AlignVCenter
                        text: gamescope.extraArgs
                        placeholderText: "--adaptive-sync --backend wayland"
                        placeholderTextColor: Theme.faint
                        color: Theme.text
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.fsSmall
                        selectByMouse: true
                        background: Item {}
                        onTextEdited: gamescope.extraArgs = text
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                // --- scopebuddy wrap ---
                PsSwitchRow {
                    text: "Wrap with ScopeBuddy"
                    subtitle: "Emit SCB_AUTO_* env + scb -- instead of a raw gamescope line."
                    checked: gamescope.wrapWithScopebuddy
                    onToggled: gamescope.wrapWithScopebuddy = value
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.space
                    visible: gamescope.wrapWithScopebuddy
                    spacing: Theme.spaceSm
                    PsSwitchRow {
                        text: "Auto resolution"; checked: gamescope.scbAutoRes
                        onToggled: gamescope.scbAutoRes = value
                    }
                    PsSwitchRow {
                        text: "Auto HDR"; checked: gamescope.scbAutoHdr
                        onToggled: gamescope.scbAutoHdr = value
                    }
                    PsSwitchRow {
                        text: "Auto VRR"; checked: gamescope.scbAutoVrr
                        onToggled: gamescope.scbAutoVrr = value
                    }
                    PsSwitchRow {
                        text: "Auto refresh"; checked: gamescope.scbAutoRefresh
                        onToggled: gamescope.scbAutoRefresh = value
                    }
                    PsSwitchRow {
                        text: "Auto frame limit"; checked: gamescope.scbAutoFrameLimit
                        onToggled: gamescope.scbAutoFrameLimit = value
                    }
                    PsSwitchRow {
                        text: "No scope (passthrough)"; checked: gamescope.scbNoscope
                        onToggled: gamescope.scbNoscope = value
                    }
                }
            }
        }
    }

    // ============================ PREVIEW =================================
    PsCard {
        Layout.fillWidth: true
        Layout.fillHeight: true
        glowing: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space

            PsSectionHeader {
                Layout.fillWidth: true
                text: "Launch command"
                subtitle: "A complete Steam launch-options line. Add it to the game selected in Library, or copy it."
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.radius
                color: Theme.bgDeep
                border.color: Theme.border
                border.width: 1

                Flickable {
                    anchors.fill: parent
                    anchors.margins: Theme.space
                    contentHeight: cmd.implicitHeight
                    clip: true
                    TextEdit {
                        id: cmd
                        width: parent.width
                        text: gamescope.command
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.WrapAnywhere
                        color: Theme.primaryBright
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.fsBody

                        // subtle flash when the command changes, so edits feel live
                        Connections {
                            target: gamescope
                            function onChanged() { flash.restart() }
                        }
                        SequentialAnimation {
                            id: flash
                            ColorAnimation { target: cmd; property: "color"; to: Theme.text; duration: 60 }
                            ColorAnimation { target: cmd; property: "color"; to: Theme.primaryBright; duration: 400 }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: copied.running ? "Copied to clipboard."
                      : added.running ? "Added to " + page.targetName + "'s launch options. Not saved yet: review and save it in Library."
                      : page.hasTarget ? "Selected in Library: " + page.targetName + "."
                      : "Select a Steam game in Library to add this to its launch options."
                color: (copied.running || added.running) ? Theme.success : Theme.faint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: page.hasTarget ? "Add to " + page.targetName : "Add to game"
                    enabled: page.hasTarget
                    // long game names must not push the button off the card
                    width: Math.min(implicitWidth, 320)
                    onClicked: { launch.appendPreset(gamescope.prefix); added.restart() }
                }
                PsButton {
                    text: "Open Library"
                    primary: false
                    visible: page.hasTarget && launch.dirty
                    onClicked: window.currentPage = 0
                }
                PsButton {
                    text: "Copy command"
                    primary: false
                    onClicked: { gamescope.copyCommand(); copied.restart() }
                }
            }
        }

        Timer { id: copied; interval: 1600; repeat: false }
        Timer { id: added; interval: 6000; repeat: false }
    }
}
