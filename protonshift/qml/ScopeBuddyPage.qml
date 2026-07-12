import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Fifth slice: the global ScopeBuddy scb.conf editor. `scopebuddy` is the
// controller. Comment/bash-preserving write lives in the core (#M1/#M2).
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
                    text: "ScopeBuddy"
                    subtitle: "~/.config/scopebuddy/scb.conf · comments & bash preserved"
                }
                // availability chip
                Rectangle {
                    visible: scopebuddy.available
                    implicitWidth: verLbl.implicitWidth + 16
                    implicitHeight: 22
                    radius: 11
                    color: "#12281f"
                    border.color: Theme.success
                    border.width: 1
                    Text {
                        id: verLbl
                        anchors.centerIn: parent
                        text: scopebuddy.binaryName + (scopebuddy.version ? " " + scopebuddy.version : "")
                        color: Theme.success
                        font.family: Theme.monoFamily
                        font.pixelSize: Theme.fsCaption
                        font.weight: Font.DemiBold
                    }
                }
                BusyIndicator {
                    running: scopebuddy.loading
                    visible: scopebuddy.loading
                    implicitWidth: 22; implicitHeight: 22
                }
            }

            Rectangle {
                Layout.fillWidth: true
                visible: !scopebuddy.available
                radius: Theme.radiusSm
                color: "#2a1f12"
                border.color: "#7c5a1e"
                border.width: 1
                implicitHeight: naLbl.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: naLbl
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: "#f0c088"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "ScopeBuddy (scb) isn't installed — you can still edit the config for later."
                }
            }

            // read error → no editor, so save can't overwrite
            Rectangle {
                Layout.fillWidth: true
                visible: scopebuddy.loadError.length > 0
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
                    text: "Couldn't read scb.conf — editing disabled so nothing gets overwritten.\n" + scopebuddy.loadError
                }
            }

            // known-key quick-add chips
            Flow {
                Layout.fillWidth: true
                visible: !scopebuddy.loadError.length
                spacing: Theme.spaceXs
                Repeater {
                    model: scopebuddy.knownKeys
                    delegate: Rectangle {
                        required property string modelData
                        implicitWidth: chip.implicitWidth + 18
                        implicitHeight: 24
                        radius: 12
                        color: ch.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: ch.hovered ? Theme.primary : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 100 } }
                        HoverHandler { id: ch }
                        TapHandler { onTapped: if (scopebuddy.loaded) scopebuddy.addKey(modelData) }
                        Text {
                            id: chip
                            anchors.centerIn: parent
                            text: "+ " + modelData
                            color: ch.hovered ? Theme.primaryBright : Theme.muted
                            font.family: Theme.monoFamily
                            font.pixelSize: 10
                        }
                    }
                }
            }

            // rows
            ListView {
                id: list
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: scopebuddy.model
                visible: !scopebuddy.loadError.length
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}

                delegate: RowLayout {
                    id: row
                    required property int index
                    required property string key
                    required property string value
                    width: ListView.view.width
                    spacing: Theme.spaceSm

                    Connections {
                        target: scopebuddy.model
                        function onDataChanged(topLeft, bottomRight) {
                            if (row.index < topLeft.row || row.index > bottomRight.row) return
                            if (!keyField.editing) keyField.text = row.key
                            if (!valField.editing) valField.text = row.value
                        }
                    }
                    EnvField {
                        id: keyField
                        Layout.preferredWidth: 220
                        mono: true
                        placeholder: "SCB_KEY"
                        Component.onCompleted: text = row.key
                        onEdited: scopebuddy.model.setKey(row.index, newText)
                    }
                    EnvField {
                        id: valField
                        Layout.fillWidth: true
                        mono: true
                        placeholder: "value"
                        Component.onCompleted: text = row.value
                        onEdited: scopebuddy.model.setValue(row.index, newText)
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
                        TapHandler { onTapped: scopebuddy.model.removeRow(row.index) }
                    }
                }

                footer: Item {
                    width: ListView.view.width
                    height: list.count === 0 ? 40 : 0
                    visible: list.count === 0 && !scopebuddy.loading
                    Text {
                        anchors.centerIn: parent
                        text: "No SCB_ keys yet — add one above or apply a preset."
                        color: Theme.faint
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !scopebuddy.loadError.length
                spacing: Theme.spaceSm
                PsButton {
                    text: "+ Add row"
                    primary: false
                    enabled: scopebuddy.loaded
                    onClicked: scopebuddy.model.addRow()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: scopebuddy.status
                    color: (scopebuddy.status.indexOf("failed") >= 0
                            || scopebuddy.status.indexOf("Not saved") >= 0)
                           ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: scopebuddy.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save"
                    enabled: scopebuddy.loaded && scopebuddy.dirty
                    onClicked: scopebuddy.save()
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
                subtitle: "Merge into the current config."
            }
            Repeater {
                model: scopebuddy.presetNames
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
                    TapHandler { onTapped: if (scopebuddy.loaded) scopebuddy.applyPreset(modelData) }
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
                        Text { text: "+"; color: Theme.primaryBright; font.pixelSize: 16; font.bold: true }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }
    }
}
