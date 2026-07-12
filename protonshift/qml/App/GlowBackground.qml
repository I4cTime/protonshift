import QtQuick
import QtQuick.Effects
import App

// Ambient background: a deep base with two large violet glows slowly drifting.
// GPU-composited, cheap, and it's the kind of "luster" the web build had —
// here done natively with a blur effect instead of CSS.
Item {
    id: root
    clip: true

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.bg }
            GradientStop { position: 1.0; color: Theme.bgDeep }
        }
    }

    Item {
        id: blobs
        anchors.fill: parent

        Rectangle {
            id: blobA
            width: 460; height: 460; radius: width / 2
            color: Theme.primaryDeep
            opacity: 0.28
            x: -80; y: -120
            SequentialAnimation on x {
                loops: Animation.Infinite
                NumberAnimation { to: root.width * 0.35; duration: 14000; easing.type: Easing.InOutSine }
                NumberAnimation { to: -80; duration: 14000; easing.type: Easing.InOutSine }
            }
        }
        Rectangle {
            id: blobB
            width: 520; height: 520; radius: width / 2
            color: Theme.glow
            opacity: 0.20
            x: root.width - 360; y: root.height - 380
            SequentialAnimation on y {
                loops: Animation.Infinite
                NumberAnimation { to: root.height - 520; duration: 18000; easing.type: Easing.InOutSine }
                NumberAnimation { to: root.height - 300; duration: 18000; easing.type: Easing.InOutSine }
            }
        }

        layer.enabled: true
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1.0
            blurMax: 64
        }
    }
}
