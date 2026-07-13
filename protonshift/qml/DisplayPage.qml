import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Displays: connected outputs + resolution/refresh switching. `display` controller.
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    function backendLabel(b) {
        if (b === "xrandr") return "X11 · xrandr"
        if (b === "wlr-randr") return "Wayland · wlr-randr"
        if (b === "kscreen-doctor") return "KDE Wayland · kscreen-doctor"
        return "no display tool"
    }

    RowLayout {
        Layout.fillWidth: true
        PsSectionHeader {
            Layout.fillWidth: true
            text: "Displays"
            subtitle: display.backend.length ? page.backendLabel(display.backend)
                                             : "Resolution and refresh rate"
        }
        BusyIndicator {
            running: display.loading; visible: display.loading
            implicitWidth: 22; implicitHeight: 22
        }
        PsButton {
            text: "Refresh"; primary: false
            onClicked: display.refresh()
        }
    }

    // status line
    Text {
        Layout.fillWidth: true
        visible: display.status.length > 0
        text: display.status
        wrapMode: Text.WordWrap
        color: (display.status.indexOf("Couldn't") >= 0 || display.status.indexOf("Failed") >= 0
                || display.status.indexOf("not found") >= 0) ? Theme.danger : Theme.success
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
    }

    // no backend / no outputs placeholder
    PsCard {
        Layout.fillWidth: true
        Layout.preferredHeight: 120
        visible: !display.loading && display.outputs.length === 0
        Text {
            anchors.centerIn: parent
            width: parent.width - 2 * Theme.spaceLg
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: display.backend.length
                  ? "No connected outputs reported by " + display.backend + "."
                  : "No display tool found. Install xrandr (X11), wlr-randr (wlroots), or use KDE's kscreen-doctor."
            color: Theme.faint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
        }
    }

    // outputs
    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        visible: display.outputs.length > 0

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceLg

            Repeater {
                model: display.outputs
                delegate: PsCard {
                    id: outCard
                    required property var modelData
                    Layout.fillWidth: true
                    glowing: modelData.primary
                    Layout.preferredHeight: outCol.implicitHeight + 2 * Theme.spaceLg

                    ColumnLayout {
                        id: outCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.space

                        // header row: name + primary/current badges
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Text {
                                text: outCard.modelData.name
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsTitle
                                font.weight: Font.Bold
                            }
                            Rectangle {
                                visible: outCard.modelData.primary
                                implicitWidth: primLbl.implicitWidth + 16
                                implicitHeight: 20
                                radius: 10
                                color: Theme.surfaceElevated
                                border.color: Theme.primary
                                border.width: 1
                                Text {
                                    id: primLbl
                                    anchors.centerIn: parent
                                    text: "primary"
                                    color: Theme.primaryBright
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                visible: outCard.modelData.currentLabel.length > 0
                                text: outCard.modelData.currentLabel
                                color: Theme.primaryBright
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsSmall
                                font.weight: Font.Bold
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                        // mode grid — click to apply
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.spaceXs

                            Repeater {
                                model: outCard.modelData.modes
                                delegate: Rectangle {
                                    id: modeChip
                                    required property var modelData
                                    property bool active: modeChip.modelData.key === outCard.modelData.currentKey
                                    implicitWidth: modeLbl.implicitWidth + 22
                                    implicitHeight: 30
                                    radius: Theme.radiusSm
                                    color: active ? Theme.surfaceElevated
                                                  : (mh.hovered ? Theme.surface : Theme.bgDeep)
                                    border.color: active ? Theme.primary : (mh.hovered ? Theme.borderStrong : Theme.border)
                                    border.width: active ? 2 : 1
                                    Behavior on color { ColorAnimation { duration: 100 } }
                                    HoverHandler { id: mh }
                                    TapHandler {
                                        onTapped: if (!modeChip.active)
                                            display.applyMode(outCard.modelData.name,
                                                              modeChip.modelData.width,
                                                              modeChip.modelData.height,
                                                              modeChip.modelData.refresh)
                                    }
                                    Text {
                                        id: modeLbl
                                        anchors.centerIn: parent
                                        text: modeChip.modelData.label
                                        color: modeChip.active ? Theme.text
                                                               : (mh.hovered ? Theme.text : Theme.muted)
                                        font.family: Theme.monoFamily
                                        font.pixelSize: Theme.fsCaption
                                        font.weight: modeChip.active ? Font.Bold : Font.Normal
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
