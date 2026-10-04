import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts
import App

// Settings: everything that is about ProtonShift itself rather than about a
// game - the look (`themeCtl`), the interface sounds (`sounds`), the one
// network opt-out (`protondb`), and what version this is (`about`).
ColumnLayout {
    id: page
    spacing: Theme.spaceLg

    readonly property var modeOptions: [
        { id: "system", label: "System" },
        { id: "dark", label: "Dark" },
        { id: "light", label: "Light" }
    ]
    readonly property var links: [
        { label: "Website and guides", url: "https://protonshift.i4c.studio" },
        { label: "What's new (changelog)", url: "https://protonshift.i4c.studio/changelog" },
        { label: "Report a problem", url: "https://github.com/I4cTime/protonshift/issues" },
        { label: "Source code and license (AGPL-3.0)", url: "https://github.com/I4cTime/protonshift" }
    ]
    // Index of the preset swatch matching the accent override, -1 when there
    // is no override or it is a custom color.
    readonly property int presetIndex: {
        var want = themeCtl.accent.toLowerCase()
        for (var i = 0; i < themeCtl.accentPresets.length; i++)
            if (themeCtl.accentPresets[i].hex.toLowerCase() === want)
                return i
        return -1
    }

    // Arrow keys inside a group of choices: move focus to the neighbour and
    // pick it (a radio group's keyboard model). Delegates expose choose().
    // Focus moves first: the chosen item is the group's only Tab stop, and Qt
    // refuses to take the Tab stop away from the item that still has focus.
    function stepChoice(repeater, index, delta) {
        var n = repeater.count
        var item = repeater.itemAt((index + delta + n) % n)
        item.forceActiveFocus()
        item.choose()
    }
    // Sound-set cards keep focus on their inner choice area, not the card.
    function stepSet(index, delta) {
        var n = setRepeater.count
        var card = setRepeater.itemAt((index + delta + n) % n)
        card.focusChoice()
        card.choose()
    }
    // set while an update check is running, to play its result sound once
    property bool wasChecking: false

    component FieldLabel: Text {
        color: Theme.muted
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
        font.weight: Font.DemiBold
    }
    component Hint: Text {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        color: Theme.faint
        font.family: Theme.fontFamily
        font.pixelSize: Theme.fsCaption
    }
    component FocusRing: Rectangle {
        anchors.fill: parent
        anchors.margins: -3
        radius: parent.radius + 3
        color: "transparent"
        border.width: 2
        border.color: Theme.accentBright
    }
    component Divider: Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: Theme.border
    }

    ColorDialog {
        id: accentDialog
        title: "Custom accent color"
        onAccepted: themeCtl.setAccent(selectedColor.toString())
    }

    PsSectionHeader {
        Layout.fillWidth: true
        text: "Settings"
        subtitle: "Appearance, sounds, privacy, and about"
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: Theme.spaceLg

            // --- Appearance ---------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: appearanceCol.implicitHeight + 2 * Theme.spaceLg

                ColumnLayout {
                    id: appearanceCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space

                    PsSectionHeader {
                        Layout.fillWidth: true
                        text: "Appearance"
                        subtitle: "Choose dark or light, pick a style, then optionally override its accent. "
                                  + "All three apply instantly and are remembered on this machine."
                    }

                    // Mode ----------------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        FieldLabel { text: "Mode" }
                        RowLayout {
                            spacing: Theme.spaceXs
                            Accessible.role: Accessible.Grouping
                            Accessible.name: "Color mode"
                            Repeater {
                                id: modeRepeater
                                model: page.modeOptions
                                delegate: Rectangle {
                                    id: modeSeg
                                    required property var modelData
                                    required property int index
                                    readonly property bool active: themeCtl.mode === modeSeg.modelData.id
                                    function choose() {
                                        if (modeSeg.active) return
                                        themeCtl.setMode(modeSeg.modelData.id)
                                        sounds.play("toggle_on")
                                    }
                                    implicitWidth: modeLbl.implicitWidth + 2 * Theme.space
                                    implicitHeight: 34
                                    radius: Theme.radiusSm
                                    color: active ? Theme.surfaceElevated : (segHover.hovered ? Theme.surface : Theme.bgDeep)
                                    border.color: active ? Theme.primary : Theme.border
                                    border.width: active ? 2 : 1
                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    activeFocusOnTab: active
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: modeSeg.modelData.label
                                    Accessible.checked: modeSeg.active
                                    Accessible.onPressAction: modeSeg.choose()
                                    Keys.onLeftPressed: page.stepChoice(modeRepeater, modeSeg.index, -1)
                                    Keys.onRightPressed: page.stepChoice(modeRepeater, modeSeg.index, 1)
                                    Keys.onSpacePressed: modeSeg.choose()

                                    HoverHandler { id: segHover }
                                    TapHandler { onTapped: { modeSeg.forceActiveFocus(); modeSeg.choose() } }
                                    FocusRing { visible: modeSeg.activeFocus }
                                    Text {
                                        id: modeLbl
                                        anchors.centerIn: parent
                                        // "System" says what it currently resolves to
                                        text: modeSeg.modelData.label
                                              + (modeSeg.modelData.id === "system"
                                                 ? " (now " + (themeCtl.resolvedDark ? "dark" : "light") + ")" : "")
                                        color: modeSeg.active ? Theme.text : Theme.muted
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: modeSeg.active ? Font.DemiBold : Font.Normal
                                    }
                                }
                            }
                        }
                    }

                    Divider {}

                    // Style ---------------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        FieldLabel { text: "Style" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space
                            Accessible.role: Accessible.Grouping
                            Accessible.name: "Style"
                            Repeater {
                                id: styleRepeater
                                model: themeCtl.styles
                                delegate: ColumnLayout {
                                    id: styleItem
                                    required property var modelData
                                    required property int index
                                    readonly property var styleDef: Theme.styles[styleItem.modelData.id]
                                    readonly property var neutrals: Theme.dark ? styleItem.styleDef.dark
                                                                                : styleItem.styleDef.light
                                    readonly property bool selected: themeCtl.style === styleItem.modelData.id
                                    function choose() {
                                        if (styleItem.selected) return
                                        themeCtl.setStyle(styleItem.modelData.id)
                                        sounds.play("toggle_on")
                                    }
                                    spacing: Theme.spaceXs
                                    // Every card is the same size regardless of tagline length or
                                    // the selected border, so the row reads as a grid.
                                    Layout.alignment: Qt.AlignTop
                                    Layout.preferredWidth: 150
                                    Layout.preferredHeight: 92 + Theme.spaceXs + 20 + Theme.spaceXs + 2 * 15
                                    Layout.minimumHeight: Layout.preferredHeight
                                    Layout.maximumHeight: Layout.preferredHeight

                                    activeFocusOnTab: selected
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: styleItem.modelData.label
                                    Accessible.description: styleItem.modelData.tagline
                                    Accessible.checked: styleItem.selected
                                    Accessible.onPressAction: styleItem.choose()
                                    Keys.onLeftPressed: page.stepChoice(styleRepeater, styleItem.index, -1)
                                    Keys.onRightPressed: page.stepChoice(styleRepeater, styleItem.index, 1)
                                    Keys.onSpacePressed: styleItem.choose()

                                    Rectangle {
                                        id: preview
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 92
                                        Layout.minimumHeight: 92
                                        Layout.maximumHeight: 92
                                        radius: styleItem.styleDef.radiusLg
                                        color: styleItem.neutrals.bg
                                        border.width: styleItem.selected ? 2 : 1
                                        border.color: styleItem.selected ? Theme.primary : Theme.border
                                        Behavior on border.color { ColorAnimation { duration: 120 } }

                                        // surface strip
                                        Rectangle {
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            anchors.margins: 10
                                            height: 28
                                            radius: styleItem.styleDef.radius
                                            color: styleItem.neutrals.surface
                                            border.color: styleItem.neutrals.border
                                            border.width: 1
                                        }
                                        // accent pill
                                        Rectangle {
                                            anchors.top: parent.top
                                            anchors.left: parent.left
                                            anchors.margins: 12
                                            width: 34; height: 12
                                            radius: styleItem.styleDef.radiusSm
                                            color: Theme.accent
                                        }
                                        // selected check
                                        Rectangle {
                                            anchors.top: parent.top
                                            anchors.right: parent.right
                                            anchors.margins: 10
                                            width: 18; height: 18; radius: 9
                                            visible: styleItem.selected
                                            color: Theme.primary
                                            Text {
                                                anchors.centerIn: parent
                                                text: "✓"
                                                color: Theme.onPrimary
                                                font.pixelSize: 11
                                                font.bold: true
                                            }
                                        }

                                        TapHandler { onTapped: { styleItem.forceActiveFocus(); styleItem.choose() } }
                                        FocusRing { visible: styleItem.activeFocus }
                                    }
                                    Text {
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 20
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                        text: styleItem.modelData.label
                                        color: styleItem.selected ? Theme.text : Theme.muted
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                        font.weight: styleItem.selected ? Font.DemiBold : Font.Normal
                                    }
                                    Text {
                                        Layout.preferredWidth: 150
                                        Layout.preferredHeight: 2 * 15
                                        Layout.fillHeight: false
                                        text: styleItem.modelData.tagline
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                        lineHeight: 15
                                        lineHeightMode: Text.FixedHeight
                                        color: Theme.faint
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsCaption
                                    }
                                }
                            }
                        }
                    }

                    Divider {}

                    // Accent override -------------------------------------------
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        FieldLabel { text: "Accent override" }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            Repeater {
                                id: swatchRepeater
                                model: themeCtl.accentPresets
                                delegate: Item {
                                    id: swatchItem
                                    required property var modelData
                                    required property int index
                                    readonly property bool active: page.presetIndex === swatchItem.index
                                    readonly property real radius: 16
                                    function choose() {
                                        if (swatchItem.active) return
                                        themeCtl.setAccent(swatchItem.modelData.hex)
                                        sounds.play("toggle_on")
                                    }
                                    implicitWidth: 32
                                    implicitHeight: 32
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 26; height: 26; radius: 13
                                        color: swatchItem.modelData.hex
                                        border.width: swatchItem.active ? 3 : 1
                                        border.color: swatchItem.active ? Theme.text : Theme.border
                                    }
                                    // One Tab stop for the row: the chosen preset, or the
                                    // first swatch while no preset is chosen.
                                    activeFocusOnTab: swatchItem.index === Math.max(0, page.presetIndex)
                                    Accessible.role: Accessible.RadioButton
                                    Accessible.name: swatchItem.modelData.name
                                    Accessible.checked: swatchItem.active
                                    Accessible.onPressAction: swatchItem.choose()
                                    Keys.onLeftPressed: page.stepChoice(swatchRepeater, swatchItem.index, -1)
                                    Keys.onRightPressed: page.stepChoice(swatchRepeater, swatchItem.index, 1)
                                    Keys.onSpacePressed: swatchItem.choose()
                                    TapHandler { onTapped: { swatchItem.forceActiveFocus(); swatchItem.choose() } }
                                    FocusRing { anchors.margins: 0; visible: swatchItem.activeFocus }
                                }
                            }
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Theme.spaceSm
                            PsButton {
                                text: "Custom color…"
                                primary: false
                                onClicked: {
                                    accentDialog.selectedColor = Theme.accent
                                    accentDialog.open()
                                }
                            }
                            TextField {
                                id: accentField
                                width: 130
                                height: 40
                                placeholderText: "#22c3e6"
                                placeholderTextColor: Theme.faint
                                selectByMouse: true
                                color: Theme.text
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsSmall
                                Accessible.name: "Custom accent hex"

                                // Same idiom as PsSwitchRow: a plain `text:
                                // themeCtl.accent` binding is destroyed by the
                                // first keystroke, so a reset or preset tap
                                // elsewhere would never re-sync the field. A
                                // Binding element survives direct edits.
                                Binding on text {
                                    value: themeCtl.accent
                                    restoreMode: Binding.RestoreBindingOrValue
                                }

                                onAccepted: themeCtl.setAccent(text)

                                background: Rectangle {
                                    radius: Theme.radiusSm
                                    color: Theme.bgDeep
                                    border.color: accentField.activeFocus ? Theme.primary
                                                  : (themeCtl.accentError.length > 0 ? Theme.danger : Theme.border)
                                    border.width: accentField.activeFocus ? 2 : 1
                                    Behavior on border.color { ColorAnimation { duration: 120 } }
                                }
                            }
                            PsButton {
                                text: "Reset to style accent"
                                primary: false
                                sound: "back"
                                visible: themeCtl.accent.length > 0
                                onClicked: themeCtl.resetAccent()
                            }
                        }
                        Hint {
                            text: themeCtl.accent.length > 0
                                  ? "Using your color everywhere in the app."
                                  : "Using the style's own accent. Pick a swatch, a custom color, or type a hex value and press Enter."
                        }
                        Hint {
                            visible: themeCtl.accentAdjusted
                            text: "In light mode a bright pick is shown darker, so text and icons in this color "
                                  + "stay readable. Your choice is kept as picked for dark mode."
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: themeCtl.accentError.length > 0
                            text: themeCtl.accentError
                            color: Theme.danger
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                        }
                    }
                }
            }

            // --- Sounds --------------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: soundsCol.implicitHeight + 2 * Theme.spaceLg
                ColumnLayout {
                    id: soundsCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space

                    PsSectionHeader {
                        Layout.fillWidth: true
                        text: "Sounds"
                        subtitle: "The small sounds ProtonShift makes when you click, switch and finish things. "
                                  + "They apply instantly and are remembered on this machine."
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: !sounds.available
                        radius: Theme.radiusSm
                        color: Theme.warningSurface
                        border.color: Theme.warningBorder
                        border.width: 1
                        implicitHeight: noAudioLbl.implicitHeight + 2 * Theme.spaceSm
                        Text {
                            id: noAudioLbl
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            wrapMode: Text.WordWrap
                            color: Theme.warning
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                            text: "This build has no Qt Multimedia, so sounds can't play. The settings are kept for a build that has it."
                        }
                    }

                    PsSwitchRow {
                        Layout.fillWidth: true
                        text: "Play interface sounds"
                        checked: sounds.enabled
                        onToggled: sounds.setEnabled(value)
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 420
                        spacing: Theme.spaceXs
                        PsSlider {
                            Layout.fillWidth: true
                            label: "Volume"
                            suffix: "%"
                            from: 0; to: 100; stepSize: 5
                            enabled: sounds.enabled
                            value: sounds.volume
                            // PsSlider ticks after `moved`, so the tick is heard at the new volume
                            onMoved: sounds.setVolume(Math.round(value))
                        }
                        Hint { text: "Relative to your system volume. Move the slider to hear it." }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        FieldLabel { text: "Sound set" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space
                            Accessible.role: Accessible.Grouping
                            Accessible.name: "Sound set"
                            Repeater {
                                id: setRepeater
                                model: sounds.sets
                                delegate: Rectangle {
                                    id: setCard
                                    required property var modelData
                                    required property int index
                                    readonly property bool selected: sounds.soundSet === setCard.modelData.id
                                    // setSoundSet auditions the set itself when sounds are on
                                    function choose() { sounds.setSoundSet(setCard.modelData.id) }
                                    function focusChoice() { setChoice.forceActiveFocus() }
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.preferredWidth: 1
                                    implicitHeight: setRow.implicitHeight + 2 * Theme.spaceSm
                                    radius: Theme.radiusSm
                                    color: selected ? Theme.surfaceElevated : Theme.bgDeep
                                    border.color: selected ? Theme.primary : Theme.border
                                    border.width: selected ? 2 : 1
                                    Behavior on color { ColorAnimation { duration: 120 } }

                                    RowLayout {
                                        id: setRow
                                        anchors.fill: parent
                                        anchors.margins: Theme.spaceSm
                                        spacing: Theme.spaceSm

                                        // the choice itself (the Preview button is a separate control)
                                        Item {
                                            id: setChoice
                                            readonly property real radius: Theme.radiusSm
                                            Layout.fillWidth: true
                                            implicitHeight: setText.implicitHeight
                                            activeFocusOnTab: setCard.selected
                                            Accessible.role: Accessible.RadioButton
                                            Accessible.name: setCard.modelData.label
                                            Accessible.description: setCard.modelData.description
                                            Accessible.checked: setCard.selected
                                            Accessible.onPressAction: setCard.choose()
                                            Keys.onLeftPressed: page.stepSet(setCard.index, -1)
                                            Keys.onRightPressed: page.stepSet(setCard.index, 1)
                                            Keys.onSpacePressed: setCard.choose()
                                            TapHandler { onTapped: { setChoice.forceActiveFocus(); setCard.choose() } }
                                            FocusRing { visible: setChoice.activeFocus }
                                            ColumnLayout {
                                                id: setText
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                spacing: 2
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: Theme.spaceXs
                                                    Text {
                                                        text: setCard.modelData.label
                                                        color: Theme.text
                                                        font.family: Theme.fontFamily
                                                        font.pixelSize: Theme.fsSmall
                                                        font.weight: Font.DemiBold
                                                    }
                                                    Rectangle {
                                                        width: 16; height: 16; radius: 8
                                                        visible: setCard.selected
                                                        color: Theme.primary
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: "✓"
                                                            color: Theme.onPrimary
                                                            font.pixelSize: 10
                                                            font.bold: true
                                                        }
                                                    }
                                                    Item { Layout.fillWidth: true }
                                                }
                                                Text {
                                                    Layout.fillWidth: true
                                                    text: setCard.modelData.description
                                                    wrapMode: Text.WordWrap
                                                    color: Theme.faint
                                                    font.family: Theme.fontFamily
                                                    font.pixelSize: Theme.fsCaption
                                                }
                                            }
                                        }
                                        PsButton {
                                            text: "Preview"
                                            primary: false
                                            sound: ""  // the preview is the sound
                                            implicitHeight: 32
                                            enabled: sounds.available
                                            Accessible.name: "Preview the " + setCard.modelData.label + " sounds"
                                            onClicked: sounds.preview(setCard.modelData.id)
                                        }
                                    }
                                }
                            }
                        }
                        Hint { text: "Preview plays even while sounds are off, so you can choose before turning them on." }
                    }
                }
            }

            // --- Privacy -------------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: privacyCol.implicitHeight + 2 * Theme.spaceLg
                ColumnLayout {
                    id: privacyCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space
                    PsSectionHeader { Layout.fillWidth: true; text: "Privacy" }
                    PsSwitchRow {
                        Layout.fillWidth: true
                        text: "Look up ProtonDB ratings"
                        subtitle: "Sends only the Steam App ID to protondb.com when you select a game"
                        checked: protondb.enabled
                        onToggled: protondb.setEnabled(value)
                    }
                }
            }

            // --- About -----------------------------------------------------------
            PsCard {
                Layout.fillWidth: true
                Layout.preferredHeight: aboutCol.implicitHeight + 2 * Theme.spaceLg
                ColumnLayout {
                    id: aboutCol
                    anchors.fill: parent
                    anchors.margins: Theme.spaceLg
                    spacing: Theme.space

                    // sound for the result of a check: it arrives on a later tick
                    Connections {
                        target: about
                        function onUpdateChanged() {
                            if (page.wasChecking && !about.checking)
                                sounds.play(about.updateError.length > 0 ? "error"
                                            : (about.updateAvailable ? "notification" : "success"))
                            page.wasChecking = about.checking
                        }
                    }

                    PsSectionHeader {
                        Layout.fillWidth: true
                        text: "About ProtonShift"
                        subtitle: "Free and open source (AGPL-3.0). Not affiliated with Valve, Steam or the Proton project."
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.space
                        Row {
                            height: 32
                            spacing: Theme.spaceXs
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Version"
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: about.version
                                color: Theme.text
                                font.family: Theme.monoFamily
                                font.pixelSize: Theme.fsBody
                                font.weight: Font.DemiBold
                            }
                        }
                        Text {
                            height: 32
                            verticalAlignment: Text.AlignVCenter
                            text: about.platformLabel
                            color: Theme.muted
                            font.family: Theme.fontFamily
                            font.pixelSize: Theme.fsCaption
                        }
                        PsButton {
                            text: about.checking ? "Checking…" : "Check for updates"
                            primary: false
                            implicitHeight: 32
                            enabled: !about.checking
                            onClicked: about.checkForUpdates()
                        }
                        Rectangle {
                            visible: about.checked && !about.updateAvailable
                            width: latestLbl.implicitWidth + 20
                            height: 26
                            y: 3
                            radius: 13
                            color: Theme.successTint
                            border.color: Theme.success
                            border.width: 1
                            Text {
                                id: latestLbl
                                anchors.centerIn: parent
                                text: "✓ You have the latest version"
                                color: Theme.success
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsCaption
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: about.updateAvailable
                        radius: Theme.radiusSm
                        color: Theme.surfaceElevated
                        border.color: Theme.primary
                        border.width: 1
                        implicitHeight: updateRow.implicitHeight + 2 * Theme.spaceSm
                        Accessible.role: Accessible.AlertMessage
                        Accessible.name: updateLbl.text
                        RowLayout {
                            id: updateRow
                            anchors.fill: parent
                            anchors.margins: Theme.spaceSm
                            spacing: Theme.spaceSm
                            Text {
                                id: updateLbl
                                Layout.fillWidth: true
                                wrapMode: Text.WordWrap
                                text: "ProtonShift " + about.latestVersion + " is available - you have " + about.version + "."
                                color: Theme.text
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.fsSmall
                            }
                            PsButton {
                                text: "Open the download page"
                                implicitHeight: 32
                                onClicked: Qt.openUrlExternally(about.updateUrl)
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: about.updateError.length > 0
                        text: about.updateError
                        wrapMode: Text.WordWrap
                        color: Theme.danger
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }
                    Hint {
                        text: "ProtonShift never checks on its own - only when you press the button. It asks GitHub "
                              + "for the newest release and sends nothing about you or your games."
                    }

                    Divider {}

                    FieldLabel { text: "Where ProtonShift keeps its files" }
                    Repeater {
                        model: about.folders
                        delegate: Rectangle {
                            id: folderRow
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: folderLine.implicitHeight + 2 * Theme.spaceSm
                            radius: Theme.radiusSm
                            color: Theme.bgDeep
                            border.color: Theme.border
                            border.width: 1
                            RowLayout {
                                id: folderLine
                                anchors.fill: parent
                                anchors.margins: Theme.spaceSm
                                anchors.leftMargin: Theme.space
                                spacing: Theme.spaceSm
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                        text: folderRow.modelData.label + "  -  " + folderRow.modelData.hint
                                              + (folderRow.modelData.exists ? "" : " (not created yet)")
                                        color: Theme.text
                                        font.family: Theme.fontFamily
                                        font.pixelSize: Theme.fsSmall
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: folderRow.modelData.path
                                        wrapMode: Text.WrapAnywhere
                                        color: Theme.muted
                                        font.family: Theme.monoFamily
                                        font.pixelSize: Theme.fsCaption
                                    }
                                }
                                PsButton {
                                    text: "Copy path"
                                    primary: false
                                    sound: ""  // success / error says it instead
                                    implicitHeight: 32
                                    Accessible.name: "Copy the path of the " + folderRow.modelData.label.toLowerCase()
                                    onClicked: sounds.play(about.copyPath(folderRow.modelData.id) ? "success" : "error")
                                }
                                PsButton {
                                    text: "Open"
                                    primary: false
                                    sound: ""
                                    implicitHeight: 32
                                    Accessible.name: "Open the " + folderRow.modelData.label.toLowerCase()
                                    onClicked: sounds.play(about.openFolder(folderRow.modelData.id) ? "click" : "error")
                                }
                            }
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: about.notice.length > 0
                        text: about.notice
                        wrapMode: Text.WordWrap
                        color: about.noticeOk ? Theme.success : Theme.danger
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.fsCaption
                    }

                    Divider {}

                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.spaceSm
                        Repeater {
                            model: page.links
                            delegate: PsButton {
                                required property var modelData
                                text: modelData.label + " ↗"
                                primary: false
                                implicitHeight: 34
                                onClicked: Qt.openUrlExternally(modelData.url)
                            }
                        }
                    }
                }
            }
        }
    }
}
