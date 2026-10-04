import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Displays: connected outputs + resolution/refresh switching. `display` controller.
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    // The `display` controller under another name. Inside a Button, a bare
    // `display` is the button's own `display` property (icon/text layout), so
    // `display.applyMode(...)` there fails with "not a function". Handlers on
    // buttons must go through this.
    readonly property var displayCtl: display

    function backendLabel(b) {
        if (b === "xrandr") return "X11 · xrandr"
        if (b === "hyprctl") return "Hyprland · hyprctl"
        if (b === "wlr-randr") return "Wayland · wlr-randr"
        if (b === "kscreen-doctor") return "KDE Wayland · kscreen-doctor"
        return "no display tool"
    }

    // Mimics Python's `{:g}` formatting (up to 6 significant figures, no
    // trailing zeros) so "144.000" reads as "144 Hz" and "59.940" as
    // "59.94 Hz" — matches core/display.py's DisplayMode.key/.label.
    function formatRefresh(r) {
        var s = r.toPrecision(6)
        if (s.indexOf(".") >= 0)
            s = s.replace(/0+$/, "").replace(/\.$/, "")
        return s + " Hz"
    }

    // The mode to go back to if a change isn't confirmed: {output, width,
    // height, refresh, label}. Set when Apply is pressed, cleared on Keep.
    property var pendingRevert: null
    // true while the revert itself is being applied (it must not ask again)
    property bool reverting: false

    function revertMode() {
        var p = page.pendingRevert
        if (!p) return
        page.reverting = true
        keepDialog.close()
        page.displayCtl.applyMode(p.output, p.width, p.height, p.refresh)
    }

    Connections {
        target: display
        function onModeApplied(output) {
            if (page.reverting) {
                page.reverting = false
                page.pendingRevert = null
            } else if (page.pendingRevert && page.pendingRevert.output === output) {
                keepDialog.open()
            }
        }
    }

    // A new mode can leave the screen black or unreadable. Unless it is
    // confirmed, the previous mode comes back on its own.
    PsDialog {
        id: keepDialog
        property int secondsLeft: 15
        title: "Keep this display mode?"
        width: 440
        closePolicy: Popup.CloseOnEscape
        onOpened: {
            secondsLeft = 15
            sounds.play("notification")
        }
        // closed without an answer (Escape, the close button): go back
        onClosed: if (page.pendingRevert && !page.reverting) page.revertMode()
        Timer {
            interval: 1000
            repeat: true
            running: keepDialog.opened
            onTriggered: {
                keepDialog.secondsLeft -= 1
                if (keepDialog.secondsLeft <= 0)
                    page.revertMode()
            }
        }
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "Going back to " + (page.pendingRevert ? page.pendingRevert.label : "the previous mode")
                      + " in " + keepDialog.secondsLeft + (keepDialog.secondsLeft === 1 ? " second" : " seconds")
                      + " unless you keep the new one."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Go back"; primary: false; sound: "back"
                    onClicked: page.revertMode()
                }
                PsButton {
                    text: "Keep this mode"
                    onClicked: {
                        page.pendingRevert = null
                        keepDialog.close()
                    }
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        PsSectionHeader {
            Layout.fillWidth: true
            text: "Displays"
            subtitle: display.backend.length ? page.backendLabel(display.backend)
                                             : "Resolution and refresh rate"
        }
        BusyIndicator {
            running: display.loading; visible: display.loading
            implicitWidth: 22; implicitHeight: 22
        }
        PsButton {
            text: "Refresh"; primary: false
            onClicked: page.displayCtl.refresh()
        }
    }

    // status line
    Text {
        Layout.fillWidth: true
        visible: display.status.length > 0
        text: display.status
        wrapMode: Text.WordWrap
        color: display.statusOk ? Theme.success : Theme.danger
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
    }

    // no backend / no outputs placeholder
    PsCard {
        Layout.fillWidth: true
        Layout.preferredHeight: 120
        visible: !display.loading && display.outputs.length === 0
        Text {
            anchors.centerIn: parent
            width: parent.width - 2 * Theme.spaceLg
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: display.backend.length
                  ? "No connected outputs reported by " + display.backend + "."
                  : "No display tool found. Install xrandr (X11), wlr-randr (wlroots), or use KDE's kscreen-doctor."
            color: Theme.faint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsSmall
        }
    }

    // outputs
    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        visible: display.outputs.length > 0

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceLg

            Repeater {
                model: display.outputs
                delegate: PsCard {
                    id: outCard
                    required property var modelData
                    onModelDataChanged: outCol.resetSelection()
                    Layout.fillWidth: true
                    glowing: modelData.primary
                    Layout.preferredHeight: outCol.implicitHeight + 2 * Theme.spaceLg

                    ColumnLayout {
                        id: outCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceLg
                        spacing: Theme.space

                        // header row: name + primary/current badges
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Text {
                                text: outCard.modelData.name
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsTitle
                                font.weight: Font.Bold
                            }
                            Rectangle {
                                visible: outCard.modelData.primary
                                implicitWidth: primLbl.implicitWidth + 16
                                implicitHeight: 20
                                radius: 10
                                color: Theme.surfaceElevated
                                border.color: Theme.primary
                                border.width: 1
                                Text {
                                    id: primLbl
                                    anchors.centerIn: parent
                                    text: "primary"
                                    color: Theme.primaryBright
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }
                            Item { Layout.fillWidth: true }
                            Text {
                                visible: outCard.modelData.currentLabel.length > 0
                                text: outCard.modelData.currentLabel
                                color: Theme.primaryBright
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsSmall
                                font.weight: Font.Bold
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                        // resolution + refresh rate pickers
                        // Unique WxH keys, largest first (modelData.modes is
                        // already sorted by area desc, then refresh desc).
                        property var resKeys: {
                            var seen = ({})
                            var out = []
                            var modes = outCard.modelData.modes
                            for (var i = 0; i < modes.length; i++) {
                                var key = modes[i].width + "x" + modes[i].height
                                if (!seen[key]) {
                                    seen[key] = true
                                    out.push(key)
                                }
                            }
                            return out
                        }
                        property string selectedRes: ""
                        property var refreshRates: {
                            var out = []
                            var modes = outCard.modelData.modes
                            var parts = outCol.selectedRes.split("x")
                            var w = parseInt(parts[0] || "0", 10)
                            var h = parseInt(parts[1] || "0", 10)
                            for (var i = 0; i < modes.length; i++)
                                if (modes[i].width === w && modes[i].height === h)
                                    out.push(modes[i].refresh)
                            return out
                        }
                        property string selectedRefresh: ""
                        // full mode key for the current selection, in the same
                        // "WxH@refresh.mmm" shape as core/display.py's
                        // DisplayMode.key, so it can be compared directly.
                        property string selectedKey: outCol.selectedRes.length && outCol.selectedRefresh.length
                                ? outCol.selectedRes + "@" + parseFloat(outCol.selectedRefresh).toFixed(3)
                                : ""

                        function resetSelection() {
                            var parts = outCard.modelData.currentKey.split("@")
                            outCol.selectedRes = parts[0] || (outCol.resKeys.length ? outCol.resKeys[0] : "")
                            resSelect.currentIndex = outCol.resKeys.indexOf(outCol.selectedRes)
                            outCol.selectedRefresh = outCol.refreshRates.length ? String(outCol.refreshRates[0]) : ""
                            refreshSelect.currentIndex = 0
                            if (parts.length > 1) {
                                var want = parseFloat(parts[1])
                                for (var i = 0; i < outCol.refreshRates.length; i++) {
                                    if (Math.abs(outCol.refreshRates[i] - want) < 0.001) {
                                        outCol.selectedRefresh = String(outCol.refreshRates[i])
                                        refreshSelect.currentIndex = i
                                        break
                                    }
                                }
                            }
                        }
                        Component.onCompleted: outCol.resetSelection()

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space

                            ColumnLayout {
                                spacing: Theme.spaceXs
                                Text {
                                    text: "Resolution"
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                    font.weight: Font.DemiBold
                                }
                                PsSelect {
                                    id: resSelect
                                    Layout.preferredWidth: 160
                                    enabled: outCol.resKeys.length > 0
                                    model: outCol.resKeys
                                    Accessible.name: "Resolution for " + outCard.modelData.name
                                    onChosen: {
                                        outCol.selectedRes = value
                                        // default the refresh pick to the
                                        // highest rate for the new resolution
                                        refreshSelect.currentIndex = 0
                                        outCol.selectedRefresh = outCol.refreshRates.length
                                                ? String(outCol.refreshRates[0]) : ""
                                    }
                                }
                            }

                            ColumnLayout {
                                spacing: Theme.spaceXs
                                Text {
                                    text: "Refresh rate"
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                    font.weight: Font.DemiBold
                                }
                                PsSelect {
                                    id: refreshSelect
                                    Layout.preferredWidth: 140
                                    enabled: outCol.refreshRates.length > 0
                                    model: outCol.refreshRates.map(function (r) { return String(r) })
                                    displayMap: {
                                        var m = ({})
                                        for (var i = 0; i < outCol.refreshRates.length; i++)
                                            m[String(outCol.refreshRates[i])] = page.formatRefresh(outCol.refreshRates[i])
                                        return m
                                    }
                                    Accessible.name: "Refresh rate for " + outCard.modelData.name
                                    onChosen: outCol.selectedRefresh = value
                                }
                            }

                            Item { Layout.fillWidth: true }

                            ColumnLayout {
                                Layout.alignment: Qt.AlignBottom
                                spacing: Theme.spaceXs
                                Text {
                                    text: outCard.modelData.currentKey.length
                                          ? "Current: " + outCard.modelData.currentKey.split("@")[0] + " @ "
                                            + page.formatRefresh(parseFloat(outCard.modelData.currentKey.split("@")[1]))
                                          : "Current mode not detected"
                                    color: Theme.faint
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                                PsButton {
                                    text: "Apply"
                                    enabled: outCol.selectedKey.length > 0
                                             && outCol.selectedKey !== outCard.modelData.currentKey
                                    Accessible.name: "Apply mode to " + outCard.modelData.name
                                    onClicked: {
                                        // remember the mode to return to if this one isn't kept
                                        var cur = outCard.modelData.currentKey.split("@")
                                        var curRes = cur[0].split("x")
                                        page.reverting = false
                                        page.pendingRevert = cur.length > 1 ? {
                                            output: outCard.modelData.name,
                                            width: parseInt(curRes[0], 10),
                                            height: parseInt(curRes[1], 10),
                                            refresh: parseFloat(cur[1]),
                                            label: cur[0] + " @ " + page.formatRefresh(parseFloat(cur[1]))
                                        } : null
                                        var parts = outCol.selectedRes.split("x")
                                        page.displayCtl.applyMode(outCard.modelData.name,
                                                          parseInt(parts[0], 10),
                                                          parseInt(parts[1], 10),
                                                          parseFloat(outCol.selectedRefresh))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
