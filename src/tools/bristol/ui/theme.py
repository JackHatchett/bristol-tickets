"""ui/theme.py — the appearance manager: schemes, design tokens, stylesheet.

This module holds every visual constant the rest of the UI draws with: the
column definitions, the custom item-data role, the named colour schemes, the
spacing / radius / type token scales, the global Qt stylesheet builder, and a
few small stateless helper functions. It imports nothing from the rest of the
package, so it is the safe bottom of the import graph — every other ui module
may import from here, and this module imports from none of them.

What each scheme key means and which token governs which element is the styling
contract in ``ui/README.md``.

Themes and modes
--------------------------------
A scheme is one complete palette under a name. A **theme** is a pair of them, a
light member and a dark member, and a **mode** is which of the two is drawn:
``light``, ``dark``, or ``system`` to follow the OS. The two are separate
choices, so a picker names themes rather than every combination of theme and
mode. ``resolve_scheme()`` turns a theme, a mode and the OS state into one
scheme name, and ``set_scheme(name)`` makes it live.

A theme with no dark member is a theme: ``theme_has_dark()`` says which, and
``resolve_scheme()`` draws its light palette whatever the mode and the OS say.
An older build stored the two choices collapsed into one value;
``appearance_choice()`` reads that value back as the theme and mode it named.

The collection
--------------------------------
Which themes an installation offers is not this module's to decide. It ships
the ones under ``THEME_CHOICES``; the configuration carries the differences —
themes the user added, names he deleted, a palette stored under a shipped
theme's name where he changed one — and ``resolve_collection()`` puts the two
together. ``install_collection()`` then rewrites ``SCHEMES`` and ``THEMES``
from the result, so a theme the user built is an ordinary theme from that point
and no resolver has a case for it. Storing differences rather than the whole
collection is what lets the themes a later release ships reach an installation
that has already been used.

``collection_differences()`` is the inverse, and what the manage-themes dialog
hands back to be stored.

Every consumer reads the current palette out of the single mutable dict ``C``
rather than binding colour names at import time, which could not be re-pointed
live. ``set_scheme()`` swaps ``C``'s contents in place, and
``build_style_sheet()`` renders the global Qt stylesheet from whatever ``C``
currently holds. Because ``C`` is mutated in place, a module that did
``from .theme import C`` keeps seeing live values — so a repaint after a scheme
change is all it takes for QPainter-drawn widgets (the cards) to re-theme, and a
single ``app.setStyleSheet(build_style_sheet())`` re-themes everything
stylesheet-driven, including child dialogs and message boxes.

Tokens
--------------------------------
Spacing, corner radius and font size are named steps rather than literals, so a
change to a scale reaches every painter and the stylesheet at once. Tokens are
scheme-independent: a scheme changes what a surface is coloured, never how far
apart two things sit.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# ---------------------------------------------------------------------------
# Board columns and the custom data role the card delegate paints from
# ---------------------------------------------------------------------------
COLUMNS = [
    ("todo", "To Do"),
    ("doing", "Doing"),
    ("done", "Done"),
]

CARD_ROLE = Qt.UserRole + 1  # structured payload the delegate paints from

# The fleet's agent slugs plus 'user' — the valid set of owners/originators for
# a task. Kept here as the single source for the record dialog's Owner picker
#. Order: 'user' first (the most common default), then agents
# alphabetically. Mirrors src/agent_identities/*.md.
FLEET_AGENTS = [
    "user",
    "career_coach",
    "chief_of_staff",
    "client_services",
    "game_designer",
    "librarian",
    "teaching_assistant",
    "writers_room",
]

# ---------------------------------------------------------------------------
# Design tokens — spacing, corner radius, type size
# ---------------------------------------------------------------------------
# Three fixed scales. A module needing a gap, a pad, a corner or a font size
# names a step instead of writing a number, so re-tuning the app's density is an
# edit here. Steps are in device-independent pixels, except TYPE, which is in
# points.
SPACE = {"xs": 2, "sm": 4, "md": 7, "lg": 11, "xl": 16, "2xl": 24}
RADIUS = {"sm": 4, "md": 7, "lg": 10, "xl": 12, "pill": 999}
TYPE = {"caption": 8, "body": 10, "title": 11, "section": 12, "display": 14}

# Window geometry, in device-independent pixels, and the splitter's opening
# split. Not a spacing scale — these size the window itself, and a module that
# needs one names it here rather than writing the number.
LAYOUT = {
    "window_min_w": 1240,
    "window_min_h": 780,
    "window_w": 1960,
    "window_h": 1080,
    "split_board": 1180,   # opening width of the board side
    "split_detail": 720,   # opening width of the detail side
    "column_min_w": 260,   # a board column narrower than this is unreadable
    "detail_min_w": 320,   # the detail pane narrower than this is unreadable
    "filter_menu_w": 300,      # the filter panel, wide enough for an epic name
    "filter_menu_max_h": 420,  # its option list, before it scrolls
    "wizard_min_w": 720,
    "wizard_min_h": 480,
    "dialog_min_w": 760,        # the record dialog
    "agent_dialog_min_w": 1180,  # the agent form: two columns, side by side
    "agent_dialog_min_h": 820,
    "agent_fields_min_w": 480,   # its left column, the entry's own fields
    "charter_min_w": 520,        # its right column, the charter document
    "skill_list_min_h": 170,     # its tick list of skills
    "path_list_min_h": 92,       # a list of declared paths, with its picker
    "env_name_w": 210,           # an environment variable's name box
    "env_choose_w": 34,          # the pick and remove buttons beside its value
    "extra_min_h": 90,           # its JSON field for keys this build predates
    "small_dialog_min_w": 420,  # a single-purpose modal: add link
    "preview_min_w": 480,       # the image preview modal
    "preview_min_h": 360,
    "theme_dialog_min_w": 1000,  # manage themes: the list, and a palette beside it
    "theme_dialog_min_h": 700,
    "theme_list_min_w": 230,     # its left column, wide enough for a theme's name
    "palette_caption_w": 210,    # what a colour row is called, at its longest
    "palette_swatch_w": 44,      # the block of colour a row opens the picker from
    "palette_hex_w": 110,        # its hex value, wide enough for #AARRGGBB
}

# What a stored value is called on screen. The database keeps the value and a
# reader sees the caption, so a vocabulary can be reworded without a migration —
# `src/tools/bristol/ui/README.md` §Words on screen states the rule and its one
# exception. Each list is ordered as the picker offers it.
STATUS_CHOICES: list[tuple[str, str]] = [
    ("todo", "To Do"),
    ("doing", "Doing"),
    ("done", "Done"),
]

# `active` is captioned Board, because that is the tab the card appears on.
STAGE_CHOICES: list[tuple[str, str]] = [
    ("backlog", "Backlog"),
    ("active", "Board"),
    ("archive", "Archive"),
]

# The vocabulary create_tickets.EPIC_STATUS_CHOICES writes.
EPIC_STATUS_CHOICES: list[tuple[str, str]] = [
    ("not started", "Not Started"),
    ("in progress", "In Progress"),
    ("completed", "Completed"),
    ("on hold", "On Hold"),
]

# An effort code as the word a reader who does not know the codes can read.
EFFORT_WORDS = {"S": "Small", "M": "Medium", "L": "Large", "XL": "Extra Large"}
EFFORT_CHOICES: list[tuple[str, str]] = [("", "Not Sized")] + [
    (code, word) for code, word in EFFORT_WORDS.items()
]
EFFORT_HINT = (
    "How much of a full usage budget this card would take.\n"
    "Small — under a tenth.    Medium — a tenth to about half.\n"
    "Large — half a budget or more.    Extra Large — more than one; split it."
)

# What kind of thing has stopped a card. None is not blocked. A dependency names
# no card here — that is a 'blocks' link, resolved live — and the prose goes in a
# comment. Mirrors ticket_tools/create_tickets.BLOCK_REASONS; the viewer carries
# its own copy so it depends on no package outside itself.
BLOCK_REASON_CHOICES: list[tuple[str | None, str]] = [
    (None, "Not Blocked"),
    ("dependency", "Dependency"),
    ("decision", "User Decision"),
    ("capability", "Missing Capability"),
    ("transient", "Transient Failure"),
]
BLOCK_REASON_HINT = (
    "What kind of thing has stopped this card. Which card is a Links entry.\n"
    "Dependency — another card.    User Decision — yours to make.\n"
    "Missing Capability — never granted.    Transient Failure — it failed once."
)


def space(step: str) -> int:
    """A gap or pad, by name."""
    return SPACE[step]


def radius(step: str) -> int:
    """A corner radius, by name."""
    return RADIUS[step]


def type_size(step: str) -> int:
    """A font point size, by name."""
    return TYPE[step]


# ---------------------------------------------------------------------------
# The house schemes — the warm orange family and a cool neutral alternate
# ---------------------------------------------------------------------------
# Every key here is read somewhere in the stylesheet or the card delegate. All
# schemes MUST carry the same keys so a swap never leaves a hole; check_schemes()
# names any that does.
WARM_LIGHT = {
    "INK":          "#3d3325",  # primary text (warm near-black)
    "INK_SOFT":     "#675c49",  # secondary text (6.1:1 on CANVAS)
    "CANVAS":       "#faf6ef",  # app / dialog background
    "SURFACE":      "#fffdf9",  # card / input surface
    "BORDER":       "#e7dcc6",  # hairline borders
    "ACCENT":       "#c2410c",  # primary orange (4.8:1 on CANVAS, 5.2:1 under white)
    "ACCENT_DK":    "#9a3412",  # deeper orange — bright accent text
    "ON_ACCENT":    "#ffffff",  # text and marks drawn on an accent fill
    "AMBER_BG":     "#fef3c7",  # epic pill background
    "AMBER_TX":     "#7c3608",  # epic pill text (7.9:1 on its tint)
    "BUILD_BG":     "#e4eee6",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#2e5a3d",  # Build record-type pill text (6.7:1 on its tint)
    "FIX_BG":       "#fbe2db",  # Fix record-type pill background (rust)
    "FIX_TX":       "#97301b",  # Fix record-type pill text (6.2:1 on its tint)
    "SEL_BG":       "#fff1e2",  # selected card fill
    "HOVER_BG":     "#fffaf2",  # hovered card fill
    "LIST_BG":      "#fbf6ee",  # kanban list / scroll area background
    "BTN_BG":       "#fff4e8",  # normal button fill
    "BTN_BORDER":   "#f7c99a",  # normal button border
    "BTN_HOVER":    "#ffe9d2",  # button hover fill
    "BTN_PRESSED":  "#ffddb8",  # button pressed fill
    "CREATE_HOVER": "#a83a0b",  # accent (Create) button hover fill
    "DELETE_BG":    "#c53a20",  # delete button fill (5.3:1 under white)
    "DELETE_HOVER": "#b03118",  # delete button hover fill
    "MISSING":      "#d61f1f",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#f3ece0",  # unclickable button fill
    "DISABLED_TX":  "#b3a389",  # unclickable button text
    "NEUTRAL_BG":   "#f0e7d6",  # a quiet pill: effort, pressure
    "NEUTRAL_TX":   "#574e3b",  # text on a NEUTRAL_BG pill (6.7:1 on its tint)
    "SHADOW":       "#33241c10",  # the soft drop shadow under a card
}

WARM_DARK = {
    "INK":          "#f2e6d5",  # primary text (warm near-white)
    "INK_SOFT":     "#b89f7d",  # secondary text
    "CANVAS":       "#17120c",  # app / dialog background (deep warm)
    "SURFACE":      "#241c14",  # card / input surface (dark warm)
    "BORDER":       "#463724",  # hairline borders
    "ACCENT":       "#f97316",  # primary orange (brighter for dark)
    "ACCENT_DK":    "#fdba74",  # light orange — bright accent text on dark
    "ON_ACCENT":    "#201409",  # deep warm text on the bright accent (6.4:1)
    "AMBER_BG":     "#3a2a10",  # epic pill background (dark amber)
    "AMBER_TX":     "#fcd34d",  # epic pill text (bright amber)
    "BUILD_BG":     "#1e2a1e",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#8fca9a",  # Build record-type pill text
    "FIX_BG":       "#3a1f18",  # Fix record-type pill background (rust)
    "FIX_TX":       "#f0a58e",  # Fix record-type pill text
    "SEL_BG":       "#3a2914",  # selected card fill
    "HOVER_BG":     "#2a2115",  # hovered card fill
    "LIST_BG":      "#1c160f",  # kanban list / scroll area background
    "BTN_BG":       "#33281b",  # normal button fill
    "BTN_BORDER":   "#6b4f2e",  # normal button border
    "BTN_HOVER":    "#40311f",  # button hover fill
    "BTN_PRESSED":  "#4a3826",  # button pressed fill
    "CREATE_HOVER": "#fb8b3d",  # accent (Create) button hover fill
    "DELETE_BG":    "#e0563b",  # delete button fill (4.8:1 under ON_ACCENT)
    "DELETE_HOVER": "#ea6448",  # delete button hover fill
    "MISSING":      "#ff5449",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#241c14",  # unclickable button fill
    "DISABLED_TX":  "#6b5b45",  # unclickable button text
    "NEUTRAL_BG":   "#2f2618",  # a quiet pill: effort, pressure
    "NEUTRAL_TX":   "#c4ae8e",  # text on a NEUTRAL_BG pill
    "SHADOW":       "#66000000",  # the soft drop shadow under a card
}

# The cool neutral alternate: grey canvas, white surfaces, a blue accent. Where
# the warm family reads as paper, this one reads as a modern web tool.
COOL_LIGHT = {
    "INK":          "#0f172a",  # primary text (near-black slate)
    "INK_SOFT":     "#5b6779",  # secondary text (4.9:1 on LIST_BG)
    "CANVAS":       "#f4f5f7",  # app / dialog background
    "SURFACE":      "#ffffff",  # card / input surface
    "BORDER":       "#e2e8f0",  # hairline borders
    "ACCENT":       "#2563eb",  # primary blue
    "ACCENT_DK":    "#1d4ed8",  # deeper blue — bright accent text
    "ON_ACCENT":    "#ffffff",  # text and marks drawn on an accent fill
    "AMBER_BG":     "#e0e7ff",  # epic pill background (indigo tint)
    "AMBER_TX":     "#3730a3",  # epic pill text
    "BUILD_BG":     "#dcfce7",  # Build record-type pill background (green)
    "BUILD_TX":     "#166534",  # Build record-type pill text (6.5:1 on its tint)
    "FIX_BG":       "#fee2e2",  # Fix record-type pill background (red)
    "FIX_TX":       "#991b1b",  # Fix record-type pill text (6.8:1 on its tint)
    "SEL_BG":       "#e8f0fe",  # selected card fill
    "HOVER_BG":     "#f8fafc",  # hovered card fill
    "LIST_BG":      "#ebecf0",  # kanban list / scroll area background
    "BTN_BG":       "#ffffff",  # normal button fill
    "BTN_BORDER":   "#cbd5e1",  # normal button border
    "BTN_HOVER":    "#f1f5f9",  # button hover fill
    "BTN_PRESSED":  "#e2e8f0",  # button pressed fill
    "CREATE_HOVER": "#1d4ed8",  # accent (Create) button hover fill
    "DELETE_BG":    "#dc2626",  # delete button fill
    "DELETE_HOVER": "#b91c1c",  # delete button hover fill
    "MISSING":      "#dc2626",  # required-but-empty field border
    "DISABLED_BG":  "#f1f5f9",  # unclickable button fill
    "DISABLED_TX":  "#94a3b8",  # unclickable button text
    "NEUTRAL_BG":   "#eef1f5",  # a quiet pill: effort, pressure
    "NEUTRAL_TX":   "#475569",  # text on a NEUTRAL_BG pill
    "SHADOW":       "#2b0f172a",  # the soft drop shadow under a card
}

COOL_DARK = {
    "INK":          "#e2e8f0",  # primary text (near-white slate)
    "INK_SOFT":     "#94a3b8",  # secondary text
    "CANVAS":       "#0f1216",  # app / dialog background
    "SURFACE":      "#1a1f26",  # card / input surface
    "BORDER":       "#2c333d",  # hairline borders
    "ACCENT":       "#3b82f6",  # primary blue (brighter for dark)
    "ACCENT_DK":    "#93c5fd",  # light blue — bright accent text on dark
    "ON_ACCENT":    "#0f1216",  # deep slate text on the bright accent (5.1:1)
    "AMBER_BG":     "#1e1b4b",  # epic pill background (deep indigo)
    "AMBER_TX":     "#a5b4fc",  # epic pill text
    "BUILD_BG":     "#14261a",  # Build record-type pill background (green)
    "BUILD_TX":     "#86efac",  # Build record-type pill text
    "FIX_BG":       "#2c1618",  # Fix record-type pill background (red)
    "FIX_TX":       "#fca5a5",  # Fix record-type pill text
    "SEL_BG":       "#1e293b",  # selected card fill
    "HOVER_BG":     "#20262e",  # hovered card fill
    "LIST_BG":      "#14181d",  # kanban list / scroll area background
    "BTN_BG":       "#232a33",  # normal button fill
    "BTN_BORDER":   "#39424e",  # normal button border
    "BTN_HOVER":    "#2b333d",  # button hover fill
    "BTN_PRESSED":  "#333c48",  # button pressed fill
    "CREATE_HOVER": "#60a5fa",  # accent (Create) button hover fill
    "DELETE_BG":    "#ef4444",  # delete button fill (5.0:1 under ON_ACCENT)
    "DELETE_HOVER": "#f87171",  # delete button hover fill
    "MISSING":      "#f87171",  # required-but-empty field border
    "DISABLED_BG":  "#1a1f26",  # unclickable button fill
    "DISABLED_TX":  "#5b6672",  # unclickable button text
    "NEUTRAL_BG":   "#242b34",  # a quiet pill: effort, pressure
    "NEUTRAL_TX":   "#b6c0cc",  # text on a NEUTRAL_BG pill
    "SHADOW":       "#66000000",  # the soft drop shadow under a card
}

# ---------------------------------------------------------------------------
# The borrowed shelf — one theme per scheme people already read code in
# ---------------------------------------------------------------------------
# Each is a palette rather than a mechanism: the grounds, the text and the
# signal colours come from the scheme its name points at, and the fills, pills
# and button states are that palette's own colours tinted onto its own ground.
# Every one of them clears CONTRAST_MIN on every pair in TEXT_PAIRS, which is
# what the accent and the secondary text are pinned to where a source palette
# sits under it.

# Ayu
AYU_LIGHT = {
    "INK":          "#5c6166",
    "INK_SOFT":     "#696e74",
    "CANVAS":       "#fcfcfc",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e7e8e9",
    "ACCENT":       "#ff9940",
    "ACCENT_DK":    "#a26229",
    "ON_ACCENT":    "#241509",
    "AMBER_BG":     "#faebd5",
    "AMBER_TX":     "#88622a",
    "BUILD_BG":     "#e2ecc5",
    "BUILD_TX":     "#516e00",
    "FIX_BG":       "#f9dddd",
    "FIX_TX":       "#9d4b4b",
    "SEL_BG":       "#fceee2",
    "HOVER_BG":     "#f7f7f7",
    "LIST_BG":      "#f3f4f5",
    "BTN_BG":       "#fff8f2",
    "BTN_BORDER":   "#f1c7a2",
    "BTN_HOVER":    "#fff0e2",
    "BTN_PRESSED":  "#ffe7d1",
    "CREATE_HOVER": "#ffa95f",
    "DELETE_BG":    "#f07171",
    "DELETE_HOVER": "#f28282",
    "MISSING":      "#f07171",
    "DISABLED_BG":  "#f1f1f2",
    "DISABLED_TX":  "#c9cccf",
    "NEUTRAL_BG":   "#ecedee",
    "NEUTRAL_TX":   "#63686e",
    "SHADOW":       "#2e333538",
}

AYU_DARK = {
    "INK":          "#cccac2",
    "INK_SOFT":     "#9ba1ac",
    "CANVAS":       "#1f2430",
    "SURFACE":      "#242936",
    "BORDER":       "#313747",
    "ACCENT":       "#ffcc66",
    "ACCENT_DK":    "#ffcc66",
    "ON_ACCENT":    "#241d0e",
    "AMBER_BG":     "#43403d",
    "AMBER_TX":     "#ffd580",
    "BUILD_BG":     "#30413a",
    "BUILD_TX":     "#87d96c",
    "FIX_BG":       "#432f39",
    "FIX_TX":       "#ff7373",
    "SEL_BG":       "#50493c",
    "HOVER_BG":     "#353944",
    "LIST_BG":      "#1a1f29",
    "BTN_BG":       "#353944",
    "BTN_BORDER":   "#887654",
    "BTN_HOVER":    "#41444e",
    "BTN_PRESSED":  "#4e5159",
    "CREATE_HOVER": "#ffd47e",
    "DELETE_BG":    "#ff6666",
    "DELETE_HOVER": "#ff7878",
    "MISSING":      "#ff6666",
    "DISABLED_BG":  "#242936",
    "DISABLED_TX":  "#575c68",
    "NEUTRAL_BG":   "#2f3440",
    "NEUTRAL_TX":   "#9ba1ac",
    "SHADOW":       "#66000000",
}


# Blue Topaz
BLUE_TOPAZ_LIGHT = {
    "INK":          "#22303f",
    "INK_SOFT":     "#5a6b7b",
    "CANVAS":       "#f2f5f8",
    "SURFACE":      "#ffffff",
    "BORDER":       "#d6dee6",
    "ACCENT":       "#2873c2",
    "ACCENT_DK":    "#2770bc",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e7ddc8",
    "AMBER_TX":     "#7e5a10",
    "BUILD_BG":     "#cbdfd0",
    "BUILD_TX":     "#2d682e",
    "FIX_BG":       "#edd0d3",
    "FIX_TX":       "#9b3939",
    "SEL_BG":       "#d6e3f0",
    "HOVER_BG":     "#f4f5f5",
    "LIST_BG":      "#e8edf2",
    "BTN_BG":       "#f0f5fb",
    "BTN_BORDER":   "#8db1d7",
    "BTN_HOVER":    "#dfeaf6",
    "BTN_PRESSED":  "#cbddf0",
    "CREATE_HOVER": "#2261a3",
    "DELETE_BG":    "#c64949",
    "DELETE_HOVER": "#ae4040",
    "MISSING":      "#d94f4f",
    "DISABLED_BG":  "#e3e7ec",
    "DISABLED_TX":  "#aeb7c0",
    "NEUTRAL_BG":   "#dde2e6",
    "NEUTRAL_TX":   "#516270",
    "SHADOW":       "#2e131a23",
}

BLUE_TOPAZ_DARK = {
    "INK":          "#dbe6f0",
    "INK_SOFT":     "#9fb2c4",
    "CANVAS":       "#1b222b",
    "SURFACE":      "#232c37",
    "BORDER":       "#33404e",
    "ACCENT":       "#58a6f0",
    "ACCENT_DK":    "#58a6f0",
    "ON_ACCENT":    "#0c1722",
    "AMBER_BG":     "#3c3c35",
    "AMBER_TX":     "#e9c46a",
    "BUILD_BG":     "#2b3e39",
    "BUILD_TX":     "#7fce85",
    "FIX_BG":       "#3d3038",
    "FIX_TX":       "#f07c81",
    "SEL_BG":       "#283f56",
    "HOVER_BG":     "#353f4a",
    "LIST_BG":      "#161c24",
    "BTN_BG":       "#353f4a",
    "BTN_BORDER":   "#436b92",
    "BTN_HOVER":    "#424c56",
    "BTN_PRESSED":  "#515a65",
    "CREATE_HOVER": "#73b4f2",
    "DELETE_BG":    "#f0787d",
    "DELETE_HOVER": "#f2888d",
    "MISSING":      "#f0787d",
    "DISABLED_BG":  "#232c37",
    "DISABLED_TX":  "#566370",
    "NEUTRAL_BG":   "#2c353f",
    "NEUTRAL_TX":   "#9fb2c4",
    "SHADOW":       "#66000000",
}


# Catppuccin
CATPPUCCIN_LIGHT = {
    "INK":          "#4c4f69",
    "INK_SOFT":     "#636679",
    "CANVAS":       "#eff1f5",
    "SURFACE":      "#ffffff",
    "BORDER":       "#dce0e8",
    "ACCENT":       "#1e66f5",
    "ACCENT_DK":    "#1c60e7",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#ebdbc5",
    "AMBER_TX":     "#865410",
    "BUILD_BG":     "#c9dfc9",
    "BUILD_TX":     "#2a691d",
    "FIX_BG":       "#e9bfcc",
    "FIX_TX":       "#a50f2d",
    "SEL_BG":       "#d2def5",
    "HOVER_BG":     "#f6f6f8",
    "LIST_BG":      "#e6e9ef",
    "BTN_BG":       "#eff4fe",
    "BTN_BORDER":   "#8caded",
    "BTN_HOVER":    "#dde8fe",
    "BTN_PRESSED":  "#c9dafd",
    "CREATE_HOVER": "#1956ce",
    "DELETE_BG":    "#d20f39",
    "DELETE_HOVER": "#b90d32",
    "MISSING":      "#d20f39",
    "DISABLED_BG":  "#e2e4ea",
    "DISABLED_TX":  "#b4b6c3",
    "NEUTRAL_BG":   "#dddfe5",
    "NEUTRAL_TX":   "#5d6071",
    "SHADOW":       "#2e2a2b3a",
}

CATPPUCCIN_DARK = {
    "INK":          "#cdd6f4",
    "INK_SOFT":     "#a6adc8",
    "CANVAS":       "#1e1e2e",
    "SURFACE":      "#313244",
    "BORDER":       "#45475a",
    "ACCENT":       "#89b4fa",
    "ACCENT_DK":    "#89b4fa",
    "ON_ACCENT":    "#131923",
    "AMBER_BG":     "#413d43",
    "AMBER_TX":     "#f9e2af",
    "BUILD_BG":     "#343e40",
    "BUILD_TX":     "#a6e3a1",
    "FIX_BG":       "#402f42",
    "FIX_TX":       "#f38ba8",
    "SEL_BG":       "#363f5b",
    "HOVER_BG":     "#414256",
    "LIST_BG":      "#181825",
    "BTN_BG":       "#414256",
    "BTN_BORDER":   "#62759d",
    "BTN_HOVER":    "#4c4e62",
    "BTN_PRESSED":  "#53566b",
    "CREATE_HOVER": "#9cc0fb",
    "DELETE_BG":    "#f38ba8",
    "DELETE_HOVER": "#f499b2",
    "MISSING":      "#f38ba8",
    "DISABLED_BG":  "#313244",
    "DISABLED_TX":  "#5b5e73",
    "NEUTRAL_BG":   "#303142",
    "NEUTRAL_TX":   "#a6adc8",
    "SHADOW":       "#66000000",
}


# Dracula
DRACULA_LIGHT = {
    "INK":          "#1f1f1f",
    "INK_SOFT":     "#6c664b",
    "CANVAS":       "#fffbeb",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e8e3ce",
    "ACCENT":       "#644ac9",
    "ACCENT_DK":    "#644ac9",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e4dcbc",
    "AMBER_TX":     "#6e5c10",
    "BUILD_BG":     "#cbddba",
    "BUILD_TX":     "#126b0a",
    "FIX_BG":       "#f4d1c1",
    "FIX_TX":       "#a92f24",
    "SEL_BG":       "#e9e2e6",
    "HOVER_BG":     "#f4f4f4",
    "LIST_BG":      "#f5f1e0",
    "BTN_BG":       "#f4f2fb",
    "BTN_BORDER":   "#b1a3cc",
    "BTN_HOVER":    "#e8e4f7",
    "BTN_PRESSED":  "#dad4f2",
    "CREATE_HOVER": "#543ea9",
    "DELETE_BG":    "#cb3a2a",
    "DELETE_HOVER": "#b33325",
    "MISSING":      "#cb3a2a",
    "DISABLED_BG":  "#f0ecdb",
    "DISABLED_TX":  "#bdb8a3",
    "NEUTRAL_BG":   "#eae6d5",
    "NEUTRAL_TX":   "#696349",
    "SHADOW":       "#2e111111",
}

DRACULA_DARK = {
    "INK":          "#f8f8f2",
    "INK_SOFT":     "#a7aed0",
    "CANVAS":       "#282a36",
    "SURFACE":      "#343746",
    "BORDER":       "#44475a",
    "ACCENT":       "#bd93f9",
    "ACCENT_DK":    "#bd93f9",
    "ON_ACCENT":    "#1a1523",
    "AMBER_BG":     "#484b44",
    "AMBER_TX":     "#f1fa8c",
    "BUILD_BG":     "#2e4b41",
    "BUILD_TX":     "#50fa7b",
    "FIX_BG":       "#4a313b",
    "FIX_TX":       "#ff7a7a",
    "SEL_BG":       "#494161",
    "HOVER_BG":     "#484a57",
    "LIST_BG":      "#21222c",
    "BTN_BG":       "#484a57",
    "BTN_BORDER":   "#77679d",
    "BTN_HOVER":    "#555863",
    "BTN_PRESSED":  "#656771",
    "CREATE_HOVER": "#c8a4fa",
    "DELETE_BG":    "#ff5555",
    "DELETE_HOVER": "#ff6969",
    "MISSING":      "#ff5555",
    "DISABLED_BG":  "#343746",
    "DISABLED_TX":  "#61657b",
    "NEUTRAL_BG":   "#393b4a",
    "NEUTRAL_TX":   "#a7aed0",
    "SHADOW":       "#66000000",
}


# Everforest
EVERFOREST_LIGHT = {
    "INK":          "#5c6a72",
    "INK_SOFT":     "#636e62",
    "CANVAS":       "#fdf6e3",
    "SURFACE":      "#fffbef",
    "BORDER":       "#e6e2cc",
    "ACCENT":       "#2f7ca4",
    "ACCENT_DK":    "#2d749a",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#f6e3b1",
    "AMBER_TX":     "#825d00",
    "BUILD_BG":     "#e4e3b1",
    "BUILD_TX":     "#596601",
    "FIX_BG":       "#fcd3c3",
    "FIX_TX":       "#a33836",
    "SEL_BG":       "#ecebdd",
    "HOVER_BG":     "#f7f4e9",
    "LIST_BG":      "#f4f0d9",
    "BTN_BG":       "#f0f2ea",
    "BTN_BORDER":   "#99b7bb",
    "BTN_HOVER":    "#e8ece4",
    "BTN_PRESSED":  "#eaecdd",
    "CREATE_HOVER": "#27688a",
    "DELETE_BG":    "#c94644",
    "DELETE_HOVER": "#b13e3c",
    "MISSING":      "#f85552",
    "DISABLED_BG":  "#f1ecd9",
    "DISABLED_TX":  "#c6c9b7",
    "NEUTRAL_BG":   "#ece8d5",
    "NEUTRAL_TX":   "#5d685c",
    "SHADOW":       "#2e333a3f",
}

EVERFOREST_DARK = {
    "INK":          "#d3c6aa",
    "INK_SOFT":     "#a3aea6",
    "CANVAS":       "#2d353b",
    "SURFACE":      "#343f44",
    "BORDER":       "#3d484d",
    "ACCENT":       "#7fbbb3",
    "ACCENT_DK":    "#7fbbb3",
    "ON_ACCENT":    "#121a19",
    "AMBER_BG":     "#494b46",
    "AMBER_TX":     "#dbbc7f",
    "BUILD_BG":     "#414b46",
    "BUILD_TX":     "#aac284",
    "FIX_BG":       "#4b4146",
    "FIX_TX":       "#ef9d9e",
    "SEL_BG":       "#3f5255",
    "HOVER_BG":     "#444c4e",
    "LIST_BG":      "#272e33",
    "BTN_BG":       "#444c4e",
    "BTN_BORDER":   "#597878",
    "BTN_HOVER":    "#4c5353",
    "BTN_PRESSED":  "#4c5252",
    "CREATE_HOVER": "#93c6bf",
    "DELETE_BG":    "#e67e80",
    "DELETE_HOVER": "#e98d8f",
    "MISSING":      "#e67e80",
    "DISABLED_BG":  "#343f44",
    "DISABLED_TX":  "#5f6968",
    "NEUTRAL_BG":   "#3c4448",
    "NEUTRAL_TX":   "#acb4ae",
    "SHADOW":       "#66000000",
}


# GitHub
GITHUB_LIGHT = {
    "INK":          "#1f2328",
    "INK_SOFT":     "#656d76",
    "CANVAS":       "#f6f8fa",
    "SURFACE":      "#ffffff",
    "BORDER":       "#d0d7de",
    "ACCENT":       "#0969da",
    "ACCENT_DK":    "#0969da",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e2d8c3",
    "AMBER_TX":     "#7d5200",
    "BUILD_BG":     "#c6ddcf",
    "BUILD_TX":     "#146a2e",
    "FIX_BG":       "#edc9cd",
    "FIX_TX":       "#ad1c28",
    "SEL_BG":       "#d5e4f6",
    "HOVER_BG":     "#f4f4f4",
    "LIST_BG":      "#eef1f4",
    "BTN_BG":       "#eef4fc",
    "BTN_BORDER":   "#7ca9dc",
    "BTN_HOVER":    "#dae8f9",
    "BTN_PRESSED":  "#c4dbf6",
    "CREATE_HOVER": "#0858b7",
    "DELETE_BG":    "#cf222e",
    "DELETE_HOVER": "#b61e28",
    "MISSING":      "#cf222e",
    "DISABLED_BG":  "#e8eaed",
    "DISABLED_TX":  "#b5b9bf",
    "NEUTRAL_BG":   "#e2e5e8",
    "NEUTRAL_TX":   "#5c646c",
    "SHADOW":       "#2e111316",
}

GITHUB_DARK = {
    "INK":          "#e6edf3",
    "INK_SOFT":     "#8b949e",
    "CANVAS":       "#0d1117",
    "SURFACE":      "#161b22",
    "BORDER":       "#30363d",
    "ACCENT":       "#58a6ff",
    "ACCENT_DK":    "#58a6ff",
    "ON_ACCENT":    "#0c1724",
    "AMBER_BG":     "#2d2719",
    "AMBER_TX":     "#d29922",
    "BUILD_BG":     "#152c20",
    "BUILD_TX":     "#3fb950",
    "FIX_BG":       "#331b1f",
    "FIX_TX":       "#f85149",
    "SEL_BG":       "#1e324a",
    "HOVER_BG":     "#2b3037",
    "LIST_BG":      "#010409",
    "BTN_BG":       "#2b3037",
    "BTN_BORDER":   "#41658e",
    "BTN_HOVER":    "#393f46",
    "BTN_PRESSED":  "#4a5056",
    "CREATE_HOVER": "#73b4ff",
    "DELETE_BG":    "#f85149",
    "DELETE_HOVER": "#f9665f",
    "MISSING":      "#f85149",
    "DISABLED_BG":  "#161b22",
    "DISABLED_TX":  "#464c54",
    "NEUTRAL_BG":   "#1d2229",
    "NEUTRAL_TX":   "#8b949e",
    "SHADOW":       "#66000000",
}


# Gruvbox
GRUVBOX_LIGHT = {
    "INK":          "#3c3836",
    "INK_SOFT":     "#665c54",
    "CANVAS":       "#fbf1c7",
    "SURFACE":      "#fffbe8",
    "BORDER":       "#e5d9ac",
    "ACCENT":       "#af3a03",
    "ACCENT_DK":    "#af3a03",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#ecd6a0",
    "AMBER_TX":     "#7e5110",
    "BUILD_BG":     "#ded69e",
    "BUILD_TX":     "#5f5c0e",
    "FIX_BG":       "#e6bc9d",
    "FIX_TX":       "#9d0006",
    "SEL_BG":       "#f0d7ac",
    "HOVER_BG":     "#f5f1df",
    "LIST_BG":      "#f2e5bc",
    "BTN_BG":       "#f9edd8",
    "BTN_BORDER":   "#ce9665",
    "BTN_HOVER":    "#f3dec6",
    "BTN_PRESSED":  "#eccdb1",
    "CREATE_HOVER": "#933103",
    "DELETE_BG":    "#9d0006",
    "DELETE_HOVER": "#8a0005",
    "MISSING":      "#9d0006",
    "DISABLED_BG":  "#ece2bc",
    "DISABLED_TX":  "#b8ae93",
    "NEUTRAL_BG":   "#e6dcb7",
    "NEUTRAL_TX":   "#665c54",
    "SHADOW":       "#2e211f1e",
}

GRUVBOX_DARK = {
    "INK":          "#ebdbb2",
    "INK_SOFT":     "#bdae93",
    "CANVAS":       "#282828",
    "SURFACE":      "#32302f",
    "BORDER":       "#504945",
    "ACCENT":       "#fe8019",
    "ACCENT_DK":    "#fe8019",
    "ON_ACCENT":    "#241204",
    "AMBER_BG":     "#4a4029",
    "AMBER_TX":     "#fabd2f",
    "BUILD_BG":     "#3f4028",
    "BUILD_TX":     "#b8bb26",
    "FIX_BG":       "#4a2d2a",
    "FIX_TX":       "#fb786a",
    "SEL_BG":       "#573b25",
    "HOVER_BG":     "#44413c",
    "LIST_BG":      "#1d2021",
    "BTN_BG":       "#44413c",
    "BTN_BORDER":   "#996033",
    "BTN_HOVER":    "#514d45",
    "BTN_PRESSED":  "#605b50",
    "CREATE_HOVER": "#fe943e",
    "DELETE_BG":    "#fb4934",
    "DELETE_HOVER": "#fb5f4c",
    "MISSING":      "#fb4934",
    "DISABLED_BG":  "#32302f",
    "DISABLED_TX":  "#6b6458",
    "NEUTRAL_BG":   "#3b3936",
    "NEUTRAL_TX":   "#bdae93",
    "SHADOW":       "#66000000",
}


# Horizon
HORIZON_LIGHT = {
    "INK":          "#232530",
    "INK_SOFT":     "#5d607f",
    "CANVAS":       "#fdf0ed",
    "SURFACE":      "#fff8f6",
    "BORDER":       "#f0d3c9",
    "ACCENT":       "#cc4068",
    "ACCENT_DK":    "#c03c62",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#f5dac3",
    "AMBER_TX":     "#865420",
    "BUILD_BG":     "#cce4d5",
    "BUILD_TX":     "#106e4d",
    "FIX_BG":       "#fbc9cd",
    "FIX_TX":       "#a52a3f",
    "SEL_BG":       "#f6d7da",
    "HOVER_BG":     "#f4edec",
    "LIST_BG":      "#fadad1",
    "BTN_BG":       "#fbebec",
    "BTN_BORDER":   "#e195a0",
    "BTN_HOVER":    "#f7dce1",
    "BTN_PRESSED":  "#f3ccd4",
    "CREATE_HOVER": "#ab3657",
    "DELETE_BG":    "#d2344f",
    "DELETE_HOVER": "#b92e46",
    "MISSING":      "#f43e5c",
    "DISABLED_BG":  "#efe3e4",
    "DISABLED_TX":  "#bcb6c5",
    "NEUTRAL_BG":   "#e9dee0",
    "NEUTRAL_TX":   "#5d607f",
    "SHADOW":       "#2e13141a",
}

HORIZON_DARK = {
    "INK":          "#d5d8da",
    "INK_SOFT":     "#9a9db8",
    "CANVAS":       "#1c1e26",
    "SURFACE":      "#232530",
    "BORDER":       "#2e303e",
    "ACCENT":       "#e95678",
    "ACCENT_DK":    "#eb6080",
    "ON_ACCENT":    "#210c11",
    "AMBER_BG":     "#403638",
    "AMBER_TX":     "#fab795",
    "BUILD_BG":     "#1e3b38",
    "BUILD_TX":     "#29d398",
    "FIX_BG":       "#3f232f",
    "FIX_TX":       "#f4637b",
    "SEL_BG":       "#492a38",
    "HOVER_BG":     "#353741",
    "LIST_BG":      "#16181e",
    "BTN_BG":       "#353741",
    "BTN_BORDER":   "#7d4056",
    "BTN_HOVER":    "#41434d",
    "BTN_PRESSED":  "#50525a",
    "CREATE_HOVER": "#ed718e",
    "DELETE_BG":    "#f43e5c",
    "DELETE_HOVER": "#f55570",
    "MISSING":      "#f43e5c",
    "DISABLED_BG":  "#232530",
    "DISABLED_TX":  "#555768",
    "NEUTRAL_BG":   "#2c2f39",
    "NEUTRAL_TX":   "#9a9db8",
    "SHADOW":       "#66000000",
}


# iA Writer
IA_WRITER_LIGHT = {
    "INK":          "#2e2e2e",
    "INK_SOFT":     "#6b6b66",
    "CANVAS":       "#fbfbf9",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e2e2dc",
    "ACCENT":       "#197ab7",
    "ACCENT_DK":    "#1876b2",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e9dec8",
    "AMBER_TX":     "#7c5912",
    "BUILD_BG":     "#d1dfd0",
    "BUILD_TX":     "#336935",
    "FIX_BG":       "#eed0cc",
    "FIX_TX":       "#a53026",
    "SEL_BG":       "#dbe9f0",
    "HOVER_BG":     "#f5f5f5",
    "LIST_BG":      "#f2f2ee",
    "BTN_BG":       "#eff6fa",
    "BTN_BORDER":   "#8eb6cc",
    "BTN_HOVER":    "#dcebf4",
    "BTN_PRESSED":  "#c8dfee",
    "CREATE_HOVER": "#15669a",
    "DELETE_BG":    "#c0392b",
    "DELETE_HOVER": "#a93226",
    "MISSING":      "#c0392b",
    "DISABLED_BG":  "#ededea",
    "DISABLED_TX":  "#babab7",
    "NEUTRAL_BG":   "#e7e7e4",
    "NEUTRAL_TX":   "#656560",
    "SHADOW":       "#2e191919",
}

IA_WRITER_DARK = {
    "INK":          "#d8d8d4",
    "INK_SOFT":     "#a0a09a",
    "CANVAS":       "#131314",
    "SURFACE":      "#1c1c1e",
    "BORDER":       "#2c2c2e",
    "ACCENT":       "#4ab3ee",
    "ACCENT_DK":    "#4ab3ee",
    "ON_ACCENT":    "#0a1921",
    "AMBER_BG":     "#332c20",
    "AMBER_TX":     "#dcb161",
    "BUILD_BG":     "#253027",
    "BUILD_TX":     "#86c98a",
    "FIX_BG":       "#362423",
    "FIX_TX":       "#ef7c72",
    "SEL_BG":       "#1f3644",
    "HOVER_BG":     "#2f2f30",
    "LIST_BG":      "#0d0d0e",
    "BTN_BG":       "#2f2f30",
    "BTN_BORDER":   "#39657f",
    "BTN_HOVER":    "#3c3c3d",
    "BTN_PRESSED":  "#4b4b4c",
    "CREATE_HOVER": "#67bff1",
    "DELETE_BG":    "#ef7c72",
    "DELETE_HOVER": "#f18c83",
    "MISSING":      "#ef7c72",
    "DISABLED_BG":  "#1c1c1e",
    "DISABLED_TX":  "#525250",
    "NEUTRAL_BG":   "#252525",
    "NEUTRAL_TX":   "#a0a09a",
    "SHADOW":       "#66000000",
}


# Kanagawa
KANAGAWA_LIGHT = {
    "INK":          "#545464",
    "INK_SOFT":     "#5f5c50",
    "CANVAS":       "#f2ecbc",
    "SURFACE":      "#f9f4d8",
    "BORDER":       "#dcd5ac",
    "ACCENT":       "#4d699b",
    "ACCENT_DK":    "#4b6696",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#d7d1a0",
    "AMBER_TX":     "#5b562f",
    "BUILD_BG":     "#d5d6a4",
    "BUILD_TX":     "#4d5f36",
    "FIX_BG":       "#e9c6a5",
    "FIX_TX":       "#982f41",
    "SEL_BG":       "#dbdab7",
    "HOVER_BG":     "#f1ecd2",
    "LIST_BG":      "#e7dba0",
    "BTN_BG":       "#edead4",
    "BTN_BORDER":   "#a0a8a5",
    "BTN_HOVER":    "#dfdfcf",
    "BTN_PRESSED":  "#d0d3c9",
    "CREATE_HOVER": "#415882",
    "DELETE_BG":    "#c84053",
    "DELETE_HOVER": "#b03849",
    "MISSING":      "#c84053",
    "DISABLED_BG":  "#e5dfb3",
    "DISABLED_TX":  "#b8b393",
    "NEUTRAL_BG":   "#e0daaf",
    "NEUTRAL_TX":   "#5f5c50",
    "SHADOW":       "#2e2e2e37",
}

KANAGAWA_DARK = {
    "INK":          "#dcd7ba",
    "INK_SOFT":     "#a8a396",
    "CANVAS":       "#1f1f28",
    "SURFACE":      "#2a2a37",
    "BORDER":       "#363646",
    "ACCENT":       "#7e9cd8",
    "ACCENT_DK":    "#7e9cd8",
    "ON_ACCENT":    "#12161e",
    "AMBER_BG":     "#3d3431",
    "AMBER_TX":     "#dca561",
    "BUILD_BG":     "#323833",
    "BUILD_TX":     "#98bb6c",
    "FIX_BG":       "#3f2b34",
    "FIX_TX":       "#e87986",
    "SEL_BG":       "#343a4f",
    "HOVER_BG":     "#3c3b44",
    "LIST_BG":      "#16161d",
    "BTN_BG":       "#3c3b44",
    "BTN_BORDER":   "#546183",
    "BTN_HOVER":    "#48474d",
    "BTN_PRESSED":  "#565558",
    "CREATE_HOVER": "#93acde",
    "DELETE_BG":    "#e46876",
    "DELETE_HOVER": "#e77a86",
    "MISSING":      "#e46876",
    "DISABLED_BG":  "#2a2a37",
    "DISABLED_TX":  "#5d5a5a",
    "NEUTRAL_BG":   "#313036",
    "NEUTRAL_TX":   "#a8a396",
    "SHADOW":       "#66000000",
}


# Material
MATERIAL_LIGHT = {
    "INK":          "#37474f",
    "INK_SOFT":     "#5b6b71",
    "CANVAS":       "#fafafa",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e0e0e0",
    "ACCENT":       "#39adb5",
    "ACCENT_DK":    "#2a7c82",
    "ON_ACCENT":    "#081819",
    "AMBER_BG":     "#f9e7ce",
    "AMBER_TX":     "#8a5c1f",
    "BUILD_BG":     "#e3ebd7",
    "BUILD_TX":     "#566e35",
    "FIX_BG":       "#f5d0cf",
    "FIX_TX":       "#ae2c2a",
    "SEL_BG":       "#dfeff0",
    "HOVER_BG":     "#f5f6f6",
    "LIST_BG":      "#eeeeee",
    "BTN_BG":       "#f1f9fa",
    "BTN_BORDER":   "#9acbce",
    "BTN_HOVER":    "#e1f3f4",
    "BTN_PRESSED":  "#cfebed",
    "CREATE_HOVER": "#59bac1",
    "DELETE_BG":    "#e84b47",
    "DELETE_HOVER": "#eb615d",
    "MISSING":      "#e53935",
    "DISABLED_BG":  "#ecedee",
    "DISABLED_TX":  "#b9c1c5",
    "NEUTRAL_BG":   "#e6e8ea",
    "NEUTRAL_TX":   "#58686e",
    "SHADOW":       "#2e1e272b",
}

MATERIAL_DARK = {
    "INK":          "#eeffff",
    "INK_SOFT":     "#a8b3b8",
    "CANVAS":       "#212121",
    "SURFACE":      "#2a2a2a",
    "BORDER":       "#3a3a3a",
    "ACCENT":       "#80cbc4",
    "ACCENT_DK":    "#80cbc4",
    "ON_ACCENT":    "#121c1b",
    "AMBER_BG":     "#453c2d",
    "AMBER_TX":     "#ffcb6b",
    "BUILD_BG":     "#3b4132",
    "BUILD_TX":     "#c3e88d",
    "FIX_BG":       "#45292e",
    "FIX_TX":       "#ff6780",
    "SEL_BG":       "#364645",
    "HOVER_BG":     "#3e3f3f",
    "LIST_BG":      "#1b1b1b",
    "BTN_BG":       "#3e3f3f",
    "BTN_BORDER":   "#577774",
    "BTN_HOVER":    "#4b4e4e",
    "BTN_PRESSED":  "#5b5f5f",
    "CREATE_HOVER": "#94d3cd",
    "DELETE_BG":    "#ff5370",
    "DELETE_HOVER": "#ff6881",
    "MISSING":      "#ff5370",
    "DISABLED_BG":  "#2a2a2a",
    "DISABLED_TX":  "#5e6365",
    "NEUTRAL_BG":   "#333435",
    "NEUTRAL_TX":   "#a8b3b8",
    "SHADOW":       "#66000000",
}


# Minimal
MINIMAL_LIGHT = {
    "INK":          "#222222",
    "INK_SOFT":     "#6b6b6b",
    "CANVAS":       "#f7f7f7",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e3e3e3",
    "ACCENT":       "#705dcf",
    "ACCENT_DK":    "#705dcf",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e6dcc6",
    "AMBER_TX":     "#7a5910",
    "BUILD_BG":     "#cee0cf",
    "BUILD_TX":     "#2d692f",
    "FIX_BG":       "#edd0cd",
    "FIX_TX":       "#a2362e",
    "SEL_BG":       "#e4e1f1",
    "HOVER_BG":     "#f4f4f4",
    "LIST_BG":      "#f0f0f0",
    "BTN_BG":       "#f5f4fc",
    "BTN_BORDER":   "#b3abdb",
    "BTN_HOVER":    "#eae7f8",
    "BTN_PRESSED":  "#ddd8f3",
    "CREATE_HOVER": "#5e4eae",
    "DELETE_BG":    "#c8443a",
    "DELETE_HOVER": "#b03c33",
    "MISSING":      "#c8443a",
    "DISABLED_BG":  "#e9e9e9",
    "DISABLED_TX":  "#b9b9b9",
    "NEUTRAL_BG":   "#e4e4e4",
    "NEUTRAL_TX":   "#626262",
    "SHADOW":       "#2e131313",
}

MINIMAL_DARK = {
    "INK":          "#dadada",
    "INK_SOFT":     "#a0a0a0",
    "CANVAS":       "#1e1e1e",
    "SURFACE":      "#262626",
    "BORDER":       "#363636",
    "ACCENT":       "#a48cf2",
    "ACCENT_DK":    "#a48cf2",
    "ON_ACCENT":    "#171422",
    "AMBER_BG":     "#3c3628",
    "AMBER_TX":     "#d9b45e",
    "BUILD_BG":     "#2e392f",
    "BUILD_TX":     "#85c98a",
    "FIX_BG":       "#3f2d2b",
    "FIX_TX":       "#ef7a70",
    "SEL_BG":       "#3b364d",
    "HOVER_BG":     "#383838",
    "LIST_BG":      "#171717",
    "BTN_BG":       "#383838",
    "BTN_BORDER":   "#645a85",
    "BTN_HOVER":    "#454545",
    "BTN_PRESSED":  "#535353",
    "CREATE_HOVER": "#b39ef4",
    "DELETE_BG":    "#ef7a70",
    "DELETE_HOVER": "#f18a81",
    "MISSING":      "#ef7a70",
    "DISABLED_BG":  "#262626",
    "DISABLED_TX":  "#585858",
    "NEUTRAL_BG":   "#2f2f2f",
    "NEUTRAL_TX":   "#a0a0a0",
    "SHADOW":       "#66000000",
}


# Monokai
MONOKAI_LIGHT = {
    "INK":          "#2c232e",
    "INK_SOFT":     "#6c6367",
    "CANVAS":       "#f8efe7",
    "SURFACE":      "#fdf7f1",
    "BORDER":       "#e2d6c8",
    "ACCENT":       "#187c94",
    "ACCENT_DK":    "#16748c",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#eed5b6",
    "AMBER_TX":     "#864f0a",
    "BUILD_BG":     "#caddcb",
    "BUILD_TX":     "#186745",
    "FIX_BG":       "#efcacd",
    "FIX_TX":       "#983352",
    "SEL_BG":       "#d9dfdb",
    "HOVER_BG":     "#f3ece7",
    "LIST_BG":      "#efe4d8",
    "BTN_BG":       "#edeeea",
    "BTN_BORDER":   "#8db0b2",
    "BTN_HOVER":    "#dbe5e3",
    "BTN_PRESSED":  "#c6d9db",
    "CREATE_HOVER": "#14687c",
    "DELETE_BG":    "#c8456d",
    "DELETE_HOVER": "#b03d60",
    "MISSING":      "#ce4770",
    "DISABLED_BG":  "#ebe2db",
    "DISABLED_TX":  "#bcb3b0",
    "NEUTRAL_BG":   "#e5dcd6",
    "NEUTRAL_TX":   "#665d61",
    "SHADOW":       "#2e181319",
}

MONOKAI_DARK = {
    "INK":          "#f8f8f2",
    "INK_SOFT":     "#a9a795",
    "CANVAS":       "#272822",
    "SURFACE":      "#31322c",
    "BORDER":       "#414339",
    "ACCENT":       "#66d9ef",
    "ACCENT_DK":    "#66d9ef",
    "ON_ACCENT":    "#0e1e21",
    "AMBER_BG":     "#46452f",
    "AMBER_TX":     "#e6db74",
    "BUILD_BG":     "#3b4624",
    "BUILD_TX":     "#a6e22e",
    "FIX_BG":       "#49282f",
    "FIX_TX":       "#f9699d",
    "SEL_BG":       "#354f4f",
    "HOVER_BG":     "#454640",
    "LIST_BG":      "#1e1f1a",
    "BTN_BG":       "#454640",
    "BTN_BORDER":   "#518285",
    "BTN_HOVER":    "#53544e",
    "BTN_PRESSED":  "#63645e",
    "CREATE_HOVER": "#7edff2",
    "DELETE_BG":    "#f9337a",
    "DELETE_HOVER": "#fa4b8a",
    "MISSING":      "#f92672",
    "DISABLED_BG":  "#31322c",
    "DISABLED_TX":  "#626156",
    "NEUTRAL_BG":   "#383931",
    "NEUTRAL_TX":   "#a9a795",
    "SHADOW":       "#66000000",
}


# Night Owl
NIGHT_OWL_LIGHT = {
    "INK":          "#403f53",
    "INK_SOFT":     "#676c7c",
    "CANVAS":       "#fbfbfb",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e0e0e0",
    "ACCENT":       "#446fca",
    "ACCENT_DK":    "#446fca",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#f4e9c4",
    "AMBER_TX":     "#7e6301",
    "BUILD_BG":     "#cde7e5",
    "BUILD_TX":     "#1d6d67",
    "FIX_BG":       "#f5d1d1",
    "FIX_TX":       "#a92e2d",
    "SEL_BG":       "#e1e7f4",
    "HOVER_BG":     "#f5f5f6",
    "LIST_BG":      "#f1f1f1",
    "BTN_BG":       "#f2f5fb",
    "BTN_BORDER":   "#9eb1d7",
    "BTN_HOVER":    "#e3e9f7",
    "BTN_PRESSED":  "#d2dcf2",
    "CREATE_HOVER": "#395daa",
    "DELETE_BG":    "#d13937",
    "DELETE_HOVER": "#b83230",
    "MISSING":      "#de3d3b",
    "DISABLED_BG":  "#edeef0",
    "DISABLED_TX":  "#bec1c9",
    "NEUTRAL_BG":   "#e8e9eb",
    "NEUTRAL_TX":   "#616674",
    "SHADOW":       "#2e23232e",
}

NIGHT_OWL_DARK = {
    "INK":          "#d6deeb",
    "INK_SOFT":     "#93a8b5",
    "CANVAS":       "#011627",
    "SURFACE":      "#0b2942",
    "BORDER":       "#1d3b53",
    "ACCENT":       "#82aaff",
    "ACCENT_DK":    "#82aaff",
    "ON_ACCENT":    "#121824",
    "AMBER_BG":     "#273237",
    "AMBER_TX":     "#ecc48d",
    "BUILD_BG":     "#1d3631",
    "BUILD_TX":     "#addb67",
    "FIX_BG":       "#27202e",
    "FIX_TX":       "#ef5855",
    "SEL_BG":       "#1d3757",
    "HOVER_BG":     "#1f3b53",
    "LIST_BG":      "#01111d",
    "BTN_BG":       "#1f3b53",
    "BTN_BORDER":   "#476a9b",
    "BTN_HOVER":    "#2e485f",
    "BTN_PRESSED":  "#3e566c",
    "CREATE_HOVER": "#96b8ff",
    "DELETE_BG":    "#ef5350",
    "DELETE_HOVER": "#f16865",
    "MISSING":      "#ef5350",
    "DISABLED_BG":  "#0b2942",
    "DISABLED_TX":  "#435867",
    "NEUTRAL_BG":   "#142939",
    "NEUTRAL_TX":   "#93a8b5",
    "SHADOW":       "#66000000",
}


# Nord
NORD_LIGHT = {
    "INK":          "#2e3440",
    "INK_SOFT":     "#4c566a",
    "CANVAS":       "#eceff4",
    "SURFACE":      "#ffffff",
    "BORDER":       "#d8dee9",
    "ACCENT":       "#55759d",
    "ACCENT_DK":    "#4e6b8f",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e4ddcf",
    "AMBER_TX":     "#745c2d",
    "BUILD_BG":     "#d4ddd6",
    "BUILD_TX":     "#4f6344",
    "FIX_BG":       "#e2d0d6",
    "FIX_TX":       "#89464c",
    "SEL_BG":       "#d7dee8",
    "HOVER_BG":     "#f5f5f5",
    "LIST_BG":      "#e5e9f0",
    "BTN_BG":       "#f3f5f8",
    "BTN_BORDER":   "#a1b2c9",
    "BTN_HOVER":    "#e6eaf0",
    "BTN_PRESSED":  "#d6dee7",
    "CREATE_HOVER": "#476284",
    "DELETE_BG":    "#ae5861",
    "DELETE_HOVER": "#994d55",
    "MISSING":      "#bf616a",
    "DISABLED_BG":  "#dce0e6",
    "DISABLED_TX":  "#a4aab6",
    "NEUTRAL_BG":   "#d6dae1",
    "NEUTRAL_TX":   "#4c566a",
    "SHADOW":       "#2e191d23",
}

NORD_DARK = {
    "INK":          "#eceff4",
    "INK_SOFT":     "#c3cbd8",
    "CANVAS":       "#2e3440",
    "SURFACE":      "#3b4252",
    "BORDER":       "#434c5e",
    "ACCENT":       "#88c0d0",
    "ACCENT_DK":    "#88c0d0",
    "ON_ACCENT":    "#131b1d",
    "AMBER_BG":     "#4c4c4c",
    "AMBER_TX":     "#ebcb8b",
    "BUILD_BG":     "#414a4c",
    "BUILD_TX":     "#a9c292",
    "FIX_BG":       "#453b47",
    "FIX_TX":       "#d69da3",
    "SEL_BG":       "#425360",
    "HOVER_BG":     "#4d5362",
    "LIST_BG":      "#292e39",
    "BTN_BG":       "#4d5362",
    "BTN_BORDER":   "#607d8e",
    "BTN_HOVER":    "#595f6e",
    "BTN_PRESSED":  "#626875",
    "CREATE_HOVER": "#9bcad8",
    "DELETE_BG":    "#c36b72",
    "DELETE_HOVER": "#ca7d83",
    "MISSING":      "#bf616a",
    "DISABLED_BG":  "#3b4252",
    "DISABLED_TX":  "#717884",
    "NEUTRAL_BG":   "#414854",
    "NEUTRAL_TX":   "#c3cbd8",
    "SHADOW":       "#66000000",
}


# One
ONE_LIGHT = {
    "INK":          "#383a42",
    "INK_SOFT":     "#666973",
    "CANVAS":       "#fafafa",
    "SURFACE":      "#ffffff",
    "BORDER":       "#e5e5e6",
    "ACCENT":       "#3a6edd",
    "ACCENT_DK":    "#386bd6",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#ede0c3",
    "AMBER_TX":     "#825901",
    "BUILD_BG":     "#d5e6d4",
    "BUILD_TX":     "#366c35",
    "FIX_BG":       "#f5d6d3",
    "FIX_TX":       "#a33f33",
    "SEL_BG":       "#dfe6f6",
    "HOVER_BG":     "#f5f5f6",
    "LIST_BG":      "#f0f0f0",
    "BTN_BG":       "#f1f5fd",
    "BTN_BORDER":   "#9db3e2",
    "BTN_HOVER":    "#e1e9fa",
    "BTN_PRESSED":  "#d0dcf7",
    "CREATE_HOVER": "#315cba",
    "DELETE_BG":    "#c44b3f",
    "DELETE_HOVER": "#ac4237",
    "MISSING":      "#e45649",
    "DISABLED_BG":  "#ececed",
    "DISABLED_TX":  "#b9babf",
    "NEUTRAL_BG":   "#e6e6e8",
    "NEUTRAL_TX":   "#60636d",
    "SHADOW":       "#2e1f2024",
}

ONE_DARK = {
    "INK":          "#abb2bf",
    "INK_SOFT":     "#97a0b0",
    "CANVAS":       "#282c34",
    "SURFACE":      "#31353f",
    "BORDER":       "#3e4451",
    "ACCENT":       "#61afef",
    "ACCENT_DK":    "#61afef",
    "ON_ACCENT":    "#0e1921",
    "AMBER_BG":     "#46443f",
    "AMBER_TX":     "#e5c07b",
    "BUILD_BG":     "#3a443f",
    "BUILD_TX":     "#98c379",
    "FIX_BG":       "#45363e",
    "FIX_TX":       "#e88c93",
    "SEL_BG":       "#334557",
    "HOVER_BG":     "#3d424c",
    "LIST_BG":      "#21252b",
    "BTN_BG":       "#3d424c",
    "BTN_BORDER":   "#4d7193",
    "BTN_HOVER":    "#3e424c",
    "BTN_PRESSED":  "#3f434d",
    "CREATE_HOVER": "#7abcf2",
    "DELETE_BG":    "#e06c75",
    "DELETE_HOVER": "#e47e86",
    "MISSING":      "#e06c75",
    "DISABLED_BG":  "#31353f",
    "DISABLED_TX":  "#555b67",
    "NEUTRAL_BG":   "#353a43",
    "NEUTRAL_TX":   "#9da6b4",
    "SHADOW":       "#66000000",
}


# Rosé Pine
ROSE_PINE_LIGHT = {
    "INK":          "#575279",
    "INK_SOFT":     "#68657f",
    "CANVAS":       "#faf4ed",
    "SURFACE":      "#fffaf3",
    "BORDER":       "#e3d9d1",
    "ACCENT":       "#806c95",
    "ACCENT_DK":    "#78668d",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#f6e1c4",
    "AMBER_TX":     "#885b20",
    "BUILD_BG":     "#ccd5d6",
    "BUILD_TX":     "#256077",
    "FIX_BG":       "#ebd4d4",
    "FIX_TX":       "#86495a",
    "SEL_BG":       "#e9e1e1",
    "HOVER_BG":     "#f7f2ed",
    "LIST_BG":      "#f2e9e1",
    "BTN_BG":       "#f6f0ec",
    "BTN_BORDER":   "#b9abb8",
    "BTN_HOVER":    "#ece5e5",
    "BTN_PRESSED":  "#e1d8dc",
    "CREATE_HOVER": "#6c5b7d",
    "DELETE_BG":    "#aa5d72",
    "DELETE_HOVER": "#965264",
    "MISSING":      "#b4637a",
    "DISABLED_BG":  "#ede7e4",
    "DISABLED_TX":  "#c0bbc5",
    "NEUTRAL_BG":   "#e8e2e0",
    "NEUTRAL_TX":   "#625f77",
    "SHADOW":       "#2e302d43",
}

ROSE_PINE_DARK = {
    "INK":          "#e0def4",
    "INK_SOFT":     "#a5a1bd",
    "CANVAS":       "#191724",
    "SURFACE":      "#1f1d2e",
    "BORDER":       "#26233a",
    "ACCENT":       "#c4a7e7",
    "ACCENT_DK":    "#c4a7e7",
    "ON_ACCENT":    "#1b1720",
    "AMBER_BG":     "#3c3231",
    "AMBER_TX":     "#f6c177",
    "BUILD_BG":     "#2e3441",
    "BUILD_TX":     "#9ccfd8",
    "FIX_BG":       "#3b2536",
    "FIX_TX":       "#eb6f92",
    "SEL_BG":       "#3f374f",
    "HOVER_BG":     "#323042",
    "LIST_BG":      "#16141f",
    "BTN_BG":       "#323042",
    "BTN_BORDER":   "#685a83",
    "BTN_HOVER":    "#403e50",
    "BTN_PRESSED":  "#4f4d60",
    "CREATE_HOVER": "#cdb5eb",
    "DELETE_BG":    "#eb6f92",
    "DELETE_HOVER": "#ed809f",
    "MISSING":      "#eb6f92",
    "DISABLED_BG":  "#1f1d2e",
    "DISABLED_TX":  "#585569",
    "NEUTRAL_BG":   "#2b2938",
    "NEUTRAL_TX":   "#a5a1bd",
    "SHADOW":       "#66000000",
}


# Soft Paper
SOFT_PAPER_LIGHT = {
    "INK":          "#423b31",
    "INK_SOFT":     "#685f52",
    "CANVAS":       "#efe9dd",
    "SURFACE":      "#f8f4ea",
    "BORDER":       "#d8cfbc",
    "ACCENT":       "#7d6b52",
    "ACCENT_DK":    "#75654e",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#dcd1b5",
    "AMBER_TX":     "#6b551c",
    "BUILD_BG":     "#cfd1bd",
    "BUILD_TX":     "#475d38",
    "FIX_BG":       "#dfc5b9",
    "FIX_TX":       "#8c382f",
    "SEL_BG":       "#dfd7ca",
    "HOVER_BG":     "#efebe1",
    "LIST_BG":      "#e6dfd0",
    "BTN_BG":       "#efeadf",
    "BTN_BORDER":   "#b2a58f",
    "BTN_HOVER":    "#e6dfd3",
    "BTN_PRESSED":  "#dad3c6",
    "CREATE_HOVER": "#695a45",
    "DELETE_BG":    "#a8443a",
    "DELETE_HOVER": "#943c33",
    "MISSING":      "#a8443a",
    "DISABLED_BG":  "#e2dcd0",
    "DISABLED_TX":  "#b5aea1",
    "NEUTRAL_BG":   "#ddd7ca",
    "NEUTRAL_TX":   "#62594e",
    "SHADOW":       "#2e24201b",
}

SOFT_PAPER_DARK = {
    "INK":          "#e6ddcb",
    "INK_SOFT":     "#b3a894",
    "CANVAS":       "#242018",
    "SURFACE":      "#2e2920",
    "BORDER":       "#3d3629",
    "ACCENT":       "#c2a878",
    "ACCENT_DK":    "#c2a878",
    "ON_ACCENT":    "#1b1811",
    "AMBER_BG":     "#413a28",
    "AMBER_TX":     "#dcc07a",
    "BUILD_BG":     "#393a2a",
    "BUILD_TX":     "#a8c08a",
    "FIX_BG":       "#423128",
    "FIX_TX":       "#e08b7f",
    "SEL_BG":       "#473e2d",
    "HOVER_BG":     "#403b31",
    "LIST_BG":      "#1d1a14",
    "BTN_BG":       "#403b31",
    "BTN_BORDER":   "#75664a",
    "BTN_HOVER":    "#4d483d",
    "BTN_PRESSED":  "#5c564b",
    "CREATE_HOVER": "#ccb68e",
    "DELETE_BG":    "#e08b7f",
    "DELETE_HOVER": "#e4998e",
    "MISSING":      "#e08b7f",
    "DISABLED_BG":  "#2e2920",
    "DISABLED_TX":  "#645d50",
    "NEUTRAL_BG":   "#373228",
    "NEUTRAL_TX":   "#b3a894",
    "SHADOW":       "#66000000",
}


# Solarized
SOLARIZED_LIGHT = {
    "INK":          "#073642",
    "INK_SOFT":     "#586e75",
    "CANVAS":       "#fdf6e3",
    "SURFACE":      "#fffcf2",
    "BORDER":       "#e6dfc8",
    "ACCENT":       "#2177b4",
    "ACCENT_DK":    "#2073af",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#eddeb1",
    "AMBER_TX":     "#7a5c00",
    "BUILD_BG":     "#e3e2b1",
    "BUILD_TX":     "#596800",
    "FIX_BG":       "#f6cbbb",
    "FIX_TX":       "#a82826",
    "SEL_BG":       "#dee4dc",
    "HOVER_BG":     "#f3f2e9",
    "LIST_BG":      "#f7f0dc",
    "BTN_BG":       "#eff3ee",
    "BTN_BORDER":   "#93b3c0",
    "BTN_HOVER":    "#dee8e9",
    "BTN_PRESSED":  "#cadce3",
    "CREATE_HOVER": "#1c6497",
    "DELETE_BG":    "#dc322f",
    "DELETE_HOVER": "#c22c29",
    "MISSING":      "#dc322f",
    "DISABLED_BG":  "#ede8d8",
    "DISABLED_TX":  "#b3b9b2",
    "NEUTRAL_BG":   "#e6e3d4",
    "NEUTRAL_TX":   "#50656b",
    "SHADOW":       "#2e041e24",
}

SOLARIZED_DARK = {
    "INK":          "#eee8d5",
    "INK_SOFT":     "#93a1a1",
    "CANVAS":       "#002b36",
    "SURFACE":      "#073642",
    "BORDER":       "#12414e",
    "ACCENT":       "#268bd2",
    "ACCENT_DK":    "#55a3da",
    "ON_ACCENT":    "#05131d",
    "AMBER_BG":     "#1d3a2d",
    "AMBER_TX":     "#c19c2b",
    "BUILD_BG":     "#153d2d",
    "BUILD_TX":     "#99ab2b",
    "FIX_BG":       "#232c35",
    "FIX_TX":       "#e8716f",
    "SEL_BG":       "#084058",
    "HOVER_BG":     "#1e4851",
    "LIST_BG":      "#00252f",
    "BTN_BG":       "#1e4851",
    "BTN_BORDER":   "#1a6085",
    "BTN_HOVER":    "#2e545b",
    "BTN_PRESSED":  "#416267",
    "CREATE_HOVER": "#499ed9",
    "DELETE_BG":    "#e04a47",
    "DELETE_HOVER": "#e4605d",
    "MISSING":      "#dc322f",
    "DISABLED_BG":  "#073642",
    "DISABLED_TX":  "#426066",
    "NEUTRAL_BG":   "#133a44",
    "NEUTRAL_TX":   "#96a4a4",
    "SHADOW":       "#66000000",
}


# Tokyo Night
TOKYO_NIGHT_LIGHT = {
    "INK":          "#343b58",
    "INK_SOFT":     "#515b8c",
    "CANVAS":       "#e1e2e7",
    "SURFACE":      "#f0f0f5",
    "BORDER":       "#c4c8da",
    "ACCENT":       "#2b71d4",
    "ACCENT_DK":    "#2662b6",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#cec8c2",
    "AMBER_TX":     "#654d2c",
    "BUILD_BG":     "#c3cac1",
    "BUILD_TX":     "#44592c",
    "FIX_BG":       "#e5baca",
    "FIX_TX":       "#9b1b41",
    "SEL_BG":       "#c8d2e4",
    "HOVER_BG":     "#e7e7ed",
    "LIST_BG":      "#d9dae0",
    "BTN_BG":       "#e2e7f3",
    "BTN_BORDER":   "#84a3d7",
    "BTN_HOVER":    "#d2ddf0",
    "BTN_PRESSED":  "#c1d2ed",
    "CREATE_HOVER": "#245fb2",
    "DELETE_BG":    "#d92659",
    "DELETE_HOVER": "#bf214e",
    "MISSING":      "#f52a65",
    "DISABLED_BG":  "#d4d5df",
    "DISABLED_TX":  "#a4a9c4",
    "NEUTRAL_BG":   "#ced0dc",
    "NEUTRAL_TX":   "#4d5584",
    "SHADOW":       "#2e1d2030",
}

TOKYO_NIGHT_DARK = {
    "INK":          "#c0caf5",
    "INK_SOFT":     "#9aa5ce",
    "CANVAS":       "#1a1b26",
    "SURFACE":      "#24283b",
    "BORDER":       "#2f334d",
    "ACCENT":       "#7aa2f7",
    "ACCENT_DK":    "#7aa2f7",
    "ON_ACCENT":    "#111723",
    "AMBER_BG":     "#3a3331",
    "AMBER_TX":     "#e0af68",
    "BUILD_BG":     "#2f3831",
    "BUILD_TX":     "#9ece6a",
    "FIX_BG":       "#3d2a37",
    "FIX_TX":       "#f7768e",
    "SEL_BG":       "#2f3954",
    "HOVER_BG":     "#34384e",
    "LIST_BG":      "#16161e",
    "BTN_BG":       "#34384e",
    "BTN_BORDER":   "#4e6294",
    "BTN_HOVER":    "#3f445b",
    "BTN_PRESSED":  "#4b506a",
    "CREATE_HOVER": "#8fb1f8",
    "DELETE_BG":    "#f7768e",
    "DELETE_HOVER": "#f8869c",
    "MISSING":      "#f7768e",
    "DISABLED_BG":  "#24283b",
    "DISABLED_TX":  "#545972",
    "NEUTRAL_BG":   "#2b2d3c",
    "NEUTRAL_TX":   "#9aa5ce",
    "SHADOW":       "#66000000",
}


# Wikipedia
WIKIPEDIA_LIGHT = {
    "INK":          "#202122",
    "INK_SOFT":     "#54595d",
    "CANVAS":       "#f8f9fa",
    "SURFACE":      "#ffffff",
    "BORDER":       "#c8ccd1",
    "ACCENT":       "#3366cc",
    "ACCENT_DK":    "#3366cc",
    "ON_ACCENT":    "#ffffff",
    "AMBER_BG":     "#e7d9c3",
    "AMBER_TX":     "#874f00",
    "BUILD_BG":     "#c6e0db",
    "BUILD_TX":     "#106955",
    "FIX_BG":       "#f1cdce",
    "FIX_TX":       "#a92a2a",
    "SEL_BG":       "#dce4f4",
    "HOVER_BG":     "#f4f4f4",
    "LIST_BG":      "#eaecf0",
    "BTN_BG":       "#f1f4fb",
    "BTN_BORDER":   "#89a1cf",
    "BTN_HOVER":    "#e0e8f7",
    "BTN_PRESSED":  "#cedaf3",
    "CREATE_HOVER": "#2b56ab",
    "DELETE_BG":    "#d73333",
    "DELETE_HOVER": "#bd2d2d",
    "MISSING":      "#d73333",
    "DISABLED_BG":  "#e8e9ea",
    "DISABLED_TX":  "#aeb1b3",
    "NEUTRAL_BG":   "#e1e3e4",
    "NEUTRAL_TX":   "#54595d",
    "SHADOW":       "#2e121213",
}

WIKIPEDIA_DARK = {
    "INK":          "#eaecf0",
    "INK_SOFT":     "#a2a9b1",
    "CANVAS":       "#101418",
    "SURFACE":      "#27292d",
    "BORDER":       "#43464a",
    "ACCENT":       "#88a3e8",
    "ACCENT_DK":    "#88a3e8",
    "ON_ACCENT":    "#131720",
    "AMBER_BG":     "#312b16",
    "AMBER_TX":     "#dfa30b",
    "BUILD_BG":     "#162c2a",
    "BUILD_TX":     "#34ad86",
    "FIX_BG":       "#362424",
    "FIX_TX":       "#fd7865",
    "SEL_BG":       "#2a3346",
    "HOVER_BG":     "#3a3c40",
    "LIST_BG":      "#0b0e11",
    "BTN_BG":       "#3a3c40",
    "BTN_BORDER":   "#606d8c",
    "BTN_HOVER":    "#484a4e",
    "BTN_PRESSED":  "#585a5e",
    "CREATE_HOVER": "#9bb2ec",
    "DELETE_BG":    "#fd7865",
    "DELETE_HOVER": "#fd8877",
    "MISSING":      "#fd7865",
    "DISABLED_BG":  "#27292d",
    "DISABLED_TX":  "#52575d",
    "NEUTRAL_BG":   "#23272c",
    "NEUTRAL_TX":   "#a2a9b1",
    "SHADOW":       "#66000000",
}

# The registry. A name here is what config.local.json stores and what
# set_scheme() takes.
SCHEMES: dict[str, dict[str, str]] = {
    "warm_light": WARM_LIGHT,
    "warm_dark": WARM_DARK,
    "cool_light": COOL_LIGHT,
    "cool_dark": COOL_DARK,
    "ayu_light": AYU_LIGHT,
    "ayu_dark": AYU_DARK,
    "blue_topaz_light": BLUE_TOPAZ_LIGHT,
    "blue_topaz_dark": BLUE_TOPAZ_DARK,
    "catppuccin_light": CATPPUCCIN_LIGHT,
    "catppuccin_dark": CATPPUCCIN_DARK,
    "dracula_light": DRACULA_LIGHT,
    "dracula_dark": DRACULA_DARK,
    "everforest_light": EVERFOREST_LIGHT,
    "everforest_dark": EVERFOREST_DARK,
    "github_light": GITHUB_LIGHT,
    "github_dark": GITHUB_DARK,
    "gruvbox_light": GRUVBOX_LIGHT,
    "gruvbox_dark": GRUVBOX_DARK,
    "horizon_light": HORIZON_LIGHT,
    "horizon_dark": HORIZON_DARK,
    "ia_writer_light": IA_WRITER_LIGHT,
    "ia_writer_dark": IA_WRITER_DARK,
    "kanagawa_light": KANAGAWA_LIGHT,
    "kanagawa_dark": KANAGAWA_DARK,
    "material_light": MATERIAL_LIGHT,
    "material_dark": MATERIAL_DARK,
    "minimal_light": MINIMAL_LIGHT,
    "minimal_dark": MINIMAL_DARK,
    "monokai_light": MONOKAI_LIGHT,
    "monokai_dark": MONOKAI_DARK,
    "night_owl_light": NIGHT_OWL_LIGHT,
    "night_owl_dark": NIGHT_OWL_DARK,
    "nord_light": NORD_LIGHT,
    "nord_dark": NORD_DARK,
    "one_light": ONE_LIGHT,
    "one_dark": ONE_DARK,
    "rose_pine_light": ROSE_PINE_LIGHT,
    "rose_pine_dark": ROSE_PINE_DARK,
    "soft_paper_light": SOFT_PAPER_LIGHT,
    "soft_paper_dark": SOFT_PAPER_DARK,
    "solarized_light": SOLARIZED_LIGHT,
    "solarized_dark": SOLARIZED_DARK,
    "tokyo_night_light": TOKYO_NIGHT_LIGHT,
    "tokyo_night_dark": TOKYO_NIGHT_DARK,
    "wikipedia_light": WIKIPEDIA_LIGHT,
    "wikipedia_dark": WIKIPEDIA_DARK,
}

# A theme is a (light, dark) pair of scheme names. A theme whose dark member is
# None goes dark nowhere, and every resolver draws its light palette instead.
THEMES: dict[str, tuple[str, str | None]] = {
    "warm": ("warm_light", "warm_dark"),
    "cool": ("cool_light", "cool_dark"),
    "ayu": ("ayu_light", "ayu_dark"),
    "blue_topaz": ("blue_topaz_light", "blue_topaz_dark"),
    "catppuccin": ("catppuccin_light", "catppuccin_dark"),
    "dracula": ("dracula_light", "dracula_dark"),
    "everforest": ("everforest_light", "everforest_dark"),
    "github": ("github_light", "github_dark"),
    "gruvbox": ("gruvbox_light", "gruvbox_dark"),
    "horizon": ("horizon_light", "horizon_dark"),
    "ia_writer": ("ia_writer_light", "ia_writer_dark"),
    "kanagawa": ("kanagawa_light", "kanagawa_dark"),
    "material": ("material_light", "material_dark"),
    "minimal": ("minimal_light", "minimal_dark"),
    "monokai": ("monokai_light", "monokai_dark"),
    "night_owl": ("night_owl_light", "night_owl_dark"),
    "nord": ("nord_light", "nord_dark"),
    "one": ("one_light", "one_dark"),
    "rose_pine": ("rose_pine_light", "rose_pine_dark"),
    "soft_paper": ("soft_paper_light", "soft_paper_dark"),
    "solarized": ("solarized_light", "solarized_dark"),
    "tokyo_night": ("tokyo_night_light", "tokyo_night_dark"),
    "wikipedia": ("wikipedia_light", "wikipedia_dark"),
}

# The scheme whose key set defines a complete palette, and the fallback for a
# name the config asks for and this build does not have.
REFERENCE_SCHEME = "warm_light"
DEFAULT_THEME = "warm"

# The palette every other one is completed against. It is a copy rather than a
# lookup into ``SCHEMES``, because deleting Pumpkin takes ``warm_light`` out of
# ``SCHEMES`` and every completion after that would have nothing to read.
REFERENCE_PALETTE: dict[str, str] = dict(WARM_LIGHT)

# The palette a dark half is seeded and completed against. A dark half filled
# from the light reference is the half-lit palette a dark half is turned on
# whole to avoid, so each half completes against its own kind.
REFERENCE_DARK_PALETTE: dict[str, str] = dict(WARM_DARK)

# Which half of a theme is drawn. SYSTEM_MODE follows the OS; the other two pin
# one half whatever the OS is set to.
LIGHT_MODE = "light"
DARK_MODE = "dark"
SYSTEM_MODE = "system"
DEFAULT_MODE = SYSTEM_MODE

# What this build calls each theme it ships. The value is the theme's id, which
# is what a stored choice names; the caption is the name on screen. The two are
# deliberately separate — a theme can be renamed without migrating a stored
# choice. What the Settings picker offers is the collection rather than this
# list: ``theme_choices()`` is what builds it.
THEME_CHOICES: list[tuple[str, str]] = [
    ("ayu", "Ayu"),
    ("blue_topaz", "Blue Topaz"),
    ("catppuccin", "Catppuccin"),
    ("dracula", "Dracula"),
    ("everforest", "Everforest"),
    ("cool", "Frosty"),
    ("github", "GitHub"),
    ("gruvbox", "Gruvbox"),
    ("horizon", "Horizon"),
    ("ia_writer", "iA Writer"),
    ("kanagawa", "Kanagawa"),
    ("material", "Material"),
    ("minimal", "Minimal"),
    ("monokai", "Monokai"),
    ("night_owl", "Night Owl"),
    ("nord", "Nord"),
    ("one", "One"),
    ("warm", "Pumpkin"),
    ("rose_pine", "Rosé Pine"),
    ("soft_paper", "Soft Paper"),
    ("solarized", "Solarized"),
    ("tokyo_night", "Tokyo Night"),
    ("wikipedia", "Wikipedia"),
]

# What this build ships, held apart from the live SCHEMES and THEMES, which the
# collection rewrites. Restore Shipped Themes reads these, so an edit the user
# makes can always be undone against what the build actually defines.
_SHIPPED_SCHEMES: dict[str, dict[str, str]] = {
    name: dict(palette) for name, palette in SCHEMES.items()
}
_SHIPPED_THEMES: dict[str, tuple[str, str | None]] = dict(THEMES)

MODE_CHOICES: list[tuple[str, str]] = [
    (LIGHT_MODE, "Light"),
    (DARK_MODE, "Dark"),
    (SYSTEM_MODE, "Follow System"),
]

# What a mode the theme in force cannot offer says when the pointer rests on it.
NO_DARK_HALF = "This theme has no dark colours yet."

# What a build before the theme and the mode were separate controls stored in
# one key, and the theme and mode each of its values named. A configuration
# written by such a build comes up as the appearance it named.
LEGACY_APPEARANCE: dict[str, tuple[str, str]] = {
    "warm": ("warm", SYSTEM_MODE),
    "warm_light": ("warm", LIGHT_MODE),
    "warm_dark": ("warm", DARK_MODE),
    "cool": ("cool", SYSTEM_MODE),
    "cool_light": ("cool", LIGHT_MODE),
    "cool_dark": ("cool", DARK_MODE),
    "custom": ("custom", LIGHT_MODE),
}

# The id and the name a palette built when the picker offered one Custom option
# comes back as. Such a palette joins the collection as an ordinary theme, so
# nothing about it is a special case once it is there.
LEGACY_CUSTOM_THEME = "custom"
LEGACY_CUSTOM_NAME = "Custom"

# A palette form's rows, in the order it offers them: a heading, then the keys
# it groups. A key the reference scheme carries and no group names still gets a
# field, under the last heading — ``palette_rows()`` is what places it.
KEY_GROUPS: list[tuple[str, list[str]]] = [
    ("Text", ["INK", "INK_SOFT"]),
    ("Surfaces", ["CANVAS", "SURFACE", "LIST_BG", "BORDER", "SHADOW"]),
    ("Accent", ["ACCENT", "ACCENT_DK", "ON_ACCENT"]),
    ("Cards", ["SEL_BG", "HOVER_BG"]),
    ("Badges", ["AMBER_BG", "AMBER_TX", "BUILD_BG", "BUILD_TX",
                "FIX_BG", "FIX_TX", "NEUTRAL_BG", "NEUTRAL_TX"]),
    ("Buttons", ["BTN_BG", "BTN_BORDER", "BTN_HOVER", "BTN_PRESSED",
                 "CREATE_HOVER", "DELETE_BG", "DELETE_HOVER",
                 "DISABLED_BG", "DISABLED_TX", "MISSING"]),
]

# What each key is called on a palette form's rows. A caption names the thing
# the colour lands on, so a row can be read without the styling contract open.
KEY_CAPTIONS: dict[str, str] = {
    "INK": "Primary Text",
    "INK_SOFT": "Secondary Text",
    "CANVAS": "Window Background",
    "SURFACE": "Card Surface",
    "LIST_BG": "Recessed List",
    "BORDER": "Hairline Border",
    "SHADOW": "Card Shadow",
    "ACCENT": "Accent",
    "ACCENT_DK": "Accent Text",
    "ON_ACCENT": "Text on Accent",
    "SEL_BG": "Selected Card",
    "HOVER_BG": "Hovered Card",
    "AMBER_BG": "Epic Badge",
    "AMBER_TX": "Epic Badge Text",
    "BUILD_BG": "Build Pill",
    "BUILD_TX": "Build Pill Text",
    "FIX_BG": "Fix Pill",
    "FIX_TX": "Fix Pill Text",
    "NEUTRAL_BG": "Quiet Pill",
    "NEUTRAL_TX": "Quiet Pill Text",
    "BTN_BG": "Button",
    "BTN_BORDER": "Button Border",
    "BTN_HOVER": "Button Hovered",
    "BTN_PRESSED": "Button Pressed",
    "CREATE_HOVER": "Primary Button Hovered",
    "DELETE_BG": "Delete Button",
    "DELETE_HOVER": "Delete Button Hovered",
    "DISABLED_BG": "Unclickable Button",
    "DISABLED_TX": "Unclickable Button Text",
    "MISSING": "Empty Required Field",
}

# Text that has to be read, over the surface it is read on. Every shipped scheme
# clears CONTRAST_MIN on every pair here, so a palette that does not is one the
# builder names rather than one this product ships.
#
# The unclickable pair is deliberately absent: text a control greys out is meant
# to be hard to read, and every shipped scheme puts it near 2:1.
TEXT_PAIRS: list[tuple[str, str]] = [
    ("INK", "CANVAS"), ("INK", "SURFACE"), ("INK", "LIST_BG"),
    ("INK", "SEL_BG"), ("INK", "HOVER_BG"),
    ("INK", "BTN_BG"), ("INK", "BTN_HOVER"), ("INK", "BTN_PRESSED"),
    ("INK_SOFT", "CANVAS"), ("INK_SOFT", "SURFACE"), ("INK_SOFT", "LIST_BG"),
    ("ON_ACCENT", "ACCENT"), ("ON_ACCENT", "DELETE_BG"),
    ("ACCENT_DK", "SURFACE"), ("ACCENT_DK", "CANVAS"),
    ("AMBER_TX", "AMBER_BG"), ("BUILD_TX", "BUILD_BG"), ("FIX_TX", "FIX_BG"),
    ("NEUTRAL_TX", "NEUTRAL_BG"),
]

# The ratio a pair above has to reach. WCAG AA for body text.
CONTRAST_MIN = 4.5

# The single live palette every consumer reads from. Starts at the reference
# scheme; the app calls set_scheme() at startup, on every OS colour-scheme
# change, and whenever the choice is edited in Settings.
C: dict[str, str] = dict(REFERENCE_PALETTE)

_current_scheme = REFERENCE_SCHEME


def theme_has_dark(theme: str | None) -> bool:
    """True when this theme has a dark half to draw."""
    return bool(THEMES.get(theme or "", (None, None))[1])


def default_theme() -> str:
    """The theme a choice falls back to.

    This build's default where the collection still holds it, and the first
    theme in the collection where it does not: a user who deletes Pumpkin is
    left with a fallback rather than with none.
    """
    if DEFAULT_THEME in THEMES:
        return DEFAULT_THEME
    return next(iter(THEMES), DEFAULT_THEME)


def resolve_scheme(theme: str | None, mode: str | None, dark: bool) -> str:
    """The scheme name a theme and a mode mean right now.

    ``system`` resolves against the OS state and the other two modes pin one
    half. A theme with no dark half draws its light one whatever either says,
    which is what makes such a theme an ordinary choice rather than a broken
    one. An unknown theme falls back to the default.
    """
    fallback = THEMES.get(default_theme(), (REFERENCE_SCHEME, None))
    light, dark_member = THEMES.get(theme or "", fallback)
    if dark_member and (mode == DARK_MODE or (mode == SYSTEM_MODE and dark)):
        return dark_member
    return light


def appearance_choice(theme, mode, legacy) -> tuple[str, str]:
    """The theme and mode in force, from the three values config can hold.

    The two current keys win where they name a theme the collection holds.
    Where they do not, the one key an older build wrote is read for the theme
    and mode it named. Where neither answers, the default.
    """
    modes = {name for name, _caption in MODE_CHOICES}
    if isinstance(theme, str) and theme in THEMES:
        return theme, mode if isinstance(mode, str) and mode in modes else DEFAULT_MODE
    if isinstance(legacy, str) and legacy in LEGACY_APPEARANCE:
        named, named_mode = LEGACY_APPEARANCE[legacy]
        if named in THEMES:
            return named, named_mode
    return default_theme(), DEFAULT_MODE


def set_scheme(name: str) -> None:
    """Point the live palette ``C`` at a named scheme, in place, so existing
    ``from .theme import C`` references keep seeing current values.

    A key the named scheme is missing is filled from the reference palette, so
    an incomplete palette shows the wrong colour rather than raising mid-paint.
    ``check_schemes()`` is what names such a gap.
    """
    global _current_scheme
    scheme = SCHEMES.get(name)
    if scheme is None:
        name = resolve_scheme(default_theme(), LIGHT_MODE, False)
        scheme = SCHEMES.get(name, REFERENCE_PALETTE)
    _current_scheme = name
    C.clear()
    C.update(REFERENCE_PALETTE)
    C.update(scheme)


def apply_scheme(app, theme: str | None, mode: str | None,
                 stored: dict | None = None,
                 legacy_custom: dict | None = None) -> None:
    """Install the collection, resolve a theme and a mode against the OS state,
    make the scheme live, and style ``app``.

    Every window the application opens is styled by this one call, so it runs
    before the first window is built rather than inside any of them.

    ``stored`` is the differences the configuration carries and ``legacy_custom``
    the palette a build that offered one Custom option wrote. Both go in first,
    because a stored choice can name a theme only the collection has.
    """
    register_collection(stored, legacy_custom)
    set_scheme(resolve_scheme(
        theme, mode, is_dark_scheme(app) if app is not None else False))
    if app is not None:
        app.setStyleSheet(build_style_sheet())


# ---------------------------------------------------------------------------
# The collection: which themes this installation offers
#
# A theme is a record — a name, a light palette, and a dark palette or None —
# under an id that never changes. The configuration carries only the
# differences from what the build ships: the themes the user added, the names
# he deleted, and a palette stored under a shipped theme's name where he
# changed one. An installation that has touched nothing stores nothing, which
# is what lets a later release's new themes reach it.
# ---------------------------------------------------------------------------

def _complete(palette: dict | None, dark: bool = False) -> dict[str, str]:
    """``palette`` with every key the reference palette defines, its own values
    winning. A value that is not a colour string is dropped, so nothing
    unpaintable reaches a scheme. A dark half is completed against the dark
    reference, so a key it does not carry comes back dark."""
    usable = {key: value for key, value in (palette or {}).items()
              if isinstance(key, str) and isinstance(value, str) and value.strip()}
    complete = dict(REFERENCE_DARK_PALETTE if dark else REFERENCE_PALETTE)
    complete.update({key: value for key, value in usable.items()
                     if key in complete})
    return complete


def shipped_collection() -> dict[str, dict]:
    """Every theme this build ships, as records. Restore Shipped Themes puts
    exactly this back."""
    captions = dict(THEME_CHOICES)
    return {
        theme_id: {
            "name": captions.get(theme_id, theme_id.replace("_", " ").title()),
            "light": dict(_SHIPPED_SCHEMES[light]),
            "dark": dict(_SHIPPED_SCHEMES[dark]) if dark else None,
        }
        for theme_id, (light, dark) in _SHIPPED_THEMES.items()
    }


def _baseline(legacy_custom: dict | None = None) -> dict[str, dict]:
    """What the differences are measured against: the shipped themes, and the
    one palette an older build stored outside them."""
    collection = shipped_collection()
    if (isinstance(legacy_custom, dict) and legacy_custom
            and LEGACY_CUSTOM_THEME not in collection):
        collection[LEGACY_CUSTOM_THEME] = {
            "name": LEGACY_CUSTOM_NAME,
            "light": _complete(legacy_custom),
            "dark": None,
        }
    return collection


def _stored_record(raw, fallback_name: str) -> dict | None:
    """One stored theme as a record, or None where it is not one."""
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    dark = raw.get("dark")
    return {
        "name": name.strip() if isinstance(name, str) and name.strip()
                else fallback_name,
        "light": _complete(raw.get("light")),
        "dark": (_complete(dark, dark=True)
                 if isinstance(dark, dict) and dark else None),
    }


def resolve_collection(stored: dict | None = None,
                       legacy_custom: dict | None = None) -> dict[str, dict]:
    """The themes on offer: what this build ships, with the differences the
    configuration carries applied, ordered by name.

    A collection that came out empty is the shipped one, because an app with no
    theme has nothing to draw.
    """
    stored = stored if isinstance(stored, dict) else {}
    deleted = {name for name in stored.get("deleted", [])
               if isinstance(name, str)}
    edited = stored.get("edited")
    edited = edited if isinstance(edited, dict) else {}
    added = stored.get("added")
    added = added if isinstance(added, dict) else {}

    collection: dict[str, dict] = {}
    for theme_id, record in _baseline(legacy_custom).items():
        if theme_id in deleted:
            continue
        change = edited.get(theme_id)
        if isinstance(change, dict):
            name = change.get("name")
            if isinstance(name, str) and name.strip():
                record["name"] = name.strip()
            if isinstance(change.get("light"), dict):
                record["light"] = _complete(change["light"])
            if "dark" in change:
                half = change["dark"]
                record["dark"] = (_complete(half, dark=True)
                                  if isinstance(half, dict) and half else None)
        collection[theme_id] = record

    for theme_id, raw in added.items():
        if not isinstance(theme_id, str) or theme_id in collection:
            continue
        record = _stored_record(raw, theme_id.replace("_", " ").title())
        if record is not None:
            collection[theme_id] = record

    if not collection:
        collection = _baseline(legacy_custom)
    return order_collection(collection)


def order_collection(collection: dict[str, dict]) -> dict[str, dict]:
    """The collection by name, which is the order a picker holding two dozen of
    them is read in: scan to the letter."""
    return {theme_id: collection[theme_id] for theme_id in sorted(
        collection, key=lambda key: (collection[key]["name"].casefold(), key))}


def collection_differences(collection: dict[str, dict],
                           legacy_custom: dict | None = None) -> dict:
    """What the configuration stores for ``collection``: the themes added, the
    changes to shipped ones, and the shipped names deleted. A theme nobody has
    touched appears in none of them."""
    baseline = _baseline(legacy_custom)
    added: dict[str, dict] = {}
    edited: dict[str, dict] = {}
    for theme_id, record in collection.items():
        base = baseline.get(theme_id)
        if base is None:
            added[theme_id] = {
                "name": record["name"],
                "light": dict(record["light"]),
                "dark": dict(record["dark"]) if record["dark"] else None,
            }
            continue
        change: dict = {}
        if record["name"] != base["name"]:
            change["name"] = record["name"]
        if record["light"] != base["light"]:
            change["light"] = dict(record["light"])
        if record["dark"] != base["dark"]:
            change["dark"] = dict(record["dark"]) if record["dark"] else None
        if change:
            edited[theme_id] = change
    deleted = sorted(theme_id for theme_id in baseline
                     if theme_id not in collection)
    difference: dict = {}
    if added:
        difference["added"] = added
    if edited:
        difference["edited"] = edited
    if deleted:
        difference["deleted"] = deleted
    return difference


def install_collection(collection: dict[str, dict]) -> dict[str, dict]:
    """Make ``collection`` the themes this app draws from: one scheme per half,
    named for the theme it belongs to, and one ``THEMES`` pair per theme.

    Every resolver, the completeness check and the stylesheet read ``SCHEMES``
    and ``THEMES``, so a theme the user built is one of them from here on and
    no path has a case for it.
    """
    SCHEMES.clear()
    THEMES.clear()
    for theme_id, record in collection.items():
        light_name = f"{theme_id}_light"
        SCHEMES[light_name] = _complete(record["light"])
        dark_name = None
        if record.get("dark"):
            dark_name = f"{theme_id}_dark"
            SCHEMES[dark_name] = _complete(record["dark"], dark=True)
        THEMES[theme_id] = (light_name, dark_name)
    return collection


def register_collection(stored: dict | None = None,
                        legacy_custom: dict | None = None) -> dict[str, dict]:
    """Resolve the stored differences and install what they come to."""
    return install_collection(resolve_collection(stored, legacy_custom))


def theme_choices(collection: dict[str, dict]) -> list[tuple[str, str]]:
    """What the Theme picker offers: each theme's id and its name, in the
    collection's own order."""
    return [(theme_id, record["name"])
            for theme_id, record in collection.items()]


def theme_id_for(name: str, taken) -> str:
    """A stable id for a theme just named, unused among ``taken``.

    The name changes afterwards and this does not: what the configuration
    stores as the theme in force is the id, so a rename never has to migrate a
    stored choice.
    """
    base = re.sub(r"[^a-z0-9]+", "_", name.strip().casefold()).strip("_")
    candidate = base or "theme"
    suffix = 2
    while candidate in taken:
        candidate = f"{base or 'theme'}_{suffix}"
        suffix += 1
    return candidate


def palette_rows() -> list[tuple[str, list[str]]]:
    """A palette form: a heading and the keys under it, covering every key the
    reference palette defines.

    A key no group names is appended to the last heading rather than left out,
    so a palette gaining a key gains a field with no edit here.
    """
    grouped = {key for _, keys in KEY_GROUPS for key in keys}
    rows = [(heading, [key for key in keys if key in REFERENCE_PALETTE])
            for heading, keys in KEY_GROUPS]
    loose = [key for key in REFERENCE_PALETTE if key not in grouped]
    if loose:
        rows[-1] = (rows[-1][0], rows[-1][1] + loose)
    return rows


def key_caption(key: str) -> str:
    """What a palette key is called on screen. A key with no caption reads as
    itself, so a palette gaining a key is still editable."""
    return KEY_CAPTIONS.get(key, key.replace("_", " ").title())


def _relative_luminance(colour: str) -> float:
    """The WCAG relative luminance of a ``#RRGGBB`` or ``#AARRGGBB`` colour.

    An alpha channel is ignored: what a translucent colour actually reads
    against depends on what is behind it, and the pairs checked here are opaque.
    """
    digits = colour.strip().lstrip("#")
    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) != 6:
        raise ValueError(f"not a colour: {colour!r}")
    channels = []
    for start in (0, 2, 4):
        value = int(digits[start:start + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928
                        else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """How far apart two colours read, on the WCAG 1:1 to 21:1 scale."""
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def readable_on(background: str) -> str:
    """Black or white, whichever reads further from ``background``.

    The one colour in this product not taken from a scheme. A palette being
    edited is previewed live, so the line naming what is unreadable is drawn in
    the palette that broke it; this is what keeps that one line legible. Falls
    back to the live ink for a value that is not a colour.
    """
    try:
        light = contrast_ratio("#ffffff", background)
        dark = contrast_ratio("#000000", background)
    except ValueError:
        return C["INK"]
    return "#ffffff" if light > dark else "#000000"


def contrast_complaints(palette: dict) -> list[str]:
    """Every pair in ``TEXT_PAIRS`` that ``palette`` puts under ``CONTRAST_MIN``,
    as readable lines naming both sides and the ratio.

    Empty means every pair reads. A pair either side of which is missing or
    unparseable is skipped: an incomplete palette is ``check_schemes()``'s to
    name, and a field mid-edit is the form's.
    """
    complaints = []
    for foreground, background in TEXT_PAIRS:
        try:
            ratio = contrast_ratio(palette[foreground], palette[background])
        except (KeyError, ValueError):
            continue
        if ratio < CONTRAST_MIN:
            complaints.append(
                f"{key_caption(foreground)} on {key_caption(background)} "
                f"reads at {ratio:.1f}:1, under {CONTRAST_MIN}:1"
            )
    return complaints


def current_scheme() -> str:
    """The scheme name ``C`` currently holds."""
    return _current_scheme


def check_schemes() -> list[str]:
    """Every key one scheme carries and another does not, as readable lines.

    Empty means every scheme is complete against the union of all of them.
    """
    every_key = set()
    for palette in SCHEMES.values():
        every_key.update(palette)
    complaints = []
    for name in sorted(SCHEMES):
        missing = sorted(every_key - set(SCHEMES[name]))
        if missing:
            complaints.append(f"{name} is missing: {', '.join(missing)}")
    for name, pair in sorted(THEMES.items()):
        for member in pair:
            if member is not None and member not in SCHEMES:
                complaints.append(f"theme {name} names {member}, which is not a scheme")
    return complaints


def is_dark_scheme(app) -> bool:
    """True when the OS colour scheme is Dark, and False wherever that cannot
    be read."""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def chevron_image(colour: str, direction: str = "down") -> str | None:
    """A chevron in the given colour and direction (``down`` or ``up``), as a
    cached image file the stylesheet can point a combo box's or spin box's
    arrow at. Returns None when nothing can be written, in which case the
    arrow rule is left out.
    """
    try:
        from PySide6.QtCore import QDir
        from PySide6.QtGui import QPainter, QPen, QPixmap

        folder = Path(QDir.tempPath()) / "bristol_tickets_ui"
        target = folder / f"chevron_{direction}_{colour.lstrip('#')}.png"
        if target.exists():
            return str(target)
        folder.mkdir(parents=True, exist_ok=True)

        width, height = space("lg"), space("md")
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            pen = QPen(QColor(colour), 1.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            inset = 1
            if direction == "up":
                painter.drawLine(inset, height - inset, width // 2, inset)
                painter.drawLine(width // 2, inset, width - inset, height - inset)
            else:
                painter.drawLine(inset, inset, width // 2, height - inset)
                painter.drawLine(width // 2, height - inset, width - inset, inset)
        finally:
            painter.end()
        return str(target) if pixmap.save(str(target)) else None
    except Exception:  # noqa: BLE001 — an arrow is never worth failing a paint
        return None


def check_image(colour: str) -> str | None:
    """A check mark in the given colour, as a cached image file the stylesheet
    points a checked checkbox indicator at. Returns None when nothing can be
    written, in which case the checked state is a plain accent fill."""
    try:
        from PySide6.QtCore import QDir
        from PySide6.QtGui import QPainter, QPen, QPixmap

        folder = Path(QDir.tempPath()) / "bristol_tickets_ui"
        target = folder / f"check_{colour.lstrip('#')}.png"
        if target.exists():
            return str(target)
        folder.mkdir(parents=True, exist_ok=True)

        side = space("md")
        pixmap = QPixmap(side, side)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.Antialiasing, True)
            pen = QPen(QColor(colour), 1.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            inset = 1
            elbow = side * 2 // 5
            painter.drawLine(inset, side * 3 // 5, elbow, side - inset)
            painter.drawLine(elbow, side - inset, side - inset, inset)
        finally:
            painter.end()
        return str(target) if pixmap.save(str(target)) else None
    except Exception:  # noqa: BLE001 — a tick is never worth failing a paint
        return None


def build_style_sheet() -> str:
    """Render the global Qt stylesheet from the live palette ``C`` and the token
    scales, so a scheme swap and a token change both reach every styled widget."""
    r_sm, r_md, r_lg = radius("sm"), radius("md"), radius("lg")
    chevron = chevron_image(C["INK_SOFT"])
    chevron_up = chevron_image(C["INK_SOFT"], "up")
    check = check_image(C["ON_ACCENT"])
    arrow_rule = (f"QComboBox::down-arrow {{ image: url({chevron}); "
                  f"width: {space('lg')}px; height: {space('md')}px; }}"
                  if chevron else "")
    spin_arrow_rule = (
        f"QSpinBox::up-arrow {{ image: url({chevron_up}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}\n"
        f"QSpinBox::down-arrow {{ image: url({chevron}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}"
        if chevron and chevron_up else "")
    check_rule = f"image: url({check});" if check else ""
    s_xs, s_sm, s_md, s_lg, s_xl, s_2xl = (space("xs"), space("sm"), space("md"),
                                           space("lg"), space("xl"), space("2xl"))
    return f"""
QMainWindow, QWidget#leftContainer, QDialog {{
    background-color: {C['CANVAS']};
    color: {C['INK']};
}}
QSplitter::handle {{
    background-color: {C['CANVAS']};
}}
/* The header bar: one full-width strip carrying identity, the agent selector,
   the view tabs and Create, closed by a single hairline. */
QWidget#appHeader {{
    background-color: {C['CANVAS']};
    border-bottom: 1px solid {C['BORDER']};
}}
QLabel#appIdentity {{
    color: {C['INK']};
    font-size: {type_size('section')}pt;
    font-weight: 700;
}}
QFrame#headerRule {{ background-color: {C['BORDER']}; border: none; }}
/* A view tab is text on the canvas: hover changes its state, and the selected
   one is carried by weight and an accent underline rather than a fill. */
QPushButton#viewTab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0px;
    padding: {s_md}px {s_lg}px;
    margin: 0px {s_xs}px;
    color: {C['INK_SOFT']};
    font-weight: 600;
}}
QPushButton#viewTab:hover {{
    background-color: {C['HOVER_BG']};
    color: {C['INK']};
}}
QPushButton#viewTab:checked {{
    color: {C['ACCENT']};
    border-bottom: 2px solid {C['ACCENT']};
    font-weight: 700;
}}
QGroupBox {{
    font-weight: 600;
    border: 1px solid {C['BORDER']};
    border-radius: {r_lg}px;
    background-color: {C['SURFACE']};
    margin-top: {s_xl}px;
    padding: {s_lg}px;
    color: {C['INK']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: {s_xl}px;
    padding: 0 {s_md}px;
    color: {C['ACCENT']};
}}
QListWidget {{
    background-color: {C['LIST_BG']};
    border: 1px solid {C['BORDER']};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
    outline: 0;
}}
/* A board column is a region of the canvas, not a container: the cards are the
   only raised surfaces on the view, so the well they sit in has no fill and no
   border of its own. */
QListWidget#columnCards {{
    background: transparent;
    border: none;
    padding: 0px;
}}
QLabel#columnName {{
    color: {C['INK']};
    font-size: {type_size('title')}pt;
    font-weight: 700;
}}
QLabel#columnCount {{ color: {C['INK_SOFT']}; }}
/* The detail pane is a sidebar surface: the one raised region right of the
   splitter, separated from the board canvas by a hairline. */
QWidget#detailPane {{
    background-color: {C['SURFACE']};
    border-left: 1px solid {C['BORDER']};
}}
QScrollArea#detailScroll, QScrollArea#detailScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
/* The hairline under a section header in the detail pane. */
QFrame#sectionRule {{ background-color: {C['BORDER']}; border: none; }}
/* The pane's collapse control, and the strip that brings it back: both quiet
   glyphs that only gain a surface on hover. */
QPushButton#paneToggle, QPushButton#paneReveal {{
    background: transparent;
    border: none;
    border-radius: {r_md}px;
    padding: {s_xs}px {s_md}px;
    color: {C['INK_SOFT']};
    font-weight: 700;
}}
QPushButton#paneToggle:hover, QPushButton#paneReveal:hover {{
    background-color: {C['HOVER_BG']};
    color: {C['INK']};
}}
QPushButton#paneReveal {{
    border-left: 1px solid {C['BORDER']};
    border-radius: 0px;
}}
/* A path the user may need to find on disk reads as a path. */
QLabel#pathRow {{
    background-color: {C['LIST_BG']};
    border: 1px solid {C['BORDER']};
    border-radius: {r_md}px;
    padding: {s_md}px {s_lg}px;
    color: {C['INK_SOFT']};
    font-family: Menlo, Consolas, monospace;
    font-size: {type_size('body')}pt;
}}
QLabel#formCaption {{ color: {C['INK_SOFT']}; }}
/* The filter panel: one raised surface under the Filter button, holding a
   section per facet and one row per option. A row is a whole click target, so
   it takes the pointer fill a card does. */
QFrame#filterMenu {{
    background-color: {C['SURFACE']};
    border: 1px solid {C['BORDER']};
    border-radius: {r_lg}px;
}}
QLabel#filterTitle {{
    color: {C['INK']};
    font-size: {type_size('section')}pt;
    font-weight: 700;
}}
QLabel#facetHeading {{
    color: {C['INK_SOFT']};
    font-size: {type_size('caption')}pt;
    font-weight: 700;
}}
QWidget#facetRow {{ border-radius: {r_md}px; }}
QWidget#facetRow:hover {{ background-color: {C['HOVER_BG']}; }}
QLabel#facetCount {{ color: {C['INK_SOFT']}; }}
QScrollArea#filterScroll, QScrollArea#filterScroll > QWidget > QWidget,
QScrollArea#paletteScroll, QScrollArea#paletteScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
/* A text action inside a panel or a control row: no surface of its own. */
QPushButton#filterClear {{
    background: transparent;
    border: none;
    padding: {s_xs}px {s_md}px;
    color: {C['ACCENT']};
    font-weight: 600;
}}
QPushButton#filterClear:hover {{
    color: {C['ACCENT_DK']};
    text-decoration: underline;
}}
QPushButton#filterClear:disabled {{
    color: {C['DISABLED_TX']};
    text-decoration: none;
}}
/* The Filter button takes the accent while it is holding something back, so a
   narrowed board never reads as an empty one. */
QPushButton#filterBtn[active="true"] {{
    background-color: {C['SEL_BG']};
    border: 1px solid {C['ACCENT']};
    color: {C['ACCENT_DK']};
}}
/* One applied filter, removable where it is read. */
QPushButton#filterChip {{
    background-color: {C['NEUTRAL_BG']};
    color: {C['NEUTRAL_TX']};
    border: none;
    border-radius: {radius('pill')}px;
    padding: {s_sm}px {s_lg}px;
    font-weight: 600;
}}
QPushButton#filterChip:hover {{
    background-color: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
/* A scroll bar is chrome: a slim handle on an empty groove, so a column that
   overflows does not gain a heavy black rail down its edge. */
QScrollBar:vertical {{
    background: transparent;
    width: {s_lg}px;
    margin: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {s_lg}px;
    margin: 0px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {C['BORDER']};
    border-radius: {r_sm}px;
    min-height: {s_2xl}px;
    min-width: {s_2xl}px;
}}
QScrollBar::handle:hover {{ background: {C['INK_SOFT']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
/* The setup wizard is the same application: the ground it draws on, the type
   its pages are titled in, and the buttons it is driven by all come from here. */
QWizard {{ background-color: {C['CANVAS']}; }}
/* Direct children only: the header band, the page container and the button
   row. A field inside a page is not matched, so the input rules still win. */
QWizard > QWidget {{ background-color: {C['CANVAS']}; }}
QWizardPage {{ background-color: {C['CANVAS']}; }}
QWizardPage > QLabel {{ font-size: {type_size('body')}pt; }}

QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: transparent; }}
/* Search results and the theme list are plain text items (not
   delegate-painted cards), so the transparent-selection rule above would leave
   them with the palette's highlighted-text colour on a light fill —
   near-invisible. Give these lists a visible selected fill and the brightest
   accent the board uses for text. */
QListWidget#searchResults::item, QListWidget#themeList::item {{
    padding: {s_md}px {s_lg}px;
    border-radius: {r_md}px;
}}
QListWidget#searchResults::item:selected, QListWidget#themeList::item:selected {{
    background: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
QListWidget#searchResults::item:hover, QListWidget#themeList::item:hover {{
    background: {C['HOVER_BG']};
}}
QComboBox, QLineEdit, QSpinBox, QTextEdit {{
    background-color: {C['SURFACE']};
    border: 1px solid {C['BORDER']};
    border-radius: {r_md}px;
    padding: {s_md}px {s_md}px;
    color: {C['INK']};
    selection-background-color: {C['ACCENT']};
    selection-color: {C['ON_ACCENT']};
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {C['ACCENT']};
}}
/* A required field that is currently empty. Set via the dynamic property
   fieldMissing=true (see record_dialog._refresh_required_state), and repeated
   for :focus so the accent border does not paint over the warning while the
   user is typing in — or deleting out of — the very field that is missing. */
QLineEdit[fieldMissing="true"], QTextEdit[fieldMissing="true"],
QLineEdit[fieldMissing="true"]:focus, QTextEdit[fieldMissing="true"]:focus {{
    border: 2px solid {C['MISSING']};
}}
QLabel[fieldMissing="true"] {{ color: {C['MISSING']}; font-weight: 600; }}
/* A formCaption carries its own missing state. */
QLabel#formCaption[fieldMissing="true"] {{ color: {C['MISSING']}; font-weight: 600; }}
QComboBox QAbstractItemView {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BORDER']};
    selection-background-color: {C['ACCENT']};
    selection-color: {C['ON_ACCENT']};
}}
/* A picker reads as a picker: the drop-down carries a chevron of its own. */
QComboBox::drop-down {{
    border: none;
    width: {s_2xl}px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
{arrow_rule}
/* The spin box steps with the same chevrons every picker carries, drawn
   inside the field. */
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: padding;
    width: {s_2xl}px;
    border: none;
    background: transparent;
}}
QSpinBox::up-button {{ subcontrol-position: top right; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; }}
{spin_arrow_rule}
QLabel {{ color: {C['INK']}; background: transparent; }}
QLabel#inspectorTitle {{ color: {C['ACCENT']}; }}
QLabel#sectionHeader {{ color: {C['INK_SOFT']}; font-weight: 600; }}
/* The one thing a confirmation or a notice says first: the largest text in a
   modal that carries no icon, since the words are all it has. */
QLabel#dialogHeading {{
    color: {C['INK']};
    font-size: {type_size('section')}pt;
    font-weight: 700;
}}
QLabel#metaText {{ color: {C['INK_SOFT']}; }}
/* A link row is a quiet reference, not a headline: left-aligned accent text
   at body scale and normal weight, underlined on hover so it is obviously
   clickable — it must never out-weigh the section header above it. */
QPushButton#linkRow {{
    background: transparent;
    border: none;
    padding: {s_xs}px 0px;
    text-align: left;
    color: {C['ACCENT']};
    font-size: {type_size('body')}pt;
    font-weight: 400;
}}
QPushButton#linkRow:hover {{ color: {C['ACCENT_DK']}; text-decoration: underline; }}
/* The ✕ that removes a link or attachment: the ordinary button face, minus
   the wide padding that would clip the mark inside its narrow fixed square. */
QPushButton#attachRemoveBtn {{ padding: {s_xs}px 0px; }}
/* A link row that is not clickable (a pending link on an unsaved ticket). */
QLabel#linkRowText {{ color: {C['INK_SOFT']}; font-size: {type_size('body')}pt; }}
QCheckBox {{ color: {C['INK']}; background: transparent; }}
/* The checkbox is the scheme's own control: a surface with a hairline, an
   accent fill when checked — never the platform's indicator. */
QCheckBox::indicator {{
    width: {s_lg}px;
    height: {s_lg}px;
    border: 1px solid {C['BORDER']};
    border-radius: {r_sm}px;
    background-color: {C['SURFACE']};
}}
QCheckBox::indicator:hover {{ border-color: {C['ACCENT']}; }}
QCheckBox::indicator:checked {{
    background-color: {C['ACCENT']};
    border-color: {C['ACCENT']};
    {check_rule}
}}
QMenu {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BORDER']};
    border-radius: {r_md}px;
    padding: {s_sm}px;
}}
QMenu::item {{ padding: {s_md}px {s_xl}px {s_md}px {s_lg}px; border-radius: {r_md}px; }}
QMenu::item:selected {{ background-color: {C['SEL_BG']}; color: {C['ACCENT_DK']}; }}
QMenu::separator {{ height: 1px; background: {C['BORDER']}; margin: {s_sm}px {s_md}px; }}
QPushButton {{
    background-color: {C['BTN_BG']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_md}px;
    padding: {s_md}px {s_lg}px;
    font-weight: 600;
    color: {C['ACCENT_DK']};
}}
QPushButton:hover {{ background-color: {C['BTN_HOVER']}; }}
QPushButton:pressed {{ background-color: {C['BTN_PRESSED']}; }}
/* A button held unclickable until its form is valid must LOOK unclickable —
   Qt's default disabled rendering is barely distinguishable under this
   stylesheet, which would read as "the button is broken". */
QPushButton:disabled {{
    background-color: {C['DISABLED_BG']};
    border: 1px solid {C['BORDER']};
    color: {C['DISABLED_TX']};
}}
QPushButton::menu-indicator {{ width: 0px; image: none; }}
QPushButton#globalCreateBtn {{
    background-color: {C['ACCENT']};
    color: {C['ON_ACCENT']};
    border: none;
}}
QPushButton#globalCreateBtn:hover {{ background-color: {C['CREATE_HOVER']}; }}
/* The id selector outranks the generic :disabled rule, so the primary button
   needs its own unclickable look or it would stay accent-filled while dead. */
QPushButton#globalCreateBtn:disabled {{
    background-color: {C['DISABLED_BG']};
    border: 1px solid {C['BORDER']};
    color: {C['DISABLED_TX']};
}}
QPushButton#deleteBtn {{
    background-color: {C['DELETE_BG']};
    color: {C['ON_ACCENT']};
    border: none;
}}
QPushButton#deleteBtn:hover {{ background-color: {C['DELETE_HOVER']}; }}
"""


# ---------------------------------------------------------------------------
# Tiny stateless helpers
# ---------------------------------------------------------------------------
def _mono_font(point_size: int | None = None):
    """A monospace font so mad-lib templates and their fill-in blanks line up in
    the Description editor. Menlo, with a Monospace style hint behind it."""
    from PySide6.QtGui import QFont
    f = QFont("Menlo")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(point_size if point_size is not None else type_size("section"))
    return f


def _is_checked(state) -> bool:
    """True when a Qt.CheckStateRole value is checked, whether it arrives as a
    Qt.CheckState enum or as the raw int 2."""
    if state is None:
        return False
    val = getattr(state, "value", state)
    try:
        return int(val) == 2  # Qt.Checked == 2
    except (TypeError, ValueError):
        return bool(state == Qt.Checked)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_lines(conn, task_id: int, comments: bool = True,
              changes: bool = True) -> list[str]:
    """One ticket's log as display lines, newest first.

    Two kinds share the list: `issue_log` comments, written by a person or an
    agent, and `task_event` changes, written by the database triggers. Each kind
    is toggled by its own checkbox in the views, so this returns whichever were
    asked for, merged in time order.

    A change line carries the field and its new value only; title and
    description changes arrive as '(changed)' from the trigger, so no ticket
    text is ever duplicated into the log.
    """
    entries: list[tuple[str, int, int, str]] = []
    if comments:
        try:
            for row_id, author, body, ts in conn.execute(
                "SELECT id, author, body, created_at FROM issue_log WHERE task_id=?",
                (task_id,),
            ).fetchall():
                entries.append((ts or "", 0, row_id,
                                f"[{_fmt_dt(ts)}] {author}: {body}"))
        except Exception:  # noqa: BLE001 — a missing log must not blank the pane
            pass
    if changes:
        try:
            for row_id, at, actor, field, to_value in conn.execute(
                "SELECT id, at, actor, field, to_value FROM task_event WHERE task_id=?",
                (task_id,),
            ).fetchall():
                entries.append(
                    (at or "", 1, row_id,
                     f"[{_fmt_dt(at)}] {actor or 'unknown'} · {field}: {to_value}")
                )
        except Exception:  # noqa: BLE001
            pass
    # Row id breaks ties: several fields changed by one write share a timestamp,
    # and the newest of them should still sort to the top.
    entries.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [line for _, _, _, line in entries]


def log_entries(conn, task_id: int, comments: bool = True,
                changes: bool = True) -> list[dict]:
    """One ticket's log as structured entries, newest first — what the detail
    pane's timeline renders from. Same two sources and the same merge order as
    ``log_lines``; each entry is a dict:

    * a comment: ``{"kind": "comment", "author", "at", "body"}``
    * a change:  ``{"kind": "change", "author", "at", "field", "value"}``
    """
    rows: list[tuple[str, int, int, dict]] = []
    if comments:
        try:
            for row_id, author, body, ts in conn.execute(
                "SELECT id, author, body, created_at FROM issue_log WHERE task_id=?",
                (task_id,),
            ).fetchall():
                rows.append((ts or "", 0, row_id, {
                    "kind": "comment", "author": author or "unknown",
                    "at": ts, "body": body or ""}))
        except Exception:  # noqa: BLE001 — a missing log must not blank the pane
            pass
    if changes:
        try:
            for row_id, at, actor, field, to_value in conn.execute(
                "SELECT id, at, actor, field, to_value FROM task_event WHERE task_id=?",
                (task_id,),
            ).fetchall():
                rows.append((at or "", 1, row_id, {
                    "kind": "change", "author": actor or "unknown",
                    "at": at, "field": field, "value": to_value}))
        except Exception:  # noqa: BLE001
            pass
    rows.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return [entry for _, _, _, entry in rows]


def relative_time(value: str | None) -> str:
    """A stored ISO timestamp as the distance back it reads from now — "just
    now", "20m ago", "3h ago", "5d ago" — falling back to the compact date once
    it is over a month old, or for a value that does not parse."""
    if not value:
        return "—"
    try:
        then = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return _fmt_dt(value)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - then).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    if seconds < 31 * 86400:
        return f"{int(seconds // 86400)}d ago"
    return _fmt_dt(value)


def _fmt_dt(value: str | None) -> str:
    """Render a stored ISO timestamp as a compact 'YYYY-MM-DD HH:MM' for the
    inspector. Falls back gracefully for missing or non-ISO values."""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(value)[:16]


def _get_epic_badge(epic_name: str, epic_id: int | None) -> str:
    if not epic_name or epic_id is None:
        return ""
    first_letter = epic_name.strip()[0].upper() if epic_name.strip() else "E"
    return f"[{first_letter}{epic_id}] "


def effort_label(code: str | None) -> str:
    """An effort size as a word. An unrecognised or absent code returns the code
    itself, so a board carrying something else still says what it holds."""
    key = (code or "").strip().upper()
    if not key:
        return ""
    return EFFORT_WORDS.get(key, key)
