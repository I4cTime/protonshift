pragma Singleton
import QtQuick

// The ProtonShift design system. One source of truth for the look — every Ps*
// component reads its colors from here. Colors are now palette-driven: set
// `themeName` to one of the ids in `palettes` and every token re-resolves, so
// the whole app restyles from one property. Geometry/type are theme-independent.
QtObject {
    id: theme

    // Active palette id. Driven from ThemeController (which resolves "system" to
    // a concrete palette based on the OS color scheme). Default keeps the
    // original violet-dark look until the controller binds in.
    property string themeName: "violet-night"

    readonly property var palettes: ({
        // ---- Dark: Violet Night (original brand) ----
        "violet-night": {
            dark: true, ambient: 1.0,
            bg: "#0d0b14", bgDeep: "#08060e", surface: "#17131f", surfaceElevated: "#211a33",
            border: "#2c2442", borderStrong: "#3a2f57",
            primary: "#8b5cf6", primaryBright: "#a78bfa", primaryDeep: "#6d28d9", glow: "#7c3aed",
            text: "#f4f2fa", muted: "#9d94b8", faint: "#6b6386",
            success: "#34d399", danger: "#f87171",
            gradA: "#a78bfa", gradB: "#7c3aed"
        },
        // ---- Dark: Deep Sea (teal accent, slate base) ----
        "deep-sea": {
            dark: true, ambient: 1.0,
            bg: "#0a1013", bgDeep: "#050b0d", surface: "#111c20", surfaceElevated: "#19282e",
            border: "#22343b", borderStrong: "#2d4650",
            primary: "#2dd4bf", primaryBright: "#5eead4", primaryDeep: "#0d9488", glow: "#14b8a6",
            text: "#ecf7f6", muted: "#8ba7ab", faint: "#587075",
            success: "#34d399", danger: "#fb7185",
            gradA: "#5eead4", gradB: "#0d9488"
        },
        // ---- Light: Violet Day (violet accent on lavender-white) ----
        "violet-day": {
            dark: false, ambient: 0.42,
            bg: "#faf8ff", bgDeep: "#efeafa", surface: "#ffffff", surfaceElevated: "#f4f0fc",
            border: "#e4ddf2", borderStrong: "#cfc3ea",
            primary: "#7c3aed", primaryBright: "#8b5cf6", primaryDeep: "#6d28d9", glow: "#a78bfa",
            text: "#1c1626", muted: "#5b5470", faint: "#8b83a3",
            success: "#059669", danger: "#dc2626",
            gradA: "#8b5cf6", gradB: "#6d28d9"
        },
        // ---- Light: Sandstone (warm neutral, amber accent) ----
        "sandstone": {
            dark: false, ambient: 0.42,
            bg: "#fbf8f3", bgDeep: "#f2ece1", surface: "#ffffff", surfaceElevated: "#f7f1e7",
            border: "#e8ddcc", borderStrong: "#d8c8ad",
            primary: "#d97706", primaryBright: "#f59e0b", primaryDeep: "#b45309", glow: "#fbbf24",
            text: "#261f18", muted: "#6b5f4e", faint: "#9c8d78",
            success: "#059669", danger: "#dc2626",
            gradA: "#f59e0b", gradB: "#d97706"
        }
    })

    // Selected palette, falling back to the default if an unknown id is set.
    readonly property var _p: palettes[themeName] !== undefined ? palettes[themeName]
                                                                : palettes["violet-night"]

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
    readonly property string fontFamily: "Inter, Noto Sans, sans-serif"
    readonly property string monoFamily: "JetBrains Mono, DejaVu Sans Mono, monospace"
    readonly property int fsCaption: 11
    readonly property int fsSmall: 13
    readonly property int fsBody: 15
    readonly property int fsTitle: 19
    readonly property int fsDisplay: 30
}
