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

    // selecting a game drives the launch-options controller
    Connections {
        target: library
        function onSelectedChanged() { launch.appId = library.selectedAppId }
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

            Item { Layout.fillHeight: true }
        }
    }
}
