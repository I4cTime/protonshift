import QtQuick
import QtQuick.Effects
import App

// Elevated surface with a soft violet drop-glow. Default container for panels.
Rectangle {
    id: card
    property bool glowing: false
    default property alias content: inner.data

    radius: Theme.radiusLg
    color: Theme.surface
    border.color: glowing ? Theme.borderStrong : Theme.border
    border.width: 1

    Behavior on border.color { ColorAnimation { duration: 180 } }

    // Drop shadow / glow beneath the card. RectangularShadow is computed
    // analytically (no per-card FBO like the previous layer+MultiEffect,
    // which re-rendered the whole card on any content change). The card is
    // an opaque rounded rect, so the silhouette is identical; blur values
    // mirror the old shadowBlur (0.6 / 1.0) x MultiEffect's 32px blurMax.
    // z < 0 paints the child below the parent's own fill.
    RectangularShadow {
        anchors.fill: parent
        z: -1
        radius: card.radius
        blur: card.glowing ? 32 : 19
        spread: 0
        offset.y: 6
        color: card.glowing ? Qt.alpha(Theme.glow, 0.45)
                            : Qt.alpha(Theme.shadow, Theme.shadowOpacity)
    }

    Item {
        id: inner
        anchors.fill: parent
    }
}
