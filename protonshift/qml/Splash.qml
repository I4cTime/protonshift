import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import App

// Branded startup overlay. NOT a separate window — it's an opaque layer that
// fills the main window, hiding the UI behind it for a beat, then fades out to
// reveal the app. (An earlier version used a second Window; nested Window.close()
// is unreliable across compositors and left a ghost window on screen.)
Item {
    id: splash

    // 1.0 = fully covering the app, 0.0 = gone. Drives every child's opacity.
    property real cover: 1.0
    visible: cover > 0.001
    signal finished()

    // opaque backdrop that masks the live UI during the intro
    Rectangle {
        anchors.fill: parent
        opacity: splash.cover
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bg }
            GradientStop { position: 1.0; color: Theme.bgDeep }
        }
    }

    // soft violet bloom behind the card
    Rectangle {
        anchors.centerIn: parent
        width: 520; height: 520; radius: 260
        color: Theme.glow
        opacity: splash.cover * 0.18
        layer.enabled: true
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1.0
            blurMax: 64
        }
    }

    // hold, then dissolve
    Timer {
        interval: 1000; running: true; repeat: false
        onTriggered: dissolve.start()
    }
    NumberAnimation {
        id: dissolve
        target: splash; property: "cover"
        from: 1.0; to: 0.0; duration: 360; easing.type: Easing.InQuad
        onFinished: splash.finished()
    }

    // --- the card -----------------------------------------------------------
    Rectangle {
        id: card
        anchors.centerIn: parent
        width: 360; height: 200
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.borderStrong
        border.width: 1
        opacity: splash.cover

        // subtle intro pop
        scale: 0.94
        Component.onCompleted: popIn.start()
        NumberAnimation {
            id: popIn
            target: card; property: "scale"
            from: 0.94; to: 1.0; duration: 320; easing.type: Easing.OutBack
        }

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.glow
            shadowOpacity: 0.5
            shadowBlur: 1.0
            shadowVerticalOffset: 8
        }

        ColumnLayout {
            anchors.centerIn: parent
            spacing: Theme.space
            width: parent.width - 2 * Theme.spaceLg

            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: Theme.spaceSm
                Rectangle {
                    width: 44; height: 44; radius: 12
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: Theme.gradA }
                        GradientStop { position: 1.0; color: Theme.gradB }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "»"; color: "#ffffff"; font.pixelSize: 26; font.bold: true
                    }
                }
                RowLayout {
                    spacing: 0
                    Text {
                        text: "Proton"; color: Theme.text
                        font.family: Theme.fontFamily; font.pixelSize: 28; font.weight: Font.Bold
                    }
                    Text {
                        text: "Shift"; color: Theme.primaryBright
                        font.family: Theme.fontFamily; font.pixelSize: 28; font.weight: Font.Bold
                    }
                }
            }

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Linux gaming, tuned."
                color: Theme.muted
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
            }

            // indeterminate sweep
            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: Theme.spaceSm
                width: 170; height: 4; radius: 2
                color: Theme.bgDeep
                clip: true
                Rectangle {
                    width: 66; height: parent.height; radius: 2
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: Theme.gradA }
                        GradientStop { position: 1.0; color: Theme.gradB }
                    }
                    SequentialAnimation on x {
                        loops: Animation.Infinite
                        NumberAnimation { from: -66; to: 170; duration: 850; easing.type: Easing.InOutQuad }
                        NumberAnimation { from: 170; to: -66; duration: 850; easing.type: Easing.InOutQuad }
                    }
                }
            }
        }
    }
}
