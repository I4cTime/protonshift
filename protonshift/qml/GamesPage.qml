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
    property string sourceFilter: "all"   // all | steam | heroic | lutris
    // Rebuilt imperatively rather than via a binding: a fresh array on every
    // change made the ListView reset and jump to the top. refilter() skips
    // rebuilds whose result is identical, and preserves the scroll position
    // when the rebuild was triggered by a background library refresh.
    property var filtered: []
    function computeFiltered() {
        var q = query.toLowerCase()
        var src = sourceFilter
        return library.games.filter(function (g) {
            if (src !== "all" && (g.source || "steam") !== src) return false
            if (q.length > 0 && g.name.toLowerCase().indexOf(q) < 0) return false
            return true
        })
    }
    function refilter(preserveScroll) {
        var next = computeFiltered()
        // identical result (e.g. a rescan that found nothing new): keep the model
        if (JSON.stringify(next) === JSON.stringify(filtered))
            return
        var y = preserveScroll ? list.contentY : 0
        filtered = next
        if (preserveScroll)
            list.contentY = Math.max(0, Math.min(y, list.contentHeight - list.height))
    }
    onQueryChanged: refilter(false)
    onSourceFilterChanged: refilter(false)
    Component.onCompleted: refilter(false)

    // selecting a game drives the launch-options + game-tools controllers
    Connections {
        target: library
        function onGamesChanged() { page.refilter(true) }
        function onSelectedChanged() {
            launch.appId = library.selectedAppId
            gameTools.appId = library.selectedAppId
            gameTools.prefixPath = library.selected.compatdataPath || ""
            gameTools.installPath = library.selected.installPath || ""
            detailCard.confirmDelete = false
            profiles.appId = library.selectedAppId
            saves.appId = library.selectedAppId
            saves.prefixPath = library.selected.compatdataPath || ""
            fixes.appId = library.selectedAppId
            heroic.appId = (library.selected.source === "heroic") ? library.selectedAppId : ""
            if (library.selectedAppId.length > 0) gameTools.refresh()
        }
    }

    // ============================ LIST =====================================
    PsCard {
        // responsive: ~1/3 of the page, clamped so neither pane starves
        Layout.preferredWidth: Math.max(300, Math.min(420, Math.round(page.width * 0.34)))
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

            // source filter (only shown when there's more than one source)
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceXs
                visible: (library.sourceCounts.heroic > 0) || (library.sourceCounts.lutris > 0)
                Repeater {
                    model: [
                        { k: "all", l: "All", n: library.count },
                        { k: "steam", l: "Steam", n: library.sourceCounts.steam || 0 },
                        { k: "heroic", l: "Heroic", n: library.sourceCounts.heroic || 0 },
                        { k: "lutris", l: "Lutris", n: library.sourceCounts.lutris || 0 }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        visible: modelData.k === "all" || modelData.n > 0
                        implicitWidth: sfLbl.implicitWidth + 18
                        implicitHeight: 24
                        radius: 12
                        property bool active: page.sourceFilter === modelData.k
                        color: active ? Theme.surfaceElevated : (sfh.hovered ? Theme.surface : Theme.bgDeep)
                        border.color: active ? Theme.primary : Theme.border
                        border.width: active ? 2 : 1
                        Behavior on color { ColorAnimation { duration: 100 } }
                        HoverHandler { id: sfh }
                        TapHandler { onTapped: page.sourceFilter = modelData.k }
                        Text {
                            id: sfLbl
                            anchors.centerIn: parent
                            text: modelData.l + " " + modelData.n
                            color: active ? Theme.primaryBright : Theme.muted
                            font.family: Theme.fontFamily; font.pixelSize: 10
                            font.weight: active ? Font.DemiBold : Font.Normal
                        }
                    }
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
                                       : (rowMouse.containsMouse ? Theme.surface : "transparent")
                        border.width: current ? 1 : 0
                        border.color: Theme.borderStrong
                        Behavior on color { ColorAnimation { duration: 80 } }

                        // MouseArea (not HoverHandler): hover handlers in ListView
                        // delegates drop their hovered state once the pointer rests,
                        // leaving no steady highlight. containsMouse is reliable.
                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: library.select(gameRow.modelData.appId)
                        }

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
                                    text: (modelData.source === "steam")
                                          ? "App " + modelData.appId
                                          : (modelData.store === "epic" ? "Epic"
                                             : modelData.store === "gog" ? "GOG"
                                             : "Lutris") + " · " + modelData.appId
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                    color: Theme.faint
                                    font.family: Theme.monoFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                            }

                            // source badge for non-Steam games
                            Rectangle {
                                visible: modelData.source !== "steam"
                                implicitWidth: srcBadge.implicitWidth + 12
                                implicitHeight: 18
                                radius: 9
                                color: Theme.surfaceElevated
                                border.color: Theme.primary
                                border.width: 1
                                Text {
                                    id: srcBadge
                                    anchors.centerIn: parent
                                    text: modelData.source === "heroic" ? "Heroic" : "Lutris"
                                    color: Theme.primaryBright
                                    font.family: Theme.fontFamily
                                    font.pixelSize: 10
                                    font.weight: Font.DemiBold
                                }
                            }

                            Rectangle {
                                visible: modelData.hasPrefix
                                implicitWidth: prefixLbl.implicitWidth + 12
                                implicitHeight: 18
                                radius: 9
                                color: Theme.successTint
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
        // Steam-only sections (Proton/launch options/per-game tweaks) hide for
        // Heroic/Lutris games, which get their own controls.
        property bool isSteam: (library.selected.source || "steam") === "steam"

        // placeholder
        Text {
            anchors.centerIn: parent
            visible: !detailCard.hasSelection
            text: "Select a game to see its details"
            color: Theme.faint
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsBody
        }

        ScrollView {
            anchors.fill: parent
            anchors.margins: Theme.spaceLg
            visible: detailCard.hasSelection
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
            width: parent.width
            spacing: Theme.space

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
                    color: library.selected.hasPrefix ? Theme.successTint : Theme.surfaceElevated
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

            // ===== Steam-only: Proton + launch options + presets =====
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Theme.space
              visible: detailCard.isSteam

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
                color: Theme.dangerSurface
                border.color: Theme.danger
                border.width: 1
                implicitHeight: loErr.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: loErr
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: Theme.danger
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

            } // ===== end Steam-only (Proton + launch options + presets) =====

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

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "Launch"
                    primary: false
                    visible: detailCard.isSteam
                    onClicked: gameTools.launchGame()
                }
                PsButton {
                    text: "Open in Steam"
                    primary: false
                    visible: detailCard.isSteam
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
                PsButton {
                    text: "Clear shader cache"
                    primary: false
                    visible: detailCard.isSteam
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

            // ===== Steam-only: per-game tweaks + fixes/profiles/saves =====
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Theme.space
              visible: detailCard.isSteam

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- per-game overrides ---
            PsSectionHeader {
                Layout.fillWidth: true
                text: "Per-game tweaks"
                subtitle: "gamescope/ScopeBuddy overrides just for this game"
            }
            Flow {
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
                PsButton {
                    text: "Known fixes…"
                    primary: false
                    onClicked: { fixes.appId = library.selected.appId; fixesDialog.open() }
                }
                PsButton {
                    text: "Profiles…"
                    primary: false
                    onClicked: { profiles.appId = library.selected.appId; profiles.refresh(); profilesDialog.open() }
                }
                PsButton {
                    text: "Save backups…"
                    primary: false
                    onClicked: {
                        saves.appId = library.selected.appId
                        saves.prefixPath = library.selected.compatdataPath || ""
                        saves.refresh()
                        savesDialog.open()
                    }
                }
            }
            } // ===== end Steam-only (per-game tweaks + fixes/profiles/saves) =====

            // ===== Heroic-only: per-game wine/proton config =====
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.space
                visible: library.selected.source === "heroic"

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                RowLayout {
                    Layout.fillWidth: true
                    PsSectionHeader {
                        Layout.fillWidth: true
                        text: "Heroic settings"
                        subtitle: heroic.config.exists ? "GamesConfig · saved on change"
                                                       : "No per-game config yet — toggling creates one"
                    }
                    BusyIndicator { running: heroic.loading; visible: heroic.loading; implicitWidth: 20; implicitHeight: 20 }
                }

                // wine/proton version
                PsSectionHeader { Layout.fillWidth: true; text: "Wine / Proton version" }
                PsSelect {
                    id: heroicWineSelect
                    Layout.fillWidth: true
                    enabled: heroic.wineVersions.length > 0
                    model: heroic.wineVersions.map(function (v) { return v.name })
                    function syncCurrent() {
                        currentIndex = Math.max(0, model.indexOf(heroic.config.wineName))
                    }
                    // Re-sync whenever the selected game's config or the list of
                    // builds changes (mirrors protonSelect): without this, switching
                    // Heroic games kept showing the previous game's version.
                    onModelChanged: syncCurrent()
                    Component.onCompleted: syncCurrent()
                    Connections {
                        target: heroic
                        function onConfigChanged() { heroicWineSelect.syncCurrent() }
                    }
                    onChosen: {
                        for (var i = 0; i < heroic.wineVersions.length; i++) {
                            if (heroic.wineVersions[i].name === value) {
                                heroic.setWineVersion(value, heroic.wineVersions[i].bin, heroic.wineVersions[i].type)
                                break
                            }
                        }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: heroic.wineVersions.length === 0
                    text: "No wine/proton builds found under Heroic's tools dir."
                    wrapMode: Text.WordWrap
                    color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }

                // toggles
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 520 ? 2 : 1
                    columnSpacing: Theme.spaceLg
                    rowSpacing: Theme.spaceXs
                    Repeater {
                        model: [
                            { k: "enableEsync", l: "Esync" },
                            { k: "enableFsync", l: "Fsync" },
                            { k: "autoInstallDxvk", l: "Auto-install DXVK" },
                            { k: "autoInstallVkd3d", l: "Auto-install VKD3D" },
                            { k: "showMangohud", l: "MangoHud overlay" },
                            { k: "useGameMode", l: "GameMode" },
                            { k: "nvidiaPrime", l: "NVIDIA dGPU (Prime)" }
                        ]
                        delegate: PsSwitchRow {
                            required property var modelData
                            Layout.fillWidth: true
                            text: modelData.l
                            checked: heroic.config[modelData.k] === true
                            onToggled: heroic.setToggle(modelData.k, value)
                        }
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    PsButton { text: "Launch via Heroic"; primary: false; onClicked: heroic.launch() }
                    PsButton {
                        text: "Open prefix"; primary: false
                        enabled: (library.selected.compatdataPath || "").length > 0
                        onClicked: gameTools.openFolder(library.selected.compatdataPath)
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: heroic.status.length > 0
                    text: heroic.status
                    wrapMode: Text.WordWrap
                    color: heroic.status.indexOf("Couldn't") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
            }

            }
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
                        color: rmv.hovered ? Theme.dangerSurface : "transparent"
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
                color: Theme.dangerSurface
                border.color: Theme.danger
                border.width: 1
                implicitHeight: naText.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: naText
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: Theme.danger
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
                                        text: "✓"; color: Theme.onPrimary; font.pixelSize: 11; font.bold: true
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

    // ============================ KNOWN FIXES DIALOG =======================
    PsDialog {
        id: fixesDialog
        objectName: "fixesDialog"
        width: 680
        title: "Known fixes"
        subtitle: (library.selected.name || "") + " · appends to launch options"

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            Text {
                Layout.fillWidth: true
                visible: fixes.fixes.length === 0
                text: "No known fixes for this game yet."
                color: Theme.faint
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
            }

            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 40), 320)
                clip: true; spacing: 8
                model: fixes.fixes
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width
                    implicitHeight: fxCol.implicitHeight + 2 * Theme.spaceSm
                    radius: Theme.radiusSm
                    color: Theme.bgDeep
                    border.color: Theme.border; border.width: 1
                    ColumnLayout {
                        id: fxCol
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: 3
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title
                                color: Theme.text
                                font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall; font.weight: Font.DemiBold
                            }
                            Rectangle {
                                implicitWidth: srcLbl.implicitWidth + 12; implicitHeight: 16; radius: 8
                                color: Theme.surfaceElevated
                                Text { id: srcLbl; anchors.centerIn: parent; text: modelData.source; color: Theme.muted; font.pixelSize: 9; font.family: Theme.fontFamily }
                            }
                            PsButton {
                                text: "Apply"; primary: false
                                enabled: launch.loaded
                                onClicked: { launch.appendPreset(modelData.snippet); fixesDialog.close() }
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.description
                            wrapMode: Text.WordWrap
                            color: Theme.muted
                            font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                        }
                        Text {
                            text: modelData.snippet
                            color: Theme.primaryBright
                            font.family: Theme.monoFamily; font.pixelSize: 10
                        }
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: !launch.loaded
                text: "Select the game's launch options load before applying (open the detail pane)."
                color: Theme.faint; wrapMode: Text.WordWrap
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
        }
    }

    // ============================ PROFILES DIALOG ==========================
    PsDialog {
        id: profilesDialog
        objectName: "profilesDialog"
        width: 620
        title: "Configuration profiles"
        subtitle: (library.selected.name || "") + " · launch + Proton + env + power"

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 38; radius: Theme.radiusSm
                    color: Theme.bgDeep
                    border.width: profName.activeFocus ? 2 : 1
                    border.color: profName.activeFocus ? Theme.primary : Theme.border
                    TextField {
                        id: profName
                        anchors.fill: parent; anchors.leftMargin: Theme.spaceSm; anchors.rightMargin: Theme.spaceSm
                        verticalAlignment: TextInput.AlignVCenter
                        placeholderText: "New profile name…"
                        placeholderTextColor: Theme.faint
                        color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
                        selectByMouse: true; background: Item {}
                    }
                }
                PsButton {
                    text: "Save current"
                    enabled: profName.text.length > 0 && !profiles.busy
                    onClicked: { profiles.saveCurrent(profName.text); profName.text = "" }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: profiles.profiles.length === 0
                text: "No saved profiles. Capture the current launch options, Proton, env vars and power profile above."
                wrapMode: Text.WordWrap
                color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }

            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 0), 240)
                clip: true; spacing: 6
                model: profiles.profiles
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property string modelData
                    width: ListView.view.width; implicitHeight: 42; radius: Theme.radiusSm
                    color: Theme.bgDeep; border.color: Theme.border; border.width: 1
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.spaceSm; anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm
                        Text {
                            Layout.fillWidth: true; text: modelData
                            color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fsSmall
                        }
                        PsButton { text: "Apply"; primary: false; enabled: !profiles.busy; onClicked: profiles.apply(modelData) }
                        PsButton { text: "Delete"; primary: false; danger: true; enabled: !profiles.busy; onClicked: profiles.deleteProfile(modelData) }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                BusyIndicator { running: profiles.busy; visible: profiles.busy; implicitWidth: 18; implicitHeight: 18 }
                Text {
                    Layout.fillWidth: true; text: profiles.status
                    wrapMode: Text.WordWrap
                    color: profiles.status.indexOf("Couldn't") >= 0 || profiles.status.indexOf("Nothing") >= 0 ? Theme.danger : Theme.success
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
            }
        }
    }

    // ============================ SAVE BACKUPS DIALOG ======================
    PsDialog {
        id: savesDialog
        objectName: "savesDialog"
        width: 680
        title: "Save backups"
        subtitle: (library.selected.name || "") + " · discovered saves are zipped; restores go to a safe folder"

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            PsSectionHeader { Layout.fillWidth: true; text: "Detected saves" }
            Text {
                Layout.fillWidth: true
                visible: saves.saves.length === 0 && !saves.busy
                text: "No save folders detected (Proton prefix + Steam userdata scanned)."
                wrapMode: Text.WordWrap
                color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
            Repeater {
                model: saves.saves
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Theme.spaceSm
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 0
                        Text { text: modelData.label; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: modelData.path; elide: Text.ElideMiddle; color: Theme.faint; font.family: Theme.monoFamily; font.pixelSize: 10 }
                    }
                    Text { text: modelData.size; color: Theme.muted; font.family: Theme.monoFamily; font.pixelSize: Theme.fsCaption }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                PsButton {
                    text: "Back up now"; enabled: saves.saves.length > 0 && !saves.busy
                    onClicked: saves.backup()
                }
                BusyIndicator { running: saves.busy; visible: saves.busy; implicitWidth: 18; implicitHeight: 18 }
                Item { Layout.fillWidth: true }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            PsSectionHeader { Layout.fillWidth: true; text: "Backups" }
            Text {
                Layout.fillWidth: true
                visible: saves.backups.length === 0
                text: "No backups yet."
                color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 0), 200)
                clip: true; spacing: 6
                model: saves.backups
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width; implicitHeight: 42; radius: Theme.radiusSm
                    color: Theme.bgDeep; border.color: Theme.border; border.width: 1
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.spaceSm; anchors.rightMargin: Theme.spaceSm
                        spacing: Theme.spaceSm
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 0
                            Text { text: modelData.created; color: Theme.text; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption }
                            Text { text: modelData.filename + " · " + modelData.size; color: Theme.faint; font.family: Theme.monoFamily; font.pixelSize: 10 }
                        }
                        PsButton { text: "Restore"; primary: false; enabled: !saves.busy; onClicked: saves.restore(modelData.path) }
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: saves.status.length > 0
                text: saves.status
                wrapMode: Text.WordWrap
                color: saves.status.indexOf("failed") >= 0 ? Theme.danger : Theme.success
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
        }
    }
}
