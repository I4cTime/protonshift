import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// A labelled toggle row: title + optional subtitle on the left, violet switch
// on the right. Emits `toggled(checked)` on user interaction.
RowLayout {
    id: row
    property alias text: title.text
    property string subtitle: ""
    property bool checked: false
    signal toggled(bool value)

    spacing: Theme.space
    Layout.fillWidth: true

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 1
        Text {
            id: title
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
            font.weight: Font.Medium
        }
        Text {
            text: row.subtitle
            visible: row.subtitle.length > 0
            color: Theme.faint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsCaption
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    Switch {
        id: sw
        Accessible.name: title.text
        onToggled: row.toggled(checked)

        // A plain `checked: row.checked` binding is destroyed by the first
        // user toggle, so later external changes to the bound config value
        // (e.g. an optimistic toggle the backend reverted) would never
        // re-sync the switch. A Binding element survives direct writes and
        // re-asserts whenever row.checked changes.
        Binding on checked {
            value: row.checked
            restoreMode: Binding.RestoreBindingOrValue
        }

        indicator: Rectangle {
            implicitWidth: 46
            implicitHeight: 26
            radius: 13
            color: sw.checked ? Theme.primary : Theme.surfaceElevated
            border.color: sw.checked ? Theme.primaryBright : Theme.border
            border.width: 1
            Behavior on color { ColorAnimation { duration: 150 } }

            // keyboard focus ring
            Rectangle {
                anchors.fill: parent
                anchors.margins: -3
                radius: height / 2
                color: "transparent"
                border.width: 2
                border.color: Theme.accentBright
                visible: sw.activeFocus && !sw.pressed
            }

            Rectangle {
                width: 20; height: 20; radius: 10
                y: 3
                x: sw.checked ? parent.width - width - 3 : 3
                color: Theme.knob
                Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
            }
        }
    }
}
