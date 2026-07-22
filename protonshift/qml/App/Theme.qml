pragma Singleton
import QtQuick

// The ProtonShift design system. One source of truth for the look — every Ps*
// component reads its colors from here. Colors are palette-driven: set
// `themeName` to one of the ids in `palettes` and every token re-resolves, so
// the whole app restyles from one property. Geometry/type are theme-independent.
//
// Contrast contract (WCAG): text / muted / faint / warning / danger / success
// hold >= 4.5:1 on `surface`; `onPrimary` holds >= 4.5:1 on both gradient
// stops (gradA, gradB); `wordmark` holds >= 3:1 (large text) on `bg`.
// If you change a color here, re-verify those pairs.
QtObject {
    id: theme

    // Active palette id. Driven from ThemeController (which resolves "system" to
    // a concrete palette based on the OS color scheme). Default keeps the
    // brand look until the controller binds in.
    property string themeName: "proton-neon"

    readonly property var palettes: ({
        // ---- Dark: Proton Neon (brand — sampled from the ProtonShift logo:
        // electric-cyan hex/circuits, magenta "Shift", blue-charcoal base) ----
        "proton-neon": {
            dark: true, ambient: 1.0,
            bg: "#0c1118", bgDeep: "#070b11", surface: "#121a26", surfaceElevated: "#1a2638",
            border: "#243450", borderStrong: "#31476b",
            primary: "#22c3e6", primaryBright: "#5bf6fe", primaryDeep: "#0891b2", glow: "#22d3ee",
            text: "#eef6fb", muted: "#93a9c1", faint: "#7e91a8",
            success: "#34d399", danger: "#f87171",
            gradA: "#18b8da", gradB: "#d94aec",
            accent: "#de3eb8", accentBright: "#ff50f0",
            onPrimary: "#06202b", wordmark: "#ff50f0", knob: "#ffffff",
            warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
            dangerSurface: "#2a1216",
            scrim: "#cc070b11", shadow: "#000000", shadowOpacity: 0.35
        },
        // ---- Dark: Violet Night (original look) ----
        "violet-night": {
            dark: true, ambient: 1.0,
            bg: "#0d0b14", bgDeep: "#08060e", surface: "#17131f", surfaceElevated: "#211a33",
            border: "#2c2442", borderStrong: "#3a2f57",
            primary: "#8b5cf6", primaryBright: "#a78bfa", primaryDeep: "#6d28d9", glow: "#7c3aed",
            text: "#f4f2fa", muted: "#9d94b8", faint: "#8c84a6",
            success: "#34d399", danger: "#f87171",
            gradA: "#7c3aed", gradB: "#6d28d9",
            accent: "#8b5cf6", accentBright: "#a78bfa",
            onPrimary: "#ffffff", wordmark: "#a78bfa", knob: "#ffffff",
            warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
            dangerSurface: "#2a1216",
            scrim: "#cc08060e", shadow: "#000000", shadowOpacity: 0.35
        },
        // ---- Dark: Deep Sea (teal accent, slate base) ----
        "deep-sea": {
            dark: true, ambient: 1.0,
            bg: "#0a1013", bgDeep: "#050b0d", surface: "#111c20", surfaceElevated: "#19282e",
            border: "#22343b", borderStrong: "#2d4650",
            primary: "#2dd4bf", primaryBright: "#5eead4", primaryDeep: "#0d9488", glow: "#14b8a6",
            text: "#ecf7f6", muted: "#8ba7ab", faint: "#7995a0",
            success: "#34d399", danger: "#fb7185",
            gradA: "#5eead4", gradB: "#0d9488",
            accent: "#2dd4bf", accentBright: "#5eead4",
            onPrimary: "#04201d", wordmark: "#5eead4", knob: "#ffffff",
            warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
            dangerSurface: "#2a1216",
            scrim: "#cc050b0d", shadow: "#000000", shadowOpacity: 0.35
        },
        // ---- Light: Proton Day (brand cyan/magenta on airy blue-white) ----
        "proton-day": {
            dark: false, ambient: 0.42,
            bg: "#f6fbfd", bgDeep: "#e8f3f8", surface: "#ffffff", surfaceElevated: "#eef7fa",
            border: "#d7e7ee", borderStrong: "#b9d4e0",
            primary: "#0891b2", primaryBright: "#0e7490", primaryDeep: "#0e7490", glow: "#22d3ee",
            text: "#0f1c24", muted: "#4e6674", faint: "#5d7484",
            success: "#047857", danger: "#b91c1c",
            gradA: "#0e7490", gradB: "#a21caf",
            accent: "#be2fa4", accentBright: "#de3eb8",
            onPrimary: "#ffffff", wordmark: "#de3eb8", knob: "#ffffff",
            warning: "#b45309", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
            dangerSurface: "#fdeaea",
            scrim: "#66101820", shadow: "#1a2638", shadowOpacity: 0.16
        },
        // ---- Light: Violet Day (violet accent on lavender-white) ----
        "violet-day": {
            dark: false, ambient: 0.42,
            bg: "#faf8ff", bgDeep: "#efeafa", surface: "#ffffff", surfaceElevated: "#f4f0fc",
            border: "#e4ddf2", borderStrong: "#cfc3ea",
            primary: "#7c3aed", primaryBright: "#7c3aed", primaryDeep: "#6d28d9", glow: "#a78bfa",
            text: "#1c1626", muted: "#5b5470", faint: "#6b628c",
            success: "#047857", danger: "#b91c1c",
            gradA: "#7c3aed", gradB: "#6d28d9",
            accent: "#7c3aed", accentBright: "#8b5cf6",
            onPrimary: "#ffffff", wordmark: "#8b5cf6", knob: "#ffffff",
            warning: "#b45309", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
            dangerSurface: "#fdeaea",
            scrim: "#661c1626", shadow: "#241a3d", shadowOpacity: 0.16
        },
        // ---- Light: Sandstone (warm neutral, amber accent) ----
        "sandstone": {
            dark: false, ambient: 0.42,
            bg: "#fbf8f3", bgDeep: "#f2ece1", surface: "#ffffff", surfaceElevated: "#f7f1e7",
            border: "#e8ddcc", borderStrong: "#d8c8ad",
            primary: "#d97706", primaryBright: "#92400e", primaryDeep: "#b45309", glow: "#fbbf24",
            text: "#261f18", muted: "#6b5f4e", faint: "#77694f",
            success: "#047857", danger: "#b91c1c",
            gradA: "#f59e0b", gradB: "#d97706",
            accent: "#d97706", accentBright: "#b45309",
            onPrimary: "#2b1503", wordmark: "#b45309", knob: "#ffffff",
            warning: "#92400e", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
            dangerSurface: "#fdeaea",
            scrim: "#66261f18", shadow: "#3d2f1d", shadowOpacity: 0.16
        }
    })

    // Selected palette, falling back to the default if an unknown id is set.
    readonly property var _p: palettes[themeName] !== undefined ? palettes[themeName]
                                                                : palettes["proton-neon"]

    readonly property bool isDark: _p.dark
    // Ambient glow-blob strength multiplier — dimmed on light themes.
    readonly property real ambientStrength: _p.ambient

    // --- palette (resolved) ---------------------------------------------------
    readonly property color bg: _p.bg
    readonly property color bgDeep: _p.bgDeep
    readonly property color surface: _p.surface
    readonly property color surfaceElevated: _p.surfaceElevated
    readonly property color border: _p.border
    readonly property color borderStrong: _p.borderStrong

    readonly property color primary: _p.primary
    readonly property color primaryBright: _p.primaryBright
    readonly property color primaryDeep: _p.primaryDeep
    readonly property color glow: _p.glow

    readonly property color text: _p.text
    readonly property color muted: _p.muted
    readonly property color faint: _p.faint

    readonly property color success: _p.success
    readonly property color danger: _p.danger

    readonly property color gradA: _p.gradA
    readonly property color gradB: _p.gradB

    // Secondary brand hue (the logo's magenta "Shift"); falls back to the
    // palette's primary family on non-brand palettes.
    readonly property color accent: _p.accent
    readonly property color accentBright: _p.accentBright

    // Text/glyph color for content sitting ON the primary gradient (gradA→gradB):
    // primary buttons, active pills. >= 4.5:1 on both stops in every palette.
    readonly property color onPrimary: _p.onPrimary
    // The "Shift" half of the wordmark. accentBright everywhere except palettes
    // where accentBright can't hold 3:1 on bg (sandstone).
    readonly property color wordmark: _p.wordmark
    // Slider handle / switch knob fill (consumers pair it with a border token).
    readonly property color knob: _p.knob

    // --- state ------------------------------------------------------------
    // warning* replaces the hardcoded amber banner hexes; dangerSurface replaces
    // the hardcoded maroon fills. warning/danger are text-grade on surface.
    readonly property color warning: _p.warning
    readonly property color warningSurface: _p.warningSurface
    readonly property color warningBorder: _p.warningBorder
    readonly property color dangerSurface: _p.dangerSurface
    // 14% tints for "ok" pills and success-tinted rows (replaces inline Qt.rgba).
    readonly property color successTint: Qt.rgba(success.r, success.g, success.b, 0.14)
    readonly property color dangerTint: Qt.rgba(danger.r, danger.g, danger.b, 0.14)

    // --- elevation / overlay ----------------------------------------------
    // Modal backdrop (PsDialog Overlay.modal) and card drop-shadow color+opacity.
    readonly property color scrim: _p.scrim
    readonly property color shadow: _p.shadow
    readonly property real shadowOpacity: _p.shadowOpacity

    // --- geometry (theme-independent) -----------------------------------------
    readonly property int radiusSm: 8
    readonly property int radius: 14
    readonly property int radiusLg: 20

    readonly property int spaceXs: 6
    readonly property int spaceSm: 10
    readonly property int space: 16
    readonly property int spaceLg: 24
    readonly property int spaceXl: 36

    // --- type -----------------------------------------------------------------
    // QML font.family takes a SINGLE family name (CSS-style fallback lists are
    // matched as one literal — nonexistent — family). Use `fontFamily` with
    // font.family, or the *Families lists with font.families (Qt 6.2+) to get
    // real fallback.
    readonly property string fontFamily: "Inter"
    readonly property string monoFamily: "JetBrains Mono"
    readonly property var fontFamilies: ["Inter", "Noto Sans", "DejaVu Sans"]
    readonly property var monoFamilies: ["JetBrains Mono", "DejaVu Sans Mono"]
    readonly property int fsCaption: 11
    readonly property int fsSmall: 13
    readonly property int fsBody: 15
    readonly property int fsTitle: 19
    readonly property int fsDisplay: 30
}
