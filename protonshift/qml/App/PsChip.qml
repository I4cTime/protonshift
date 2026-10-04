import QtQuick
import App

// Small pill button: filters ("All 6"), quick-adds ("+ MANGOHUD=1") and
// pickers. `active` marks the chosen one in a group. Works by mouse and by
// keyboard (Tab to it, Space/Enter to press). Emits `clicked()`.
Rectangle {
    id: chip
    property alias text: lbl.text
    property bool active: false
    property bool mono: false
    // visually quieter without being disabled (e.g. a tool that isn't installed)
    property bool dimmed: false
    signal clicked()

    function activate() {
        if (!chip.enabled)
            return
        sounds.play("click")
        chip.clicked()
    }

    implicitWidth: lbl.implicitWidth + 18
    implicitHeight: 24
    radius: 12
    opacity: chip.enabled ? (chip.dimmed ? 0.55 : 1.0) : 0.5
    color: (chip.active || hover.hovered) ? Theme.surfaceElevated : Theme.bgDeep
    border.color: (chip.active || hover.hovered) ? Theme.primary : Theme.border
    border.width: chip.active ? 2 : 1
    Behavior on color { ColorAnimation { duration: 100 } }

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: lbl.text
    Accessible.onPressAction: chip.activate()
    Keys.onSpacePressed: chip.activate()
    Keys.onReturnPressed: chip.activate()
    Keys.onEnterPressed: chip.activate()

    HoverHandler { id: hover }
    TapHandler { onTapped: chip.activate() }

    Text {
        id: lbl
        anchors.centerIn: parent
        color: (chip.active || hover.hovered) ? Theme.primaryBright : Theme.muted
        font.family: chip.mono ? Theme.monoFamily : Theme.fontFamily
        font.pixelSize: 10
        font.weight: chip.active ? Font.DemiBold : Font.Normal
    }

    // keyboard focus ring
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: height / 2
        color: "transparent"
        border.width: 2
        border.color: Theme.accentBright
        visible: chip.activeFocus
    }
}
