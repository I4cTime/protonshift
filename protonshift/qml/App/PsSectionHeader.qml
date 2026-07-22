import QtQuick
import QtQuick.Layouts
import App

// Small uppercase section label with a violet tick, plus optional subtitle.
ColumnLayout {
    property alias text: title.text
    property string subtitle: ""
    spacing: 2

    Accessible.role: Accessible.Heading
    Accessible.name: title.text

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceXs
        Rectangle {
            width: 3; height: 14; radius: 2
            color: Theme.primary
        }
        Text {
            id: title
            Layout.fillWidth: true
            elide: Text.ElideRight
            color: Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
            font.weight: Font.Bold
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 0.8
        }
    }
    Text {
        Layout.fillWidth: true
        text: parent.subtitle
        visible: parent.subtitle.length > 0
        wrapMode: Text.WordWrap
        color: Theme.faint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
        Layout.leftMargin: Theme.space
    }
}
