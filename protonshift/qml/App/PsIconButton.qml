import QtQuick
import App

// Square glyph button (remove "✕", refresh "↻"). `label` is what a screen
// reader says, since the glyph alone says nothing. Works by mouse and by
// keyboard (Tab to it, Space/Enter to press). Emits `clicked()`.
Rectangle {
    id: btn
    property alias glyph: lbl.text
    property string label: ""
    // destructive: turns red on hover
    property bool danger: false
    // keeps the glyph turning (a refresh in progress)
    property bool spinning: false
    signal clicked()

    function activate() {
        if (!btn.enabled)
            return
        sounds.play(btn.danger ? "back" : "click")
        btn.clicked()
    }

    implicitWidth: 28
    implicitHeight: 28
    radius: Theme.radiusSm
    opacity: btn.enabled ? 1.0 : 0.5
    color: hover.hovered ? (btn.danger ? Theme.dangerSurface : Theme.surfaceElevated) : "transparent"
    border.width: 1
    border.color: hover.hovered ? (btn.danger ? Theme.danger : Theme.borderStrong) : Theme.border

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: btn.label
    Accessible.onPressAction: btn.activate()
    Keys.onSpacePressed: btn.activate()
    Keys.onReturnPressed: btn.activate()
    Keys.onEnterPressed: btn.activate()

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: btn.activate() }

    Text {
        id: lbl
        anchors.centerIn: parent
        color: hover.hovered ? (btn.danger ? Theme.danger : Theme.primaryBright) : Theme.muted
        font.pixelSize: 13
        RotationAnimation on rotation {
            running: btn.spinning
            loops: Animation.Infinite
            from: 0; to: 360; duration: 900
            onRunningChanged: if (!running) lbl.rotation = 0
        }
    }

    // keyboard focus ring
    Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: parent.radius + 3
        color: "transparent"
        border.width: 2
        border.color: Theme.accentBright
        visible: btn.activeFocus
    }
}
