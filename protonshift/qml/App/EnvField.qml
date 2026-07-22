import QtQuick
import QtQuick.Controls.Basic
import App

// Text field for editable model delegates. Exposes `editing` (has focus) so the
// delegate can re-sync `text` from the model on external changes without
// clobbering what the user is currently typing. Emits `edited(newText)`.
Rectangle {
    id: root
    property alias text: input.text
    property alias editing: input.activeFocus
    property string placeholder: ""
    property bool mono: false
    signal edited(string newText)

    implicitHeight: 34
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
        placeholderText: root.placeholder
        placeholderTextColor: Theme.faint
        color: Theme.text
        font.family: root.mono ? Theme.monoFamily : Theme.fontFamily
        font.pixelSize: Theme.fsSmall
        selectByMouse: true
        background: Item {}
        onTextEdited: root.edited(text)
    }
}
