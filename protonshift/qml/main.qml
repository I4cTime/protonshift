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
    readonly property var pages: ["Library", "Proton", "Environment", "MangoHud", "ScopeBuddy", "Gamescope", "Displays", "System", "Controllers", "Settings"]

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
                sourceComponent: EnvironmentPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 3
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: MangoHudPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 4
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: ScopeBuddyPage {}
            }
            Loader {
                Layout.fillWidth: true; Layout.fillHeight: true
                property bool loadedOnce: false
                active: loadedOnce || window.currentPage === 5
                onLoaded: Qt.callLater(() => loadedOnce = true)
                sourceComponent: GamescopeBuilderPage {}
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
