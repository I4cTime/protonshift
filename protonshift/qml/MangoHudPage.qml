import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Fourth slice: the global MangoHud.conf editor. `mangohud` is the controller.
// Same safe read-modify-write as the env editor (guarded save, error != empty).
RowLayout {
    id: page
    spacing: Theme.spaceLg

    // ============================ EDITOR ===================================
    PsCard {
        Layout.fillWidth: true
        Layout.fillHeight: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "MangoHud Overlay"
                    subtitle: "~/.config/MangoHud/MangoHud.conf"
                }
                BusyIndicator {
                    running: mangohud.loading
                    visible: mangohud.loading
                    implicitWidth: 22; implicitHeight: 22
                }
            }

            // not-installed hint (config still editable)
            Rectangle {
                Layout.fillWidth: true
                visible: !mangohud.available
                radius: Theme.radiusSm
                color: Theme.warningSurface
                border.color: Theme.warningBorder
                border.width: 1
                implicitHeight: naLbl.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: naLbl
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: Theme.warning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "MangoHud isn't installed — you can still edit the config for later."
                }
            }

            // read error (fail-safe: no editor, so a save can't overwrite)
            Rectangle {
                Layout.fillWidth: true
                visible: mangohud.loadError.length > 0
                radius: Theme.radiusSm
                color: Theme.dangerSurface
                border.color: Theme.danger
                border.width: 1
                implicitHeight: errLbl.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: errLbl
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: Theme.danger
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "Couldn't read MangoHud.conf — editing disabled so nothing gets overwritten.\n" + mangohud.loadError
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                visible: !mangohud.loadError.length

                ColumnLayout {
                    width: parent.width
                    spacing: Theme.space

                    PsSectionHeader { Layout.fillWidth: true; text: "Metrics" }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spaceLg
                        rowSpacing: Theme.spaceSm
                        Repeater {
                            model: mangohud.toggleParams
                            delegate: PsSwitchRow {
                                required property var modelData
                                Layout.fillWidth: true
                                enabled: mangohud.loaded
                                text: modelData.label
                                checked: mangohud.config[modelData.key] !== undefined
                                onToggled: mangohud.setToggle(modelData.key, value)
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                    PsSectionHeader { Layout.fillWidth: true; text: "Values" }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: Theme.spaceLg
                        rowSpacing: Theme.spaceSm
                        Repeater {
                            model: mangohud.valueParams
                            delegate: ColumnLayout {
                                id: vrow
                                required property var modelData
                                Layout.fillWidth: true
                                spacing: 3
                                Text {
                                    text: modelData.label
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                    font.weight: Font.DemiBold
                                }
                                EnvField {
                                    id: vfield
                                    Layout.fillWidth: true
                                    mono: true
                                    enabled: mangohud.loaded
                                    placeholder: "unset"
                                    Component.onCompleted: text = mangohud.config[vrow.modelData.key] || ""
                                    onEdited: mangohud.setValue(vrow.modelData.key, newText)
                                    Connections {
                                        target: mangohud
                                        function onConfigChanged() {
                                            if (!vfield.editing)
                                                vfield.text = mangohud.config[vrow.modelData.key] || ""
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !mangohud.loadError.length
                spacing: Theme.spaceSm
                Text {
                    Layout.fillWidth: true
                    text: mangohud.status
                    color: (mangohud.status.indexOf("failed") >= 0
                            || mangohud.status.indexOf("Not saved") >= 0)
                           ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: mangohud.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save"
                    enabled: mangohud.loaded && mangohud.dirty
                    onClicked: mangohud.save()
                }
            }
        }
    }

    // ============================ PRESETS ==================================
    PsCard {
        Layout.preferredWidth: 220
        Layout.fillHeight: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space

            PsSectionHeader {
                Layout.fillWidth: true
                text: "Presets"
                subtitle: "Replaces the current config."
            }

            Repeater {
                model: mangohud.presetNames
                delegate: Rectangle {
                    required property string modelData
                    Layout.fillWidth: true
                    implicitHeight: 38
                    radius: Theme.radiusSm
                    color: ph.hovered ? Theme.surfaceElevated : Theme.bgDeep
                    border.color: ph.hovered ? Theme.borderStrong : Theme.border
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 120 } }
                    HoverHandler { id: ph }
                    TapHandler { onTapped: if (mangohud.loaded) mangohud.applyPreset(modelData) }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.left: parent.left
                        anchors.leftMargin: Theme.spaceSm
                        text: modelData
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                        font.weight: Font.Medium
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }
}
