pragma Singleton
import QtQuick

// The ProtonShift design system. One source of truth for the look — every Ps*
// component reads its colors from here. The look is split three ways:
//   - `style`  — a visual STYLE id (shape + neutral personality: radius,
//                 shadow/ambient weight, gradient buttons y/n, hairline
//                 borders y/n, plus a default accent per resolved mode).
//   - `dark`   — resolved dark/light mode (system/dark/light, resolved by
//                 ThemeController).
//   - `accent` — the single hue driving the whole primary/gradient/glow
//                 family, either a style's default or a user override.
// All three are bound in from ThemeController via Binding elements in
// main.qml, so the whole app restyles from those three properties.
//
// Contrast contract (WCAG): text >= 7:1 and muted >= 4.5:1 on `bg` in dark
// styles (proportionally relaxed in light styles, where text-on-white holds
// far more headroom); `onPrimary` holds >= 4.5:1 on `accent`. If you add or
// edit a style's neutrals, re-verify those pairs. `wordmark`/`accentBright`
// ride on the user-chosen accent, so their contrast is best-effort, not
// guaranteed, once a user picks an unusual custom accent.
QtObject {
    id: theme

    // --- inputs (bound from ThemeController in main.qml) -------------------
    property string style: "neon"
    property bool dark: true
    property color accent: "#22c3e6"

    // Per-style shape tokens + neutral (accent-independent) sub-palettes for
    // each resolved mode. Adding a style? Add its id here AND to
    // `core/appearance.py`'s STYLES — `tests/test_theme_parity.py` checks both.
    readonly property var styles: ({
        // ---- Proton Neon (brand): ambient glow, gradient buttons ----------
        "neon": {
            radiusSm: 8, radius: 14, radiusLg: 20,
            ambient: 1.0, gradientButtons: true, hairline: false,
            dark: {
                bg: "#0c1118", bgDeep: "#070b11", surface: "#121a26", surfaceElevated: "#1a2638",
                border: "#243450", borderStrong: "#31476b",
                text: "#eef6fb", muted: "#93a9c1", faint: "#7e91a8",
                success: "#34d399", danger: "#f87171",
                warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
                dangerSurface: "#2a1216",
                scrim: "#cc070b11", shadow: "#000000", shadowOpacity: 0.35,
                knob: "#ffffff"
            },
            light: {
                bg: "#f6fbfd", bgDeep: "#e8f3f8", surface: "#ffffff", surfaceElevated: "#eef7fa",
                border: "#d7e7ee", borderStrong: "#b9d4e0",
                text: "#0f1c24", muted: "#4e6674", faint: "#5d7484",
                success: "#047857", danger: "#b91c1c",
                warning: "#b45309", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
                dangerSurface: "#fdeaea",
                scrim: "#66101820", shadow: "#1a2638", shadowOpacity: 0.16,
                knob: "#ffffff"
            }
        },
        // ---- Phosphor Console: near-black, hairline borders, no shadows ----
        "console": {
            radiusSm: 4, radius: 6, radiusLg: 10,
            ambient: 0.0, gradientButtons: false, hairline: true,
            dark: {
                bg: "#0b0c0e", bgDeep: "#060708", surface: "#111316", surfaceElevated: "#17191d",
                border: "#24262b", borderStrong: "#34373d",
                text: "#f2f3f5", muted: "#9aa0a8", faint: "#7d838b",
                success: "#34d399", danger: "#f87171",
                warning: "#ffb224", warningSurface: "#241d0f", warningBorder: "#6b4a12",
                dangerSurface: "#2a1216",
                scrim: "#cc060708", shadow: "#000000", shadowOpacity: 0.0,
                knob: "#ffffff"
            },
            light: {
                bg: "#f7f7f8", bgDeep: "#ececee", surface: "#ffffff", surfaceElevated: "#f2f2f4",
                border: "#dcdde0", borderStrong: "#c7c9ce",
                text: "#101113", muted: "#565a60", faint: "#64686e",
                success: "#047857", danger: "#b91c1c",
                warning: "#b45309", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
                dangerSurface: "#fdeaea",
                scrim: "#66101113", shadow: "#101113", shadowOpacity: 0.0,
                knob: "#ffffff"
            }
        },
        // ---- Soft Glass: calm, rounded, native-grade -----------------------
        "soft": {
            radiusSm: 14, radius: 20, radiusLg: 28,
            ambient: 0.35, gradientButtons: false, hairline: false,
            dark: {
                bg: "#171310", bgDeep: "#100d0a", surface: "#201a15", surfaceElevated: "#2a2119",
                border: "#3a2f24", borderStrong: "#4d3e2e",
                text: "#f7f0e8", muted: "#b8a693", faint: "#a3927f",
                success: "#34d399", danger: "#f87171",
                warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
                dangerSurface: "#2a1216",
                scrim: "#cc100d0a", shadow: "#000000", shadowOpacity: 0.18,
                knob: "#ffffff"
            },
            light: {
                bg: "#fbf7f2", bgDeep: "#f1e9dd", surface: "#ffffff", surfaceElevated: "#f7f1e7",
                border: "#e9ddcc", borderStrong: "#d9c8ad",
                text: "#241c14", muted: "#6d6050", faint: "#7a6c56",
                success: "#047857", danger: "#b91c1c",
                warning: "#92400e", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
                dangerSurface: "#fdeaea",
                scrim: "#66241c14", shadow: "#3d2f1d", shadowOpacity: 0.18,
                knob: "#ffffff"
            }
        },
        // ---- Deepslate: flat, tight radius, emerald signal -----------------
        "slate": {
            radiusSm: 2, radius: 4, radiusLg: 6,
            ambient: 0.0, gradientButtons: false, hairline: false,
            dark: {
                bg: "#0f1214", bgDeep: "#0a0c0d", surface: "#171b1e", surfaceElevated: "#1e2226",
                border: "#2b3136", borderStrong: "#3a4147",
                text: "#e9edef", muted: "#8b969c", faint: "#78848a",
                success: "#34d399", danger: "#f87171",
                warning: "#fbbf24", warningSurface: "#2a1f12", warningBorder: "#7c5a1e",
                dangerSurface: "#2a1216",
                scrim: "#cc0a0c0d", shadow: "#000000", shadowOpacity: 0.25,
                knob: "#ffffff"
            },
            light: {
                bg: "#f5f7f7", bgDeep: "#e7ebec", surface: "#ffffff", surfaceElevated: "#eef1f2",
                border: "#d7dee0", borderStrong: "#bcc6c9",
                text: "#101416", muted: "#4d5a5f", faint: "#5c6a6f",
                success: "#047857", danger: "#b91c1c",
                warning: "#b45309", warningSurface: "#fef3e2", warningBorder: "#f0d9b0",
                dangerSurface: "#fdeaea",
                scrim: "#66101416", shadow: "#101416", shadowOpacity: 0.25,
                knob: "#ffffff"
            }
        }
    })

    // Selected style, falling back to the default if an unknown id is set.
    readonly property var _s: styles[style] !== undefined ? styles[style] : styles["neon"]
    // Selected neutral sub-palette for the resolved mode.
    readonly property var _n: dark ? _s.dark : _s.light

    readonly property bool isDark: dark
    // Ambient glow-blob strength multiplier — a per-style constant (some
    // styles are deliberately flat/shadowless regardless of mode).
    readonly property real ambientStrength: _s.ambient

    // --- palette (resolved neutrals) -------------------------------------------
    readonly property color bg: _n.bg
    readonly property color bgDeep: _n.bgDeep
    readonly property color surface: _n.surface
    readonly property color surfaceElevated: _n.surfaceElevated
    readonly property color border: _n.border
    readonly property color borderStrong: _n.borderStrong

    readonly property color text: _n.text
    readonly property color muted: _n.muted
    readonly property color faint: _n.faint

    readonly property color success: _n.success
    readonly property color danger: _n.danger

    readonly property color warning: _n.warning
    readonly property color warningSurface: _n.warningSurface
    readonly property color warningBorder: _n.warningBorder
    readonly property color dangerSurface: _n.dangerSurface
    // 14% tints for "ok" pills and success-tinted rows (replaces inline Qt.rgba).
    readonly property color successTint: Qt.rgba(success.r, success.g, success.b, 0.14)
    readonly property color dangerTint: Qt.rgba(danger.r, danger.g, danger.b, 0.14)

    readonly property color scrim: _n.scrim
    readonly property color shadow: _n.shadow
    readonly property real shadowOpacity: _n.shadowOpacity
    readonly property color knob: _n.knob

    // --- accent-derived family ---------------------------------------------
    // Relative luminance (WCAG) of a QML color, 0..1. Used to flip onPrimary
    // between a dark and a light glyph so it holds contrast on any accent.
    function _lum(c) {
        function chan(v) {
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)
        }
        return 0.2126 * chan(c.r) + 0.7152 * chan(c.g) + 0.0722 * chan(c.b)
    }

    readonly property color primary: accent
    readonly property color primaryBright: Qt.lighter(accent, 1.25)
    readonly property color primaryDeep: Qt.darker(accent, 1.35)
    readonly property color glow: accent

    readonly property color gradA: accent
    // Gradient-button styles shift the second stop +40° around the hue wheel;
    // flat styles just repeat the accent so no visible gradient is drawn.
    readonly property color gradB: _s.gradientButtons
        ? Qt.hsla((accent.hslHue + 0.11) % 1, accent.hslSaturation, accent.hslLightness, 1)
        : accent

    // Secondary brand hue — collapsed onto the single user accent in this
    // model (no separate secondary hue to configure).
    readonly property color accentBright: primaryBright

    // Text/glyph color for content sitting ON the primary gradient (gradA→gradB)
    // or a solid `accent` fill: primary buttons, active pills.
    readonly property color onPrimary: _lum(accent) > 0.5 ? "#0b1117" : "#ffffff"
    // The "Shift" half of the wordmark — rides the accent family.
    readonly property color wordmark: primaryBright

    // --- ProtonDB tiers (theme-independent) ---------------------------------
    // Badge fills sampled from ProtonDB's own tier palette so a rating reads
    // the same here as on protondb.com in every style. Each holds >= 4.5:1
    // against `tierInk`, the fixed dark glyph color drawn on top of them
    // (bronze is the tightest at ~5.0:1). Use as pill fill + tierInk text —
    // never as text on `surface`, where gold/silver can't hold contrast on
    // light styles.
    readonly property color tierPlatinum: "#b4c7dc"
    readonly property color tierGold: "#cfb53b"
    readonly property color tierSilver: "#c0c0c0"
    readonly property color tierBronze: "#cd7f32"
    readonly property color tierBorked: "#f87171"
    readonly property color tierPending: "#9aa8b5"
    readonly property color tierInk: "#0b1117"

    // --- geometry (per-style) -----------------------------------------------
    readonly property int radiusSm: _s.radiusSm
    readonly property int radius: _s.radius
    readonly property int radiusLg: _s.radiusLg

    // --- geometry (theme-independent) -----------------------------------------
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
