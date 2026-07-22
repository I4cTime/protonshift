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

    // Only animate while the window is focused and the item is visible — the
    // full-window blur layer below re-renders every animation frame, so the
    // GPU idles whenever the app is unfocused/minimized.
    readonly property bool animating: root.visible && Window.active

    Item {
        id: blobs
        anchors.fill: parent

        // Blobs animate a 0..1 progress and bind x/y to it, so positions
        // track the CURRENT size — animating x/y directly snapshots
        // root.width/height into `to:` at loop start and drifts after a
        // resize.
        Rectangle {
            id: blobA
            property real t: 0
            width: 460; height: 460; radius: width / 2
            color: Theme.primaryDeep
            opacity: 0.28 * Theme.ambientStrength
            x: -80 + t * (root.width * 0.35 + 80); y: -120
            SequentialAnimation on t {
                running: root.animating
                loops: Animation.Infinite
                NumberAnimation { to: 1; duration: 14000; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0; duration: 14000; easing.type: Easing.InOutSine }
            }
        }
        Rectangle {
            id: blobB
            // 0 → y = height-300, 1 → y = height-520; starts at the old
            // rest position height-380.
            property real t: 80 / 220
            width: 520; height: 520; radius: width / 2
            color: Theme.glow
            opacity: 0.20 * Theme.ambientStrength
            x: root.width - 360; y: root.height - 300 - t * 220
            SequentialAnimation on t {
                running: root.animating
                loops: Animation.Infinite
                NumberAnimation { to: 1; duration: 18000; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0; duration: 18000; easing.type: Easing.InOutSine }
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
