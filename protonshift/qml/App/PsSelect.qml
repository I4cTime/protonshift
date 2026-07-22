import QtQuick
import QtQuick.Controls.Basic
import App

// Styled dropdown over a plain string-list model. `displayMap` optionally maps
// raw ids to friendly labels; `currentText` is the raw selected id.
// Emits `chosen(value)` on user selection.
ComboBox {
    id: control
    property var displayMap: ({})
    signal chosen(string value)

    function labelFor(v) {
        if (displayMap[v] !== undefined)
            return displayMap[v]
        return v === "" ? "Steam default" : v
    }

    implicitHeight: 38
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fsSmall
    Accessible.name: control.labelFor(control.currentText)

    onActivated: control.chosen(control.currentText)

    // focus-visible: same treatment as the open-popup state
    background: Rectangle {
        radius: Theme.radiusSm
        color: control.enabled ? Theme.bgDeep : Theme.surface
        opacity: control.enabled ? 1.0 : 0.5
        border.color: (control.popup.visible || control.activeFocus) ? Theme.primary : Theme.border
        border.width: (control.popup.visible || control.activeFocus) ? 2 : 1
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }

    contentItem: Text {
        leftPadding: Theme.spaceSm
        rightPadding: 28
        text: control.labelFor(control.currentText)
        color: Theme.text
        font: control.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        x: control.width - width - Theme.spaceSm
        y: (control.height - height) / 2
        text: "▾"
        color: Theme.muted
        font.pixelSize: 12
    }

    delegate: ItemDelegate {
        id: item
        required property var modelData
        required property int index
        width: control.width
        height: 34
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            leftPadding: Theme.spaceSm
            text: control.labelFor(item.modelData)
            color: item.highlighted ? Theme.primaryBright : Theme.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            color: item.highlighted ? Theme.surfaceElevated : "transparent"
        }
    }

    popup: Popup {
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(listview.contentHeight + 8, 280)
        padding: 4
        background: Rectangle {
            radius: Theme.radiusSm
            color: Theme.surface
            border.color: Theme.borderStrong
            border.width: 1
        }
        contentItem: ListView {
            id: listview
            clip: true
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollBar.vertical: ScrollBar {}
        }
    }
}
