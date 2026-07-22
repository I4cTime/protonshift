import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Controllers: detect gamepads, copy an SDL mapping, live-test buttons/axes,
// and rumble. `gamepad` controller.
RowLayout {
    id: page
    spacing: Theme.spaceLg

    function typeGlyph(t) {
        if (t === "xbox") return "🎮"
        if (t === "playstation") return "🎮"
        if (t === "nintendo") return "🕹"
        if (t === "steam") return "🎮"
        return "🎮"
    }

    // ============================ LIST =====================================
    PsCard {
        Layout.preferredWidth: 360
        Layout.fillHeight: true
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Controllers"
                    subtitle: gamepad.controllers.length + " connected"
                }
                BusyIndicator { running: gamepad.loading; visible: gamepad.loading; implicitWidth: 20; implicitHeight: 20 }
                PsButton { text: "Refresh"; primary: false; onClicked: gamepad.refresh() }
            }

            Text {
                Layout.fillWidth: true
                visible: gamepad.controllers.length === 0 && !gamepad.loading
                wrapMode: Text.WordWrap
                text: "No controllers detected. Connect a gamepad (USB or Bluetooth). In Flatpak this needs the input device permission."
                color: Theme.faint
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
            }

            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true; spacing: 6
                model: gamepad.controllers
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    id: ctrlRow
                    required property var modelData
                    width: ListView.view.width
                    implicitHeight: 64
                    radius: Theme.radiusSm
                    property bool active: gamepad.testingPath === modelData.devicePath
                    color: active ? Theme.surfaceElevated : Theme.bgDeep
                    border.color: active ? Theme.primary : Theme.border
                    border.width: active ? 2 : 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: 2
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: page.typeGlyph(modelData.type); font.pixelSize: 16 }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                elide: Text.ElideRight
                                color: Theme.text
                                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall; font.weight: Font.DemiBold
                            }
                        }
                        Text {
                            text: modelData.devicePath + "  ·  " + modelData.vendor + ":" + modelData.product
                            color: Theme.faint
                            font.family: Theme.monoFamily; font.pixelSize: 10
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceXs
                            PsButton {
                                text: ctrlRow.active ? "Stop test" : "Test"
                                primary: false
                                implicitHeight: 28
                                onClicked: ctrlRow.active
                                           ? gamepad.stopTest()
                                           : gamepad.startTest(ctrlRow.modelData.devicePath, ctrlRow.modelData.name)
                            }
                            PsButton { text: "Rumble"; primary: false; implicitHeight: 28; onClicked: gamepad.rumble(modelData.devicePath) }
                            PsButton { text: "Copy SDL"; primary: false; implicitHeight: 28; onClicked: gamepad.copyMapping(modelData.id) }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: gamepad.status.length > 0
                text: gamepad.status
                wrapMode: Text.WordWrap
                color: (gamepad.status.indexOf("Couldn't") >= 0 || gamepad.status.indexOf("not supported") >= 0
                        || gamepad.status.indexOf("No force") >= 0) ? Theme.danger : Theme.success
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
        }
    }

    // ============================ TESTER ===================================
    PsCard {
        Layout.fillWidth: true
        Layout.fillHeight: true
        glowing: gamepad.testingPath.length > 0
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space

            PsSectionHeader {
                Layout.fillWidth: true
                text: "Live tester"
                subtitle: gamepad.testingPath.length > 0 ? gamepad.testingName : "Press “Test” on a controller"
            }

            Text {
                Layout.fillWidth: true
                visible: gamepad.testingPath.length === 0
                text: "Button presses and stick/trigger movement will show here in real time."
                wrapMode: Text.WordWrap
                color: Theme.faint
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
            }

            // buttons
            PsSectionHeader { Layout.fillWidth: true; text: "Buttons"; visible: gamepad.testingPath.length > 0 }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                visible: gamepad.testingPath.length > 0
                Repeater {
                    // model on the COUNT only: the buttons list is re-emitted at
                    // ~60Hz while testing, and a list model would destroy and
                    // recreate every delegate each tick (killing the Behaviors).
                    // Persistent delegates read their own slot out of the list.
                    model: gamepad.buttons.length
                    delegate: Rectangle {
                        id: buttonCell
                        required property int index
                        readonly property bool pressed: gamepad.buttons[buttonCell.index] ? true : false
                        width: 34; height: 34; radius: 8
                        color: pressed ? Theme.primary : Theme.bgDeep
                        border.color: pressed ? Theme.primaryBright : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 60 } }
                        Text {
                            anchors.centerIn: parent
                            text: buttonCell.index
                            color: buttonCell.pressed ? Theme.onPrimary : Theme.faint
                            font.family: Theme.monoFamily; font.pixelSize: 11; font.weight: Font.Bold
                        }
                    }
                }
            }

            // axes
            PsSectionHeader { Layout.fillWidth: true; text: "Axes"; visible: gamepad.testingPath.length > 0 }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                visible: gamepad.testingPath.length > 0
                Repeater {
                    // count-only model for the same reason as the buttons above:
                    // keep delegates alive across the ~60Hz axes re-emits so the
                    // x/width Behaviors actually animate.
                    model: gamepad.axes.length
                    delegate: RowLayout {
                        id: axisRow
                        required property int index
                        readonly property real axisValue: {
                            var v = gamepad.axes[axisRow.index]
                            return v === undefined ? 0 : v
                        }
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Text {
                            text: "a" + axisRow.index
                            color: Theme.muted
                            font.family: Theme.monoFamily; font.pixelSize: 11
                            Layout.preferredWidth: 28
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 12; radius: 6
                            color: Theme.bgDeep
                            border.color: Theme.border; border.width: 1
                            // centre marker
                            Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 1; height: parent.height; color: Theme.border }
                            Rectangle {
                                // fill from centre toward the axis value
                                height: parent.height - 2; y: 1; radius: 5
                                color: Theme.primary
                                x: axisRow.axisValue >= 0 ? parent.width / 2 : parent.width / 2 * (1 + axisRow.axisValue)
                                width: Math.max(2, Math.abs(axisRow.axisValue) * parent.width / 2)
                                Behavior on x { NumberAnimation { duration: 40 } }
                                Behavior on width { NumberAnimation { duration: 40 } }
                            }
                        }
                        Text {
                            text: axisRow.axisValue.toFixed(2)
                            color: Theme.primaryBright
                            font.family: Theme.monoFamily; font.pixelSize: 11
                            Layout.preferredWidth: 42
                            horizontalAlignment: Text.AlignRight
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }
}
