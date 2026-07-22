import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Labelled integer field with a violet focus ring. `value` is two-way friendly:
// read `value`, and handle `edited(newValue)` to write back. 0 renders as blank
// (the core treats 0 as "unset"), sidestepping the NaN/422 bug from the web app.
ColumnLayout {
    id: field
    property alias label: cap.text
    property int value: 0
    property int from: 0
    property int to: 7680
    property string placeholder: "auto"
    signal edited(int value)

    spacing: 4

    Text {
        id: cap
        color: Theme.muted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
        font.weight: Font.DemiBold
    }

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 38
        radius: Theme.radiusSm
        color: Theme.bgDeep
        border.width: input.activeFocus ? 2 : 1
        border.color: input.activeFocus ? Theme.primary : Theme.border
        Behavior on border.color { ColorAnimation { duration: 120 } }

        TextField {
            id: input
            anchors.fill: parent
            anchors.leftMargin: Theme.spaceSm
            anchors.rightMargin: Theme.spaceSm
            verticalAlignment: TextInput.AlignVCenter
            text: field.value > 0 ? String(field.value) : ""
            placeholderText: field.placeholder
            placeholderTextColor: Theme.faint
            color: Theme.text
            font.family: Theme.monoFamily
            font.pixelSize: Theme.fsSmall
            selectByMouse: true
            inputMethodHints: Qt.ImhDigitsOnly
            validator: IntValidator { bottom: field.from; top: field.to }
            background: Item {}

            onTextEdited: {
                var v = parseInt(text, 10)
                field.edited(isNaN(v) ? 0 : v)
            }
        }
    }
}
