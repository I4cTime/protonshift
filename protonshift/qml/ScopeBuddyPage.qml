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
                    color: Theme.successTint
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
                        color: modelData.ok ? Theme.successTint : Theme.bgDeep
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
                    text: "- no supported backend detected"
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
                    text: "ScopeBuddy (scb) isn't installed - you can still edit the config for later."
                }
            }

            // read error → no editor, so save can't overwrite
            Rectangle {
                Layout.fillWidth: true
                visible: scopebuddy.loadError.length > 0
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
                    text: "Couldn't read scb.conf - editing disabled so nothing gets overwritten.\n" + scopebuddy.loadError
                }
            }

            // known-key quick-add chips
            Flow {
                Layout.fillWidth: true
                visible: !scopebuddy.loadError.length
                spacing: Theme.spaceXs
                Repeater {
                    model: scopebuddy.knownKeys
                    delegate: PsChip {
                        required property string modelData
                        text: "+ " + modelData
                        mono: true
                        enabled: scopebuddy.loaded
                        Accessible.name: "Add key " + modelData
                        onClicked: scopebuddy.addKey(modelData)
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
                    PsIconButton {
                        glyph: "✕"
                        danger: true
                        label: "Remove " + (row.key.length > 0 ? row.key : "this row")
                        onClicked: scopebuddy.model.removeRow(row.index)
                    }
                }

                footer: Item {
                    width: ListView.view.width
                    height: list.count === 0 ? 40 : 0
                    visible: list.count === 0 && !scopebuddy.loading
                    Text {
                        anchors.centerIn: parent
                        text: "No SCB_ keys yet - add one above or apply a preset."
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
                    color: scopebuddy.statusOk ? Theme.success : Theme.danger
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
                delegate: PsRowButton {
                    required property string modelData
                    Layout.fillWidth: true
                    text: modelData
                    trailing: "+"
                    enabled: scopebuddy.loaded
                    Accessible.name: "Add preset " + modelData
                    onClicked: scopebuddy.applyPreset(modelData)
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
                        delegate: PsChip {
                            required property string modelData
                            text: modelData
                            mono: true
                            active: scbEnvvars.name === modelData
                            Accessible.name: "Edit snippet " + modelData
                            onClicked: scbEnvvars.select(modelData)
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
                    delegate: PsChip {
                        required property string modelData
                        text: "+ " + modelData
                        mono: true
                        Accessible.name: "Add key " + modelData
                        onClicked: scbEnvvars.addKey(modelData)
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
                    PsIconButton {
                        glyph: "✕"
                        danger: true
                        label: "Remove " + (sr.key.length > 0 ? sr.key : "this row")
                        onClicked: scbEnvvars.model.removeRow(sr.index)
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton { text: "+ Add row"; primary: false; enabled: scbEnvvars.loaded; onClicked: scbEnvvars.model.addRow() }
                PsButton {
                    text: "Delete snippet"; primary: false; danger: true
                    visible: scbEnvvars.exists
                    onClicked: deleteSnippetConfirm.open()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: scbEnvvars.status
                    color: scbEnvvars.statusOk ? Theme.success : Theme.danger
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                Text { visible: scbEnvvars.dirty; text: "● unsaved"; color: Theme.primaryBright; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption }
                PsButton { text: "Save"; enabled: scbEnvvars.loaded && scbEnvvars.dirty; onClicked: scbEnvvars.save() }
            }
        }
    }

    // Deleting a snippet removes envvars/<name>.conf outright — confirm first.
    PsDialog {
        id: deleteSnippetConfirm
        title: "Delete snippet?"
        width: 380
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "“" + scbEnvvars.name + "” will be permanently removed."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Cancel"; primary: false
                    onClicked: deleteSnippetConfirm.close()
                }
                PsButton {
                    text: "Delete"; primary: false; danger: true
                    onClicked: {
                        scbEnvvars.deleteSnippet()
                        deleteSnippetConfirm.close()
                    }
                }
            }
        }
    }
}
