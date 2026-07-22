import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Effects
import QtQuick.Layouts
import App

ApplicationWindow {
    id: window
    visible: true
    width: 1040
    height: 720
    minimumWidth: 840
    minimumHeight: 560
    title: "ProtonShift"
    color: Theme.bg

    // theme: drive the Theme singleton from the persisted/ resolved choice
    Binding { target: Theme; property: "themeName"; value: themeCtl.resolvedTheme }

    // smooth cross-fade when the palette changes
    Behavior on color { ColorAnimation { duration: 220 } }

    // ambient animated background
    GlowBackground { anchors.fill: parent }

    property int currentPage: 0
    readonly property var pages: ["Library", "Environment", "MangoHud", "ScopeBuddy", "Gamescope", "Displays", "System", "Controllers"]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spaceLg
        spacing: Theme.spaceLg

        // --- header / wordmark ---------------------------------------------
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.spaceSm

            Image {
                source: "assets/logo.png"
                Layout.preferredWidth: 34
                Layout.preferredHeight: 34
                sourceSize: Qt.size(128, 128)
                smooth: true
                mipmap: true
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.glow
                    shadowOpacity: 0.55
                    shadowBlur: 0.9
                    shadowVerticalOffset: 2
                }
            }

            RowLayout {
                spacing: 0
                Text {
                    text: "Proton"
                    color: Theme.text
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsTitle
                    font.weight: Font.Bold
                }
                Text {
                    text: "Shift"
                    color: Theme.wordmark
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsTitle
                    font.weight: Font.Bold
                }
            }

            Item { Layout.fillWidth: true }

            // --- theme picker ---
            Rectangle {
                id: themeBtn
                implicitWidth: themeRow.implicitWidth + 2 * Theme.spaceSm
                implicitHeight: 30
                radius: Theme.radiusSm
                color: themeHover.hovered || themeMenu.visible ? Theme.surfaceElevated : Theme.surface
                border.color: themeBtn.activeFocus ? Theme.accentBright
                              : (themeMenu.visible ? Theme.primary : Theme.border)
                border.width: themeBtn.activeFocus ? 2 : 1
                Behavior on color { ColorAnimation { duration: 120 } }

                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: "Theme: " + themeBtn.labelFor(themeCtl.choice)
                Accessible.focusable: true
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                            || event.key === Qt.Key_Enter || event.key === Qt.Key_Down) {
                        themeMenu.open()
                        event.accepted = true
                    }
                }

                function labelFor(choice) {
                    if (choice === "system") return "System"
                    for (var i = 0; i < themeCtl.themes.length; i++)
                        if (themeCtl.themes[i].id === choice) return themeCtl.themes[i].label
                    return choice
                }

                RowLayout {
                    id: themeRow
                    anchors.centerIn: parent
                    spacing: 6
                    // swatch of the active palette
                    Rectangle {
                        width: 14; height: 14; radius: 4
                        color: Theme.surface
                        border.color: Theme.border; border.width: 1
                        Rectangle {
                            anchors.centerIn: parent
                            width: 8; height: 8; radius: 4
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Theme.gradA }
                                GradientStop { position: 1.0; color: Theme.gradB }
                            }
                        }
                    }
                    Text {
                        text: themeBtn.labelFor(themeCtl.choice)
                        color: Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                        font.weight: Font.DemiBold
                    }
                    Text { text: "▾"; color: Theme.faint; font.pixelSize: 10 }
                }
                HoverHandler { id: themeHover }
                TapHandler { onTapped: themeMenu.open() }

                Popup {
                    id: themeMenu
                    y: themeBtn.height + 6
                    x: themeBtn.width - width
                    width: 200
                    padding: 6
                    focus: true
                    background: Rectangle {
                        radius: Theme.radiusSm
                        color: Theme.surface
                        border.color: Theme.borderStrong
                        border.width: 1
                    }

                    // keyboard model/selection: Up/Down move the highlight,
                    // Enter/Space picks it, Escape closes (default closePolicy)
                    readonly property var menuModel: [{ id: "system", label: "System (auto)" }].concat(themeCtl.themes)
                    property int highlightIndex: 0
                    function activateHighlight() {
                        themeCtl.setTheme(menuModel[highlightIndex].id)
                        themeMenu.close()
                    }
                    onOpened: {
                        highlightIndex = 0
                        for (var i = 0; i < menuModel.length; i++)
                            if (menuModel[i].id === themeCtl.choice) { highlightIndex = i; break }
                    }

                    contentItem: ColumnLayout {
                        spacing: 2
                        focus: true
                        Keys.onPressed: (event) => {
                            var n = themeMenu.menuModel.length
                            if (event.key === Qt.Key_Up) {
                                themeMenu.highlightIndex = (themeMenu.highlightIndex + n - 1) % n
                                event.accepted = true
                            } else if (event.key === Qt.Key_Down) {
                                themeMenu.highlightIndex = (themeMenu.highlightIndex + 1) % n
                                event.accepted = true
                            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter
                                       || event.key === Qt.Key_Space) {
                                themeMenu.activateHighlight()
                                event.accepted = true
                            }
                        }
                        // System (auto) row
                        Repeater {
                            model: themeMenu.menuModel
                            delegate: Rectangle {
                                id: themeMenuRow
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true
                                implicitWidth: 188
                                implicitHeight: 34
                                radius: Theme.radiusSm
                                property bool active: themeCtl.choice === modelData.id
                                property bool highlighted: themeMenu.highlightIndex === index
                                color: active ? Theme.surfaceElevated
                                     : (rowHov.hovered || highlighted ? Theme.bgDeep : "transparent")
                                border.width: highlighted ? 1 : 0
                                border.color: Theme.accentBright
                                Accessible.role: Accessible.MenuItem
                                Accessible.name: themeMenuRow.modelData.label
                                HoverHandler { id: rowHov }
                                TapHandler { onTapped: { themeCtl.setTheme(themeMenuRow.modelData.id); themeMenu.close() } }
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.spaceSm
                                    anchors.rightMargin: Theme.spaceSm
                                    spacing: Theme.spaceSm
                                    // swatch (system shows a split light/dark)
                                    Rectangle {
                                        width: 18; height: 18; radius: 5
                                        color: themeMenuRow.modelData.id === "system" ? Theme.bg
                                               : Theme.palettes[themeMenuRow.modelData.id].bg
                                        border.color: Theme.border; border.width: 1
                                        Rectangle {
                                            anchors.centerIn: parent
                                            width: 9; height: 9; radius: 4.5
                                            color: themeMenuRow.modelData.id === "system" ? Theme.primary
                                                   : Theme.palettes[themeMenuRow.modelData.id].primary
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: themeMenuRow.modelData.label
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: themeMenuRow.active ? Font.DemiBold : Font.Normal
                                    }
                                    Text {
                                        visible: themeMenuRow.active
                                        text: "✓"; color: Theme.primaryBright; font.pixelSize: 13; font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Text {
                text: "v" + appVersion
                color: Theme.faint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
        }

        // --- tabs (wrap to a second line on narrow windows) ----------------
        // Keyboard: the selected tab is the strip's Tab stop (roving tabindex);
        // Left/Right move focus along the strip, Space/Enter activate a page.
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            Repeater {
                id: tabRepeater
                model: window.pages
                delegate: Rectangle {
                    id: tab
                    required property int index
                    required property string modelData
                    implicitWidth: tabLbl.implicitWidth + 2 * Theme.space
                    implicitHeight: 32
                    radius: Theme.radiusSm
                    property bool active: window.currentPage === index
                    color: active ? Theme.surfaceElevated
                                  : (tabHover.hovered ? Theme.surface : "transparent")
                    border.width: tab.activeFocus ? 2 : (active ? 1 : 0)
                    border.color: tab.activeFocus ? Theme.accentBright : Theme.borderStrong
                    Behavior on color { ColorAnimation { duration: 120 } }

                    activeFocusOnTab: tab.active
                    Accessible.role: Accessible.PageTab
                    Accessible.name: tab.modelData
                    Accessible.focusable: true
                    Keys.onPressed: (event) => {
                        var n = window.pages.length
                        if (event.key === Qt.Key_Left) {
                            tabRepeater.itemAt((tab.index + n - 1) % n).forceActiveFocus(Qt.BacktabFocusReason)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Right) {
                            tabRepeater.itemAt((tab.index + 1) % n).forceActiveFocus(Qt.TabFocusReason)
                            event.accepted = true
                        } else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                                   || event.key === Qt.Key_Enter) {
                            window.currentPage = tab.index
                            event.accepted = true
                        }
                    }

                    HoverHandler { id: tabHover }
                    TapHandler { onTapped: window.currentPage = tab.index }
                    Text {
                        id: tabLbl
                        anchors.centerIn: parent
                        text: tab.modelData
                        color: tab.active ? Theme.text : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                        font.weight: tab.active ? Font.DemiBold : Font.Normal
                    }
                }
            }
        }

        // --- page stack -----------------------------------------------------
        // Each page sits behind a Loader that activates on first visit and then
        // stays loaded, so page state persists but startup doesn't pay for all
        // eight pages (GamesPage alone carries six dialogs).
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.currentPage

            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 0
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: GamesPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 1
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: EnvironmentPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 2
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: MangoHudPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 3
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: ScopeBuddyPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 4
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: GamescopeBuilderPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 5
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: DisplayPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 6
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: SystemPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 7
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: ControllersPage {}
            }
        }
    }

    // branded startup overlay — covers the UI briefly, then dissolves.
    // Last child, so it sits above everything (header, tabs, pages); unloaded
    // for good once the intro finishes so its MultiEffect layers don't linger.
    Loader {
        id: splashLoader
        anchors.fill: parent
        z: 1000
        sourceComponent: Splash {
            onFinished: splashLoader.active = false
        }
    }
}
