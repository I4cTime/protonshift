import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// System dashboard: GPU, power profile, session/host info. `system` controller.
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    function tempColor(t) {
        if (t < 0) return Theme.muted
        if (t < 55) return Theme.success
        if (t < 78) return "#f0b048"
        return Theme.danger
    }

    RowLayout {
        Layout.fillWidth: true
        PsSectionHeader {
            Layout.fillWidth: true
            text: "System"
            subtitle: "Hardware, drivers, and session"
        }
        BusyIndicator {
            running: system.loading; visible: system.loading
            implicitWidth: 22; implicitHeight: 22
        }
        PsButton {
            text: "Refresh"; primary: false
            onClicked: system.refresh()
        }
    }

    // --- GPU + power row ---------------------------------------------------
    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Theme.spaceLg

        // GPU(s)
        PsCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            glowing: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.space

                PsSectionHeader { Layout.fillWidth: true; text: "Graphics" }

                Text {
                    visible: system.gpus.length === 0 && !system.loading
                    text: "No GPU detected."
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                Repeater {
                    model: system.gpus
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        Text {
                            Layout.fillWidth: true
                            text: modelData.name
                            wrapMode: Text.WordWrap
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsTitle
                            font.weight: Font.Bold
                        }
                        RowLayout {
                            spacing: Theme.spaceSm
                            Repeater {
                                model: [
                                    { l: "Driver", v: modelData.driver || "—" },
                                    { l: "VRAM", v: modelData.vramMb >= 0 ? (modelData.vramMb + " MB") : "—" }
                                ]
                                delegate: Rectangle {
                                    id: chipItem
                                    required property var modelData
                                    implicitWidth: chipRow.implicitWidth + 20
                                    implicitHeight: 26
                                    radius: 13
                                    color: Theme.bgDeep
                                    border.color: Theme.border
                                    border.width: 1
                                    RowLayout {
                                        id: chipRow
                                        anchors.centerIn: parent
                                        spacing: 5
                                        Text {
                                            text: chipItem.modelData.l
                                            color: Theme.faint
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fsCaption
                                        }
                                        Text {
                                            text: chipItem.modelData.v
                                            color: Theme.text
                                            font.family: Theme.monoFamily
                                            font.pixelSize: Theme.fsCaption
                                            font.weight: Font.DemiBold
                                        }
                                    }
                                }
                            }
                            Item { Layout.fillWidth: true }
                            // temperature
                            RowLayout {
                                spacing: 6
                                visible: modelData.temperature >= 0
                                Rectangle {
                                    width: 10; height: 10; radius: 5
                                    color: page.tempColor(modelData.temperature)
                                }
                                Text {
                                    text: Math.round(modelData.temperature) + "°C"
                                    color: page.tempColor(modelData.temperature)
                                    font.family: Theme.monoFamily
                                    font.pixelSize: Theme.fsBody
                                    font.weight: Font.Bold
                                }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; height: 1; color: Theme.border
                            visible: index < system.gpus.length - 1
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }

        // Power profile
        PsCard {
            Layout.preferredWidth: 300
            Layout.fillHeight: true
            visible: system.powerProfiles.length > 0
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.space
                PsSectionHeader { Layout.fillWidth: true; text: "Power profile" }

                Repeater {
                    model: system.powerProfiles
                    delegate: Rectangle {
                        required property string modelData
                        Layout.fillWidth: true
                        implicitHeight: 44
                        radius: Theme.radiusSm
                        property bool active: system.currentProfile === modelData
                        color: active ? Theme.surfaceElevated : (pw.hovered ? Theme.surface : Theme.bgDeep)
                        border.color: active ? Theme.primary : Theme.border
                        border.width: active ? 2 : 1
                        Behavior on color { ColorAnimation { duration: 120 } }
                        HoverHandler { id: pw }
                        TapHandler { onTapped: system.setPowerProfile(modelData) }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.space
                            anchors.rightMargin: Theme.space
                            Text {
                                Layout.fillWidth: true
                                text: modelData.charAt(0).toUpperCase() + modelData.slice(1)
                                color: parent.parent.active ? Theme.text : Theme.muted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                                font.weight: parent.parent.active ? Font.Bold : Font.Normal
                            }
                            Rectangle {
                                visible: parent.parent.active
                                width: 8; height: 8; radius: 4; color: Theme.primary
                            }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: system.status.length > 0
                    text: system.status
                    wrapMode: Text.WordWrap
                    color: system.status.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Item { Layout.fillHeight: true }
            }
        }
    }

    // --- system info -------------------------------------------------------
    PsCard {
        Layout.fillWidth: true
        Layout.preferredHeight: infoGrid.implicitHeight + 2 * Theme.spaceLg + 24
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space
            PsSectionHeader { Layout.fillWidth: true; text: "Session" }
            GridLayout {
                id: infoGrid
                Layout.fillWidth: true
                columns: 3
                columnSpacing: Theme.spaceXl
                rowSpacing: Theme.space
                Repeater {
                    model: [
                        { l: "Distro", v: system.systemInfo.distro || "—" },
                        { l: "Kernel", v: system.systemInfo.kernel || "—" },
                        { l: "CPU", v: system.systemInfo.cpu || "—" },
                        { l: "Session", v: system.systemInfo.sessionType || "—" },
                        { l: "Desktop", v: system.systemInfo.desktop || "—" },
                        { l: "Arch", v: system.systemInfo.arch || "—" }
                    ]
                    delegate: ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: modelData.l
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.DemiBold
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.v
                            wrapMode: Text.WrapAnywhere
                            color: Theme.text
                            font.family: Theme.monoFamily
                            font.pixelSize: Theme.fsSmall
                        }
                    }
                }
            }
        }
    }
}
