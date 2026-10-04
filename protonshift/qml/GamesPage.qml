import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import App

// Second slice: Steam library discovery -> QML list model -> master/detail.
// `library` is the GamesController context property.
RowLayout {
    id: page
    spacing: Theme.spaceLg

    property string query: ""
    property string sourceFilter: "all"   // all | steam | shortcut | heroic | lutris

    function sourceLabel(source) {
        if (source === "heroic") return "Heroic"
        if (source === "lutris") return "Lutris"
        if (source === "shortcut") return "Non-Steam"
        return "Steam"
    }
    function runLaunchCheck() {
        var g = library.selected
        // "\u0000" = read the saved launch options from Steam; a Non-Steam
        // shortcut carries its own, which Steam keeps inside the shortcut.
        launchCheck.run(g.appId, g.installPath || "", g.compatdataPath || "",
                        g.source === "shortcut" ? (g.launchOptions || "") : "\u0000",
                        (g.source === "steam" && protondb.enabled && protondb.loaded) ? protondb.tierLabel : "")
    }
    function levelColor(level) {
        if (level === "error") return Theme.danger
        if (level === "warn") return Theme.warning
        if (level === "ok") return Theme.success
        return Theme.muted
    }
    function levelGlyph(level) {
        if (level === "error") return "✕"
        if (level === "warn") return "!"
        if (level === "ok") return "✓"
        return "i"
    }

    // Selecting another game reloads the launch options, which would drop
    // unsaved edits without a word. Ask first.
    function requestSelect(appId) {
        if (appId === library.selectedAppId)
            return
        if (launch.dirty) {
            unsavedDialog.pendingAppId = appId
            unsavedDialog.open()
        } else {
            library.select(appId)
        }
    }
    // Up/Down in the game list: select the neighbour and keep it in view.
    function stepSelection(delta) {
        if (filtered.length === 0)
            return
        var at = -1
        for (var i = 0; i < filtered.length; i++)
            if (filtered[i].appId === library.selectedAppId) { at = i; break }
        var next = Math.max(0, Math.min(filtered.length - 1, at < 0 ? 0 : at + delta))
        if (next === at)
            return
        list.positionViewAtIndex(next, ListView.Contain)
        requestSelect(filtered[next].appId)
    }
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
            // launch options and the Proton choice exist only for Steam's own
            // games and its Non-Steam shortcuts
            var src = library.selected.source || "steam"
            launch.appId = (src === "steam" || src === "shortcut") ? library.selectedAppId : ""
            gameTools.appId = library.selectedAppId
            gameTools.prefixPath = library.selected.compatdataPath || ""
            gameTools.installPath = library.selected.installPath || ""
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
                PsIconButton {
                    glyph: "↻"
                    label: "Rescan the library"
                    spinning: library.loading
                    enabled: !library.loading
                    onClicked: library.refresh()
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
                visible: library.count > (library.sourceCounts.steam || 0)
                Repeater {
                    model: [
                        { k: "all", l: "All", n: library.count },
                        { k: "steam", l: "Steam", n: library.sourceCounts.steam || 0 },
                        { k: "shortcut", l: "Non-Steam", n: library.sourceCounts.shortcut || 0 },
                        { k: "heroic", l: "Heroic", n: library.sourceCounts.heroic || 0 },
                        { k: "lutris", l: "Lutris", n: library.sourceCounts.lutris || 0 }
                    ]
                    delegate: PsChip {
                        required property var modelData
                        visible: modelData.k === "all" || modelData.n > 0
                        text: modelData.l + " " + modelData.n
                        active: page.sourceFilter === modelData.k
                        Accessible.name: "Show " + modelData.l + " games (" + modelData.n + ")"
                        onClicked: page.sourceFilter = modelData.k
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
                    text: library.count === 0
                          ? (library.steamFound
                             ? "No installed games found."
                             : "No games found. ProtonShift looked for Steam, Heroic and Lutris libraries.")
                          : (page.query.length > 0 ? "No games match “" + page.query + "”."
                                                   : "No " + page.sourceLabel(page.sourceFilter) + " games.")
                }

                ListView {
                    id: list
                    anchors.fill: parent
                    clip: true
                    spacing: 4
                    model: page.filtered
                    boundsBehavior: Flickable.StopAtBounds

                    // one Tab stop for the whole list; Up/Down pick a game
                    activeFocusOnTab: true
                    Accessible.role: Accessible.List
                    Accessible.name: "Games"
                    Keys.onUpPressed: page.stepSelection(-1)
                    Keys.onDownPressed: page.stepSelection(1)

                    // keyboard focus ring
                    Rectangle {
                        anchors.fill: parent
                        z: 2
                        radius: Theme.radiusSm
                        color: "transparent"
                        border.width: 2
                        border.color: Theme.accentBright
                        visible: list.activeFocus
                    }

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
                            onClicked: {
                                list.forceActiveFocus()
                                sounds.play("click")
                                page.requestSelect(gameRow.modelData.appId)
                            }
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
                                    text: modelData.idLabel
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
                                    text: page.sourceLabel(modelData.source)
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
        // Steam-only sections (launch options, ProtonDB, per-game tools) hide
        // for other sources, which get their own controls.
        property bool isSteam: (library.selected.source || "steam") === "steam"
        // A game added to Steam by hand: it has a Proton prefix and a Proton
        // choice like a store game, but Steam keeps its launch options itself.
        property bool isShortcut: library.selected.source === "shortcut"
        // "proton" | "wine" | "none" (Linux-native: no prefix to manage)
        property string prefixKind: library.selected.prefixKind || "proton"
        property string prefixWord: prefixKind === "proton" ? "Proton prefix" : "Wine prefix"

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

            RowLayout {
                Layout.fillWidth: true
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
                // the one thing most people came to do
                PsButton {
                    Layout.alignment: Qt.AlignTop
                    text: "Launch"
                    visible: (library.selected.launchUri || "").length > 0
                    Accessible.name: "Launch " + (library.selected.name || "") + " via "
                                     + page.sourceLabel(detailCard.isShortcut ? "steam" : library.selected.source)
                    onClicked: gameTools.launchUri(library.selected.launchUri)
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Text {
                    height: 22
                    verticalAlignment: Text.AlignVCenter
                    text: library.selected.idLabel || ""
                    color: Theme.muted
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.fsSmall
                }
                Rectangle {
                    width: statusLbl.implicitWidth + 16
                    height: 22
                    radius: 11
                    color: library.selected.hasPrefix ? Theme.successTint : Theme.surfaceElevated
                    border.width: 1
                    border.color: library.selected.hasPrefix ? Theme.success : Theme.border
                    Text {
                        id: statusLbl
                        anchors.centerIn: parent
                        text: detailCard.prefixKind === "none" ? "Runs natively, no prefix"
                              : (library.selected.hasPrefix ? detailCard.prefixWord + " present"
                                                            : "No prefix yet")
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
                    model: {
                        var rows = [{ k: "Install", v: library.selected.installPath || "Not known" }]
                        if (detailCard.prefixKind !== "none")
                            rows.push({ k: detailCard.prefixKind === "proton" ? "Prefix (compatdata)" : "Prefix",
                                        v: library.selected.compatdataPath || "Not created yet" })
                        if ((library.selected.libraryPath || "").length > 0)
                            rows.push({ k: "Library", v: library.selected.libraryPath })
                        return rows
                    }
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

            // ===== Steam + Non-Steam shortcuts: Proton; Steam only: launch options + presets =====
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Theme.space
              visible: detailCard.isSteam || detailCard.isShortcut

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- proton version (writes config.vdf, fail-closed) ---
            PsSectionHeader {
                Layout.fillWidth: true
                text: "Proton version"
                subtitle: "Compatibility tool · saved to Steam's config.vdf as soon as you pick"
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
                color: launch.protonStatusOk ? Theme.success : Theme.danger
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            // Non-Steam shortcut: Steam stores these inside the shortcut itself
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                visible: detailCard.isShortcut
                Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.border }
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Launch options"
                    subtitle: "Read-only here. Change them in Steam: right-click the game, Properties."
                }
                Text {
                    Layout.fillWidth: true
                    text: (library.selected.launchOptions || "").length > 0 ? library.selected.launchOptions : "None set"
                    wrapMode: Text.WrapAnywhere
                    color: (library.selected.launchOptions || "").length > 0 ? Theme.text : Theme.faint
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.fsSmall
                }
            }

            // Steam games: the editable launch options
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Theme.space
              visible: detailCard.isSteam

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- launch options (writes localconfig.vdf, fail-closed) ---
            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Launch options"
                    subtitle: "Saved to Steam's localconfig.vdf when you press Save to Steam"
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
                placeholder: "e.g. gamemoderun %command%"
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
                    color: launch.statusOk ? Theme.success : Theme.danger
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
                    delegate: PsChip {
                        required property var modelData
                        text: "+ " + modelData.name + (modelData.installed ? "" : " (not installed)")
                        dimmed: !modelData.installed
                        enabled: launch.loaded
                        Accessible.name: "Add " + modelData.name + " to the launch options"
                        Accessible.description: modelData.description
                        onClicked: launch.appendPreset(modelData.value)
                    }
                }
            }

            } // end Steam games: editable launch options
            } // ===== end Proton + launch options + presets =====

            // ===== ProtonDB community rating (Steam-only; opt-in network lookup) =====
            ColumnLayout {
                id: protondbSection
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                visible: detailCard.isSteam

                // Only Steam ids are ProtonDB ids — Heroic/Lutris games bind 0,
                // which clears the controller and fires no request.
                Binding {
                    target: protondb
                    property: "appid"
                    value: detailCard.isSteam ? (parseInt(library.selectedAppId, 10) || 0) : 0
                }
                // The controller hands over a Theme token *name*; resolve it here.
                function tierColor(key) {
                    var c = Theme[key]
                    return c !== undefined ? c : Theme.tierPending
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.spaceSm
                    PsSectionHeader {
                        Layout.fillWidth: true
                        text: "ProtonDB"
                        subtitle: "Community compatibility reports · protondb.com"
                    }
                    BusyIndicator {
                        running: protondb.loading
                        visible: protondb.loading
                        implicitWidth: 20; implicitHeight: 20
                    }
                    PsButton {
                        text: "\u21bb"
                        primary: false
                        visible: protondb.enabled
                        enabled: !protondb.loading
                        implicitWidth: 40
                        implicitHeight: 32
                        Accessible.name: "Refresh ProtonDB rating"
                        onClicked: protondb.refresh()
                    }
                }

                // privacy opt-in — shown while lookups are switched off
                RowLayout {
                    Layout.fillWidth: true
                    visible: !protondb.enabled
                    spacing: Theme.spaceSm
                    Text {
                        Layout.fillWidth: true
                        text: "Lookups are off. Enabling sends this game's Steam app id to protondb.com."
                        wrapMode: Text.WordWrap
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                    PsButton {
                        text: "Enable lookups"
                        primary: false
                        onClicked: protondb.setEnabled(true)
                    }
                }

                // tier badge + report count
                RowLayout {
                    Layout.fillWidth: true
                    visible: protondb.enabled && protondb.loaded
                    spacing: Theme.spaceSm
                    Rectangle {
                        implicitWidth: tierLbl.implicitWidth + 20
                        implicitHeight: 26
                        radius: 13
                        color: protondbSection.tierColor(protondb.tierColorKey)
                        Accessible.role: Accessible.StaticText
                        Accessible.name: "ProtonDB tier: " + protondb.tierLabel
                        Text {
                            id: tierLbl
                            anchors.centerIn: parent
                            text: protondb.tierLabel
                            color: Theme.inkOn(parent.color)
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            font.weight: Font.Bold
                            font.capitalization: Font.AllUppercase
                            font.letterSpacing: 0.6
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: protondb.total === 0
                              ? "No reports yet"
                              : protondb.total + (protondb.total === 1 ? " report" : " reports")
                                + (protondb.confidence.length > 0 ? " \u00b7 " + protondb.confidence + " confidence" : "")
                        elide: Text.ElideRight
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                }

                // trending tier — only when it differs from the overall one
                RowLayout {
                    visible: protondb.enabled && protondb.loaded && protondb.trendingLabel.length > 0
                    spacing: Theme.spaceXs
                    Text {
                        text: "Trending"
                        color: Theme.faint
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                    Rectangle {
                        implicitWidth: trendLbl.implicitWidth + 14
                        implicitHeight: 20
                        radius: 10
                        color: protondbSection.tierColor(protondb.trendingColorKey)
                        Text {
                            id: trendLbl
                            anchors.centerIn: parent
                            text: protondb.trendingLabel
                            color: Theme.inkOn(parent.color)
                            font.family: Theme.fontFamily
                            font.pixelSize: 10
                            font.weight: Font.Bold
                            font.capitalization: Font.AllUppercase
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: protondb.enabled && protondb.error.length > 0
                    text: protondb.error + (protondb.loaded ? " \u2014 showing the cached rating" : "")
                    wrapMode: Text.WordWrap
                    color: Theme.danger
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: protondb.enabled
                    spacing: Theme.spaceSm
                    PsButton {
                        text: "Open on ProtonDB"
                        primary: false
                        enabled: protondb.pageUrl.length > 0
                        onClicked: protondb.openPage()
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: protondb.fetchedLabel.length > 0
                        text: protondb.fetchedLabel
                        elide: Text.ElideRight
                        color: Theme.faint
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                }
            } // ===== end ProtonDB =====

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- prefix + shader cache maintenance ---
            RowLayout {
                Layout.fillWidth: true
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Maintenance"
                    subtitle: detailCard.prefixKind === "none" ? "Folders"
                              : (detailCard.isSteam ? "Prefix, shader cache and folders" : "Prefix and folders")
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
                    // only what applies: no prefix facts for a native game,
                    // no Steam shader cache outside Steam
                    model: {
                        var chips = []
                        if (detailCard.prefixKind !== "none") {
                            chips.push({ l: "Prefix", v: gameTools.info.prefixExists ? gameTools.info.prefixSize : "none" })
                            if (gameTools.info.prefixExists) {
                                chips.push({ l: "Created", v: gameTools.info.created || "unknown" })
                                chips.push({ l: "DXVK", v: gameTools.info.dxvk || "not found" })
                                chips.push({ l: "VKD3D", v: gameTools.info.vkd3d || "not found" })
                            }
                        }
                        if (detailCard.isSteam)
                            chips.push({ l: "Shader cache", v: gameTools.info.shaderExists ? gameTools.info.shaderSize : "none" })
                        return chips
                    }
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
                color: gameTools.statusOk ? Theme.success : Theme.danger
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
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
                    visible: detailCard.prefixKind !== "none"
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
                    text: "Delete prefix…"
                    primary: false
                    danger: true
                    sound: "back"
                    visible: detailCard.prefixKind !== "none"
                    enabled: gameTools.info.prefixExists === true && !gameTools.busy
                    onClicked: deletePrefixConfirm.open()
                }
            }

            // ===== Steam: per-game tools; Non-Steam shortcuts: Winetricks only =====
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Theme.space
              visible: detailCard.isSteam || detailCard.isShortcut

            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

            // --- per-game overrides ---
            PsSectionHeader {
                Layout.fillWidth: true
                text: "Per-game tools"
                subtitle: detailCard.isSteam ? "Launch check, Proton log, overrides, Winetricks, known fixes, profiles and save backups"
                                             : "Check why it won't start, or install Windows components into its prefix"
            }
            Flow {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                PsButton {
                    text: "Launch check…"
                    primary: false
                    onClicked: { launchCheckDialog.open(); page.runLaunchCheck() }
                }
                PsButton {
                    text: "Proton log…"
                    primary: false
                    visible: detailCard.isSteam
                    onClicked: { protonLog.open(library.selected.appId); protonLogDialog.open() }
                }
                PsButton {
                    text: "ScopeBuddy override…"
                    primary: false
                    visible: detailCard.isSteam
                    onClicked: {
                        perAppScb.appId = library.selected.appId
                        scbOverrideDialog.open()
                    }
                }
                PsButton {
                    text: "MangoHud override…"
                    primary: false
                    visible: detailCard.isSteam
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
                    visible: detailCard.isSteam
                    onClicked: { fixes.appId = library.selected.appId; fixesDialog.open() }
                }
                PsButton {
                    text: "Profiles…"
                    primary: false
                    visible: detailCard.isSteam
                    onClicked: { profiles.appId = library.selected.appId; profiles.refresh(); profilesDialog.open() }
                }
                PsButton {
                    text: "Save backups…"
                    primary: false
                    visible: detailCard.isSteam
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
                                                       : "No per-game config yet - toggling creates one"
                    }
                    BusyIndicator { running: heroic.loading; visible: heroic.loading; implicitWidth: 20; implicitHeight: 20 }
                }

                // wine/proton version (a native Linux game uses neither)
                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Wine / Proton version"
                    visible: detailCard.prefixKind !== "none"
                }
                PsSelect {
                    id: heroicWineSelect
                    Layout.fillWidth: true
                    visible: detailCard.prefixKind !== "none"
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
                    visible: heroic.wineVersions.length === 0 && detailCard.prefixKind !== "none"
                    text: "No Wine or Proton builds found in Heroic's tools folder. Install one from Heroic's Wine Manager."
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

                Text {
                    Layout.fillWidth: true
                    visible: heroic.status.length > 0
                    text: heroic.status
                    wrapMode: Text.WordWrap
                    color: heroic.statusOk ? Theme.success : Theme.danger
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
                    text: perAppScb.exists ? "Existing override" : "No override yet - add keys to create one."
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
                    delegate: PsChip {
                        required property string modelData
                        text: "+ " + modelData
                        mono: true
                        enabled: perAppScb.loaded
                        Accessible.name: "Add key " + modelData
                        onClicked: perAppScb.addKey(modelData)
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
                    PsIconButton {
                        glyph: "✕"
                        danger: true
                        label: "Remove " + (r.key.length > 0 ? r.key : "this row")
                        onClicked: perAppScb.model.removeRow(r.index)
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
                    text: "Delete override"; primary: false; danger: true
                    visible: perAppScb.exists
                    onClicked: {
                        deleteOverrideConfirm.controllerObj = perAppScb
                        deleteOverrideConfirm.label = "ScopeBuddy"
                        deleteOverrideConfirm.open()
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: perAppScb.status
                    color: perAppScb.statusOk ? Theme.success : Theme.danger
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
                    sound: ""  // the outcome chime says it
                    onClicked: { perAppScb.save(); sounds.result(perAppScb.statusOk) }
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
                                              : "No override yet - pick a preset or toggle metrics."
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
                    delegate: PsChip {
                        required property string modelData
                        text: modelData
                        enabled: perGameMango.loaded
                        Accessible.name: "Apply preset " + modelData
                        onClicked: {
                            perGameMangoPresetConfirm.pendingPreset = modelData
                            perGameMangoPresetConfirm.open()
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
                    text: "Delete override"; primary: false; danger: true
                    visible: perGameMango.exists
                    onClicked: {
                        deleteOverrideConfirm.controllerObj = perGameMango
                        deleteOverrideConfirm.label = "MangoHud"
                        deleteOverrideConfirm.open()
                    }
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: perGameMango.status
                    color: perGameMango.statusOk ? Theme.success : Theme.danger
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
                    sound: ""  // the outcome chime says it
                    onClicked: { perGameMango.save(); sounds.result(perGameMango.statusOk) }
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
                            function toggle() {
                                var s = protontricksDialog.selected
                                s[verbRow.modelData.verb] = !verbRow.checked
                                protontricksDialog.selected = s
                                sounds.play(verbRow.checked ? "toggle_on" : "toggle_off")
                            }
                            activeFocusOnTab: true
                            Accessible.role: Accessible.CheckBox
                            Accessible.name: verbRow.modelData.label
                            Accessible.checked: verbRow.checked
                            Accessible.onPressAction: verbRow.toggle()
                            Keys.onSpacePressed: verbRow.toggle()
                            HoverHandler { id: vh }
                            TapHandler { onTapped: verbRow.toggle() }
                            // keyboard focus ring
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: -2
                                radius: parent.radius + 2
                                color: "transparent"
                                border.width: 2
                                border.color: Theme.accentBright
                                visible: verbRow.activeFocus
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
                    color: protontricks.statusOk ? Theme.success : Theme.danger
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
        subtitle: (library.selected.name || "") + " · adds to the launch options, saved when you press Save to Steam"

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
                                text: "Add to launch options"; primary: false
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
                text: "The launch options are still loading. Fixes can be added once they are."
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

            // Export / import: profiles travel as one JSON bundle so a whole
            // setup can move between machines (or be shared).
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Text {
                    Layout.fillWidth: true
                    text: "Profiles are stored as JSON - export a bundle to back them up or move them to another PC."
                    wrapMode: Text.WordWrap
                    color: Theme.faint; font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Import…"; primary: false
                    enabled: !profiles.busy
                    onClicked: importDialog.open()
                }
                PsButton {
                    text: "Export all…"; primary: false
                    enabled: profiles.profiles.length > 0 && !profiles.busy
                    onClicked: { exportDialog.profileName = ""; exportDialog.open() }
                }
            }
            PsSwitchRow {
                id: importOverwrite
                text: "Replace same-named profiles when importing"
                subtitle: "Off: existing profiles are kept and the import reports what it skipped."
                checked: false
                onToggled: function(v) { checked = v }
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
                        PsButton {
                            text: "Export"; primary: false; enabled: !profiles.busy
                            implicitWidth: 80
                            onClicked: { exportDialog.profileName = modelData; exportDialog.open() }
                        }
                        PsButton {
                            text: "Delete"; primary: false; danger: true
                            enabled: !profiles.busy
                            onClicked: { deleteProfileConfirm.pendingName = modelData; deleteProfileConfirm.open() }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                BusyIndicator { running: profiles.busy; visible: profiles.busy; implicitWidth: 18; implicitHeight: 18 }
                Text {
                    Layout.fillWidth: true; text: profiles.status
                    wrapMode: Text.WordWrap
                    color: profiles.statusOk ? Theme.success : Theme.danger
                    font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
                }
            }
        }
    }

    // Deleting a profile removes its saved snapshot outright — confirm first.
    PsDialog {
        id: deleteProfileConfirm
        property string pendingName: ""
        title: "Delete profile?"
        width: 380
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "“" + deleteProfileConfirm.pendingName + "” will be permanently removed."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Cancel"; primary: false
                    onClicked: deleteProfileConfirm.close()
                }
                PsButton {
                    text: "Delete"; primary: false; danger: true
                    onClicked: {
                        profiles.deleteProfile(deleteProfileConfirm.pendingName)
                        deleteProfileConfirm.close()
                    }
                }
            }
        }
    }

    // Native pickers (xdg portal under Flatpak). One export dialog serves both
    // "export all" (profileName === "") and a single row's Export button.
    FileDialog {
        id: exportDialog
        property string profileName: ""
        title: profileName.length > 0 ? "Export profile “" + profileName + "”" : "Export all profiles"
        fileMode: FileDialog.SaveFile
        nameFilters: ["ProtonShift profiles (*.json)"]
        defaultSuffix: "json"
        currentFile: "file:///" + (profileName.length > 0
            ? profileName.replace(/[^A-Za-z0-9._-]+/g, "_")
            : "protonshift-profiles") + ".json"
        onAccepted: profileName.length > 0
            ? profiles.exportOne(profileName, selectedFile)
            : profiles.exportAll(selectedFile)
    }
    FileDialog {
        id: importDialog
        title: "Import profiles"
        fileMode: FileDialog.OpenFile
        nameFilters: ["ProtonShift profiles (*.json)", "All files (*)"]
        onAccepted: profiles.importFrom(selectedFile, importOverwrite.checked)
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
                color: saves.statusOk ? Theme.success : Theme.danger
                font.family: Theme.fontFamily; font.pixelSize: Theme.fsCaption
            }
        }
    }

    // ============================ LAUNCH CHECK DIALOG =======================
    PsDialog {
        id: launchCheckDialog
        objectName: "launchCheckDialog"
        width: 660
        title: "Launch check"
        subtitle: (library.selected.name || "") + " · the usual reasons a game won't start"

        // one chime when a run finishes
        property bool wasRunning: false
        Connections {
            target: launchCheck
            function onChanged() {
                if (launchCheckDialog.wasRunning && !launchCheck.running && launchCheckDialog.opened) {
                    var worst = "ok"
                    for (var i = 0; i < launchCheck.findings.length; i++) {
                        var l = launchCheck.findings[i].level
                        if (l === "error") worst = "error"
                        else if (l === "warn" && worst !== "error") worst = "warn"
                    }
                    sounds.play(worst === "error" ? "error" : (worst === "warn" ? "notification" : "success"))
                }
                launchCheckDialog.wasRunning = launchCheck.running
            }
        }

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                BusyIndicator {
                    running: launchCheck.running; visible: launchCheck.running
                    implicitWidth: 20; implicitHeight: 20
                }
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: launchCheck.running ? "Checking…" : launchCheck.summary
                    color: launchCheck.running ? Theme.muted
                           : (launchCheck.hasProblems ? Theme.text : Theme.success)
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsBody
                    font.weight: Font.DemiBold
                }
            }
            Text {
                Layout.fillWidth: true
                visible: detailCard.isSteam && launch.dirty
                wrapMode: Text.WordWrap
                text: "This checks the launch options saved in Steam. Your unsaved edits are not included."
                color: Theme.warning
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            ListView {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(Math.max(contentHeight, 40), 380)
                clip: true
                spacing: 6
                model: launchCheck.findings
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    id: findingRow
                    required property var modelData
                    readonly property color tone: page.levelColor(modelData.level)
                    width: ListView.view.width
                    implicitHeight: findingCol.implicitHeight + 2 * Theme.spaceSm
                    radius: Theme.radiusSm
                    color: Theme.bgDeep
                    border.width: 1
                    border.color: (modelData.level === "error" || modelData.level === "warn") ? tone : Theme.border
                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData.level + ": " + modelData.title
                    Accessible.description: modelData.detail + " " + modelData.fix
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.spaceSm
                        spacing: Theme.spaceSm
                        Rectangle {
                            Layout.alignment: Qt.AlignTop
                            implicitWidth: 20; implicitHeight: 20; radius: 10
                            color: "transparent"
                            border.width: 1
                            border.color: findingRow.tone
                            Text {
                                anchors.centerIn: parent
                                text: page.levelGlyph(findingRow.modelData.level)
                                color: findingRow.tone
                                font.family: Theme.fontFamily
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                        ColumnLayout {
                            id: findingCol
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                Layout.fillWidth: true
                                text: findingRow.modelData.title
                                wrapMode: Text.WordWrap
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                                font.weight: Font.DemiBold
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: findingRow.modelData.detail.length > 0
                                text: findingRow.modelData.detail
                                wrapMode: Text.Wrap
                                color: Theme.muted
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsCaption
                            }
                            Text {
                                Layout.fillWidth: true
                                visible: findingRow.modelData.fix.length > 0
                                text: "What to do: " + findingRow.modelData.fix
                                wrapMode: Text.Wrap
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsCaption
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: "Checks files and settings on this PC. It does not start the game."
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Proton log…"; primary: false
                    visible: detailCard.isSteam
                    onClicked: {
                        launchCheckDialog.close()
                        protonLog.open(library.selected.appId)
                        protonLogDialog.open()
                    }
                }
                PsButton {
                    text: "Check again"
                    enabled: !launchCheck.running
                    onClicked: page.runLaunchCheck()
                }
            }
        }
    }

    // ============================ PROTON LOG DIALOG =========================
    PsDialog {
        id: protonLogDialog
        objectName: "protonLogDialog"
        width: 820
        title: "Proton log"
        subtitle: (library.selected.name || "") + " · what Proton wrote the last time the game ran"
        readonly property bool loggingOn: protonLog.loggingEnabled(launch.text)

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            // logging switch state
            Rectangle {
                Layout.fillWidth: true
                radius: Theme.radiusSm
                color: protonLogDialog.loggingOn ? Theme.successTint : Theme.warningSurface
                border.width: 1
                border.color: protonLogDialog.loggingOn ? Theme.success : Theme.warningBorder
                implicitHeight: logState.implicitHeight + 2 * Theme.spaceSm
                RowLayout {
                    id: logState
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    spacing: Theme.spaceSm
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        text: protonLogDialog.loggingOn
                              ? (launch.dirty ? "Logging is switched on, but not saved yet. Press Save to Steam, then run the game."
                                              : "Logging is on. Each run of the game replaces the log.")
                              : "Logging is off for this game, so Proton writes no log."
                        color: protonLogDialog.loggingOn ? Theme.success : Theme.warning
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                    PsButton {
                        text: "Turn on logging"
                        primary: false
                        implicitHeight: 32
                        visible: !protonLogDialog.loggingOn
                        enabled: launch.loaded
                        onClicked: launch.appendPreset("PROTON_LOG=1")
                    }
                    PsButton {
                        text: "Save to Steam"
                        implicitHeight: 32
                        visible: protonLogDialog.loggingOn && launch.dirty
                        onClicked: launch.save()
                    }
                }
            }

            // file facts + filter
            RowLayout {
                Layout.fillWidth: true
                visible: protonLog.exists
                spacing: Theme.space
                Text {
                    Layout.fillWidth: true
                    elide: Text.ElideMiddle
                    text: protonLog.path + "  ·  " + protonLog.sizeLabel + "  ·  " + protonLog.modifiedLabel
                    color: Theme.faint
                    font.family: Theme.monoFamily
                    font.pixelSize: Theme.fsCaption
                }
                BusyIndicator {
                    running: protonLog.loading; visible: protonLog.loading
                    implicitWidth: 18; implicitHeight: 18
                }
            }
            PsSwitchRow {
                Layout.fillWidth: true
                visible: protonLog.exists
                text: "Show only lines that look like problems"
                subtitle: protonLog.problemCount === 0 ? "None found in the part of the log that was read"
                          : protonLog.problemCount + (protonLog.problemCount === 1 ? " line" : " lines")
                            + " with errors, crashes or missing files"
                checked: protonLog.problemsOnly
                onToggled: protonLog.setProblemsOnly(value)
            }

            // the log itself
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 320
                radius: Theme.radiusSm
                color: Theme.bgDeep
                border.color: Theme.border
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    width: parent.width - 2 * Theme.spaceLg
                    visible: !protonLog.loading && (!protonLog.exists || protonLog.error.length > 0
                                                    || protonLog.text.length === 0)
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    text: protonLog.error.length > 0 ? protonLog.error
                          : !protonLog.exists
                            ? "No log yet. Turn logging on, save, run the game once and quit it, then press Refresh."
                            : (protonLog.problemsOnly ? "No lines that look like problems." : "The log is empty.")
                    color: protonLog.error.length > 0 ? Theme.danger : Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                ScrollView {
                    id: logScroll
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    clip: true
                    visible: protonLog.exists && protonLog.text.length > 0
                    TextEdit {
                        id: logText
                        width: logScroll.availableWidth
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.WrapAnywhere
                        text: protonLog.text
                        color: Theme.muted
                        font.family: Theme.monoFamily
                        font.pixelSize: 11
                        Accessible.name: "Proton log"
                        // a log is read from its end: that is where it stopped
                        onTextChanged: Qt.callLater(function () {
                            logScroll.ScrollBar.vertical.position = Math.max(0, 1.0 - logScroll.ScrollBar.vertical.size)
                        })
                    }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: protonLog.exists && protonLog.truncated
                text: "Showing the end of the log. Open the file for all of it."
                color: Theme.faint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Text {
                    Layout.fillWidth: true
                    text: protonLog.notice
                    elide: Text.ElideRight
                    color: Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
                PsButton {
                    text: "Open file"; primary: false; sound: ""
                    enabled: protonLog.exists
                    onClicked: sounds.play(protonLog.openFile() ? "click" : "error")
                }
                PsButton {
                    text: "Copy"; primary: false; sound: ""
                    enabled: protonLog.exists && protonLog.text.length > 0
                    onClicked: sounds.result(protonLog.copy())
                }
                PsButton {
                    text: "Refresh"
                    enabled: !protonLog.loading
                    onClicked: protonLog.refresh()
                }
            }
        }
    }

    // Leaving a game with unsaved launch options: nothing is saved or dropped
    // without the user saying so.
    PsDialog {
        id: unsavedDialog
        property string pendingAppId: ""
        title: "Unsaved launch options"
        width: 440
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "The launch options for " + (library.selected.name || "this game")
                      + " have changes that aren't saved to Steam yet."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Discard changes"; primary: false; danger: true; sound: "back"
                    onClicked: {
                        unsavedDialog.close()
                        library.select(unsavedDialog.pendingAppId)
                    }
                }
                PsButton {
                    text: "Keep editing"
                    onClicked: unsavedDialog.close()
                }
            }
        }
    }

    // Deleting a prefix wipes the game's Windows-side files (settings, and
    // saves that aren't in the cloud). Same confirm pattern as every other delete.
    PsDialog {
        id: deletePrefixConfirm
        title: "Delete this prefix?"
        subtitle: library.selected.name || ""
        width: 480
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "This removes the " + detailCard.prefixWord + " ("
                      + (gameTools.info.prefixSize || "size unknown") + "), including in-game settings and any "
                      + "saves stored inside it. It is recreated empty the next time the game runs."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            Text {
                Layout.fillWidth: true
                text: library.selected.compatdataPath || ""
                wrapMode: Text.WrapAnywhere
                color: Theme.text
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
            Text {
                Layout.fillWidth: true
                visible: detailCard.isSteam
                wrapMode: Text.WordWrap
                text: "Tip: Per-game tools, Save backups can back up the saves first."
                color: Theme.faint
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsCaption
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Cancel"; primary: false; sound: "back"
                    onClicked: deletePrefixConfirm.close()
                }
                PsButton {
                    text: "Delete prefix"; primary: false; danger: true
                    onClicked: {
                        gameTools.deletePrefix()
                        deletePrefixConfirm.close()
                    }
                }
            }
        }
    }

    // Shared confirm for the per-game ScopeBuddy / MangoHud override delete
    // buttons above — both just call deleteOverride() on whichever controller
    // was armed.
    PsDialog {
        id: deleteOverrideConfirm
        property var controllerObj: null
        property string label: ""
        title: "Delete override?"
        width: 380
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "This removes the " + deleteOverrideConfirm.label + " override for this game."
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Cancel"; primary: false
                    onClicked: deleteOverrideConfirm.close()
                }
                PsButton {
                    text: "Delete"; primary: false; danger: true
                    onClicked: {
                        if (deleteOverrideConfirm.controllerObj)
                            deleteOverrideConfirm.controllerObj.deleteOverride()
                        deleteOverrideConfirm.close()
                    }
                }
            }
        }
    }

    // Applying a MangoHud preset to a per-game override replaces every
    // metric/value in it — confirm before overwriting.
    PsDialog {
        id: perGameMangoPresetConfirm
        property string pendingPreset: ""
        title: "Replace override?"
        width: 420
        ColumnLayout {
            width: parent.width
            spacing: Theme.space
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "“" + perGameMangoPresetConfirm.pendingPreset + "” replaces every metric and value in this game's MangoHud override"
                      + (perGameMango.dirty ? ", including your unsaved edits." : ".")
                color: Theme.muted
                font.family: Theme.fontFamily
                font.pixelSize: Theme.fsSmall
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.spaceSm
                Item { Layout.fillWidth: true }
                PsButton {
                    text: "Cancel"; primary: false
                    onClicked: perGameMangoPresetConfirm.close()
                }
                PsButton {
                    text: "Replace"; primary: false; danger: true
                    onClicked: {
                        perGameMango.applyPreset(perGameMangoPresetConfirm.pendingPreset)
                        perGameMangoPresetConfirm.close()
                    }
                }
            }
        }
    }
}
