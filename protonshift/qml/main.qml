import QtQuick
import QtQuick.Controls.Basic
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

            Rectangle {
                width: 34; height: 34; radius: 10
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: Theme.gradA }
                    GradientStop { position: 1.0; color: Theme.gradB }
                }
                Text {
                    anchors.centerIn: parent
                    text: "»"   // placeholder mark (swap for the real logo asset later)
                    color: "#ffffff"
                    font.pixelSize: 20
                    font.bold: true
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
                    color: Theme.primaryBright
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
                border.color: themeMenu.visible ? Theme.primary : Theme.border
                border.width: 1
                Behavior on color { ColorAnimation { duration: 120 } }

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
                    background: Rectangle {
                        radius: Theme.radiusSm
                        color: Theme.surface
                        border.color: Theme.borderStrong
                        border.width: 1
                    }
                    contentItem: ColumnLayout {
                        spacing: 2
                        // System (auto) row
                        Repeater {
                            model: [{ id: "system", label: "System (auto)" }].concat(themeCtl.themes)
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                implicitWidth: 188
                                implicitHeight: 34
                                radius: Theme.radiusSm
                                property bool active: themeCtl.choice === modelData.id
                                color: active ? Theme.surfaceElevated : (rowHov.hovered ? Theme.bgDeep : "transparent")
                                HoverHandler { id: rowHov }
                                TapHandler { onTapped: { themeCtl.setTheme(modelData.id); themeMenu.close() } }
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: Theme.spaceSm
                                    anchors.rightMargin: Theme.spaceSm
                                    spacing: Theme.spaceSm
                                    // swatch (system shows a split light/dark)
                                    Rectangle {
                                        width: 18; height: 18; radius: 5
                                        color: modelData.id === "system" ? Theme.bg
                                               : Theme.palettes[modelData.id].bg
                                        border.color: Theme.border; border.width: 1
                                        Rectangle {
                                            anchors.centerIn: parent
                                            width: 9; height: 9; radius: 4.5
                                            color: modelData.id === "system" ? Theme.primary
                                                   : Theme.palettes[modelData.id].primary
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.label
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: parent.parent.active ? Font.DemiBold : Font.Normal
                                    }
                                    Text {
                                        visible: parent.parent.active
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
        Flow {
            Layout.fillWidth: true
            spacing: Theme.spaceXs
            Repeater {
                model: window.pages
                delegate: Rectangle {
                    required property int index
                    required property string modelData
                    implicitWidth: tabLbl.implicitWidth + 2 * Theme.space
                    implicitHeight: 32
                    radius: Theme.radiusSm
                    property bool active: window.currentPage === index
                    color: active ? Theme.surfaceElevated
                                  : (tabHover.hovered ? Theme.surface : "transparent")
                    border.width: active ? 1 : 0
                    border.color: Theme.borderStrong
                    Behavior on color { ColorAnimation { duration: 120 } }
                    HoverHandler { id: tabHover }
                    TapHandler { onTapped: window.currentPage = index }
                    Text {
                        id: tabLbl
                        anchors.centerIn: parent
                        text: modelData
                        color: parent.active ? Theme.text : Theme.muted
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsSmall
                        font.weight: parent.active ? Font.DemiBold : Font.Normal
                    }
                }
            }
        }

        // --- page stack -----------------------------------------------------
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.currentPage

            GamesPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            EnvironmentPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            MangoHudPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            ScopeBuddyPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            GamescopeBuilderPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            DisplayPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            SystemPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
            ControllersPage {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }

    // branded startup overlay — covers the UI briefly, then dissolves.
    // Last child, so it sits above everything (header, tabs, pages).
    Splash {
        anchors.fill: parent
        z: 1000
    }
}
