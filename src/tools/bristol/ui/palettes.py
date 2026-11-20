"""ui/palettes.py — the palettes this build ships, light and dark for each theme.

Each palette is one complete set of the colour keys ``ui/README.md`` defines.
``ui/themes.py`` registers them as schemes and pairs them into themes.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# The house schemes — the warm orange family and a cool neutral alternate
# ---------------------------------------------------------------------------
# Every key here is read somewhere in the stylesheet or the card delegate. All
# schemes MUST carry the same keys so a swap never leaves a hole; check_schemes()
# names any that does.
WARM_LIGHT = {
    "INK": "#3d3325",  # primary text (warm near-black)
    "INK_SOFT": "#675c49",  # secondary text (6.1:1 on CANVAS)
    "INK_FAINT": "#796e5d",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#faf6ef",  # app / dialog background
    "SURFACE": "#fffdf9",  # card / input surface
    "BORDER": "#e7dcc6",  # hairline borders
    "ACCENT": "#c2410c",  # primary orange (4.8:1 on CANVAS, 5.2:1 under white)
    "ACCENT_DK": "#9a3412",  # deeper orange — bright accent text
    "ON_ACCENT": "#ffffff",  # text and marks drawn on an accent fill
    "BUILD_BG": "#e4eee6",  # Build record-type pill background (calm green)
    "BUILD_TX": "#2e5a3d",  # Build record-type pill text (6.7:1 on its tint)
    "FIX_BG": "#fbe2db",  # Fix record-type pill background (rust)
    "FIX_TX": "#97301b",  # Fix record-type pill text (6.2:1 on its tint)
    "SEL_BG": "#fff1e2",  # selected card fill
    "HOVER_BG": "#fffaf2",  # hovered card fill
    "LIST_BG": "#fbf6ee",  # kanban list / scroll area background
    "BTN_BG": "#fff4e8",  # normal button fill
    "BTN_BORDER": "#b18759",  # the edge of everything that can be clicked
    "BTN_HOVER": "#ffe9d2",  # button hover fill
    "BTN_PRESSED": "#ffddb8",  # button pressed fill
    "CREATE_HOVER": "#a83a0b",  # accent (Create) button hover fill
    "DELETE_BG": "#c53a20",  # destructive button text
    "DELETE_HOVER": "#b03118",  # destructive button text on hover
    "MISSING": "#d61f1f",  # required-but-empty field border (bright red)
    "DISABLED_BG": "#f3ece0",  # unclickable button fill
    "DISABLED_TX": "#b3a389",  # unclickable button text
    "NEUTRAL_BG": "#f0e7d6",  # a quiet pill: size, tier
    "NEUTRAL_TX": "#574e3b",  # text on a NEUTRAL_BG pill (6.7:1 on its tint)
}

WARM_DARK = {
    "INK": "#f2e6d5",  # primary text (warm near-white)
    "INK_SOFT": "#b89f7d",  # secondary text
    "INK_FAINT": "#988366",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#17120c",  # app / dialog background (deep warm)
    "SURFACE": "#241c14",  # card / input surface (dark warm)
    "BORDER": "#463724",  # hairline borders
    "ACCENT": "#f97316",  # primary orange (brighter for dark)
    "ACCENT_DK": "#fdba74",  # light orange — bright accent text on dark
    "ON_ACCENT": "#201409",  # deep warm text on the bright accent (6.4:1)
    "BUILD_BG": "#1e2a1e",  # Build record-type pill background (calm green)
    "BUILD_TX": "#8fca9a",  # Build record-type pill text
    "FIX_BG": "#3a1f18",  # Fix record-type pill background (rust)
    "FIX_TX": "#f0a58e",  # Fix record-type pill text
    "SEL_BG": "#3a2914",  # selected card fill
    "HOVER_BG": "#2a2115",  # hovered card fill
    "LIST_BG": "#1c160f",  # kanban list / scroll area background
    "BTN_BG": "#33281b",  # normal button fill
    "BTN_BORDER": "#806341",  # the edge of everything that can be clicked
    "BTN_HOVER": "#40311f",  # button hover fill
    "BTN_PRESSED": "#4a3826",  # button pressed fill
    "CREATE_HOVER": "#fb8b3d",  # accent (Create) button hover fill
    "DELETE_BG": "#ef6448",  # destructive button text
    "DELETE_HOVER": "#f97255",  # destructive button text on hover
    "MISSING": "#ff5449",  # required-but-empty field border (bright red)
    "DISABLED_BG": "#241c14",  # unclickable button fill
    "DISABLED_TX": "#6b5b45",  # unclickable button text
    "NEUTRAL_BG": "#2f2618",  # a quiet pill: size, tier
    "NEUTRAL_TX": "#c4ae8e",  # text on a NEUTRAL_BG pill
}

# The cool neutral alternate: grey canvas, white surfaces, a blue accent. Where
# the warm family reads as paper, this one reads as a modern web tool.
COOL_LIGHT = {
    "INK": "#0f172a",  # primary text (near-black slate)
    "INK_SOFT": "#5b6779",  # secondary text (4.9:1 on LIST_BG)
    "INK_FAINT": "#5e6a7c",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#f4f5f7",  # app / dialog background
    "SURFACE": "#ffffff",  # card / input surface
    "BORDER": "#e2e8f0",  # hairline borders
    "ACCENT": "#2563eb",  # primary blue
    "ACCENT_DK": "#1d4ed8",  # deeper blue — bright accent text
    "ON_ACCENT": "#ffffff",  # text and marks drawn on an accent fill
    "BUILD_BG": "#dcfce7",  # Build record-type pill background (green)
    "BUILD_TX": "#166534",  # Build record-type pill text (6.5:1 on its tint)
    "FIX_BG": "#fee2e2",  # Fix record-type pill background (red)
    "FIX_TX": "#991b1b",  # Fix record-type pill text (6.8:1 on its tint)
    "SEL_BG": "#e8f0fe",  # selected card fill
    "HOVER_BG": "#f8fafc",  # hovered card fill
    "LIST_BG": "#ebecf0",  # kanban list / scroll area background
    "BTN_BG": "#ffffff",  # normal button fill
    "BTN_BORDER": "#808994",  # the edge of everything that can be clicked
    "BTN_HOVER": "#f1f5f9",  # button hover fill
    "BTN_PRESSED": "#e2e8f0",  # button pressed fill
    "CREATE_HOVER": "#1d4ed8",  # accent (Create) button hover fill
    "DELETE_BG": "#dc2626",  # destructive button text
    "DELETE_HOVER": "#b91c1c",  # destructive button text on hover
    "MISSING": "#da2324",  # required-but-empty field border
    "DISABLED_BG": "#f1f5f9",  # unclickable button fill
    "DISABLED_TX": "#94a3b8",  # unclickable button text
    "NEUTRAL_BG": "#eef1f5",  # a quiet pill: size, tier
    "NEUTRAL_TX": "#475569",  # text on a NEUTRAL_BG pill
}

COOL_DARK = {
    "INK": "#e2e8f0",  # primary text (near-white slate)
    "INK_SOFT": "#94a3b8",  # secondary text
    "INK_FAINT": "#7c899b",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#0f1216",  # app / dialog background
    "SURFACE": "#1a1f26",  # card / input surface
    "BORDER": "#2c333d",  # hairline borders
    "ACCENT": "#3b82f6",  # primary blue (brighter for dark)
    "ACCENT_DK": "#93c5fd",  # light blue — bright accent text on dark
    "ON_ACCENT": "#0f1216",  # deep slate text on the bright accent (5.1:1)
    "BUILD_BG": "#14261a",  # Build record-type pill background (green)
    "BUILD_TX": "#86efac",  # Build record-type pill text
    "FIX_BG": "#2c1618",  # Fix record-type pill background (red)
    "FIX_TX": "#fca5a5",  # Fix record-type pill text
    "SEL_BG": "#1e293b",  # selected card fill
    "HOVER_BG": "#20262e",  # hovered card fill
    "LIST_BG": "#14181d",  # kanban list / scroll area background
    "BTN_BG": "#232a33",  # normal button fill
    "BTN_BORDER": "#606a77",  # the edge of everything that can be clicked
    "BTN_HOVER": "#2b333d",  # button hover fill
    "BTN_PRESSED": "#333c48",  # button pressed fill
    "CREATE_HOVER": "#60a5fa",  # accent (Create) button hover fill
    "DELETE_BG": "#fe5350",  # destructive button text
    "DELETE_HOVER": "#f87171",  # destructive button text on hover
    "MISSING": "#f87171",  # required-but-empty field border
    "DISABLED_BG": "#1a1f26",  # unclickable button fill
    "DISABLED_TX": "#5b6672",  # unclickable button text
    "NEUTRAL_BG": "#242b34",  # a quiet pill: size, tier
    "NEUTRAL_TX": "#b6c0cc",  # text on a NEUTRAL_BG pill
}

# ---------------------------------------------------------------------------
# The borrowed shelf — one theme per scheme people already read code in
# ---------------------------------------------------------------------------
# Each is a palette rather than a mechanism: the grounds, the text and the
# signal colours come from the scheme its name points at, and the fills, pills
# and button states are that palette's own colours tinted onto its own ground.
# Every one of them clears CONTRAST_MIN on every pair in TEXT_PAIRS and MARK_MIN
# on every mark in MARK_PAIRS, which is what the accent, the secondary text, the
# warning reds and the edges are pinned to where a source palette sits under it.

# GitHub
GITHUB_LIGHT = {
    "INK": "#1f2328",
    "INK_SOFT": "#656d76",
    "INK_FAINT": "#656d76",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#f6f8fa",
    "SURFACE": "#ffffff",
    "BORDER": "#d0d7de",
    "ACCENT": "#0969da",
    "ACCENT_DK": "#0061cf",
    "ON_ACCENT": "#ffffff",
    "BUILD_BG": "#c6ddcf",
    "BUILD_TX": "#146a2e",
    "FIX_BG": "#edc9cd",
    "FIX_TX": "#ad1c28",
    "SEL_BG": "#d5e4f6",
    "HOVER_BG": "#f4f4f4",
    "LIST_BG": "#eef1f4",
    "BTN_BG": "#eef4fc",
    "BTN_BORDER": "#628ec0",
    "BTN_HOVER": "#dae8f9",
    "BTN_PRESSED": "#c4dbf6",
    "CREATE_HOVER": "#0858b7",
    "DELETE_BG": "#cf222e",
    "DELETE_HOVER": "#b61e28",
    "MISSING": "#cf222e",
    "DISABLED_BG": "#e8eaed",
    "DISABLED_TX": "#b5b9bf",
    "NEUTRAL_BG": "#e2e5e8",
    "NEUTRAL_TX": "#5c646c",
}

GITHUB_DARK = {
    "INK": "#e6edf3",
    "INK_SOFT": "#8b949e",
    "INK_FAINT": "#7d868f",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#0d1117",
    "SURFACE": "#161b22",
    "BORDER": "#30363d",
    "ACCENT": "#58a6ff",
    "ACCENT_DK": "#58a6ff",
    "ON_ACCENT": "#0c1724",
    "BUILD_BG": "#152c20",
    "BUILD_TX": "#3fb950",
    "FIX_BG": "#331b1f",
    "FIX_TX": "#f85149",
    "SEL_BG": "#1e324a",
    "HOVER_BG": "#2b3037",
    "LIST_BG": "#010409",
    "BTN_BG": "#2b3037",
    "BTN_BORDER": "#456992",
    "BTN_HOVER": "#393f46",
    "BTN_PRESSED": "#4a5056",
    "CREATE_HOVER": "#73b4ff",
    "DELETE_BG": "#ff6258",
    "DELETE_HOVER": "#ff857c",
    "MISSING": "#f85149",
    "DISABLED_BG": "#161b22",
    "DISABLED_TX": "#464c54",
    "NEUTRAL_BG": "#1d2229",
    "NEUTRAL_TX": "#8b949e",
}


# Nord
NORD_LIGHT = {
    "INK": "#2e3440",
    "INK_SOFT": "#4c566a",
    "INK_FAINT": "#5e6779",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#eceff4",
    "SURFACE": "#ffffff",
    "BORDER": "#d8dee9",
    "ACCENT": "#55759d",
    "ACCENT_DK": "#476487",
    "ON_ACCENT": "#ffffff",
    "BUILD_BG": "#d4ddd6",
    "BUILD_TX": "#4f6344",
    "FIX_BG": "#e2d0d6",
    "FIX_TX": "#89464c",
    "SEL_BG": "#d7dee8",
    "HOVER_BG": "#f5f5f5",
    "LIST_BG": "#e5e9f0",
    "BTN_BG": "#f3f5f8",
    "BTN_BORDER": "#77879d",
    "BTN_HOVER": "#e6eaf0",
    "BTN_PRESSED": "#d6dee7",
    "CREATE_HOVER": "#476284",
    "DELETE_BG": "#ac565f",
    "DELETE_HOVER": "#994d55",
    "MISSING": "#ab4f59",
    "DISABLED_BG": "#dce0e6",
    "DISABLED_TX": "#a4aab6",
    "NEUTRAL_BG": "#d6dae1",
    "NEUTRAL_TX": "#4c566a",
}

NORD_DARK = {
    "INK": "#eceff4",
    "INK_SOFT": "#c3cbd8",
    "INK_FAINT": "#a8b0bd",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#2e3440",
    "SURFACE": "#3b4252",
    "BORDER": "#434c5e",
    "ACCENT": "#88c0d0",
    "ACCENT_DK": "#93ccdc",
    "ON_ACCENT": "#131b1d",
    "BUILD_BG": "#414a4c",
    "BUILD_TX": "#a9c292",
    "FIX_BG": "#453b47",
    "FIX_TX": "#d69da3",
    "SEL_BG": "#425360",
    "HOVER_BG": "#4d5362",
    "LIST_BG": "#292e39",
    "BTN_BG": "#4d5362",
    "BTN_BORDER": "#7391a2",
    "BTN_HOVER": "#595f6e",
    "BTN_PRESSED": "#626875",
    "CREATE_HOVER": "#9bcad8",
    "DELETE_BG": "#ffb2b6",
    "DELETE_HOVER": "#ffcdcf",
    "MISSING": "#f59199",
    "DISABLED_BG": "#3b4252",
    "DISABLED_TX": "#717884",
    "NEUTRAL_BG": "#414854",
    "NEUTRAL_TX": "#c3cbd8",
}


# Rosé Pine
ROSE_PINE_LIGHT = {
    "INK": "#575279",
    "INK_SOFT": "#68657f",
    "INK_FAINT": "#68657f",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#faf4ed",
    "SURFACE": "#fffaf3",
    "BORDER": "#e3d9d1",
    "ACCENT": "#806c95",
    "ACCENT_DK": "#705e84",
    "ON_ACCENT": "#ffffff",
    "BUILD_BG": "#ccd5d6",
    "BUILD_TX": "#256077",
    "FIX_BG": "#ebd4d4",
    "FIX_TX": "#86495a",
    "SEL_BG": "#e9e1e1",
    "HOVER_BG": "#f7f2ed",
    "LIST_BG": "#f2e9e1",
    "BTN_BG": "#f6f0ec",
    "BTN_BORDER": "#90838f",
    "BTN_HOVER": "#ece5e5",
    "BTN_PRESSED": "#e1d8dc",
    "CREATE_HOVER": "#6c5b7d",
    "DELETE_BG": "#a3566b",
    "DELETE_HOVER": "#965264",
    "MISSING": "#a7586f",
    "DISABLED_BG": "#ede7e4",
    "DISABLED_TX": "#c0bbc5",
    "NEUTRAL_BG": "#e8e2e0",
    "NEUTRAL_TX": "#625f77",
}

ROSE_PINE_DARK = {
    "INK": "#e0def4",
    "INK_SOFT": "#a5a1bd",
    "INK_FAINT": "#89859e",  # placeholder and example text, 4.5:1 or better
    "CANVAS": "#191724",
    "SURFACE": "#1f1d2e",
    "BORDER": "#26233a",
    "ACCENT": "#c4a7e7",
    "ACCENT_DK": "#c4a7e7",
    "ON_ACCENT": "#1b1720",
    "BUILD_BG": "#2e3441",
    "BUILD_TX": "#9ccfd8",
    "FIX_BG": "#3b2536",
    "FIX_TX": "#eb6f92",
    "SEL_BG": "#3f374f",
    "HOVER_BG": "#323042",
    "LIST_BG": "#16141f",
    "BTN_BG": "#323042",
    "BTN_BORDER": "#71638c",
    "BTN_HOVER": "#403e50",
    "BTN_PRESSED": "#4f4d60",
    "CREATE_HOVER": "#cdb5eb",
    "DELETE_BG": "#ed7194",
    "DELETE_HOVER": "#f88aa9",
    "MISSING": "#eb6f92",
    "DISABLED_BG": "#1f1d2e",
    "DISABLED_TX": "#585569",
    "NEUTRAL_BG": "#2b2938",
    "NEUTRAL_TX": "#a5a1bd",
}
