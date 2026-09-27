import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Settings: appearance (visual style / accent / dark-light-system mode),
// privacy, and about. `themeCtl` (appearance) + `protondb` (privacy toggle)
// controllers; `appVersion` context property for the About card.
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    readonly property var modeOptions: [
        { id: "system", label: "System" },
        { id: "dark", label: "Dark" },
        { id: "light", label: "Light" }
    ]

    PsSectionHeader {
        Layout.fillWidth: true
        text: "Settings"
        subtitle: "Appearance, privacy, and about"
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceLg

            // --- Appearance ---------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: appearanceCol.implicitHeight + 2 * Theme.spaceLg

                ColumnLayout {
                    id: appearanceCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space

                    PsSectionHeader { Layout.fillWidth: true; text: "Appearance" }

                    // Style ---------------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Text {
                            text: "Style"
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space
                            Repeater {
                                model: themeCtl.styles
                                delegate: ColumnLayout {
                                    id: styleItem
                                    required property var modelData
                                    readonly property var styleDef: Theme.styles[styleItem.modelData.id]
                                    readonly property var neutrals: Theme.dark ? styleItem.styleDef.dark
                                                                                : styleItem.styleDef.light
                                    readonly property bool selected: themeCtl.style === styleItem.modelData.id
                                    spacing: Theme.spaceXs

                                    Rectangle {
                                        id: preview
                                        implicitWidth: 150
                                        implicitHeight: 92
                                        radius: styleItem.styleDef.radiusLg
                                        color: styleItem.neutrals.bg
                                        border.width: styleItem.selected ? 2 : 1
                                        border.color: styleItem.selected ? Theme.primary : Theme.border
                                        Behavior on border.color { ColorAnimation { duration: 120 } }

                                        // surface strip
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            anchors.margins: 10
                                            height: 28
                                            radius: styleItem.styleDef.radius
                                            color: styleItem.neutrals.surface
                                            border.color: styleItem.neutrals.border
                                            border.width: 1
                                        }
                                        // accent pill
                                        Rectangle {
                                            anchors.top: parent.top
                                            anchors.left: parent.left
                                            anchors.margins: 12
                                            width: 34; height: 12
                                            radius: styleItem.styleDef.radiusSm
                                            color: Theme.accent
                                        }

                                        Accessible.role: Accessible.Button
                                        Accessible.name: styleItem.modelData.label
                                        HoverHandler { id: styleHover }
                                        TapHandler { onTapped: themeCtl.setStyle(styleItem.modelData.id) }
                                    }
                                    Text {
                                        Layout.preferredWidth: preview.width
                                        text: styleItem.modelData.label
                                        color: styleItem.selected ? Theme.text : Theme.muted
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: styleItem.selected ? Font.DemiBold : Font.Normal
                                    }
                                    Text {
                                        Layout.preferredWidth: preview.width
                                        text: styleItem.modelData.tagline
                                        wrapMode: Text.WordWrap
                                        color: Theme.faint
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsCaption
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

                    // Mode ----------------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Text {
                            text: "Mode"
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            spacing: Theme.spaceXs
                            Repeater {
                                model: page.modeOptions
                                delegate: Rectangle {
                                    id: modeSeg
                                    required property var modelData
                                    readonly property bool active: themeCtl.mode === modeSeg.modelData.id
                                    implicitWidth: 96
                                    implicitHeight: 34
                                    radius: Theme.radiusSm
                                    color: active ? Theme.surfaceElevated : (segHover.hovered ? Theme.surface : Theme.bgDeep)
                                    border.color: active ? Theme.primary : Theme.border
                                    border.width: active ? 2 : 1
                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: modeSeg.modelData.label
                                    Accessible.checked: modeSeg.active

                                    HoverHandler { id: segHover }
                                    TapHandler { onTapped: themeCtl.setMode(modeSeg.modelData.id) }
                                    Text {
                                        anchors.centerIn: parent
                                        text: modeSeg.modelData.label
                                        color: modeSeg.active ? Theme.text : Theme.muted
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: modeSeg.active ? Font.DemiBold : Font.Normal
                                    }
                                }
                            }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }

                    // Accent ----------------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Text {
                            text: "Accent"
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.DemiBold
                        }
                        RowLayout {
                            spacing: Theme.spaceSm
                            Repeater {
                                model: themeCtl.accentPresets
                                delegate: Item {
                                    id: swatchItem
                                    required property var modelData
                                    readonly property bool active: themeCtl.resolvedAccent.toLowerCase()
                                                                    === swatchItem.modelData.hex.toLowerCase()
                                    implicitWidth: 32
                                    implicitHeight: 32
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 26; height: 26; radius: 13
                                        color: swatchItem.modelData.hex
                                        border.width: swatchItem.active ? 3 : 1
                                        border.color: swatchItem.active ? Theme.text : Theme.border
                                    }
                                    Accessible.role: Accessible.Button
                                    Accessible.name: swatchItem.modelData.name
                                    HoverHandler { id: swatchHover }
                                    TapHandler { onTapped: themeCtl.setAccent(swatchItem.modelData.hex) }
                                }
                            }
                            Item { Layout.preferredWidth: Theme.spaceSm }
                            TextField {
                                id: accentField
                                Layout.preferredWidth: 130
                                placeholderText: "#22c3e6"
                                selectByMouse: true
                                color: Theme.text
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsSmall
                                Accessible.name: "Custom accent hex"

                                // Same idiom as PsSwitchRow: a plain `text:
                                // themeCtl.accent` binding is destroyed by the
                                // first keystroke, so a reset or preset tap
                                // elsewhere would never re-sync the field. A
                                // Binding element survives direct edits.
                                Binding on text {
                                    value: themeCtl.accent
                                    restoreMode: Binding.RestoreBindingOrValue
                                }

                                onAccepted: themeCtl.setAccent(text)

                                background: Rectangle {
                                    radius: Theme.radiusSm
                                    color: Theme.bgDeep
                                    border.color: accentField.activeFocus ? Theme.primary
                                                  : (themeCtl.accentError.length > 0 ? Theme.danger : Theme.border)
                                    border.width: accentField.activeFocus ? 2 : 1
                                    Behavior on border.color { ColorAnimation { duration: 120 } }
                                }
                            }
                            PsButton {
                                text: "Reset to style default"
                                primary: false
                                enabled: themeCtl.accent.length > 0
                                onClicked: themeCtl.resetAccent()
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: themeCtl.accentError.length > 0
                            text: themeCtl.accentError
                            color: Theme.danger
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                        }
                    }
                }
            }

            // --- Privacy -------------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: privacyCol.implicitHeight + 2 * Theme.spaceLg
                ColumnLayout {
                    id: privacyCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space
                    PsSectionHeader { Layout.fillWidth: true; text: "Privacy" }
                    PsSwitchRow {
                        Layout.fillWidth: true
                        text: "Look up ProtonDB ratings"
                        subtitle: "Sends only the Steam App ID to protondb.com when you select a game"
                        checked: protondb.enabled
                        onToggled: protondb.setEnabled(value)
                    }
                }
            }

            // --- About -----------------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: aboutCol.implicitHeight + 2 * Theme.spaceLg
                ColumnLayout {
                    id: aboutCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space
                    PsSectionHeader { Layout.fillWidth: true; text: "About" }
                    Text {
                        text: "ProtonShift v" + appVersion
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsBody
                        font.weight: Font.DemiBold
                    }
                    RowLayout {
                        spacing: Theme.spaceSm
                        PsButton {
                            text: "GitHub"
                            primary: false
                            onClicked: Qt.openUrlExternally("https://github.com/I4cTime/protonshift")
                        }
                        PsButton {
                            text: "Website"
                            primary: false
                            onClicked: Qt.openUrlExternally("https://protonshift.i4c.studio")
                        }
                    }
                }
            }
        }
    }
}
