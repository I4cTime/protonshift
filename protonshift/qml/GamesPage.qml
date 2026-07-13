import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// Second slice: Steam library discovery -> QML list model -> master/detail.
// `library` is the GamesController context property.
RowLayout {
    id: page
    spacing: Theme.spaceLg

    property string query: ""
    // re-evaluates when the query OR the underlying list changes
    property var filtered: {
        if (query.length === 0)
            return library.games
        var q = query.toLowerCase()
        return library.games.filter(function (g) {
            return g.name.toLowerCase().indexOf(q) >= 0
        })
    }

    // selecting a game drives the launch-options + game-tools controllers
    Connections {
        target: library
        function onSelectedChanged() {
            launch.appId = library.selectedAppId
            gameTools.appId = library.selectedAppId
            gameTools.prefixPath = library.selected.compatdataPath || ""
            gameTools.installPath = library.selected.installPath || ""
            detailCard.confirmDelete = false
            if (library.selectedAppId.length > 0) gameTools.refresh()
        }
    }

    // ============================ LIST =====================================
    PsCard {
        Layout.preferredWidth: 420
        Layout.fillHeight: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.space
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Library"
                    subtitle: library.loading ? "Scanning…"
                              : library.count + " game" + (library.count === 1 ? "" : "s")
                }
                Text {
                    text: "↻"
                    color: refreshArea.containsMouse ? Theme.primaryBright : Theme.muted
                    font.pixelSize: 18
                    MouseArea {
                        id: refreshArea
                        anchors.fill: parent
                        anchors.margins: -6
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: library.refresh()
                    }
                    RotationAnimation on rotation {
                        running: library.loading
                        loops: Animation.Infinite
                        from: 0; to: 360; duration: 900
                    }
                }
            }

            // search
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 36
                radius: Theme.radiusSm
                color: Theme.bgDeep
                border.width: search.activeFocus ? 2 : 1
                border.color: search.activeFocus ? Theme.primary : Theme.border
                Behavior on border.color { ColorAnimation { duration: 120 } }
                TextField {
                    id: search
                    anchors.fill: parent
                    anchors.leftMargin: Theme.spaceSm
                    anchors.rightMargin: Theme.spaceSm
                    verticalAlignment: TextInput.AlignVCenter
                    placeholderText: "Search games…"
                    placeholderTextColor: Theme.faint
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                    selectByMouse: true
                    background: Item {}
                    onTextChanged: page.query = text
                }
            }

            // states: loading / steam-missing / empty / list
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                // empty / error placeholder
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.space
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: !library.loading && page.filtered.length === 0
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                    text: !library.steamFound
                          ? "Steam installation not found."
                          : (library.count === 0 ? "No installed games found."
                                                  : "No games match “" + page.query + "”.")
                }

                ListView {
                    id: list
                    anchors.fill: parent
                    clip: true
                    spacing: 4
                    model: page.filtered
                    boundsBehavior: Flickable.StopAtBounds

                    delegate: Rectangle {
                        id: gameRow
                        required property var modelData
                        width: ListView.view.width
                        height: 52
                        radius: Theme.radiusSm
                        property bool current: modelData.appId === library.selectedAppId
                        color: current ? Theme.surfaceElevated
                                       : (hover.hovered ? Theme.surface : "transparent")
                        border.width: current ? 1 : 0
                        border.color: Theme.borderStrong
                        Behavior on color { ColorAnimation { duration: 120 } }

                        HoverHandler { id: hover }
                        TapHandler { onTapped: library.select(modelData.appId) }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.spaceSm
                            anchors.rightMargin: Theme.spaceSm
                            spacing: Theme.spaceSm

                            // selection accent bar
                            Rectangle {
                                width: 3; Layout.fillHeight: true
                                Layout.topMargin: 12; Layout.bottomMargin: 12
                                radius: 2
                                visible: gameRow.current
                                color: Theme.primary
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 1
                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    elide: Text.ElideRight
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsSmall
                                    font.weight: Font.Medium
                                }
                                Text {
                                    text: "App " + modelData.appId
                                    color: Theme.faint
                                    font.family: Theme.monoFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                            }

                            Rectangle {
                                visible: modelData.hasPrefix
                                implicitWidth: prefixLbl.implicitWidth + 12
                                implicitHeight: 18
                                radius: 9
                                color: "#12281f"
                                border.color: Theme.success
                                border.width: 1
                                Text {
                                    id: prefixLbl
                                    anchors.centerIn: parent
                                    text: "prefix"
                                    color: Theme.success
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }
                        }
                    }

                    ScrollBar.vertical: ScrollBar {}
                }
            }
        }
    }

    // ============================ DETAIL ===================================
    PsCard {
        id: detailCard
        Layout.fillWidth: true
        Layout.fillHeight: true
        glowing: hasSelection
        property bool hasSelection: Object.keys(library.selected).length > 0
        // two-step guard for the destructive prefix delete
        property bool confirmDelete: false

        // placeholder
        Text {
            anchors.centerIn: parent
            visible: !detailCard.hasSelection
            text: "Select a game to see its details"
            color: Theme.faint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsBody
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            spacing: Theme.space
            visible: detailCard.hasSelection

            Text {
                Layout.fillWidth: true
                text: library.selected.name || ""
                wrapMode: Text.WordWrap
                color: Theme.text
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsDisplay
                font.weight: Font.Bold
            }

            RowLayout {
                spacing: Theme.spaceSm
                Text {
                    text: "App " + (library.selected.appId || "")
                    color: Theme.muted
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.fsSmall
                }
                Rectangle {
                    implicitWidth: statusLbl.implicitWidth + 16
                    implicitHeight: 22
                    radius: 11
                    color: library.selected.hasPrefix ? "#12281f" : Theme.surfaceElevated
                    border.width: 1
                    border.color: library.selected.hasPrefix ? Theme.success : Theme.border
                    Text {
                        id: statusLbl
                        anchors.centerIn: parent
                        text: library.selected.hasPrefix ? "Proton prefix present" : "No prefix yet"
                        color: library.selected.hasPrefix ? Theme.success : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                        font.weight: Font.DemiBold
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            PsSectionHeader { Layout.fillWidth: true; text: "Paths" }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Repeater {
                    model: [
                        { k: "Install", v: library.selected.installPath || "—" },
                        { k: "Prefix (compatdata)", v: library.selected.compatdataPath || "—" },
                        { k: "Library", v: library.selected.libraryPath || "—" }
                    ]
                    delegate: ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: modelData.k
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.DemiBold
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.v
                            wrapMode: Text.WrapAnywhere
                            color: Theme.text
                            font.family: Theme.monoFamily
                            font.pixelSize: Theme.fsCaption
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- proton version (writes config.vdf, fail-closed) ---
            PsSectionHeader {
                Layout.fillWidth: true
                text: "Proton version"
                subtitle: "Compatibility tool · written to Steam's config.vdf"
            }
            PsSelect {
                id: protonSelect
                Layout.fillWidth: true
                enabled: launch.protonLoaded
                model: launch.protonTools
                displayMap: ({
                    "": "Steam default",
                    "proton_experimental": "Proton Experimental",
                    "proton_9_0": "Proton 9.0 (Beta)",
                    "proton_8_0": "Proton 8.0",
                    "proton_7_0": "Proton 7.0"
                })
                onChosen: launch.setProton(value)
                function syncCurrent() {
                    currentIndex = launch.protonTools.indexOf(launch.protonCurrent)
                }
                Component.onCompleted: syncCurrent()
                Connections {
                    target: launch
                    function onProtonChanged() { protonSelect.syncCurrent() }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: launch.protonStatus.length > 0
                text: launch.protonStatus
                wrapMode: Text.WordWrap
                color: launch.protonStatus.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- launch options (writes localconfig.vdf, fail-closed) ---
            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Launch options"
                    subtitle: "Written to Steam's localconfig.vdf"
                }
                BusyIndicator {
                    running: launch.loading
                    visible: launch.loading
                    implicitWidth: 20; implicitHeight: 20
                }
            }

            // read-failure: no editor shown, so a save can't overwrite (#20)
            Rectangle {
                Layout.fillWidth: true
                visible: launch.loadError.length > 0
                radius: Theme.radiusSm
                color: "#2a1216"
                border.color: Theme.danger
                border.width: 1
                implicitHeight: loErr.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: loErr
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: "#f2a3ab"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: launch.loadError
                }
            }

            EnvField {
                id: loField
                Layout.fillWidth: true
                mono: true
                visible: !launch.loadError.length
                enabled: launch.loaded
                placeholder: "gamescope -f -- %command%"
                Component.onCompleted: text = launch.text
                onEdited: launch.setText(newText)
                Connections {
                    target: launch
                    function onStateChanged() {
                        if (!loField.editing) loField.text = launch.text
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                visible: !launch.loadError.length
                spacing: Theme.spaceSm
                Text {
                    Layout.fillWidth: true
                    text: launch.status
                    wrapMode: Text.WordWrap
                    color: (launch.status.indexOf("failed") >= 0
                            || launch.status.indexOf("Not saved") >= 0)
                           ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: launch.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save to Steam"
                    enabled: launch.loaded && launch.dirty
                    onClicked: launch.save()
                }
            }

            // quick-add preset chips (append to the launch options above)
            Flow {
                Layout.fillWidth: true
                visible: !launch.loadError.length
                spacing: Theme.spaceXs
                Repeater {
                    model: launch.launchPresets
                    delegate: Rectangle {
                        required property var modelData
                        implicitWidth: lpLbl.implicitWidth + 18
                        implicitHeight: 24
                        radius: 12
                        opacity: modelData.installed ? 1.0 : 0.55
                        color: lph.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: lph.hovered ? Theme.primary : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 100 } }
                        HoverHandler { id: lph }
                        TapHandler { onTapped: if (launch.loaded) launch.appendPreset(modelData.value) }
                        Text {
                            id: lpLbl
                            anchors.centerIn: parent
                            text: "+ " + modelData.name + (modelData.installed ? "" : " (not installed)")
                            color: lph.hovered ? Theme.primaryBright : Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- prefix + shader cache maintenance ---
            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Maintenance"
                    subtitle: "Proton prefix, shader cache, and shortcuts"
                }
                BusyIndicator {
                    running: gameTools.loading || gameTools.busy
                    visible: gameTools.loading || gameTools.busy
                    implicitWidth: 20; implicitHeight: 20
                }
            }

            // prefix + shader info chips
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Repeater {
                    model: [
                        { l: "Prefix", v: gameTools.info.prefixExists ? gameTools.info.prefixSize : "none" },
                        { l: "Created", v: gameTools.info.created || "—" },
                        { l: "DXVK", v: gameTools.info.dxvk || "—" },
                        { l: "VKD3D", v: gameTools.info.vkd3d || "—" },
                        { l: "Shader cache", v: gameTools.info.shaderExists ? gameTools.info.shaderSize : "none" }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        implicitWidth: mChipRow.implicitWidth + 20
                        implicitHeight: 26
                        radius: 13
                        color: Theme.bgDeep
                        border.color: Theme.border
                        border.width: 1
                        RowLayout {
                            id: mChipRow
                            anchors.centerIn: parent
                            spacing: 5
                            Text {
                                text: modelData.l
                                color: Theme.faint
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsCaption
                            }
                            Text {
                                text: modelData.v
                                color: Theme.text
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsCaption
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: gameTools.status.length > 0
                text: gameTools.status
                wrapMode: Text.WordWrap
                color: (gameTools.status.indexOf("Couldn't") >= 0) ? Theme.danger : Theme.success
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "Launch"
                    primary: false
                    onClicked: gameTools.launchGame()
                }
                PsButton {
                    text: "Open in Steam"
                    primary: false
                    onClicked: gameTools.openInSteam()
                }
                PsButton {
                    text: "Open install folder"
                    primary: false
                    enabled: (library.selected.installPath || "").length > 0
                    onClicked: gameTools.openFolder(library.selected.installPath)
                }
                PsButton {
                    text: "Open prefix"
                    primary: false
                    enabled: gameTools.info.prefixExists === true
                    onClicked: gameTools.openFolder(library.selected.compatdataPath)
                }
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Clear shader cache"
                    primary: false
                    enabled: gameTools.info.shaderExists === true && !gameTools.busy
                    onClicked: gameTools.clearShaderCache()
                }
                PsButton {
                    text: detailCard.confirmDelete ? "Confirm delete" : "Delete prefix"
                    primary: false
                    danger: true
                    enabled: gameTools.info.prefixExists === true && !gameTools.busy
                    onClicked: {
                        if (detailCard.confirmDelete) { detailCard.confirmDelete = false; gameTools.deletePrefix() }
                        else detailCard.confirmDelete = true
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- per-game overrides ---
            PsSectionHeader {
                Layout.fillWidth: true
                text: "Per-game tweaks"
                subtitle: "gamescope/ScopeBuddy overrides just for this game"
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "ScopeBuddy override…"
                    primary: false
                    onClicked: {
                        perAppScb.appId = library.selected.appId
                        scbOverrideDialog.open()
                    }
                }
                PsButton {
                    text: "MangoHud override…"
                    primary: false
                    onClicked: {
                        perGameMango.gameName = library.selected.name
                        mangoOverrideDialog.open()
                    }
                }
                PsButton {
                    text: "Winetricks…"
                    primary: false
                    onClicked: {
                        protontricks.appId = library.selected.appId
                        protontricks.gameName = library.selected.name
                        protontricksDialog.open()
                    }
                }
                Item { Layout.fillWidth: true }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // ============================ PER-GAME SCB DIALOG =======================
    PsDialog {
        id: scbOverrideDialog
        objectName: "scbOverrideDialog"
        width: 620
        title: "ScopeBuddy override"
        subtitle: (library.selected.name || "") + " · AppID/" + (perAppScb.appId || "") + ".conf"

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: perAppScb.exists ? "Existing override" : "No override yet — add keys to create one."
                    color: perAppScb.exists ? Theme.muted : Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                BusyIndicator {
                    running: perAppScb.loading; visible: perAppScb.loading
                    implicitWidth: 20; implicitHeight: 20
                }
            }

            // known-key chips
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Repeater {
                    model: perAppScb.knownKeys
                    delegate: Rectangle {
                        required property string modelData
                        implicitWidth: chip.implicitWidth + 18
                        implicitHeight: 24
                        radius: 12
                        color: ch.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: ch.hovered ? Theme.primary : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 100 } }
                        HoverHandler { id: ch }
                        TapHandler { onTapped: if (perAppScb.loaded) perAppScb.addKey(modelData) }
                        Text {
                            id: chip
                            anchors.centerIn: parent
                            text: "+ " + modelData
                            color: ch.hovered ? Theme.primaryBright : Theme.muted
                            font.family: Theme.monoFamily
                            font.pixelSize: 10
                        }
                    }
                }
            }

            ListView {
                id: scbRows
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 40), 260)
                clip: true
                spacing: 6
                model: perAppScb.model
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}

                delegate: RowLayout {
                    id: r
                    required property int index
                    required property string key
                    required property string value
                    width: ListView.view.width
                    spacing: Theme.spaceSm
                    Connections {
                        target: perAppScb.model
                        function onDataChanged(tl, br) {
                            if (r.index < tl.row || r.index > br.row) return
                            if (!kf.editing) kf.text = r.key
                            if (!vf.editing) vf.text = r.value
                        }
                    }
                    EnvField {
                        id: kf; Layout.preferredWidth: 200; mono: true; placeholder: "SCB_KEY"
                        Component.onCompleted: text = r.key
                        onEdited: perAppScb.model.setKey(r.index, newText)
                    }
                    EnvField {
                        id: vf; Layout.fillWidth: true; mono: true; placeholder: "value"
                        Component.onCompleted: text = r.value
                        onEdited: perAppScb.model.setValue(r.index, newText)
                    }
                    Rectangle {
                        width: 28; height: 28; radius: Theme.radiusSm
                        color: rmv.hovered ? "#2a1216" : "transparent"
                        border.width: 1
                        border.color: rmv.hovered ? Theme.danger : Theme.border
                        Text { anchors.centerIn: parent; text: "✕"; color: rmv.hovered ? Theme.danger : Theme.muted; font.pixelSize: 12 }
                        HoverHandler { id: rmv }
                        TapHandler { onTapped: perAppScb.model.removeRow(r.index) }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "+ Add row"; primary: false
                    enabled: perAppScb.loaded
                    onClicked: perAppScb.model.addRow()
                }
                PsButton {
                    text: "Delete override"; primary: false
                    visible: perAppScb.exists
                    onClicked: perAppScb.deleteOverride()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: perAppScb.status
                    color: perAppScb.status.indexOf("failed") >= 0
                           || perAppScb.status.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: perAppScb.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save"
                    enabled: perAppScb.loaded && perAppScb.dirty
                    onClicked: perAppScb.save()
                }
            }
        }
    }

    // ============================ PER-GAME MANGOHUD DIALOG ==================
    PsDialog {
        id: mangoOverrideDialog
        objectName: "mangoOverrideDialog"
        width: 680
        title: "MangoHud override"
        subtitle: (library.selected.name || "") + " · per-game overlay"

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: perGameMango.exists ? "Existing override"
                                              : "No override yet — pick a preset or toggle metrics."
                    color: perGameMango.exists ? Theme.muted : Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                BusyIndicator {
                    running: perGameMango.loading; visible: perGameMango.loading
                    implicitWidth: 20; implicitHeight: 20
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                Repeater {
                    model: perGameMango.presetNames
                    delegate: Rectangle {
                        required property string modelData
                        implicitWidth: pl.implicitWidth + 18
                        implicitHeight: 24
                        radius: 12
                        color: ph.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: ph.hovered ? Theme.primary : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 100 } }
                        HoverHandler { id: ph }
                        TapHandler { onTapped: if (perGameMango.loaded) perGameMango.applyPreset(modelData) }
                        Text {
                            id: pl
                            anchors.centerIn: parent
                            text: modelData
                            color: ph.hovered ? Theme.primaryBright : Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                        }
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 260
                contentWidth: availableWidth
                clip: true
                GridLayout {
                    width: parent.width
                    columns: 2
                    columnSpacing: Theme.spaceLg
                    rowSpacing: Theme.spaceSm
                    Repeater {
                        model: perGameMango.toggleParams
                        delegate: PsSwitchRow {
                            required property var modelData
                            Layout.fillWidth: true
                            enabled: perGameMango.loaded
                            text: modelData.label
                            checked: perGameMango.config[modelData.key] !== undefined
                            onToggled: perGameMango.setToggle(modelData.key, value)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "Delete override"; primary: false
                    visible: perGameMango.exists
                    onClicked: perGameMango.deleteOverride()
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: perGameMango.status
                    color: perGameMango.status.indexOf("failed") >= 0
                           || perGameMango.status.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                Text {
                    visible: perGameMango.dirty
                    text: "● unsaved"
                    color: Theme.primaryBright
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Save"
                    enabled: perGameMango.loaded && perGameMango.dirty
                    onClicked: perGameMango.save()
                }
            }
        }
    }

    // ============================ PROTONTRICKS DIALOG ======================
    PsDialog {
        id: protontricksDialog
        objectName: "protontricksDialog"
        width: 680
        title: "Winetricks"
        subtitle: (protontricks.gameName || "") + " · protontricks " + (protontricks.appId || "")

        // track selected verbs locally; cleared whenever the dialog (re)opens
        property var selected: ({})
        onOpened: selected = ({})

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            // not-installed notice
            Rectangle {
                Layout.fillWidth: true
                visible: !protontricks.available
                radius: Theme.radiusSm
                color: "#2a1216"
                border.color: Theme.danger
                border.width: 1
                implicitHeight: naText.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: naText
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: "#f2a3ab"
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "protontricks isn't installed. Install it from your package manager, or the "
                          + "Flathub package com.github.Matoking.protontricks."
                }
            }

            Text {
                Layout.fillWidth: true
                visible: protontricks.available
                text: "Install common components into this game's Proton prefix, or open the full "
                      + "winetricks GUI. Installs run in the background and may download."
                wrapMode: Text.WordWrap
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            // verb checklist
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 240
                contentWidth: availableWidth
                clip: true
                visible: protontricks.available
                GridLayout {
                    width: parent.width
                    columns: 2
                    columnSpacing: Theme.spaceLg
                    rowSpacing: Theme.spaceXs
                    Repeater {
                        model: protontricks.verbs
                        delegate: Rectangle {
                            id: verbRow
                            required property var modelData
                            property bool checked: protontricksDialog.selected[modelData.verb] === true
                            Layout.fillWidth: true
                            implicitHeight: 40
                            radius: Theme.radiusSm
                            color: checked ? Theme.surfaceElevated : (vh.hovered ? Theme.surface : Theme.bgDeep)
                            border.color: checked ? Theme.primary : Theme.border
                            border.width: checked ? 2 : 1
                            Behavior on color { ColorAnimation { duration: 100 } }
                            enabled: !protontricks.running
                            HoverHandler { id: vh }
                            TapHandler {
                                onTapped: {
                                    var s = protontricksDialog.selected
                                    s[verbRow.modelData.verb] = !verbRow.checked
                                    protontricksDialog.selected = s
                                }
                            }
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.spaceSm
                                anchors.rightMargin: Theme.spaceSm
                                spacing: Theme.spaceSm
                                Rectangle {
                                    width: 16; height: 16; radius: 4
                                    color: verbRow.checked ? Theme.primary : "transparent"
                                    border.color: verbRow.checked ? Theme.primary : Theme.borderStrong
                                    border.width: 1
                                    Text {
                                        anchors.centerIn: parent
                                        visible: verbRow.checked
                                        text: "✓"; color: "#ffffff"; font.pixelSize: 11; font.bold: true
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text {
                                        text: verbRow.modelData.label
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: Font.Medium
                                    }
                                    Text {
                                        text: verbRow.modelData.verb
                                        color: Theme.faint
                                        font.family: Theme.monoFamily
                                        font.pixelSize: 10
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // log tail
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 96
                visible: protontricks.output.length > 0
                radius: Theme.radiusSm
                color: Theme.bgDeep
                border.color: Theme.border
                border.width: 1
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    contentWidth: availableWidth
                    clip: true
                    Text {
                        width: parent.width
                        text: protontricks.output
                        wrapMode: Text.WrapAnywhere
                        color: Theme.muted
                        font.family: Theme.monoFamily
                        font.pixelSize: 10
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "Open winetricks GUI"
                    primary: false
                    enabled: protontricks.available && !protontricks.running
                    onClicked: protontricks.openGui()
                }
                BusyIndicator {
                    running: protontricks.running; visible: protontricks.running
                    implicitWidth: 20; implicitHeight: 20
                }
                Item { Layout.fillWidth: true }
                Text {
                    Layout.maximumWidth: 260
                    text: protontricks.status
                    elide: Text.ElideRight
                    color: protontricks.status.indexOf("failed") >= 0
                           || protontricks.status.indexOf("Couldn't") >= 0
                           || protontricks.status.indexOf("not installed") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: protontricks.running ? "Installing…" : "Install selected"
                    enabled: protontricks.available && !protontricks.running
                    onClicked: {
                        var verbs = []
                        for (var k in protontricksDialog.selected)
                            if (protontricksDialog.selected[k]) verbs.push(k)
                        protontricks.installVerbs(verbs)
                    }
                }
            }
        }
    }
}
