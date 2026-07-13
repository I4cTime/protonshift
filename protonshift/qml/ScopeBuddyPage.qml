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

            // SCB_AUTO_* capability indicator: which display backend can drive
            // auto resolution / HDR / VRR on this session.
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Text {
                    text: "Auto res/HDR/VRR:"
                    color: Theme.muted
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                Repeater {
                    model: [
                        { l: "KDE", ok: scopebuddy.autoCaps.kde === true },
                        { l: "GNOME", ok: scopebuddy.autoCaps.gnome_gdctl === true },
                        { l: "wlroots", ok: scopebuddy.autoCaps.wlroots === true },
                        { l: "jq", ok: scopebuddy.autoCaps.jq === true }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        implicitWidth: capLbl.implicitWidth + 14
                        implicitHeight: 18
                        radius: 9
                        color: modelData.ok ? "#12281f" : Theme.bgDeep
                        border.color: modelData.ok ? Theme.success : Theme.border
                        border.width: 1
                        Text {
                            id: capLbl
                            anchors.centerIn: parent
                            text: (modelData.ok ? "✓ " : "· ") + modelData.l
                            color: modelData.ok ? Theme.success : Theme.faint
                            font.family: Theme.fontFamily; font.pixelSize: 10
                        }
                    }
                }
                Text {
                    visible: scopebuddy.autoCaps.any !== true
                    text: "— no supported backend detected"
                    color: Theme.faint
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Env snippets…"
                    primary: false
                    onClicked: scbSnippetsDialog.open()
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

    // ============================ ENV SNIPPETS DIALOG ======================
    PsDialog {
        id: scbSnippetsDialog
        objectName: "scbSnippetsDialog"
        width: 660
        title: "ScopeBuddy env snippets"
        subtitle: "Reusable envvars/*.conf snippets" + (scbEnvvars.name ? " · editing “" + scbEnvvars.name + "”" : "")

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            // snippet picker + create
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Text {
                    text: "Snippets:"
                    color: Theme.muted
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.spaceXs
                    Repeater {
                        model: scbEnvvars.snippets
                        delegate: Rectangle {
                            required property string modelData
                            implicitWidth: snLbl.implicitWidth + 18
                            implicitHeight: 24
                            radius: 12
                            property bool active: scbEnvvars.name === modelData
                            color: active ? Theme.surfaceElevated : (snh.hovered ? Theme.surface : Theme.bgDeep)
                            border.color: active ? Theme.primary : Theme.border
                            border.width: active ? 2 : 1
                            HoverHandler { id: snh }
                            TapHandler { onTapped: scbEnvvars.select(modelData) }
                            Text {
                                id: snLbl; anchors.centerIn: parent; text: modelData
                                color: active ? Theme.primaryBright : Theme.muted
                                font.family: Theme.monoFamily; font.pixelSize: 10
                            }
                        }
                    }
                    Text {
                        visible: scbEnvvars.snippets.length === 0
                        text: "none yet"
                        color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: 10
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 36; radius: Theme.radiusSm
                    color: Theme.bgDeep
                    border.width: newSnip.activeFocus ? 2 : 1
                    border.color: newSnip.activeFocus ? Theme.primary : Theme.border
                    TextField {
                        id: newSnip
                        anchors.fill: parent; anchors.leftMargin: Theme.spaceSm; anchors.rightMargin: Theme.spaceSm
                        verticalAlignment: TextInput.AlignVCenter
                        placeholderText: "New snippet name…"; placeholderTextColor: Theme.faint
                        color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
                        selectByMouse: true; background: Item {}
                    }
                }
                PsButton {
                    text: "New"; primary: false
                    enabled: newSnip.text.length > 0
                    onClicked: { scbEnvvars.create(newSnip.text); newSnip.text = "" }
                }
            }

            // known-key chips
            Flow {
                Layout.fillWidth: true
                visible: scbEnvvars.loaded
                spacing: Theme.spaceXs
                Repeater {
                    model: scbEnvvars.knownKeys
                    delegate: Rectangle {
                        required property string modelData
                        implicitWidth: kc.implicitWidth + 18; implicitHeight: 24; radius: 12
                        color: kch.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: kch.hovered ? Theme.primary : Theme.border; border.width: 1
                        HoverHandler { id: kch }
                        TapHandler { onTapped: scbEnvvars.addKey(modelData) }
                        Text { id: kc; anchors.centerIn: parent; text: "+ " + modelData; color: kch.hovered ? Theme.primaryBright : Theme.muted; font.family: Theme.monoFamily; font.pixelSize: 10 }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: !scbEnvvars.loaded
                text: "Pick a snippet above or create one to edit its keys."
                color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }

            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 0), 220)
                visible: scbEnvvars.loaded
                clip: true; spacing: 6
                model: scbEnvvars.model
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    id: sr
                    required property int index
                    required property string key
                    required property string value
                    width: ListView.view.width; spacing: Theme.spaceSm
                    Connections {
                        target: scbEnvvars.model
                        function onDataChanged(tl, br) {
                            if (sr.index < tl.row || sr.index > br.row) return
                            if (!skf.editing) skf.text = sr.key
                            if (!svf.editing) svf.text = sr.value
                        }
                    }
                    EnvField { id: skf; Layout.preferredWidth: 200; mono: true; placeholder: "SCB_KEY"; Component.onCompleted: text = sr.key; onEdited: scbEnvvars.model.setKey(sr.index, newText) }
                    EnvField { id: svf; Layout.fillWidth: true; mono: true; placeholder: "value"; Component.onCompleted: text = sr.value; onEdited: scbEnvvars.model.setValue(sr.index, newText) }
                    Rectangle {
                        width: 28; height: 28; radius: Theme.radiusSm
                        color: srm.hovered ? "#2a1216" : "transparent"
                        border.width: 1; border.color: srm.hovered ? Theme.danger : Theme.border
                        Text { anchors.centerIn: parent; text: "✕"; color: srm.hovered ? Theme.danger : Theme.muted; font.pixelSize: 12 }
                        HoverHandler { id: srm }
                        TapHandler { onTapped: scbEnvvars.model.removeRow(sr.index) }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton { text: "+ Add row"; primary: false; enabled: scbEnvvars.loaded; onClicked: scbEnvvars.model.addRow() }
                PsButton { text: "Delete snippet"; primary: false; danger: true; visible: scbEnvvars.exists; onClicked: scbEnvvars.deleteSnippet() }
                Item { Layout.fillWidth: true }
                Text {
                    text: scbEnvvars.status
                    color: scbEnvvars.status.indexOf("failed") >= 0 || scbEnvvars.status.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                Text { visible: scbEnvvars.dirty; text: "● unsaved"; color: Theme.primaryBright; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption }
                PsButton { text: "Save"; enabled: scbEnvvars.loaded && scbEnvvars.dirty; onClicked: scbEnvvars.save() }
            }
        }
    }
}
