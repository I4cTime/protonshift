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

    // theme: drive the Theme singleton from the persisted/resolved appearance
    Binding { target: Theme; property: "style"; value: themeCtl.style }
    Binding { target: Theme; property: "dark"; value: themeCtl.resolvedDark }
    Binding { target: Theme; property: "accent"; value: themeCtl.resolvedAccent }

    // smooth cross-fade when the palette changes
    Behavior on color { ColorAnimation { duration: 220 } }

    // ambient animated background
    GlowBackground { anchors.fill: parent }

    property int currentPage: 0
    onCurrentPageChanged: sounds.play("click")
    // Page indices are the StackLayout order below. Settings (9) is about the
    // app itself, so it sits in the header instead of among the pages.
    readonly property int settingsPage: 9
    // The nav groups pages by what they act on, so ten destinations read as
    // four kinds of thing instead of one long row.
    readonly property var navGroups: [
        { title: "Games", pages: [{ name: "Library", index: 0 }] },
        { title: "Tools", pages: [{ name: "Proton builds", index: 1 }, { name: "Gamescope", index: 2 }] },
        { title: "All games", pages: [{ name: "Environment", index: 3 }, { name: "MangoHud", index: 4 },
                                      { name: "ScopeBuddy", index: 5 }] },
        { title: "This PC", pages: [{ name: "Displays", index: 6 }, { name: "System", index: 7 },
                                    { name: "Controllers", index: 8 }] }
    ]
    readonly property int navCount: 9
    // tab items by page index, for Left/Right across groups
    property var tabItems: ({})

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

            Rectangle {
                id: settingsTab
                readonly property bool active: window.currentPage === window.settingsPage
                implicitWidth: settingsLbl.implicitWidth + 2 * Theme.space
                implicitHeight: 32
                radius: Theme.radiusSm
                color: active ? Theme.surfaceElevated : (settingsHover.hovered ? Theme.surface : "transparent")
                border.width: settingsTab.activeFocus ? 2 : 1
                border.color: settingsTab.activeFocus ? Theme.accentBright
                              : (active ? Theme.borderStrong : Theme.border)
                Behavior on color { ColorAnimation { duration: 120 } }
                activeFocusOnTab: true
                Accessible.role: Accessible.PageTab
                Accessible.name: "Settings"
                Accessible.onPressAction: window.currentPage = window.settingsPage
                Keys.onSpacePressed: window.currentPage = window.settingsPage
                Keys.onReturnPressed: window.currentPage = window.settingsPage
                Keys.onEnterPressed: window.currentPage = window.settingsPage
                HoverHandler { id: settingsHover }
                TapHandler { onTapped: window.currentPage = window.settingsPage }
                Text {
                    id: settingsLbl
                    anchors.centerIn: parent
                    text: "Settings"
                    color: settingsTab.active ? Theme.text : Theme.muted
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                    font.weight: settingsTab.active ? Font.DemiBold : Font.Normal
                }
            }

            Text {
                text: "v" + appVersion
                color: Theme.faint
                font.family: Theme.monoFamily
                font.pixelSize: Theme.fsCaption
            }
        }

        // --- nav: grouped tabs (groups wrap as units on narrow windows) -----
        // Keyboard: the selected tab is the strip's Tab stop (roving tabindex);
        // Left/Right move focus along the strip, Space/Enter activate a page.
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceLg
            Repeater {
                model: window.navGroups
                delegate: Column {
                    id: navGroup
                    required property var modelData
                    spacing: 4
                    Text {
                        leftPadding: Theme.space
                        text: navGroup.modelData.title
                        color: Theme.faint
                        font.family: Theme.fontFamily
                        font.pixelSize: 10
                        font.weight: Font.DemiBold
                        font.capitalization: Font.AllUppercase
                        font.letterSpacing: 0.8
                    }
                    Row {
                        spacing: Theme.spaceXs
                        Accessible.role: Accessible.PageTabList
                        Accessible.name: navGroup.modelData.title
                        Repeater {
                            model: navGroup.modelData.pages
                            delegate: Rectangle {
                                id: tab
                                required property var modelData
                                readonly property int pageIndex: modelData.index
                                implicitWidth: tabLbl.implicitWidth + 2 * Theme.space
                                implicitHeight: 32
                                radius: Theme.radiusSm
                                property bool active: window.currentPage === pageIndex
                                color: active ? Theme.surfaceElevated
                                              : (tabHover.hovered ? Theme.surface : "transparent")
                                border.width: tab.activeFocus ? 2 : (active ? 1 : 0)
                                border.color: tab.activeFocus ? Theme.accentBright : Theme.borderStrong
                                Behavior on color { ColorAnimation { duration: 120 } }

                                Component.onCompleted: window.tabItems[pageIndex] = tab

                                // on Settings no nav tab is selected: Library keeps the Tab stop
                                activeFocusOnTab: tab.active
                                                  || (window.currentPage === window.settingsPage && pageIndex === 0)
                                Accessible.role: Accessible.PageTab
                                Accessible.name: tab.modelData.name
                                Accessible.focusable: true
                                Keys.onPressed: (event) => {
                                    var n = window.navCount
                                    if (event.key === Qt.Key_Left) {
                                        window.tabItems[(tab.pageIndex + n - 1) % n].forceActiveFocus(Qt.BacktabFocusReason)
                                        event.accepted = true
                                    } else if (event.key === Qt.Key_Right) {
                                        window.tabItems[(tab.pageIndex + 1) % n].forceActiveFocus(Qt.TabFocusReason)
                                        event.accepted = true
                                    } else if (event.key === Qt.Key_Space || event.key === Qt.Key_Return
                                               || event.key === Qt.Key_Enter) {
                                        window.currentPage = tab.pageIndex
                                        event.accepted = true
                                    }
                                }

                                HoverHandler { id: tabHover }
                                TapHandler { onTapped: window.currentPage = tab.pageIndex }
                                Text {
                                    id: tabLbl
                                    anchors.centerIn: parent
                                    text: tab.modelData.name
                                    color: tab.active ? Theme.text : Theme.muted
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsSmall
                                    font.weight: tab.active ? Font.DemiBold : Font.Normal
                                }
                            }
                        }
                    }
                }
            }
        }

        // --- page stack -----------------------------------------------------
        // Each page sits behind a Loader that activates on first visit and then
        // stays loaded, so page state persists but startup doesn't pay for all
        // ten pages (GamesPage alone carries six dialogs).
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
                sourceComponent: ProtonPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 2
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: GamescopeBuilderPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 3
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: EnvironmentPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 4
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: MangoHudPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 5
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: ScopeBuddyPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 6
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: DisplayPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 7
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: SystemPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 8
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: ControllersPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 9
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: SettingsPage {}
            }
        }
    }

    // branded startup overlay - covers the UI briefly, then dissolves.
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
