import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Effects
import App

// Modal dialog: dimmed backdrop, elevated violet-glow card, title + close.
// Put content as children; they fill the body area below the header.
Popup {
    id: dlg
    property alias title: titleText.text
    property string subtitle: ""
    default property alias content: body.data

    modal: true
    dim: true
    anchors.centerIn: Overlay.overlay
    width: 640
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: "#cc07060e" }

    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150; easing.type: Easing.OutQuad }
        NumberAnimation { property: "scale"; from: 0.96; to: 1; duration: 150; easing.type: Easing.OutQuad }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 110 }
    }

    background: Rectangle {
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.borderStrong
        border.width: 1
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.glow
            shadowOpacity: 0.5
            shadowBlur: 1.0
            shadowVerticalOffset: 10
        }
    }

    contentItem: ColumnLayout {
        spacing: 0

        // header
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Theme.spaceLg
            Layout.bottomMargin: Theme.space
            spacing: Theme.space
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                Text {
                    id: titleText
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsTitle
                    font.weight: Font.Bold
                }
                Text {
                    text: dlg.subtitle
                    visible: dlg.subtitle.length > 0
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
            }
            Rectangle {
                width: 30; height: 30; radius: Theme.radiusSm
                color: closeH.hovered ? Theme.surfaceElevated : "transparent"
                border.color: closeH.hovered ? Theme.borderStrong : "transparent"
                border.width: 1
                Text { anchors.centerIn: parent; text: "✕"; color: Theme.muted; font.pixelSize: 14 }
                HoverHandler { id: closeH }
                TapHandler { onTapped: dlg.close() }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

        // body — children land here
        Item {
            id: body
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            Layout.margins: Theme.spaceLg
        }
    }
}
