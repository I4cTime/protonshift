import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Third slice: the environment.d editor — the safe read-modify-write pattern.
// `env` is the EnvController context property (owns a QAbstractListModel).
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
                    text: "Environment Variables"
                    subtitle: "~/.config/environment.d/70-protonshift.conf · log out/in to apply"
                }
                BusyIndicator {
                    running: env.loading
                    visible: env.loading
                    implicitWidth: 22; implicitHeight: 22
                }
            }

            // #22 made visible: a real read error is its own state, not "empty"
            Rectangle {
                Layout.fillWidth: true
                visible: env.loadError.length > 0
                radius: Theme.radiusSm
                color: "#2a1216"
                border.color: Theme.danger
                border.width: 1
                implicitHeight: errLbl.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: errLbl
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: "#f2a3ab"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "Couldn't read the config — not showing an editor so a save can't overwrite it.\n" + env.loadError
                }
            }

            // rows
            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: env.model
                visible: !env.loadError.length
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}

                header: RowLayout {
                    width: ListView.view.width
                    height: keyHead.implicitHeight + 6
                    spacing: Theme.spaceSm
                    Text {
                        Layout.preferredWidth: 220
                        id: keyHead; text: "KEY"; color: Theme.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                        font.weight: Font.DemiBold
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "VALUE"; color: Theme.muted
                        font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                        font.weight: Font.DemiBold
                    }
                    Item { width: 28 }
                }

                delegate: RowLayout {
                    id: row
                    required property int index
                    required property string key
                    required property string value
                    width: ListView.view.width
                    spacing: Theme.spaceSm

                    // Set text imperatively (never bind, so user typing can't
                    // break a binding) and re-sync from the model on external
                    // changes — e.g. a preset merge — unless this field is focused.
                    Connections {
                        target: env.model
                        function onDataChanged(topLeft, bottomRight) {
                            if (row.index < topLeft.row || row.index > bottomRight.row)
                                return
                            if (!keyField.editing) keyField.text = row.key
                            if (!valField.editing) valField.text = row.value
                        }
                    }

                    EnvField {
                        id: keyField
                        Layout.preferredWidth: 220
                        mono: true
                        placeholder: "VAR_NAME"
                        Component.onCompleted: text = row.key
                        onEdited: env.model.setKey(row.index, newText)
                    }
                    EnvField {
                        id: valField
                        Layout.fillWidth: true
                        mono: true
                        placeholder: "value"
                        Component.onCompleted: text = row.value
                        onEdited: env.model.setValue(row.index, newText)
                    }
                    Rectangle {
                        width: 28; height: 28; radius: Theme.radiusSm
                        color: rm.hovered ? "#2a1216" : "transparent"
                        border.width: 1
                        border.color: rm.hovered ? Theme.danger : Theme.border
                        Text {
                            anchors.centerIn: parent; text: "✕"
                            color: rm.hovered ? Theme.danger : Theme.muted
                            font.pixelSize: 12
                        }
                        HoverHandler { id: rm }
                        TapHandler { onTapped: env.model.removeRow(index) }
                    }
                }

                footer: Item {
                    width: ListView.view.width
                    height: list.count === 0 ? 40 : 0
                    visible: list.count === 0 && !env.loading
                    Text {
                        anchors.centerIn: parent
                        text: "No variables yet — add one or apply a preset."
                        color: Theme.faint
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                    }
                }
            }

            // footer: add + save
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                visible: !env.loadError.length

                PsButton {
                    text: "+ Add variable"
                    primary: false
                    enabled: env.loaded
                    onClicked: env.model.addRow()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: env.status
                    color: env.status.indexOf("Not saved") === 0 || env.status.indexOf("failed") >= 0
                           ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: env.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save"
                    // enabled only once a load succeeded and there are edits (#21)
                    enabled: env.loaded && env.dirty
                    onClicked: env.save()
                }
            }
        }
    }

    // ============================ PRESETS ==================================
    PsCard {
        Layout.preferredWidth: 240
        Layout.fillHeight: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space

            PsSectionHeader {
                Layout.fillWidth: true
                text: "Presets"
                subtitle: "Merge a set of known-good vars into the list."
            }

            Repeater {
                model: env.presetNames
                delegate: Rectangle {
                    required property string modelData
                    Layout.fillWidth: true
                    implicitHeight: 40
                    radius: Theme.radiusSm
                    color: ph.hovered ? Theme.surfaceElevated : Theme.bgDeep
                    border.color: ph.hovered ? Theme.borderStrong : Theme.border
                    border.width: 1
                    Behavior on color { ColorAnimation { duration: 120 } }
                    HoverHandler { id: ph }
                    TapHandler { onTapped: if (env.loaded) env.applyPreset(modelData) }
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spaceSm
                        anchors.rightMargin: Theme.spaceSm
                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            font.weight: Font.Medium
                        }
                        Text {
                            text: "+"
                            color: Theme.primaryBright
                            font.pixelSize: 16; font.bold: true
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }
}
