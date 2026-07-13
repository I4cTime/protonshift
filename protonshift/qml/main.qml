import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

ApplicationWindow {
    id: window
    visible: true
    width: 1040
    height: 720
    minimumWidth: 840
    minimumHeight: 560
    title: "ProtonShift"
    color: Theme.bg

    // ambient animated background
    GlowBackground { anchors.fill: parent }

    property int currentPage: 0
    readonly property var pages: ["Library", "Environment", "MangoHud", "ScopeBuddy", "Gamescope", "Displays", "System"]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceLg

        // --- header / wordmark ---------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Rectangle {
                width: 34; height: 34; radius: 10
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: Theme.gradA }
                    GradientStop { position: 1.0; color: Theme.gradB }
                }
                Text {
                    anchors.centerIn: parent
                    text: "»"   // placeholder mark (swap for the real logo asset later)
                    color: "#ffffff"
                    font.pixelSize: 20
                    font.bold: true
                }
            }

            RowLayout {
                spacing: 0
                Text {
                    text: "Proton"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsTitle
                    font.weight: Font.Bold
                }
                Text {
                    text: "Shift"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsTitle
                    font.weight: Font.Bold
                }
            }

            Item { width: Theme.spaceLg }

            // --- tabs ---
            RowLayout {
                spacing: Theme.spaceXs
                Repeater {
                    model: window.pages
                    delegate: Rectangle {
                        required property int index
                        required property string modelData
                        implicitWidth: tabLbl.implicitWidth + 2 * Theme.space
                        implicitHeight: 32
                        radius: Theme.radiusSm
                        property bool active: window.currentPage === index
                        color: active ? Theme.surfaceElevated
                                      : (tabHover.hovered ? Theme.surface : "transparent")
                        border.width: active ? 1 : 0
                        border.color: Theme.borderStrong
                        Behavior on color { ColorAnimation { duration: 120 } }
                        HoverHandler { id: tabHover }
                        TapHandler { onTapped: window.currentPage = index }
                        Text {
                            id: tabLbl
                            anchors.centerIn: parent
                            text: modelData
                            color: parent.active ? Theme.text : Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsSmall
                            font.weight: parent.active ? Font.DemiBold : Font.Normal
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "v" + appVersion
                color: Theme.faint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
        }

        // --- page stack -----------------------------------------------------
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.currentPage

            GamesPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            EnvironmentPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            MangoHudPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            ScopeBuddyPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            GamescopeBuilderPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            DisplayPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            SystemPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
