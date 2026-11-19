"""ui/theme.py — the appearance manager: schemes, design tokens, stylesheet.

This module contains every visual constant the rest of the UI draws with: the
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
currently contains. Because ``C`` is mutated in place, a module that did
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
from PySide6.QtGui import QColor, QPalette

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
    "chief_of_staff",
    "client_services",
    "game_designer",
    "librarian",
    "teaching_assistant",
    "writers_room",
]

# Words a caption leaves lowercase unless they open it, and words it capitalises
# whole. The same rule src/tools/skill_tools/skills.py title_phrase applies to a
# skill's name.
_CAPTION_SMALL = {"a", "an", "the", "and", "but", "or", "nor", "for", "so",
                  "yet", "as", "at", "by", "in", "of", "on", "to", "per",
                  "via", "vs", "with", "from", "into"}
_CAPTION_UPPER = {"ai", "api", "csv", "html", "jd", "pdf", "qa", "ui", "url"}


def agent_caption(slug: str | None) -> str:
    """An agent's slug as a person reads it: chief_of_staff is Chief of Staff,
    qa_engineer is QA Engineer, user is User. The slug is what every control
    stores; this is only what it shows."""
    words = [w for w in (slug or "user").replace("-", "_").split("_") if w]
    out = []
    for i, word in enumerate(words):
        low = word.lower()
        if low in _CAPTION_UPPER:
            out.append(low.upper())
        elif i and low in _CAPTION_SMALL:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def fleet_agents() -> list[str]:
    """'user' and then every agent this installation configures, read from
    config at call time so a new agent is an owner the moment it exists.
    FLEET_AGENTS stands in where no configuration can be read."""
    try:
        import config_file  # bristol-local; absent in a bare import of theme
        slugs = sorted(config_file.agent_slugs())
    except Exception:  # noqa: BLE001 - any failure falls back to the list
        slugs = []
    return ["user", *slugs] if slugs else list(FLEET_AGENTS)


def fill_agents(combo, slugs) -> None:
    """Load a picker with agents: the caption shown, the slug as item data."""
    for slug in slugs:
        combo.addItem(agent_caption(slug), slug)


def select_agent(combo, slug: str | None) -> None:
    """Seat a picker on an agent, adding it where a legacy record carries one
    the list does not, so editing never silently rewrites who owns a card."""
    slug = (slug or "user").strip() or "user"
    index = combo.findData(slug)
    if index < 0:
        combo.addItem(agent_caption(slug), slug)
        index = combo.findData(slug)
    combo.setCurrentIndex(index)


# ---------------------------------------------------------------------------
# Design tokens — spacing, corner radius, type size
# ---------------------------------------------------------------------------
# Three fixed scales. A module needing a gap, a pad, a corner or a font size
# names a step instead of writing a number, so re-tuning the app's density is an
# edit here. Steps are in device-independent pixels, except TYPE, which is in
# points.
SPACE = {"xs": 2, "sm": 4, "md": 7, "lg": 11, "xl": 16, "2xl": 24}
RADIUS = {"sm": 4, "md": 7, "lg": 10, "xl": 12, "pill": 999}
TYPE = {"caption": 10, "body": 13, "title": 13, "section": 15, "display": 17}

# Window geometry, in device-independent pixels, and the splitter's opening
# split. Not a spacing scale — these size the window itself, and a module that
# needs one names it here rather than writing the number.
LAYOUT = {
    "control_h": 34,       # every button, field and picker on a row: one height
    "toolbar_control_h": 28,  # a control in the top bar
    "header_icon": 16,        # an icon in the top bar
    "header_divider_h": 16,   # the hairline between the top bar's groups of views
    "toolbar_box_w": 34,      # an icon button in the top bar
    "header_mark_h": 20,      # the app's mark beside its name in the top bar
    "traffic_lights_tall_w": 80,  # the traffic lights in the tall title bar, and room past them
    "traffic_lights_inset": 11,   # the window's edge to the red light; the top bar's right end keeps the same
    "title_bar_h": 28,        # the Mac's title bar, which the top bar shares
    "traffic_lights_w": 80,   # the close, minimize and zoom buttons, and room past them
    "filter_field_max_w": 420,  # a Filter field, before its pickers
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
    "path_list_min_h": 132,      # a list of declared paths, with its picker
    "path_row_min_h": 40,        # one row in it: a path, its access, its ✕
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

# An epic is a project and ends, or it is the standing workstream and does not.
# `epic.type` carries the difference, and these are the two values written here:
# create_tickets.EPIC_KIND_STANDING is the one that means standing, and every
# other value, including the prose older versions wrote, means project.
EPIC_KIND_CHOICES: list[tuple[str, str]] = [
    ("project", "Project"),
    ("standing", "Standing"),
]

# The vocabulary create_tickets.EPIC_STATUS_CHOICES writes.
EPIC_STATUS_CHOICES: list[tuple[str, str]] = [
    ("not started", "Not Started"),
    ("in progress", "In Progress"),
    ("completed", "Completed"),
    ("on hold", "On Hold"),
]

# A size code as the word a reader who does not know the codes can read.
SIZE_WORDS = {"S": "Small", "M": "Medium", "L": "Large", "XL": "Extra Large"}
SIZE_CHOICES: list[tuple[str, str]] = [("", "Not Sized")] + [
    (code, word) for code, word in SIZE_WORDS.items()
]
SIZE_HINT = (
    "How much of a full usage budget this card would take.\n"
    "Small — under a tenth.    Medium — a tenth to about half.\n"
    "Large — half a budget or more.    Extra Large — more than one; split it."
)

# The depth of processing a card should be worked at. None is not yet rated.
# Mirrors ticket_tools/create_tickets.TIERS; the viewer carries its own copy so
# it depends on no package outside itself. What each tier runs on is config's
# `tiers` key, never this file.
TIER_WORDS = {"max": "Max", "standard": "Standard"}
TIER_CHOICES: list[tuple[str | None, str]] = [(None, "No Tier")] + [
    (code, word) for code, word in TIER_WORDS.items()
]
TIER_HINT = (
    "How much thinking this card needs, whatever its size.\n"
    "Max — the session must work out what right looks like,\n"
    "or a wrong answer would be built on unchecked.\n"
    "Standard — the card already says what right looks like."
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


def control_height() -> int:
    """The one height every button, text field, picker and date field is drawn
    at, so controls sharing a row line up whatever kind each one is."""
    return LAYOUT["control_h"]


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
    "INK_FAINT":    "#796e5d",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#faf6ef",  # app / dialog background
    "SURFACE":      "#fffdf9",  # card / input surface
    "BORDER":       "#e7dcc6",  # hairline borders
    "ACCENT":       "#c2410c",  # primary orange (4.8:1 on CANVAS, 5.2:1 under white)
    "ACCENT_DK":    "#9a3412",  # deeper orange — bright accent text
    "ON_ACCENT":    "#ffffff",  # text and marks drawn on an accent fill
    "BUILD_BG":     "#e4eee6",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#2e5a3d",  # Build record-type pill text (6.7:1 on its tint)
    "FIX_BG":       "#fbe2db",  # Fix record-type pill background (rust)
    "FIX_TX":       "#97301b",  # Fix record-type pill text (6.2:1 on its tint)
    "SEL_BG":       "#fff1e2",  # selected card fill
    "HOVER_BG":     "#fffaf2",  # hovered card fill
    "LIST_BG":      "#fbf6ee",  # kanban list / scroll area background
    "BTN_BG":       "#fff4e8",  # normal button fill
    "BTN_BORDER":   "#b18759",  # the edge of everything that can be clicked
    "BTN_HOVER":    "#ffe9d2",  # button hover fill
    "BTN_PRESSED":  "#ffddb8",  # button pressed fill
    "CREATE_HOVER": "#a83a0b",  # accent (Create) button hover fill
    "DELETE_BG":    "#c53a20",  # destructive button text
    "DELETE_HOVER": "#b03118",  # destructive button text on hover
    "MISSING":      "#d61f1f",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#f3ece0",  # unclickable button fill
    "DISABLED_TX":  "#b3a389",  # unclickable button text
    "NEUTRAL_BG":   "#f0e7d6",  # a quiet pill: size, tier
    "NEUTRAL_TX":   "#574e3b",  # text on a NEUTRAL_BG pill (6.7:1 on its tint)
}

WARM_DARK = {
    "INK":          "#f2e6d5",  # primary text (warm near-white)
    "INK_SOFT":     "#b89f7d",  # secondary text
    "INK_FAINT":    "#988366",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#17120c",  # app / dialog background (deep warm)
    "SURFACE":      "#241c14",  # card / input surface (dark warm)
    "BORDER":       "#463724",  # hairline borders
    "ACCENT":       "#f97316",  # primary orange (brighter for dark)
    "ACCENT_DK":    "#fdba74",  # light orange — bright accent text on dark
    "ON_ACCENT":    "#201409",  # deep warm text on the bright accent (6.4:1)
    "BUILD_BG":     "#1e2a1e",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#8fca9a",  # Build record-type pill text
    "FIX_BG":       "#3a1f18",  # Fix record-type pill background (rust)
    "FIX_TX":       "#f0a58e",  # Fix record-type pill text
    "SEL_BG":       "#3a2914",  # selected card fill
    "HOVER_BG":     "#2a2115",  # hovered card fill
    "LIST_BG":      "#1c160f",  # kanban list / scroll area background
    "BTN_BG":       "#33281b",  # normal button fill
    "BTN_BORDER":   "#806341",  # the edge of everything that can be clicked
    "BTN_HOVER":    "#40311f",  # button hover fill
    "BTN_PRESSED":  "#4a3826",  # button pressed fill
    "CREATE_HOVER": "#fb8b3d",  # accent (Create) button hover fill
    "DELETE_BG":    "#ef6448",  # destructive button text
    "DELETE_HOVER": "#f97255",  # destructive button text on hover
    "MISSING":      "#ff5449",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#241c14",  # unclickable button fill
    "DISABLED_TX":  "#6b5b45",  # unclickable button text
    "NEUTRAL_BG":   "#2f2618",  # a quiet pill: size, tier
    "NEUTRAL_TX":   "#c4ae8e",  # text on a NEUTRAL_BG pill
}

# The cool neutral alternate: grey canvas, white surfaces, a blue accent. Where
# the warm family reads as paper, this one reads as a modern web tool.
COOL_LIGHT = {
    "INK":          "#0f172a",  # primary text (near-black slate)
    "INK_SOFT":     "#5b6779",  # secondary text (4.9:1 on LIST_BG)
    "INK_FAINT":    "#5e6a7c",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#f4f5f7",  # app / dialog background
    "SURFACE":      "#ffffff",  # card / input surface
    "BORDER":       "#e2e8f0",  # hairline borders
    "ACCENT":       "#2563eb",  # primary blue
    "ACCENT_DK":    "#1d4ed8",  # deeper blue — bright accent text
    "ON_ACCENT":    "#ffffff",  # text and marks drawn on an accent fill
    "BUILD_BG":     "#dcfce7",  # Build record-type pill background (green)
    "BUILD_TX":     "#166534",  # Build record-type pill text (6.5:1 on its tint)
    "FIX_BG":       "#fee2e2",  # Fix record-type pill background (red)
    "FIX_TX":       "#991b1b",  # Fix record-type pill text (6.8:1 on its tint)
    "SEL_BG":       "#e8f0fe",  # selected card fill
    "HOVER_BG":     "#f8fafc",  # hovered card fill
    "LIST_BG":      "#ebecf0",  # kanban list / scroll area background
    "BTN_BG":       "#ffffff",  # normal button fill
    "BTN_BORDER":   "#808994",  # the edge of everything that can be clicked
    "BTN_HOVER":    "#f1f5f9",  # button hover fill
    "BTN_PRESSED":  "#e2e8f0",  # button pressed fill
    "CREATE_HOVER": "#1d4ed8",  # accent (Create) button hover fill
    "DELETE_BG":    "#dc2626",  # destructive button text
    "DELETE_HOVER": "#b91c1c",  # destructive button text on hover
    "MISSING":      "#da2324",  # required-but-empty field border
    "DISABLED_BG":  "#f1f5f9",  # unclickable button fill
    "DISABLED_TX":  "#94a3b8",  # unclickable button text
    "NEUTRAL_BG":   "#eef1f5",  # a quiet pill: size, tier
    "NEUTRAL_TX":   "#475569",  # text on a NEUTRAL_BG pill
}

COOL_DARK = {
    "INK":          "#e2e8f0",  # primary text (near-white slate)
    "INK_SOFT":     "#94a3b8",  # secondary text
    "INK_FAINT":    "#7c899b",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#0f1216",  # app / dialog background
    "SURFACE":      "#1a1f26",  # card / input surface
    "BORDER":       "#2c333d",  # hairline borders
    "ACCENT":       "#3b82f6",  # primary blue (brighter for dark)
    "ACCENT_DK":    "#93c5fd",  # light blue — bright accent text on dark
    "ON_ACCENT":    "#0f1216",  # deep slate text on the bright accent (5.1:1)
    "BUILD_BG":     "#14261a",  # Build record-type pill background (green)
    "BUILD_TX":     "#86efac",  # Build record-type pill text
    "FIX_BG":       "#2c1618",  # Fix record-type pill background (red)
    "FIX_TX":       "#fca5a5",  # Fix record-type pill text
    "SEL_BG":       "#1e293b",  # selected card fill
    "HOVER_BG":     "#20262e",  # hovered card fill
    "LIST_BG":      "#14181d",  # kanban list / scroll area background
    "BTN_BG":       "#232a33",  # normal button fill
    "BTN_BORDER":   "#606a77",  # the edge of everything that can be clicked
    "BTN_HOVER":    "#2b333d",  # button hover fill
    "BTN_PRESSED":  "#333c48",  # button pressed fill
    "CREATE_HOVER": "#60a5fa",  # accent (Create) button hover fill
    "DELETE_BG":    "#fe5350",  # destructive button text
    "DELETE_HOVER": "#f87171",  # destructive button text on hover
    "MISSING":      "#f87171",  # required-but-empty field border
    "DISABLED_BG":  "#1a1f26",  # unclickable button fill
    "DISABLED_TX":  "#5b6672",  # unclickable button text
    "NEUTRAL_BG":   "#242b34",  # a quiet pill: size, tier
    "NEUTRAL_TX":   "#b6c0cc",  # text on a NEUTRAL_BG pill
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
    "INK":          "#1f2328",
    "INK_SOFT":     "#656d76",
    "INK_FAINT":    "#656d76",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#f6f8fa",
    "SURFACE":      "#ffffff",
    "BORDER":       "#d0d7de",
    "ACCENT":       "#0969da",
    "ACCENT_DK":    "#0061cf",
    "ON_ACCENT":    "#ffffff",
    "BUILD_BG":     "#c6ddcf",
    "BUILD_TX":     "#146a2e",
    "FIX_BG":       "#edc9cd",
    "FIX_TX":       "#ad1c28",
    "SEL_BG":       "#d5e4f6",
    "HOVER_BG":     "#f4f4f4",
    "LIST_BG":      "#eef1f4",
    "BTN_BG":       "#eef4fc",
    "BTN_BORDER":   "#628ec0",
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
}

GITHUB_DARK = {
    "INK":          "#e6edf3",
    "INK_SOFT":     "#8b949e",
    "INK_FAINT":    "#7d868f",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#0d1117",
    "SURFACE":      "#161b22",
    "BORDER":       "#30363d",
    "ACCENT":       "#58a6ff",
    "ACCENT_DK":    "#58a6ff",
    "ON_ACCENT":    "#0c1724",
    "BUILD_BG":     "#152c20",
    "BUILD_TX":     "#3fb950",
    "FIX_BG":       "#331b1f",
    "FIX_TX":       "#f85149",
    "SEL_BG":       "#1e324a",
    "HOVER_BG":     "#2b3037",
    "LIST_BG":      "#010409",
    "BTN_BG":       "#2b3037",
    "BTN_BORDER":   "#456992",
    "BTN_HOVER":    "#393f46",
    "BTN_PRESSED":  "#4a5056",
    "CREATE_HOVER": "#73b4ff",
    "DELETE_BG":    "#ff6258",
    "DELETE_HOVER": "#ff857c",
    "MISSING":      "#f85149",
    "DISABLED_BG":  "#161b22",
    "DISABLED_TX":  "#464c54",
    "NEUTRAL_BG":   "#1d2229",
    "NEUTRAL_TX":   "#8b949e",
}


# Nord
NORD_LIGHT = {
    "INK":          "#2e3440",
    "INK_SOFT":     "#4c566a",
    "INK_FAINT":    "#5e6779",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#eceff4",
    "SURFACE":      "#ffffff",
    "BORDER":       "#d8dee9",
    "ACCENT":       "#55759d",
    "ACCENT_DK":    "#476487",
    "ON_ACCENT":    "#ffffff",
    "BUILD_BG":     "#d4ddd6",
    "BUILD_TX":     "#4f6344",
    "FIX_BG":       "#e2d0d6",
    "FIX_TX":       "#89464c",
    "SEL_BG":       "#d7dee8",
    "HOVER_BG":     "#f5f5f5",
    "LIST_BG":      "#e5e9f0",
    "BTN_BG":       "#f3f5f8",
    "BTN_BORDER":   "#77879d",
    "BTN_HOVER":    "#e6eaf0",
    "BTN_PRESSED":  "#d6dee7",
    "CREATE_HOVER": "#476284",
    "DELETE_BG":    "#ac565f",
    "DELETE_HOVER": "#994d55",
    "MISSING":      "#ab4f59",
    "DISABLED_BG":  "#dce0e6",
    "DISABLED_TX":  "#a4aab6",
    "NEUTRAL_BG":   "#d6dae1",
    "NEUTRAL_TX":   "#4c566a",
}

NORD_DARK = {
    "INK":          "#eceff4",
    "INK_SOFT":     "#c3cbd8",
    "INK_FAINT":    "#a8b0bd",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#2e3440",
    "SURFACE":      "#3b4252",
    "BORDER":       "#434c5e",
    "ACCENT":       "#88c0d0",
    "ACCENT_DK":    "#93ccdc",
    "ON_ACCENT":    "#131b1d",
    "BUILD_BG":     "#414a4c",
    "BUILD_TX":     "#a9c292",
    "FIX_BG":       "#453b47",
    "FIX_TX":       "#d69da3",
    "SEL_BG":       "#425360",
    "HOVER_BG":     "#4d5362",
    "LIST_BG":      "#292e39",
    "BTN_BG":       "#4d5362",
    "BTN_BORDER":   "#7391a2",
    "BTN_HOVER":    "#595f6e",
    "BTN_PRESSED":  "#626875",
    "CREATE_HOVER": "#9bcad8",
    "DELETE_BG":    "#ffb2b6",
    "DELETE_HOVER": "#ffcdcf",
    "MISSING":      "#f59199",
    "DISABLED_BG":  "#3b4252",
    "DISABLED_TX":  "#717884",
    "NEUTRAL_BG":   "#414854",
    "NEUTRAL_TX":   "#c3cbd8",
}


# Rosé Pine
ROSE_PINE_LIGHT = {
    "INK":          "#575279",
    "INK_SOFT":     "#68657f",
    "INK_FAINT":    "#68657f",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#faf4ed",
    "SURFACE":      "#fffaf3",
    "BORDER":       "#e3d9d1",
    "ACCENT":       "#806c95",
    "ACCENT_DK":    "#705e84",
    "ON_ACCENT":    "#ffffff",
    "BUILD_BG":     "#ccd5d6",
    "BUILD_TX":     "#256077",
    "FIX_BG":       "#ebd4d4",
    "FIX_TX":       "#86495a",
    "SEL_BG":       "#e9e1e1",
    "HOVER_BG":     "#f7f2ed",
    "LIST_BG":      "#f2e9e1",
    "BTN_BG":       "#f6f0ec",
    "BTN_BORDER":   "#90838f",
    "BTN_HOVER":    "#ece5e5",
    "BTN_PRESSED":  "#e1d8dc",
    "CREATE_HOVER": "#6c5b7d",
    "DELETE_BG":    "#a3566b",
    "DELETE_HOVER": "#965264",
    "MISSING":      "#a7586f",
    "DISABLED_BG":  "#ede7e4",
    "DISABLED_TX":  "#c0bbc5",
    "NEUTRAL_BG":   "#e8e2e0",
    "NEUTRAL_TX":   "#625f77",
}

ROSE_PINE_DARK = {
    "INK":          "#e0def4",
    "INK_SOFT":     "#a5a1bd",
    "INK_FAINT":    "#89859e",  # placeholder and example text, 4.5:1 or better
    "CANVAS":       "#191724",
    "SURFACE":      "#1f1d2e",
    "BORDER":       "#26233a",
    "ACCENT":       "#c4a7e7",
    "ACCENT_DK":    "#c4a7e7",
    "ON_ACCENT":    "#1b1720",
    "BUILD_BG":     "#2e3441",
    "BUILD_TX":     "#9ccfd8",
    "FIX_BG":       "#3b2536",
    "FIX_TX":       "#eb6f92",
    "SEL_BG":       "#3f374f",
    "HOVER_BG":     "#323042",
    "LIST_BG":      "#16141f",
    "BTN_BG":       "#323042",
    "BTN_BORDER":   "#71638c",
    "BTN_HOVER":    "#403e50",
    "BTN_PRESSED":  "#4f4d60",
    "CREATE_HOVER": "#cdb5eb",
    "DELETE_BG":    "#ed7194",
    "DELETE_HOVER": "#f88aa9",
    "MISSING":      "#eb6f92",
    "DISABLED_BG":  "#1f1d2e",
    "DISABLED_TX":  "#585569",
    "NEUTRAL_BG":   "#2b2938",
    "NEUTRAL_TX":   "#a5a1bd",
}


# The registry. A name here is what config.local.json stores and what
# set_scheme() takes.
SCHEMES: dict[str, dict[str, str]] = {
    "warm_light": WARM_LIGHT,
    "warm_dark": WARM_DARK,
    "cool_light": COOL_LIGHT,
    "cool_dark": COOL_DARK,
    "github_light": GITHUB_LIGHT,
    "github_dark": GITHUB_DARK,
    "nord_light": NORD_LIGHT,
    "nord_dark": NORD_DARK,
    "rose_pine_light": ROSE_PINE_LIGHT,
    "rose_pine_dark": ROSE_PINE_DARK,
}

# A theme is a (light, dark) pair of scheme names. A theme whose dark member is
# None goes dark nowhere, and every resolver draws its light palette instead.
THEMES: dict[str, tuple[str, str | None]] = {
    "warm": ("warm_light", "warm_dark"),
    "cool": ("cool_light", "cool_dark"),
    "github": ("github_light", "github_dark"),
    "nord": ("nord_light", "nord_dark"),
    "rose_pine": ("rose_pine_light", "rose_pine_dark"),
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
    ("cool", "Frosty"),
    ("github", "GitHub"),
    ("nord", "Nord"),
    ("warm", "Pumpkin"),
    ("rose_pine", "Rosé Pine"),
]

# What this build ships, kept apart from the live SCHEMES and THEMES, which the
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
NO_DARK_HALF = "This theme has no dark colors yet."

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
    ("Text", ["INK", "INK_SOFT", "INK_FAINT"]),
    ("Surfaces", ["CANVAS", "SURFACE", "LIST_BG", "BORDER"]),
    ("Accent", ["ACCENT", "ACCENT_DK", "ON_ACCENT"]),
    ("Cards", ["SEL_BG", "HOVER_BG"]),
    ("Badges", ["BUILD_BG", "BUILD_TX",
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
    "INK_FAINT": "Tertiary Text",
    "CANVAS": "Window Background",
    "SURFACE": "Card Surface",
    "LIST_BG": "Recessed List",
    "BORDER": "Hairline Border",
    "ACCENT": "Accent",
    "ACCENT_DK": "Accent Text",
    "ON_ACCENT": "Text on Accent",
    "SEL_BG": "Selected Card",
    "HOVER_BG": "Hovered Card",
    "BUILD_BG": "Build Pill",
    "BUILD_TX": "Build Pill Text",
    "FIX_BG": "Fix Pill",
    "FIX_TX": "Fix Pill Text",
    "NEUTRAL_BG": "Quiet Pill",
    "NEUTRAL_TX": "Quiet Pill Text",
    "BTN_BG": "Button",
    "BTN_BORDER": "Interactive Edge",
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
    ("INK_FAINT", "CANVAS"), ("INK_FAINT", "SURFACE"), ("INK_FAINT", "LIST_BG"),
    ("ACCENT_DK", "CANVAS"), ("ACCENT_DK", "SURFACE"), ("ACCENT_DK", "SEL_BG"),
    ("ON_ACCENT", "ACCENT"), ("ON_ACCENT", "CREATE_HOVER"),
    ("DELETE_BG", "BTN_BG"), ("DELETE_HOVER", "BTN_HOVER"),
    ("MISSING", "CANVAS"), ("MISSING", "SURFACE"),
    ("BUILD_TX", "BUILD_BG"), ("FIX_TX", "FIX_BG"),
    ("NEUTRAL_TX", "NEUTRAL_BG"),
]

# The ratio a pair above has to reach. WCAG AA for body text.
CONTRAST_MIN = 4.5

# A mark that carries a state, over what it sits on: the accent as focus, a
# checkbox's edge and a selected row's bar; an empty required field's edge; and
# the edge of everything that can be clicked.
MARK_PAIRS: list[tuple[str, str]] = [
    ("ACCENT", "CANVAS"), ("ACCENT", "SURFACE"),
    ("MISSING", "SURFACE"),
    ("BTN_BORDER", "CANVAS"), ("BTN_BORDER", "SURFACE"), ("BTN_BORDER", "LIST_BG"),
]

# The ratio a mark above has to reach. WCAG AA for non-text contrast.
MARK_MIN = 3.0

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

    This build's default where the collection still contains it, and the first
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
    """The theme and mode in force, from the three values config can contain.

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


# The app's one typeface, Inter, under the SIL Open Font License; its files and
# the licence ship in ui/fonts/. Bundled so the text looks the same on every Mac,
# whatever fonts that Mac has.
TYPEFACE = "Inter"
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def install_typeface(app) -> bool:
    """Register the bundled typeface and make it the application's font, at
    ``TYPE["body"]``. Returns whether the typeface took; the size is set either
    way.

    Every font built with ``QFont()`` afterwards starts from it, and the style
    sheet names sizes and weights only, so one call sets the face everywhere.
    The monospace face kept for templates is set by name and stays.
    """
    from PySide6.QtGui import QFontDatabase

    families: set[str] = set()
    for file in sorted(FONT_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(file))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    font = app.font()
    font.setPointSize(type_size("body"))
    installed = TYPEFACE in families
    if installed:
        font.setFamily(TYPEFACE)
    app.setFont(font)
    return installed


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
    set_scheme(live_scheme(app, theme, mode))
    if app is not None:
        from .popups import install as install_popups
        install_popups(app)
        from .scroll_bars import install as install_scroll_bars
        install_scroll_bars(app)
        if app.font().family() != TYPEFACE:
            install_typeface(app)
        style_application(app)


def style_application(app) -> None:
    """Draw ``app`` in the live palette: the style sheet, and the one colour a
    style sheet cannot set, a field's placeholder text, which takes Tertiary
    Text."""
    palette = app.palette()
    placeholder = QColor(C["INK_FAINT"])
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        palette.setColor(group, QPalette.PlaceholderText, placeholder)
    app.setPalette(palette)
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

    # A change stored against a theme this build no longer ships is the user's
    # theme, kept as one he added: the halves he changed are his, and a half he
    # left alone completes against the reference.
    for theme_id, change in edited.items():
        if (not isinstance(theme_id, str) or theme_id in collection
                or theme_id in deleted or not isinstance(change, dict)
                or not (isinstance(change.get("light"), dict)
                        or isinstance(change.get("dark"), dict))):
            continue
        record = _stored_record(change, theme_id.replace("_", " ").title())
        if record is not None:
            collection[theme_id] = record

    if not collection:
        collection = _baseline(legacy_custom)
    return order_collection(collection)


def order_collection(collection: dict[str, dict]) -> dict[str, dict]:
    """The collection by name, which is the order a picker is read in: scan to
    the letter."""
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
    then every mark in ``MARK_PAIRS`` it puts under ``MARK_MIN``, as readable
    lines naming both sides, the ratio and the minimum.

    Empty means every pair reads. A pair either side of which is missing or
    unparseable is skipped: an incomplete palette is ``check_schemes()``'s to
    name, and a field mid-edit is the form's.
    """
    complaints = []
    for pairs, minimum, what in ((TEXT_PAIRS, CONTRAST_MIN, "reads"),
                                 (MARK_PAIRS, MARK_MIN, "shows")):
        for foreground, background in pairs:
            try:
                ratio = contrast_ratio(palette[foreground], palette[background])
            except (KeyError, ValueError):
                continue
            if ratio < minimum:
                complaints.append(
                    f"{key_caption(foreground)} on {key_caption(background)} "
                    f"{what} at {ratio:.1f}:1, under {minimum:g}:1"
                )
    return complaints


def current_scheme() -> str:
    """The scheme name ``C`` currently contains."""
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


# The colour scheme the platform is held to, or None while it follows the OS.
# Kept here rather than read back from Qt, because Qt reports a held scheme as
# the OS's own.
_held_scheme = None


def scheme_is_dark(name: str) -> bool:
    """True when ``name`` is the dark half of a theme."""
    return any(dark == name for _light, dark in THEMES.values())


def _hold_platform(app, scheme) -> None:
    """Hold the platform to ``scheme``, a ``Qt.ColorScheme``, or let it follow
    the OS where ``scheme`` is None.

    The hold is recorded before Qt is told, because telling Qt raises its
    colour-scheme signal, which re-enters the theme and must find the hold
    already in place. A Qt without the call leaves the platform following the
    OS."""
    global _held_scheme
    if scheme == _held_scheme:
        return
    previous, _held_scheme = _held_scheme, scheme
    hints = app.styleHints()
    try:
        if scheme is None:
            hints.unsetColorScheme()
        else:
            hints.setColorScheme(scheme)
    except AttributeError:
        _held_scheme = previous


def live_scheme(app, theme: str | None, mode: str | None) -> str:
    """The scheme a theme and a mode mean now, with the platform held to its
    light or dark.

    The platform draws the title bar, the window frame and every control a
    stylesheet leaves to Qt's palette, so it is held to the half Bristol draws:
    a pinned mode holds it, and Follow System lets the OS's own setting through
    before that setting is read.
    """
    if app is None:
        return resolve_scheme(theme, mode, False)
    if mode == SYSTEM_MODE:
        _hold_platform(app, None)
    name = resolve_scheme(theme, mode, is_dark_scheme(app))
    if mode != SYSTEM_MODE:
        _hold_platform(app, Qt.ColorScheme.Dark if scheme_is_dark(name)
                       else Qt.ColorScheme.Light)
    return name


def chevron_image(colour: str, direction: str = "down") -> str | None:
    """Lucide's chevron in the given colour and direction (``down`` or ``up``),
    as an image file the stylesheet can point a combo box's or spin box's arrow
    at. Returns None when nothing can be written, in which case the arrow rule
    is left out.
    """
    from .icons import image_file

    # The chevron's own part of Lucide's 24-unit drawing, stroke included, at
    # the arrow's width-to-height ratio.
    return image_file(f"chevron-{direction}", colour, space("lg"), space("md"),
                      (4, 7, 16, 10))


def check_image(colour: str) -> str | None:
    """Lucide's check in the given colour, as an image file the stylesheet
    points a checked checkbox indicator at. Returns None when nothing can be
    written, in which case the checked state is a plain accent fill."""
    from .icons import image_file

    side = space("md") + 2
    return image_file("check", colour, side, side, (3, 3, 18, 18))


def build_style_sheet() -> str:
    """Render the global Qt stylesheet from the live palette ``C`` and the token
    scales, so a scheme swap and a token change both reach every styled widget."""
    r_sm, r_md, r_lg = radius("sm"), radius("md"), radius("lg")
    chevron = chevron_image(C["INK_SOFT"])
    chevron_up = chevron_image(C["INK_SOFT"], "up")
    check = check_image(C["ON_ACCENT"])
    arrow_rule = (f"QComboBox::down-arrow, QDateEdit::down-arrow {{ image: url({chevron}); "
                  f"width: {space('lg')}px; height: {space('md')}px; }}"
                  if chevron else "")
    spin_arrow_rule = (
        f"QSpinBox::up-arrow {{ image: url({chevron_up}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}\n"
        f"QSpinBox::down-arrow {{ image: url({chevron}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}"
        if chevron and chevron_up else "")
    check_rule = f"image: url({check});" if check else ""
    ctl = control_height() - 2  # inside the 1px border every control draws
    tb_ctl = LAYOUT["toolbar_control_h"] - 2
    tb_box = LAYOUT["toolbar_box_w"] - 2

    def _ink(alpha: float) -> str:
        ink = C["INK"].lstrip("#")[-6:]
        r, g, b = (int(ink[i:i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"

    ink_06, ink_10, ink_14 = _ink(0.06), _ink(0.10), _ink(0.14)
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
/* The top bar: the window's own background, closed by one hairline. */
QWidget#appHeader {{
    background-color: {C['CANVAS']};
    border-bottom: 1px solid {C['BORDER']};
}}
/* A region's name: the app's beside its mark, a board column's. */
QLabel#regionTitle {{
    color: {C['INK']};
    font-size: {type_size('title')}pt;
    font-weight: 600;
}}
/* A view in the top bar: its name on the bar, a faint fill on
   hover, and the open one in the accent on a faint fill of its own. */
QPushButton#viewTab {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    padding: 0px {s_lg}px;
    color: {C['INK_SOFT']};
    font-weight: 600;
}}
QPushButton#viewTab:hover {{
    background-color: {ink_06};
    color: {C['INK']};
}}
QPushButton#viewTab:checked {{
    background-color: {ink_10};
    color: {C['ACCENT_DK']};
}}
QPushButton#viewTab:focus {{
    border-color: {C['ACCENT']};
}}
QFrame#headerDivider {{
    background-color: {ink_14};
    border: none;
}}
/* The top bar's icon buttons — Search, Refresh, Settings — each its icon in a
   faint box; an open view's box takes the accent's edge. */
QPushButton#toolbarButton, QPushButton#toolbarToggle {{
    background-color: {ink_06};
    border: 1px solid {ink_14};
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    min-width: {tb_box}px;
    max-width: {tb_box}px;
    padding: 0px;
}}
QPushButton#toolbarButton:hover, QPushButton#toolbarToggle:hover {{
    background-color: {ink_14};
}}
QPushButton#toolbarToggle:checked {{
    background-color: {ink_10};
    border-color: {C['ACCENT']};
}}
QPushButton#toolbarButton:focus, QPushButton#toolbarToggle:focus {{
    border-color: {C['ACCENT']};
}}
/* The top bar's Create: the primary button at the top bar's height. Where a
   view has no cards it is faded by an opacity effect rather than turned grey,
   as the Mac dims a toolbar item it has no use for. */
QPushButton#toolbarCreate, QPushButton#toolbarCreate:disabled {{
    background-color: {C['ACCENT']};
    color: {C['ON_ACCENT']};
    border: 1px solid {C['ACCENT']};
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    min-width: {tb_box}px;
    max-width: {tb_box}px;
    padding: 0px;
}}
QPushButton#toolbarCreate:hover {{
    background-color: {C['CREATE_HOVER']};
    border-color: {C['CREATE_HOVER']};
}}
/* A list is a well of rows a person clicks or ticks, so it carries the edge
   everything clickable carries: its fill alone sits too close to the window's
   to be found. */
QListWidget {{
    background-color: {C['LIST_BG']};
    color: {C['INK']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
    outline: 0;
}}
/* A board column is a region of the canvas, not a container: the cards are the
   only raised surfaces on the view, so the well they sit in has no fill and no
   border of its own. One hairline across its top, under the column's name, is
   the edge a card scrolls under. */
QListWidget#columnCards {{
    background: transparent;
    border: none;
    border-top: 1px solid {C['BORDER']};
    padding: 0px;
}}
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
QPushButton#paneReveal {{
    border-left: 1px solid {C['BORDER']};
    border-radius: 0px;
}}
/* A path the user may need to find on disk reads as a path. */
QLabel#pathRow {{
    background-color: {C['LIST_BG']};
    border: 1px solid transparent;
    border-radius: {r_md}px;
    padding: {s_md}px {s_lg}px;
    color: {C['INK']};
    font-size: {type_size('body')}pt;
}}
QLabel#pathRow[fieldMissing="true"] {{
    color: {C['MISSING']};
    border-color: {C['MISSING']};
}}
QLabel#sectionHeader[fieldMissing="true"] {{ color: {C['MISSING']}; }}
QLabel#formCaption {{ color: {C['INK_SOFT']}; }}
/* The filter panel: one raised surface under the Filter button, containing a
   section per facet and one row per option. A row is a whole click target, so
   it takes the pointer fill a card does. */
QFrame#filterMenu {{
    background-color: {C['SURFACE']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_lg}px;
}}
QLabel#facetHeading {{
    color: {C['INK_SOFT']};
    font-size: {type_size('caption')}pt;
    font-weight: 600;
}}
QWidget#facetRow {{ border-radius: {r_md}px; }}
QWidget#facetRow:hover {{ background-color: {C['HOVER_BG']}; }}
QScrollArea#filterScroll, QScrollArea#filterScroll > QWidget > QWidget,
QScrollArea#paletteScroll, QScrollArea#paletteScroll > QWidget > QWidget,
QScrollArea#recordScroll, QScrollArea#recordScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QPushButton#link:disabled {{
    color: {C['DISABLED_TX']};
    text-decoration: none;
}}
/* The Filter button takes the accent while it is leaving something out, so a
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
    border: 1px solid transparent;
    border-radius: {r_sm}px;
    padding: {s_sm}px {s_lg}px;
    font-weight: 400;
}}
QPushButton#filterChip:focus {{ border-color: {C['ACCENT']}; }}
QPushButton#filterChip:hover {{
    background-color: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
/* A scroll bar is chrome: a slim handle on an empty groove, so a column that
   overflows does not gain a heavy black rail down its edge. It keeps SPACE sm
   from what it scrolls, drawn as an empty strip on the content's side. */
QScrollBar:vertical {{
    background: transparent;
    width: {s_lg + s_sm}px;
    margin: 0px 0px 0px {s_sm}px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {s_lg + s_sm}px;
    margin: {s_sm}px 0px 0px 0px;
}}
/* Where the content is already inset from the viewport's edge by SPACE sm — a
   board card by its margin, text by its document margin — that inset is the
   gap, and the bar adds none. */
QListWidget#columnCards QScrollBar:vertical, QTextEdit QScrollBar:vertical {{
    width: {s_lg}px;
    margin: 0px;
}}
QTextEdit QScrollBar:horizontal {{
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
QListWidget#textList::item {{
    padding: {s_md}px {s_lg}px;
    border-radius: {r_md}px;
    border-left: 3px solid transparent;
}}
/* The selected row also carries an accent bar, because a scheme's hover and
   selection fills sit close enough that a hovered row would otherwise read as
   a second selection. */
QListWidget#textList::item:selected {{
    background: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
    border-left: 3px solid {C['ACCENT']};
}}
QListWidget#textList::item:hover:!selected {{
    background: {C['HOVER_BG']};
}}
/* The Search and Archive results: a table read as a list, with a header per
   fact and alternate rows, and the selection in the accent the lists use. */
QTableWidget#resultsTable {{
    background-color: {C['LIST_BG']};
    alternate-background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_lg}px;
    outline: 0;
}}
QTableWidget#resultsTable::item {{ padding: {s_sm}px {s_md}px; border: none; }}
QTableWidget#resultsTable::item:selected {{
    background-color: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
QHeaderView::section {{
    background-color: {C['CANVAS']};
    color: {C['INK_SOFT']};
    border: none;
    border-bottom: 1px solid {C['BORDER']};
    padding: {s_sm}px {s_md}px;
    font-weight: 600;
}}
QComboBox, QLineEdit, QAbstractSpinBox, QTextEdit {{
    background-color: {C['SURFACE']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_md}px;
    padding: {s_md}px {s_md}px;
    color: {C['INK']};
    selection-background-color: {C['ACCENT']};
    selection-color: {C['ON_ACCENT']};
}}
/* A picker is a button that opens a list, so it takes the control face. */
QComboBox, QDateEdit {{
    background-color: {C['BTN_BG']};
    border: 1px solid {C['BTN_BORDER']};
}}
QComboBox:hover, QDateEdit:hover {{ background-color: {C['BTN_HOVER']}; }}
QComboBox:on {{ background-color: {C['BTN_PRESSED']}; }}
QComboBox:focus, QLineEdit:focus, QAbstractSpinBox:focus, QTextEdit:focus {{
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
QLabel[fieldMissing="true"] {{ color: {C['MISSING']}; }}
/* A formCaption carries its own missing state. */
QLabel#formCaption[fieldMissing="true"] {{ color: {C['MISSING']}; }}
/* A picker opens this app's own list rather than the platform's menu: a raised
   surface with a rounded corner, room around every option, and the same
   selected fill a list row takes. popups.py makes its window transparent so
   the corner is the one drawn here, and as wide as its longest option. */
QComboBox {{ combobox-popup: 0; }}
QComboBox QAbstractItemView {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
    outline: 0;
    selection-background-color: {C['SEL_BG']};
    selection-color: {C['ACCENT_DK']};
}}
QComboBox QAbstractItemView::item {{
    min-height: {s_2xl}px;
    padding: {s_xs}px {s_lg}px;
    border-radius: {r_md}px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {C['HOVER_BG']};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
/* A growing text field takes slimmer vertical padding, so one line of it is
   one control tall (growing_edit.py fixes the height). */
QTextEdit[growing="true"] {{ padding: {s_sm}px {s_md}px; }}
/* A choice that opens a section of a window: a round mark beside a heading. */
QRadioButton {{ color: {C['INK']}; background: transparent; spacing: {s_md}px; }}
QRadioButton#choiceHeading {{ font-weight: 600; }}
QRadioButton::indicator {{
    width: {s_lg}px;
    height: {s_lg}px;
    border: 1px solid {C['ACCENT']};
    border-radius: {s_lg // 2 + 1}px;
    background-color: {C['SURFACE']};
}}
QRadioButton::indicator:hover {{ border-color: {C['ACCENT']}; }}
QRadioButton::indicator:checked {{
    background-color: {C['ACCENT']};
    border-color: {C['ACCENT']};
}}
/* A picker reads as a picker: the drop-down carries a chevron of its own. */
QComboBox::drop-down, QDateEdit::drop-down {{
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
QLabel#inspectorTitle {{ color: {C['ACCENT_DK']}; }}
QLabel#sectionHeader {{ color: {C['INK_SOFT']}; font-weight: 600; }}
/* The one thing a confirmation or a notice says first: the largest text in a
   modal that carries no icon, since the words are all it has. */
QLabel#dialogHeading {{
    color: {C['INK']};
    font-size: {type_size('section')}pt;
    font-weight: 600;
}}
QLabel#metaText {{ color: {C['INK_SOFT']}; }}
/* A link: accent text with no surface, underlined under the pointer and with
   focus. A link row, Clear All in the filter panel, a skill's source. */
QPushButton#link {{
    background: transparent;
    border: none;
    padding: {s_xs}px 0px;
    text-align: left;
    color: {C['ACCENT_DK']};
    font-weight: 400;
}}
QPushButton#link:hover, QPushButton#link:focus {{ text-decoration: underline; }}
/* A quiet icon button: an icon with no face until the pointer is over it, for
   an action that sits beside what it acts on — the ✕ that removes a link, an
   attachment or a variable, the folder that picks one. The pane's collapse
   control and the strip that brings it back are the same button. */
QPushButton#quietIcon, QPushButton#paneToggle, QPushButton#paneReveal {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {r_md}px;
    padding: {s_xs}px;
    color: {C['INK_SOFT']};
    font-weight: 400;
}}
QPushButton#quietIcon:hover, QPushButton#paneToggle:hover,
QPushButton#paneReveal:hover {{
    background-color: {C['HOVER_BG']};
    color: {C['INK']};
}}
QPushButton#quietIcon:focus, QPushButton#paneToggle:focus {{
    border-color: {C['ACCENT']};
}}
QCheckBox {{
    color: {C['INK']};
    background: transparent;
    spacing: {s_md}px;
    padding: {s_xs}px 0px;
}}
QRadioButton {{ spacing: {s_md}px; }}
/* The checkbox is the scheme's own control: a surface with an accent
   hairline, an accent fill when checked — never the platform's indicator. */
QCheckBox::indicator {{
    width: {s_lg}px;
    height: {s_lg}px;
    border: 1px solid {C['ACCENT']};
    border-radius: {r_sm}px;
    background-color: {C['SURFACE']};
}}
QCheckBox::indicator:hover {{ border-color: {C['ACCENT']}; }}
QCheckBox::indicator:checked {{
    background-color: {C['ACCENT']};
    border-color: {C['ACCENT']};
    {check_rule}
}}
/* A tickable list row draws the same box a checkbox does, so an unticked one
   reads on a dark list as well as a light one. */
QListWidget::indicator {{
    width: {s_lg}px;
    height: {s_lg}px;
    border: 1px solid {C['ACCENT']};
    border-radius: {r_sm}px;
    background-color: {C['SURFACE']};
}}
QListWidget::indicator:checked {{
    background-color: {C['ACCENT']};
    border-color: {C['ACCENT']};
    {check_rule}
}}
QMenu {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BTN_BORDER']};
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
    font-weight: 400;
    color: {C['INK']};
}}
QPushButton:hover {{ background-color: {C['BTN_HOVER']}; }}
QPushButton:pressed {{ background-color: {C['BTN_PRESSED']}; }}
QPushButton:focus {{ border-color: {C['ACCENT']}; }}
/* A button kept unclickable until its form is valid must LOOK unclickable —
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
    border: 1px solid {C['ACCENT']};
}}
QPushButton#globalCreateBtn:hover {{
    background-color: {C['CREATE_HOVER']};
    border-color: {C['CREATE_HOVER']};
}}
QPushButton#globalCreateBtn:focus, QPushButton#toolbarCreate:focus {{
    border-color: {C['ON_ACCENT']};
}}
/* The id selector outranks the generic :disabled rule, so the primary button
   needs its own unclickable look or it would stay accent-filled while dead. */
QPushButton#globalCreateBtn:disabled {{
    background-color: {C['DISABLED_BG']};
    border: 1px solid {C['BORDER']};
    color: {C['DISABLED_TX']};
}}
/* A segmented control: its segments share the control face and join into one
   control; the chosen one takes the selection fill and the accent text. */
QPushButton#segment {{
    border-radius: 0px;
    padding: 0px {s_lg}px;
}}
QPushButton#segment[position="middle"], QPushButton#segment[position="last"] {{
    border-left: none;
}}
QPushButton#segment[position="first"] {{
    border-top-left-radius: {r_md}px;
    border-bottom-left-radius: {r_md}px;
}}
QPushButton#segment[position="last"] {{
    border-top-right-radius: {r_md}px;
    border-bottom-right-radius: {r_md}px;
}}
QPushButton#segment:checked {{
    background-color: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
/* A button whose window contains something that is not on disk. */
QPushButton[missing="true"] {{
    border: 1px solid {C['MISSING']};
    color: {C['MISSING']};
}}
/* A destructive action is an ordinary button whose words are red, as the Mac
   marks one; the fill stays the plain button's. */
QPushButton#deleteBtn {{
    color: {C['DELETE_BG']};
}}
QPushButton#deleteBtn:hover {{
    color: {C['DELETE_HOVER']};
}}
/* The + and − under an editable list: two square buttons joined at their
   shared edge. */
QPushButton#listEditBtn {{
    min-width: {ctl}px;
    max-width: {ctl}px;
    padding: 0px;
    border-radius: 0px;
    font-weight: 400;
}}
/* One height for every control that can share a row. Padding and border are
   zeroed vertically and the height is fixed outright, so a field, a picker, a
   date and a button beside each other line up to the pixel. */
QPushButton, QLineEdit, QComboBox, QAbstractSpinBox {{
    min-height: {ctl}px;
    max-height: {ctl}px;
    padding-top: 0px;
    padding-bottom: 0px;
}}
/* Text-like buttons are not controls on a row: they keep their own height. */
QPushButton#link, QPushButton#filterChip, QPushButton#paneToggle,
QPushButton#paneReveal, QPushButton#quietIcon, QPushButton#exampleLink {{
    min-height: 0px;
    max-height: 9999px;
}}
QPushButton#link, QPushButton#exampleLink {{ padding: {s_xs}px 0px; }}
QPushButton#quietIcon {{ padding: {s_xs}px; }}
QPushButton#paneToggle, QPushButton#paneReveal {{ padding: {s_xs}px {s_md}px; }}
QPushButton#filterChip {{ padding: {s_sm}px {s_lg}px; }}
/* An example under a field: Tertiary Text, as a placeholder is, and a link
   on hover because it opens the page it shows. */
QPushButton#exampleLink {{
    background: transparent;
    border: none;
    text-align: left;
    color: {C['INK_FAINT']};
    font-weight: 400;
}}
QPushButton#exampleLink:hover, QPushButton#exampleLink:focus {{ color: {C['ACCENT_DK']}; text-decoration: underline; }}
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


def _today() -> str:
    """Today as the board writes a date, so a due date can be compared against
    it as plain text."""
    return datetime.now().strftime("%Y-%m-%d")


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


def size_label(code: str | None) -> str:
    """A size code as a word. An unrecognised or absent code returns the code
    itself, so a board carrying something else still says what it contains."""
    key = (code or "").strip().upper()
    if not key:
        return ""
    return SIZE_WORDS.get(key, key)


def tier_label(code: str | None) -> str:
    """A tier as a word. An unrecognised code returns itself, and an absent one
    returns nothing, so a card not yet rated draws no pill."""
    key = (code or "").strip().lower()
    if not key:
        return ""
    return TIER_WORDS.get(key, key)
