pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Diagnose: one ranked list of the reasons a game may not start or run well,
// each with its evidence and, where the fix is mechanical, a previewed
// one-click fix that can be undone. The page hands in the game, the
// controller (`diagnose`) and the sound player; everything else is read from
// the controller, which only ever gives plain rows and maps.
PsDialog {
    id: dlg
    objectName: "diagnoseDialog"
    title: "Diagnose"
    subtitle: dlg.game.name || ""
    width: Overlay.overlay ? Math.min(720, Overlay.overlay.width - 2 * Theme.spaceLg) : 720
    focus: true

    // --- set by the page ------------------------------------------------------
    property var controller: null          // DiagnoseController
    property var soundPlayer: null         // SoundController
    property var game: ({})                // the selected library row
    property bool launchDirty: false       // the launch options editor has unsaved edits
    property string protondbTier: ""       // "" when unknown or lookups are off

    signal openLogRequested()

    // --- derived --------------------------------------------------------------
    readonly property string gameId: dlg.game.appId || ""
    readonly property bool isShortcut: (dlg.game.source || "") === "shortcut"
    readonly property bool isNative: (dlg.game.prefixKind || "") === "none"
    readonly property bool ready: dlg.controller !== null
    readonly property bool running: dlg.ready && dlg.controller.running
    readonly property bool busy: dlg.ready && dlg.controller.busy
    readonly property bool steamRunning: dlg.ready && dlg.controller.steamRunning === "yes"
    readonly property var preview: dlg.ready ? dlg.controller.preview : ({})
    // a result sound for a run the user started (not the re-run after a fix)
    property bool announce: false
    property bool showOk: false

    readonly property var order: ["blocking", "likely", "advice", "context", "ok"]
    readonly property var headings: ({
        "blocking": "Stops the game from starting",
        "likely": "Probably the cause",
        "advice": "Worth trying",
        "context": "For context",
        "ok": "Checked and fine"
    })
    readonly property var groups: {
        var rows = dlg.ready ? dlg.controller.findings : []
        var out = []
        for (var s = 0; s < dlg.order.length; s++) {
            var items = []
            for (var i = 0; i < rows.length; i++)
                if (rows[i].severity === dlg.order[s]) items.push(rows[i])
            if (items.length > 0)
                out.push({ severity: dlg.order[s], items: items })
        }
        return out
    }

    function toneFor(severity) {
        if (severity === "blocking") return Theme.danger
        if (severity === "likely") return Theme.warning
        if (severity === "advice") return Theme.primary
        if (severity === "ok") return Theme.success
        return Theme.muted
    }
    function glyphFor(severity) {
        if (severity === "blocking") return "✕"
        if (severity === "likely") return "!"
        if (severity === "advice") return "›"
        if (severity === "ok") return "✓"
        return "i"
    }
    function play(name) {
        if (dlg.soundPlayer) dlg.soundPlayer.play(name)
    }
    function runDiagnosis() {
        if (!dlg.ready || dlg.gameId.length === 0)
            return
        dlg.announce = true
        dlg.controller.run(dlg.gameId, dlg.game.installPath || "", dlg.game.compatdataPath || "",
                           dlg.isShortcut, dlg.isShortcut ? (dlg.game.launchOptions || "") : "",
                           dlg.isNative, dlg.protondbTier)
    }

    onOpened: { dlg.showOk = false; dlg.runDiagnosis() }
    // another game selected while open: diagnose that one, never show the old list
    onGameIdChanged: if (dlg.opened) { dlg.showOk = false; dlg.runDiagnosis() }
    onClosed: if (dlg.ready) dlg.controller.clearPreview()

    Connections {
        target: dlg.controller
        function onRunningChanged() {
            if (dlg.controller.running || !dlg.announce)
                return
            dlg.announce = false
            if (!dlg.opened)
                return
            var counts = dlg.controller.counts
            if (dlg.controller.error.length > 0 || counts.blocking > 0) dlg.play("error")
            else if (counts.likely > 0) dlg.play("notification")
            else dlg.play("success")
        }
    }

    // A one-line notice with a tone. Used for the "before you start" banners.
    component Banner: Rectangle {
        id: banner
        property alias text: bannerText.text
        property color tone: Theme.warning
        property color fill: Theme.warningSurface
        Layout.fillWidth: true
        implicitHeight: bannerText.implicitHeight + 2 * Theme.spaceSm
        radius: Theme.radiusSm
        color: banner.fill
        border.width: 1
        border.color: banner.tone
        Accessible.role: Accessible.AlertMessage
        Accessible.name: bannerText.text
        Text {
            id: bannerText
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            wrapMode: Text.WordWrap
            color: banner.tone
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsCaption
        }
    }

    // A selectable monospace block that wraps anywhere, so a long log line
    // never widens the dialog.
    component MonoBlock: Rectangle {
        id: mono
        property alias text: monoText.text
        property bool quiet: false
        Layout.fillWidth: true
        implicitHeight: monoText.implicitHeight + 2 * Theme.spaceXs
        radius: Theme.radiusSm
        color: Theme.bgDeep
        border.width: 1
        border.color: Theme.border
        TextEdit {
            id: monoText
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.spaceXs
            readOnly: true
            selectByMouse: true
            activeFocusOnTab: false
            wrapMode: TextEdit.WrapAnywhere
            color: mono.quiet ? Theme.faint : Theme.text
            selectionColor: Theme.primary
            selectedTextColor: Theme.onPrimary
            font.family: Theme.monoFamily
            font.pixelSize: Theme.fsCaption
        }
    }

    // A small text link that opens in the browser, by mouse or keyboard.
    component LinkText: Text {
        id: link
        property string url: ""
        function activate() { if (link.url.length > 0) Qt.openUrlExternally(link.url) }
        color: Theme.primaryBright
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
        font.underline: linkHover.hovered || link.activeFocus
        activeFocusOnTab: true
        Accessible.role: Accessible.Link
        Accessible.name: link.text
        Accessible.description: link.url
        Accessible.onPressAction: link.activate()
        Keys.onReturnPressed: link.activate()
        Keys.onEnterPressed: link.activate()
        Keys.onSpacePressed: link.activate()
        HoverHandler { id: linkHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: link.activate() }
    }

    ColumnLayout {
        id: content
        width: parent.width
        spacing: Theme.space

        // ===== 1. summary ======================================================
        ColumnLayout {
            id: top
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                BusyIndicator {
                    running: dlg.running
                    visible: dlg.running
                    implicitWidth: 20
                    implicitHeight: 20
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: dlg.running ? "Diagnosing…"
                          : (dlg.ready && dlg.controller.error.length > 0 ? dlg.controller.error
                             : (dlg.ready ? dlg.controller.summary : ""))
                    color: dlg.running ? Theme.muted
                           : (dlg.ready && dlg.controller.error.length > 0 ? Theme.danger
                              : (dlg.ready && dlg.controller.hasBlocking ? Theme.danger
                                 : (dlg.ready && dlg.controller.counts.likely > 0 ? Theme.text : Theme.success)))
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsBody
                    font.weight: Font.DemiBold
                    Accessible.role: Accessible.StaticText
                    Accessible.name: text
                }
            }
            Text {
                Layout.fillWidth: true
                visible: text.length > 0
                wrapMode: Text.WordWrap
                text: dlg.ready ? dlg.controller.checked : ""
                color: Theme.faint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            // ===== 2. banners ==================================================
            Banner {
                visible: dlg.steamRunning && dlg.ready && dlg.controller.canApply
                text: "Steam is running. It rewrites its settings when it closes, so a fix applied now can be lost. Quit Steam first."
            }
            Banner {
                visible: dlg.launchDirty && !dlg.isShortcut
                text: "You have unsaved launch options. Diagnose looked at what is saved in Steam."
            }
            Banner {
                visible: dlg.isShortcut
                tone: Theme.muted
                fill: Theme.bgDeep
                text: "ProtonShift can't write a Non-Steam shortcut's launch options. Use Copy and paste the line into the shortcut's properties in Steam."
            }
        }

        // ===== 3. findings, grouped by severity ================================
        Flickable {
            id: listFlick
            Layout.fillWidth: true
            // Never taller than what the window leaves, so the undo bar and the
            // footer stay in view and the list scrolls inside the dialog.
            readonly property real budget: {
                var avail = Overlay.overlay ? Overlay.overlay.height : 900
                // PsDialog's own margins, header and divider, then everything here but the list
                var chrome = 2 * Theme.spaceLg + Theme.spaceLg + Theme.space + Theme.fsTitle * 1.6
                             + (dlg.subtitle.length > 0 ? Theme.fsCaption * 1.5 : 0) + 1 + 2 * Theme.spaceLg
                var rest = top.implicitHeight + undoBar.implicitHeight * (undoBar.visible ? 1 : 0)
                           + footer.implicitHeight + 3 * content.spacing
                return Math.max(160, avail - chrome - rest)
            }
            Layout.preferredHeight: Math.min(findingsCol.implicitHeight, budget)
            visible: dlg.groups.length > 0
            contentWidth: width
            contentHeight: findingsCol.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: findingsCol
                // room on the right for the scroll bar
                width: listFlick.width - Theme.spaceSm
                spacing: Theme.space

                Repeater {
                    model: dlg.groups
                    delegate: ColumnLayout {
                        id: group
                        required property var modelData
                        readonly property bool isOk: group.modelData.severity === "ok"
                        readonly property bool expanded: !group.isOk || dlg.showOk
                        readonly property color tone: dlg.toneFor(group.modelData.severity)
                        Layout.fillWidth: true
                        spacing: Theme.spaceXs

                        // group heading; the "fine" group is a button that folds it open
                        AbstractButton {
                            id: heading
                            Layout.fillWidth: true
                            implicitHeight: headingRow.implicitHeight + 4
                            enabled: group.isOk
                            focusPolicy: group.isOk ? Qt.StrongFocus : Qt.NoFocus
                            text: dlg.headings[group.modelData.severity]
                                  + (group.isOk ? " (" + group.modelData.items.length + ")" : "")
                            Accessible.role: group.isOk ? Accessible.Button : Accessible.Heading
                            Accessible.name: heading.text
                            Accessible.description: group.isOk ? (dlg.showOk ? "Shown, press to hide" : "Hidden, press to show") : ""
                            onClicked: { dlg.play("click"); dlg.showOk = !dlg.showOk }
                            HoverHandler { enabled: group.isOk; cursorShape: Qt.PointingHandCursor }
                            background: Rectangle {
                                radius: Theme.radiusSm
                                color: "transparent"
                                border.width: 2
                                border.color: Theme.accentBright
                                visible: heading.activeFocus
                            }
                            contentItem: RowLayout {
                                id: headingRow
                                spacing: Theme.spaceXs
                                Rectangle {
                                    implicitWidth: 3
                                    implicitHeight: 14
                                    radius: 2
                                    color: group.tone
                                }
                                Text {
                                    visible: group.isOk
                                    text: dlg.showOk ? "\u25be" : "\u25b8"
                                    color: Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsSmall
                                }
                                Text {
                                    Layout.fillWidth: true
                                    elide: Text.ElideRight
                                    text: heading.text
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsSmall
                                    font.weight: Font.Bold
                                    font.capitalization: Font.AllUppercase
                                    font.letterSpacing: 0.8
                                }
                            }
                        }

                        Repeater {
                            model: group.expanded ? group.modelData.items : []
                            delegate: Rectangle {
                                id: row
                                required property var modelData
                                readonly property var finding: row.modelData
                                readonly property bool previewing: dlg.preview.findingId === row.finding.id
                                Layout.fillWidth: true
                                implicitHeight: rowLayout.implicitHeight + 2 * Theme.spaceSm
                                radius: Theme.radiusSm
                                color: Theme.bgDeep
                                border.width: row.previewing ? 2 : 1
                                border.color: row.previewing ? Theme.primary
                                              : ((row.finding.severity === "blocking" || row.finding.severity === "likely")
                                                 ? group.tone : Theme.border)
                                Accessible.role: Accessible.ListItem
                                Accessible.name: dlg.headings[row.finding.severity] + ": " + row.finding.title
                                Accessible.description: row.finding.cause

                                RowLayout {
                                    id: rowLayout
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: Theme.spaceSm
                                    spacing: Theme.spaceSm

                                    // tone marker
                                    Rectangle {
                                        Layout.alignment: Qt.AlignTop
                                        implicitWidth: 20
                                        implicitHeight: 20
                                        radius: 10
                                        color: "transparent"
                                        border.width: 1
                                        border.color: group.tone
                                        Text {
                                            anchors.centerIn: parent
                                            text: dlg.glyphFor(row.finding.severity)
                                            color: group.tone
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 11
                                            font.bold: true
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: Theme.spaceXs

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: Theme.spaceXs
                                            Text {
                                                Layout.fillWidth: true
                                                text: row.finding.title
                                                wrapMode: Text.WordWrap
                                                color: Theme.text
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fsSmall
                                                font.weight: Font.DemiBold
                                            }
                                            Rectangle {
                                                visible: row.finding.origin === "user"
                                                Layout.alignment: Qt.AlignTop
                                                implicitWidth: yoursText.implicitWidth + 12
                                                implicitHeight: 18
                                                radius: 9
                                                color: Theme.surfaceElevated
                                                border.width: 1
                                                border.color: Theme.primary
                                                Accessible.role: Accessible.StaticText
                                                Accessible.name: "Your own fix"
                                                Text {
                                                    id: yoursText
                                                    anchors.centerIn: parent
                                                    text: "yours"
                                                    color: Theme.primaryBright
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: 10
                                                    font.weight: Font.DemiBold
                                                }
                                            }
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: row.finding.cause.length > 0
                                            text: row.finding.cause
                                            wrapMode: Text.Wrap
                                            color: Theme.muted
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fsCaption
                                        }
                                        MonoBlock {
                                            visible: row.finding.evidence.length > 0
                                            text: row.finding.evidence
                                        }
                                        Text {
                                            Layout.fillWidth: true
                                            visible: row.finding.fix.length > 0
                                            text: "What to do: " + row.finding.fix
                                            wrapMode: Text.Wrap
                                            color: Theme.text
                                            font.family: Theme.fontFamily
                                            font.pixelSize: Theme.fsCaption
                                        }
                                        // manual steps (shown here unless the preview below lists them)
                                        Repeater {
                                            model: row.previewing ? [] : row.finding.manual
                                            delegate: Text {
                                                required property string modelData
                                                Layout.fillWidth: true
                                                text: "• " + modelData
                                                wrapMode: Text.Wrap
                                                color: Theme.text
                                                font.family: Theme.fontFamily
                                                font.pixelSize: Theme.fsCaption
                                            }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            visible: row.finding.source.length > 0 || (row.finding.canApply && !row.previewing)
                                            spacing: Theme.spaceSm
                                            LinkText {
                                                visible: row.finding.source.length > 0
                                                text: "Where this comes from"
                                                url: row.finding.source
                                            }
                                            Item { Layout.fillWidth: true }
                                            PsButton {
                                                visible: row.finding.canApply && !row.previewing
                                                text: "Fix this"
                                                primary: false
                                                implicitHeight: 32
                                                enabled: !dlg.running && !dlg.busy
                                                Accessible.name: "Fix this: " + row.finding.title
                                                onClicked: dlg.controller.openPreview(row.finding.id)
                                            }
                                        }

                                        // ===== 5. the fix, before and after ======
                                        Rectangle {
                                            id: previewPanel
                                            visible: row.previewing
                                            Layout.fillWidth: true
                                            implicitHeight: row.previewing ? previewCol.implicitHeight + 2 * Theme.spaceSm : 0
                                            radius: Theme.radiusSm
                                            color: Theme.surface
                                            border.width: 1
                                            border.color: Theme.borderStrong

                                            ColumnLayout {
                                                id: previewCol
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.top: parent.top
                                                anchors.margins: Theme.spaceSm
                                                spacing: Theme.spaceXs

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: "What this fix changes"
                                                    color: Theme.text
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                    font.weight: Font.Bold
                                                }

                                                // launch options before and after
                                                Text {
                                                    visible: row.previewing && dlg.preview.launchChanged === true
                                                    text: "Launch options now"
                                                    color: Theme.faint
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }
                                                MonoBlock {
                                                    visible: row.previewing && dlg.preview.launchChanged === true
                                                    quiet: (dlg.preview.beforeLaunch || "").length === 0
                                                    text: (dlg.preview.beforeLaunch || "").length > 0 ? dlg.preview.beforeLaunch : "Nothing set"
                                                }
                                                Text {
                                                    visible: row.previewing && dlg.preview.launchChanged === true
                                                    text: "After the fix"
                                                    color: Theme.faint
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }
                                                MonoBlock {
                                                    visible: row.previewing && dlg.preview.launchChanged === true
                                                    quiet: (dlg.preview.afterLaunch || "").length === 0
                                                    text: (dlg.preview.afterLaunch || "").length > 0 ? dlg.preview.afterLaunch : "Nothing set"
                                                }

                                                // Proton build before and after
                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: row.previewing && dlg.preview.protonChanged === true
                                                    wrapMode: Text.Wrap
                                                    text: "Proton build: " + ((dlg.preview.beforeProton || "").length > 0 ? dlg.preview.beforeProton : "Steam's default")
                                                          + "  →  " + ((dlg.preview.afterProton || "").length > 0 ? dlg.preview.afterProton : "Steam's default")
                                                    color: Theme.text
                                                    font.family: Theme.monoFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: row.previewing && dlg.preview.changed !== true && (dlg.preview.blocked || "").length === 0
                                                    wrapMode: Text.Wrap
                                                    text: "This fix is already in place, so there is nothing to change."
                                                    color: Theme.muted
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }
                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: row.previewing && (dlg.preview.blocked || "").length > 0
                                                    wrapMode: Text.Wrap
                                                    text: dlg.preview.blocked || ""
                                                    color: Theme.danger
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }

                                                // what is left for the user to do
                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: row.previewing && (dlg.preview.manual || []).length > 0
                                                    wrapMode: Text.Wrap
                                                    text: "You still need to do this yourself:"
                                                    color: Theme.text
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }
                                                Repeater {
                                                    model: row.previewing ? (dlg.preview.manual || []) : []
                                                    delegate: Text {
                                                        required property string modelData
                                                        Layout.fillWidth: true
                                                        text: "• " + modelData
                                                        wrapMode: Text.Wrap
                                                        color: Theme.text
                                                        font.family: Theme.fontFamily
                                                        font.pixelSize: Theme.fsCaption
                                                    }
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: row.previewing && dlg.preview.mode === "apply"
                                                             && dlg.preview.launchChanged === true && dlg.launchDirty
                                                    wrapMode: Text.Wrap
                                                    text: "Applying replaces the unsaved launch options in the editor with the line above."
                                                    color: Theme.warning
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    Layout.topMargin: Theme.spaceXs
                                                    spacing: Theme.spaceSm
                                                    Item { Layout.fillWidth: true }
                                                    PsButton {
                                                        text: "Cancel"
                                                        primary: false
                                                        implicitHeight: 32
                                                        sound: "back"
                                                        Accessible.name: "Cancel this fix"
                                                        onClicked: dlg.controller.clearPreview()
                                                    }
                                                    PsButton {
                                                        visible: dlg.preview.mode === "copy"
                                                        text: "Copy new launch options"
                                                        implicitHeight: 32
                                                        sound: ""
                                                        onClicked: dlg.play(dlg.controller.copyProposed(row.finding.id) ? "success" : "error")
                                                    }
                                                    PsButton {
                                                        visible: dlg.preview.mode === "apply"
                                                        text: dlg.steamRunning ? "Apply anyway" : "Apply"
                                                        implicitHeight: 32
                                                        enabled: !dlg.busy && !dlg.running
                                                        sound: ""   // the result chimes when the write finishes
                                                        Accessible.name: text + ": " + row.finding.title
                                                        onClicked: dlg.controller.apply(row.finding.id)
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
            }
        }

        // ===== 6. undo the last fix ============================================
        Rectangle {
            id: undoBar
            Layout.fillWidth: true
            visible: dlg.ready && (dlg.controller.undoAvailable || dlg.controller.undoConflict.length > 0)
            implicitHeight: undoCol.implicitHeight + 2 * Theme.spaceSm
            radius: Theme.radiusSm
            color: dlg.ready && dlg.controller.undoConflict.length > 0 ? Theme.warningSurface : Theme.surfaceElevated
            border.width: 1
            border.color: dlg.ready && dlg.controller.undoConflict.length > 0 ? Theme.warningBorder : Theme.border

            ColumnLayout {
                id: undoCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.spaceSm
                spacing: Theme.spaceXs

                RowLayout {
                    Layout.fillWidth: true
                    visible: dlg.ready && dlg.controller.undoConflict.length === 0
                    spacing: Theme.spaceSm
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        text: dlg.ready ? "Last fix: " + dlg.controller.undoLabel
                                          + (dlg.controller.undoWhen.length > 0 ? ", " + dlg.controller.undoWhen : "") : ""
                        color: Theme.text
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                    PsButton {
                        text: "Undo"
                        primary: false
                        implicitHeight: 32
                        sound: ""
                        enabled: !dlg.busy && !dlg.running
                        Accessible.name: "Undo the last fix"
                        onClicked: dlg.controller.undo(false)
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: dlg.ready && dlg.controller.undoConflict.length > 0
                    wrapMode: Text.Wrap
                    text: dlg.ready ? dlg.controller.undoConflict : ""
                    color: Theme.warning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: dlg.ready && dlg.controller.undoConflict.length > 0
                    spacing: Theme.spaceSm
                    Item { Layout.fillWidth: true }
                    PsButton {
                        text: "Keep"
                        primary: false
                        implicitHeight: 32
                        Accessible.name: "Keep the settings as they are now"
                        onClicked: dlg.controller.dismissUndoConflict()
                    }
                    PsButton {
                        text: "Undo anyway"
                        primary: false
                        danger: true
                        implicitHeight: 32
                        sound: ""
                        enabled: !dlg.busy && !dlg.running
                        Accessible.name: "Undo anyway and overwrite the later changes"
                        onClicked: dlg.controller.undo(true)
                    }
                }
            }
        }

        // ===== 7. footer =======================================================
        RowLayout {
            id: footer
            Layout.fillWidth: true
            spacing: Theme.spaceSm
            BusyIndicator {
                running: dlg.busy
                visible: dlg.busy
                implicitWidth: 20
                implicitHeight: 20
            }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: dlg.ready ? dlg.controller.status : ""
                color: dlg.ready && dlg.controller.statusOk ? Theme.success : Theme.danger
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
                Accessible.role: Accessible.StaticText
                Accessible.name: text
            }
            PsButton {
                text: "Check again"
                primary: false
                enabled: !dlg.running && !dlg.busy
                Accessible.name: "Diagnose this game again"
                onClicked: dlg.runDiagnosis()
            }
            PsButton {
                text: "Open log"
                primary: false
                visible: !dlg.isShortcut && !dlg.isNative
                Accessible.name: "Open the Proton log for this game"
                onClicked: dlg.openLogRequested()
            }
            PsButton {
                text: "Close"
                sound: "back"
                Accessible.name: "Close Diagnose"
                onClicked: dlg.close()
            }
        }
    }
}
