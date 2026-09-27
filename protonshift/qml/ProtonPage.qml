import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App

// GE-Proton manager: installed builds in compatibilitytools.d on the left,
// the latest GitHub releases on the right. `geProton` controller.
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    // --- header ------------------------------------------------------------
    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.spaceSm
        PsSectionHeader {
            Layout.fillWidth: true
            text: "Proton builds"
            subtitle: "GE-Proton in " + (geProton.folder || "compatibilitytools.d")
        }
        BusyIndicator {
            running: geProton.busy; visible: geProton.busy
            implicitWidth: 22; implicitHeight: 22
        }
        PsButton {
            text: "Open folder"; primary: false
            onClicked: geProton.openFolder()
        }
        PsButton {
            text: "Refresh"; primary: false
            enabled: !geProton.busy
            onClicked: geProton.refresh()
        }
    }

    // --- error banner --------------------------------------------------------
    Rectangle {
        Layout.fillWidth: true
        visible: geProton.error.length > 0
        radius: Theme.radiusSm
        color: Theme.dangerSurface
        border.color: Theme.danger
        border.width: 1
        implicitHeight: errText.implicitHeight + 2 * Theme.spaceSm
        Accessible.role: Accessible.AlertMessage
        Accessible.name: geProton.error
        Text {
            id: errText
            anchors.fill: parent
            anchors.margins: Theme.spaceSm
            wrapMode: Text.WordWrap
            color: Theme.danger
            font.family: Theme.fontFamily
            font.pixelSize: Theme.fsCaption
            text: geProton.error
        }
    }

    // --- installed | available -----------------------------------------------
    RowLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        spacing: Theme.spaceLg

        // Installed
        PsCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.space

                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Installed"
                    subtitle: geProton.installed.length === 1
                              ? "1 build" : geProton.installed.length + " builds"
                }

                Text {
                    Layout.fillWidth: true
                    visible: geProton.installed.length === 0 && !geProton.busy
                    text: "No custom Proton builds yet. Install one from the list on the right."
                    wrapMode: Text.WordWrap
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                ListView {
                    id: installedList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: Theme.spaceXs
                    model: geProton.installed
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                        id: toolRow
                        required property var modelData
                        width: ListView.view.width
                        implicitHeight: toolCol.implicitHeight + 2 * Theme.spaceSm
                        radius: Theme.radiusSm
                        color: toolHov.hovered ? Theme.surfaceElevated : Theme.bgDeep
                        border.color: Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 120 } }
                        HoverHandler { id: toolHov }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            anchors.leftMargin: Theme.space
                            spacing: Theme.spaceSm

                            ColumnLayout {
                                id: toolCol
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    spacing: Theme.spaceXs
                                    Text {
                                        text: toolRow.modelData.name
                                        elide: Text.ElideRight
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: Font.DemiBold
                                    }
                                    Rectangle {
                                        visible: toolRow.modelData.isGe
                                        implicitWidth: geTag.implicitWidth + 12
                                        implicitHeight: 18
                                        radius: 9
                                        color: Theme.successTint
                                        border.color: Theme.success
                                        border.width: 1
                                        Text {
                                            id: geTag
                                            anchors.centerIn: parent
                                            text: "GE"
                                            color: Theme.success
                                            font.family: Theme.fontFamily
                                            font.pixelSize: 10
                                            font.weight: Font.Bold
                                        }
                                    }
                                }
                                Text {
                                    text: (toolRow.modelData.version ? "v" + toolRow.modelData.version + " · " : "")
                                          + toolRow.modelData.sizeLabel
                                    color: Theme.faint
                                    font.family: Theme.monoFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                                Text {
                                    visible: toolRow.modelData.inUseCount > 0
                                    text: "In use by " + toolRow.modelData.inUseCount
                                          + (toolRow.modelData.inUseCount === 1 ? " game" : " games")
                                    color: Theme.warning
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                            }

                            PsButton {
                                text: "Remove"; primary: false; danger: true
                                implicitHeight: 32
                                enabled: !geProton.busy
                                onClicked: {
                                    removeDialog.toolName = toolRow.modelData.name
                                    removeDialog.inUse = toolRow.modelData.inUse
                                    removeDialog.open()
                                }
                            }
                        }
                    }
                }
            }
        }

        // Available
        PsCard {
            Layout.fillWidth: true
            Layout.fillHeight: true
            glowing: true
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: Theme.spaceLg
                spacing: Theme.space

                PsSectionHeader {
                    Layout.fillWidth: true
                    text: "Available (GE-Proton)"
                    subtitle: "Latest releases from GloriousEggroll/proton-ge-custom"
                }

                // offline / empty state
                Text {
                    Layout.fillWidth: true
                    visible: geProton.releases.length === 0 && !geProton.busy
                    text: geProton.error.length > 0
                          ? "Couldn't reach GitHub — installed builds still work."
                          : "No releases found."
                    wrapMode: Text.WordWrap
                    color: Theme.faint
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsSmall
                }

                ListView {
                    id: releaseList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: Theme.spaceXs
                    model: geProton.releases
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {}

                    delegate: Rectangle {
                        id: relRow
                        required property var modelData
                        width: ListView.view.width
                        implicitHeight: relCol.implicitHeight + 2 * Theme.spaceSm
                        radius: Theme.radiusSm
                        property bool active: geProton.installingTag === modelData.tag
                        color: active ? Theme.surfaceElevated : (relHov.hovered ? Theme.surfaceElevated : Theme.bgDeep)
                        border.color: active ? Theme.primary : Theme.border
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 120 } }
                        HoverHandler { id: relHov }

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            anchors.leftMargin: Theme.space
                            spacing: Theme.spaceSm

                            ColumnLayout {
                                id: relCol
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    Layout.fillWidth: true
                                    text: relRow.modelData.tag
                                    elide: Text.ElideRight
                                    color: Theme.text
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsSmall
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    text: relRow.modelData.published
                                          + (relRow.modelData.sizeLabel ? " · " + relRow.modelData.sizeLabel : "")
                                    color: Theme.faint
                                    font.family: Theme.monoFamily
                                    font.pixelSize: Theme.fsCaption
                                }
                            }

                            Rectangle {
                                visible: relRow.modelData.installed
                                implicitWidth: instLbl.implicitWidth + 16
                                implicitHeight: 24
                                radius: 12
                                color: Theme.successTint
                                border.color: Theme.success
                                border.width: 1
                                Text {
                                    id: instLbl
                                    anchors.centerIn: parent
                                    text: "Installed"
                                    color: Theme.success
                                    font.family: Theme.fontFamily
                                    font.pixelSize: Theme.fsCaption
                                    font.weight: Font.DemiBold
                                }
                            }
                            PsButton {
                                visible: !relRow.modelData.installed
                                text: relRow.active ? "Installing…" : "Install"
                                implicitHeight: 32
                                enabled: !geProton.busy
                                onClicked: geProton.install(relRow.modelData.tag)
                            }
                        }
                    }
                }

                // download progress
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: geProton.installing
                    spacing: Theme.spaceXs
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Text {
                            Layout.fillWidth: true
                            text: "Installing " + geProton.installingTag
                                  + (geProton.progressLabel ? " — " + geProton.progressLabel : "")
                            elide: Text.ElideRight
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                        }
                        PsButton {
                            text: "Cancel"; primary: false
                            implicitHeight: 30
                            onClicked: geProton.cancel()
                        }
                    }
                    Rectangle {
                        id: track
                        Layout.fillWidth: true
                        implicitHeight: 8
                        radius: 4
                        color: Theme.bgDeep
                        border.color: Theme.border
                        border.width: 1
                        Accessible.role: Accessible.ProgressBar
                        Accessible.name: "Download progress"
                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            width: Math.max(8, track.width * geProton.progress)
                            radius: 4
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: Theme.gradA }
                                GradientStop { position: 1.0; color: Theme.gradB }
                            }
                            Behavior on width { NumberAnimation { duration: 120 } }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: geProton.status.length > 0
                    text: geProton.status
                    wrapMode: Text.WordWrap
                    color: Theme.success
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                }
            }
        }
    }

    // --- remove confirmation -----------------------------------------------
    PsDialog {
        id: removeDialog
        objectName: "removeProtonDialog"
        width: 480
        title: "Remove " + removeDialog.toolName + "?"
        subtitle: "Deletes the build from compatibilitytools.d"
        property string toolName: ""
        property var inUse: []

        ColumnLayout {
            width: parent.width
            spacing: Theme.space

            Rectangle {
                Layout.fillWidth: true
                visible: removeDialog.inUse.length > 0
                radius: Theme.radiusSm
                color: Theme.warningSurface
                border.color: Theme.warningBorder
                border.width: 1
                implicitHeight: inUseText.implicitHeight + 2 * Theme.spaceSm
                Text {
                    id: inUseText
                    anchors.fill: parent
                    anchors.margins: Theme.spaceSm
                    wrapMode: Text.WordWrap
                    color: Theme.warning
                    font.family: Theme.fontFamily
                    font.pixelSize: Theme.fsCaption
                    text: "Still selected for: " + removeDialog.inUse.join(", ")
                          + ". Those games will fall back to Steam's default Proton until you pick another build."
                }
            }

            Text {
                Layout.fillWidth: true
                text: "This can't be undone, but the build can be reinstalled from the Available list."
                wrapMode: Text.WordWrap
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
                    onClicked: removeDialog.close()
                }
                PsButton {
                    text: "Remove"; primary: false; danger: true
                    enabled: !geProton.busy
                    onClicked: {
                        geProton.remove(removeDialog.toolName)
                        removeDialog.close()
                    }
                }
            }
        }
    }
}
