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

    // drop shadow / glow beneath the card
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: card.glowing ? Theme.glow : "#000000"
        shadowOpacity: card.glowing ? 0.45 : 0.35
        shadowBlur: card.glowing ? 1.0 : 0.6
        shadowVerticalOffset: 6
    }

    Item {
        id: inner
        anchors.fill: parent
    }
}
