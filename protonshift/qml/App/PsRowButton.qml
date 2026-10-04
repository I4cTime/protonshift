import QtQuick
import QtQuick.Layouts
import App

// Full-width list row that acts as a button: preset lists, option lists.
// `active` marks the chosen row; `trailing` is an optional glyph at the right
// ("+" for "adds to the list"). Works by mouse and by keyboard. Emits `clicked()`.
Rectangle {
    id: row
    property alias text: lbl.text
    property string trailing: ""
    property bool active: false
    signal clicked()

    function activate() {
        if (!row.enabled)
            return
        sounds.play("click")
        row.clicked()
    }

    implicitHeight: 40
    radius: Theme.radiusSm
    opacity: row.enabled ? 1.0 : 0.5
    color: (row.active || hover.hovered) ? Theme.surfaceElevated : Theme.bgDeep
    border.color: row.active ? Theme.primary : (hover.hovered ? Theme.borderStrong : Theme.border)
    border.width: row.active ? 2 : 1
    Behavior on color { ColorAnimation { duration: 120 } }

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: lbl.text
    Accessible.onPressAction: row.activate()
    Keys.onSpacePressed: row.activate()
    Keys.onReturnPressed: row.activate()
    Keys.onEnterPressed: row.activate()

    HoverHandler { id: hover }
    TapHandler { onTapped: row.activate() }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spaceSm
        anchors.rightMargin: Theme.spaceSm
        Text {
            id: lbl
            Layout.fillWidth: true
            elide: Text.ElideRight
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
            font.weight: row.active ? Font.Bold : Font.Medium
        }
        Text {
            visible: row.trailing.length > 0
            text: row.trailing
            color: Theme.primaryBright
            font.pixelSize: 16
            font.bold: true
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
        visible: row.activeFocus
    }
}
