import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Labelled slider with a live value readout and a violet fill.
ColumnLayout {
    id: root
    property alias label: cap.text
    property real from: 0
    property real to: 20
    property real value: 5
    property real stepSize: 1
    signal moved(real value)

    spacing: 4

    RowLayout {
        Layout.fillWidth: true
        Text {
            id: cap
            Layout.fillWidth: true
            color: Theme.muted
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsCaption
            font.weight: Font.DemiBold
        }
        Text {
            text: Math.round(slider.value)
            color: Theme.primaryBright
            font.family: Theme.monoFamily
            font.pixelSize: Theme.fsSmall
            font.weight: Font.Bold
        }
    }

    Slider {
        id: slider
        Layout.fillWidth: true
        from: root.from
        to: root.to
        value: root.value
        stepSize: root.stepSize
        onMoved: root.moved(value)

        background: Rectangle {
            x: slider.leftPadding
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: slider.availableWidth
            height: 6
            radius: 3
            color: Theme.surfaceElevated

            Rectangle {
                width: slider.visualPosition * parent.width
                height: parent.height
                radius: 3
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Theme.gradA }
                    GradientStop { position: 1.0; color: Theme.gradB }
                }
            }
        }

        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
            y: slider.topPadding + slider.availableHeight / 2 - height / 2
            width: 18; height: 18; radius: 9
            color: "#ffffff"
            border.color: Theme.primary
            border.width: slider.pressed ? 3 : 2
            scale: slider.pressed ? 1.15 : 1.0
            Behavior on scale { NumberAnimation { duration: 90 } }
        }
    }
}
