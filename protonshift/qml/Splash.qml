import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Effects
import App

// Branded startup splash: a frameless, translucent violet card that pulses
// briefly, then fades out and emits `finished`. Purely cosmetic — the app is
// interactive the moment it appears; this is the identity beat before it does.
Window {
    id: splash
    width: 440
    height: 280
    flags: Qt.SplashScreen | Qt.FramelessWindowHint
    color: "transparent"
    visible: true

    // center on the primary screen
    x: Screen.virtualX + (Screen.width - width) / 2
    y: Screen.virtualY + (Screen.height - height) / 2

    signal finished()

    // hold, then fade the whole thing out
    property real fade: 0.0
    NumberAnimation on fade {
        id: fadeIn
        from: 0.0; to: 1.0; duration: 260; easing.type: Easing.OutQuad
    }
    Timer {
        interval: 1100; running: true; repeat: false
        onTriggered: fadeOut.start()
    }
    NumberAnimation {
        id: fadeOut
        target: splash; property: "fade"
        from: 1.0; to: 0.0; duration: 260; easing.type: Easing.InQuad
        onFinished: { splash.finished(); splash.close() }
    }

    Item {
        anchors.fill: parent
        opacity: splash.fade

        // glow-backed card
        Rectangle {
            id: card
            anchors.centerIn: parent
            width: parent.width - 40
            height: parent.height - 40
            radius: Theme.radiusLg
            color: Theme.surface
            border.color: Theme.borderStrong
            border.width: 1
            scale: 0.96 + 0.04 * splash.fade

            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.glow
                shadowOpacity: 0.55
                shadowBlur: 1.0
                shadowVerticalOffset: 8
            }

            // faint top gradient sheen
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#1c1630" }
                    GradientStop { position: 1.0; color: "#00000000" }
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                spacing: Theme.space
                width: parent.width - 2 * Theme.spaceLg

                // logo mark + wordmark
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: Theme.spaceSm

                    Rectangle {
                        width: 46; height: 46; radius: 13
                        gradient: Gradient {
                            orientation: Gradient.Vertical
                            GradientStop { position: 0.0; color: Theme.gradA }
                            GradientStop { position: 1.0; color: Theme.gradB }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "»"
                            color: "#ffffff"
                            font.pixelSize: 27
                            font.bold: true
                        }
                    }
                    RowLayout {
                        spacing: 0
                        Text {
                            text: "Proton"
                            color: Theme.text
                            font.family: Theme.fontFamily
                            font.pixelSize: 30
                            font.weight: Font.Bold
                        }
                        Text {
                            text: "Shift"
                            color: Theme.primaryBright
                            font.family: Theme.fontFamily
                            font.pixelSize: 30
                            font.weight: Font.Bold
                        }
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "Linux gaming, tuned."
                    color: Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                // indeterminate sweep bar
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: Theme.spaceSm
                    width: 180; height: 4; radius: 2
                    color: Theme.bgDeep
                    clip: true
                    Rectangle {
                        width: 70; height: parent.height; radius: 2
                        gradient: Gradient {
                            orientation: Gradient.Horizontal
                            GradientStop { position: 0.0; color: Theme.gradA }
                            GradientStop { position: 1.0; color: Theme.gradB }
                        }
                        SequentialAnimation on x {
                            loops: Animation.Infinite
                            NumberAnimation { from: -70; to: 180; duration: 900; easing.type: Easing.InOutQuad }
                            NumberAnimation { from: 180; to: -70; duration: 900; easing.type: Easing.InOutQuad }
                        }
                    }
                }
            }

            // version, bottom-right
            Text {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.margins: Theme.spaceSm
                text: "v" + appVersion
                color: Theme.faint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
        }
    }
}
