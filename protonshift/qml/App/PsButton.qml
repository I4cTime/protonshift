import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import App

// Branded button. `primary` gives the violet gradient with a press animation;
// otherwise a quiet ghost style.
Button {
    id: control
    property bool primary: true
    // destructive style: red text + border on the ghost variant
    property bool danger: false

    implicitHeight: 40
    implicitWidth: Math.max(96, contentItem.implicitWidth + 2 * Theme.space)
    padding: Theme.spaceSm
    font.family: Theme.fontFamily
    font.pixelSize: Theme.fsSmall
    font.weight: Font.DemiBold

    scale: control.pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }

    // Button already provides Accessible.Button role + Space/Enter activation
    // and is tab-focusable (StrongFocus); we only add an explicit name.
    Accessible.name: control.text

    contentItem: Text {
        text: control.text
        color: control.primary ? Theme.onPrimary : (control.danger ? Theme.danger : Theme.text)
        opacity: control.enabled ? 1.0 : 0.5
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: Theme.radius
        opacity: control.enabled ? 1.0 : 0.45
        border.width: control.primary ? 0 : 1
        border.color: control.danger ? Theme.danger : Theme.borderStrong
        color: control.primary ? "transparent"
                                : (control.hovered ? (control.danger ? Theme.dangerSurface : Theme.surfaceElevated) : "transparent")

        // gradient fill for the primary variant (kept as its own rect so we
        // never conditionally swap the `gradient` property). Hover must NOT
        // swap the stops to primaryBright/primary: Theme.onPrimary is only
        // contrast-verified against gradA/gradB, and onPrimary on
        // primaryBright fails WCAG in violet-night and sandstone. Hover is
        // signalled via the glow shadow below instead.
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            visible: control.primary
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: Theme.gradA }
                GradientStop { position: 1.0; color: Theme.gradB }
            }
        }

        // keyboard focus ring — drawn inside the button bounds so the
        // primary variant's layer effect can't clip it
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: "transparent"
            border.width: 2
            border.color: Theme.accentBright
            visible: control.activeFocus && !control.pressed
        }

        layer.enabled: control.primary
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.glow
            shadowOpacity: control.hovered ? 0.6 : 0.35
            shadowBlur: 0.8
            shadowVerticalOffset: 3
        }
    }
}
