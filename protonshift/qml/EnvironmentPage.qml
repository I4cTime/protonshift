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
                    subtitle: env.targetPath + " · log out/in to apply"
                }
                BusyIndicator {
                    running: env.loading
                    visible: env.loading
                    implicitWidth: 22; implicitHeight: 22
                }
            }

            // #47: where the variables go. environment.d only reaches desktops
            // started by systemd's user manager; ~/.xsessionrc and ~/.profile
            // cover the classic display-manager sessions (Cinnamon/XFCE/MATE…).
            RowLayout {
                id: targetRow
                Layout.fillWidth: true
                spacing: Theme.spaceSm

                // id list + id→label map derived once from the controller's table
                property var targetIds: env.targetNames.map(function (t) { return t.id })
                property var targetLabels: {
                    var m = {}
                    for (var i = 0; i < env.targetNames.length; i++)
                        m[env.targetNames[i].id] = env.targetNames[i].label
                    return m
                }
                // reads env.target, so bindings on it re-evaluate on a switch
                function currentTarget() {
                    for (var i = 0; i < env.targetNames.length; i++)
                        if (env.targetNames[i].id === env.target)
                            return env.targetNames[i]
                    return null
                }

                Text {
                    text: "Where variables go"
                    color: Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    font.weight: Font.DemiBold
                }
                PsSelect {
                    id: targetSelect
                    Layout.preferredWidth: 220
                    enabled: !env.loading
                    model: targetRow.targetIds
                    displayMap: targetRow.targetLabels
                    onChosen: env.setTarget(value)
                    function syncCurrent() {
                        currentIndex = targetRow.targetIds.indexOf(env.target)
                    }
                    Component.onCompleted: syncCurrent()
                    Connections {
                        target: env
                        function onTargetChanged() { targetSelect.syncCurrent() }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    property var cur: targetRow.currentTarget()
                    text: cur ? cur.path + " · read by " + cur.readBy : ""
                    elide: Text.ElideRight
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
            }

            // #22 made visible: a real read error is its own state, not "empty"
            Rectangle {
                Layout.fillWidth: true
                visible: env.loadError.length > 0
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
                    text: "Couldn't read the config - not showing an editor so a save can't overwrite it.\n" + env.loadError
                }
            }

            // #47: the selected target isn't what this desktop reads (e.g.
            // environment.d on Cinnamon/XFCE/MATE/startx, which systemd didn't
            // start). Say so, and offer the one-click switch, instead of letting
            // "Saved" imply it works.
            Rectangle {
                Layout.fillWidth: true
                visible: env.sessionWarning.length > 0
                radius: Theme.radiusSm
                color: Theme.warningSurface
                border.color: Theme.warningBorder
                border.width: 1
                implicitHeight: warnRow.implicitHeight + 2 * Theme.spaceSm
                RowLayout {
                    id: warnRow
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    spacing: Theme.spaceSm
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                        text: env.sessionWarning
                    }
                    PsButton {
                        text: "Use recommended"
                        primary: false
                        visible: env.recommendedTarget.length > 0 && env.recommendedTarget !== env.target
                        enabled: !env.loading
                        onClicked: env.setTarget(env.recommendedTarget)
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
                // key column tracks the editor width so narrow windows keep a usable value field
                property int keyColWidth: Math.max(140, Math.min(220, Math.round(width * 0.3)))
                model: env.model
                visible: !env.loadError.length
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}

                header: RowLayout {
                    width: ListView.view.width
                    height: keyHead.implicitHeight + 6
                    spacing: Theme.spaceSm
                    Text {
                        Layout.preferredWidth: list.keyColWidth
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
                        Layout.preferredWidth: list.keyColWidth
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
                    PsIconButton {
                        glyph: "✕"
                        danger: true
                        label: "Remove " + (row.key.length > 0 ? row.key : "this variable")
                        onClicked: env.model.removeRow(row.index)
                    }
                }

                footer: Item {
                    width: ListView.view.width
                    height: list.count === 0 ? 40 : 0
                    visible: list.count === 0 && !env.loading
                    Text {
                        anchors.centerIn: parent
                        text: "No variables yet - add one or apply a preset."
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
                Text {
                    Layout.fillWidth: true
                    text: env.status
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignRight
                    color: env.statusOk ? Theme.success : Theme.danger
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
                // #47 escape hatch: the same rows as `KEY=value %command%`, for
                // a game's Steam launch options when no session file works.
                PsButton {
                    text: "Copy as Steam launch options"
                    primary: false
                    enabled: env.loaded && env.launchPrefix.length > 0
                    onClicked: env.copyLaunchPrefix()
                }
                PsButton {
                    text: "Save"
                    // enabled only once a load succeeded and there are edits (#21)
                    enabled: env.loaded && env.dirty
                    sound: ""  // the outcome chime says it
                    onClicked: { env.save(); sounds.result(env.statusOk) }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: !env.loadError.length
                text: "Copy as launch options: paste into a game's launch options if nothing else works."
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                color: Theme.faint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
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

            // scrolls when the preset list outgrows the window
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: Theme.space

                    Repeater {
                        model: env.presetNames
                        delegate: PsRowButton {
                            required property string modelData
                            Layout.fillWidth: true
                            text: modelData
                            trailing: "+"
                            enabled: env.loaded
                            Accessible.name: "Add preset " + modelData
                            onClicked: env.applyPreset(modelData)
                        }
                    }
                }
            }
        }
    }
}
