pragma Singleton
import QtQuick

// The ProtonShift design system, ported from the web app's tokens.
// One source of truth for the violet identity — every Ps* component reads
// from here, so a rebrand is a change in one file.
QtObject {
    id: theme

    // --- palette (dark violet) ------------------------------------------------
    readonly property color bg: "#0d0b14"
    readonly property color bgDeep: "#08060e"
    readonly property color surface: "#17131f"
    readonly property color surfaceElevated: "#211a33"
    readonly property color border: "#2c2442"
    readonly property color borderStrong: "#3a2f57"

    readonly property color primary: "#8b5cf6"       // violet-500
    readonly property color primaryBright: "#a78bfa" // violet-400
    readonly property color primaryDeep: "#6d28d9"   // violet-700
    readonly property color glow: "#7c3aed"

    readonly property color text: "#f4f2fa"
    readonly property color muted: "#9d94b8"
    readonly property color faint: "#6b6386"

    readonly property color success: "#34d399"
    readonly property color danger: "#f87171"

    // gradient used on the wordmark and primary buttons
    readonly property color gradA: "#a78bfa"
    readonly property color gradB: "#7c3aed"

    // --- geometry -------------------------------------------------------------
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
