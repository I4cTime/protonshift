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

            Item { Layout.fillWidth: true }

            Text {
                text: "v" + appVersion
                color: Theme.faint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
        }

        // --- the slice ------------------------------------------------------
        GamescopeBuilderPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
