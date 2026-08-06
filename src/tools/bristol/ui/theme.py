"""ui/theme.py — the appearance manager: schemes, design tokens, stylesheet.

This module holds every visual constant the rest of the UI draws with: the
column definitions, the custom item-data role, the named colour schemes, the
spacing / radius / type token scales, the global Qt stylesheet builder, and a
few small stateless helper functions. It imports nothing from the rest of the
package, so it is the safe bottom of the import graph — every other ui module
may import from here, and this module imports from none of them.

What each scheme key means and which token governs which element is the styling
contract in ``ui/README.md``.

Schemes
--------------------------------
A scheme is one complete palette under a name. Schemes are grouped into
families, each a light member and a dark member, so naming the family selects
"follow the OS" and naming a member pins one appearance. ``resolve_choice()``
turns either kind of name plus the OS state into one scheme name, and
``set_scheme(name)`` makes it live.

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
# points because Qt sizes fonts that way.
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
    "filter_w": 190,       # the epic filter, wide enough for a real epic name
    "wizard_min_w": 720,
    "wizard_min_h": 480,
    "dialog_min_w": 760,        # the record dialog
    "small_dialog_min_w": 420,  # a single-purpose modal: add link
    "preview_min_w": 480,       # the image preview modal
    "preview_min_h": 360,
}

# An effort code as the word a reader who does not know the codes can read.
EFFORT_WORDS = {"S": "Small", "M": "Medium", "L": "Large", "XL": "Extra large"}


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
# Schemes — the warm orange family and a cool neutral alternate
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

# The registry. A name here is what config.local.json stores and what
# set_scheme() takes.
SCHEMES: dict[str, dict[str, str]] = {
    "warm_light": WARM_LIGHT,
    "warm_dark": WARM_DARK,
    "cool_light": COOL_LIGHT,
    "cool_dark": COOL_DARK,
}

# A family is a (light, dark) pair. Naming a family means "follow the OS within
# it", so the two ways of choosing share one namespace and one config key.
FAMILIES: dict[str, tuple[str, str]] = {
    "warm": ("warm_light", "warm_dark"),
    "cool": ("cool_light", "cool_dark"),
}

# The scheme whose key set defines a complete palette, and the fallback for a
# name the config asks for and this build does not have.
REFERENCE_SCHEME = "warm_light"
DEFAULT_CHOICE = "warm"

# What the Settings tab offers, in the order it offers it. The value is what is
# stored; the caption is what is read.
CHOICES: list[tuple[str, str]] = [
    ("warm", "Warm — follow the system"),
    ("cool", "Cool — follow the system"),
    ("warm_light", "Warm light"),
    ("warm_dark", "Warm dark"),
    ("cool_light", "Cool light"),
    ("cool_dark", "Cool dark"),
]

# The single live palette every consumer reads from. Starts at the reference
# scheme; the app calls set_scheme() at startup, on every OS colour-scheme
# change, and whenever the choice is edited in Settings.
C: dict[str, str] = dict(SCHEMES[REFERENCE_SCHEME])

_current_scheme = REFERENCE_SCHEME


def resolve_choice(choice: str | None, dark: bool) -> str:
    """The scheme name a stored choice means right now.

    A family name resolves against the OS state; a scheme name resolves to
    itself; anything else falls back to the default family.
    """
    if choice in SCHEMES:
        return choice
    pair = FAMILIES.get(choice or "", FAMILIES[DEFAULT_CHOICE])
    return pair[1] if dark else pair[0]


def set_scheme(name: str) -> None:
    """Point the live palette ``C`` at a named scheme, in place, so existing
    ``from .theme import C`` references keep seeing current values.

    A key the named scheme is missing is filled from the reference scheme, so an
    incomplete palette shows the wrong colour rather than raising mid-paint.
    ``check_schemes()`` is what names such a gap.
    """
    global _current_scheme
    scheme = SCHEMES.get(name) or SCHEMES[REFERENCE_SCHEME]
    _current_scheme = name if name in SCHEMES else REFERENCE_SCHEME
    C.clear()
    C.update(SCHEMES[REFERENCE_SCHEME])
    C.update(scheme)


def apply_scheme(app, choice: str | None) -> None:
    """Resolve ``choice`` against the OS state, make it live, and style ``app``.

    Every window the application opens is styled by this one call, so it runs
    before the first window is built rather than inside any of them.
    """
    set_scheme(resolve_choice(
        choice, is_dark_scheme(app) if app is not None else False))
    if app is not None:
        app.setStyleSheet(build_style_sheet())


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
    for name, pair in sorted(FAMILIES.items()):
        for member in pair:
            if member not in SCHEMES:
                complaints.append(f"family {name} names {member}, which is not a scheme")
    return complaints


def is_dark_scheme(app) -> bool:
    """True when the OS/Qt colour scheme is Dark. Guarded so it degrades to
    light on Qt builds too old to report a scheme (pre-6.5)."""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def chevron_image(colour: str, direction: str = "down") -> str | None:
    """A chevron in the given colour and direction (``down`` or ``up``), as a
    cached image file the stylesheet can point a combo box's or spin box's
    arrow at. Returns None when nothing can be written, in which case the
    arrow rule is left out.

    // Qt stops drawing the style's own drop-down arrow as soon as the combo is
    // styled at all, and a stylesheet has no way to draw a triangle: a
    // zero-sized box with borders renders here as a solid block.
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
/* A column's overflow menu: a quiet glyph that only gains a surface on hover. */
QPushButton#columnMenu {{
    background: transparent;
    border: none;
    border-radius: {r_md}px;
    padding: {s_xs}px {s_md}px;
    color: {C['INK_SOFT']};
    font-weight: 700;
}}
QPushButton#columnMenu:hover {{
    background-color: {C['HOVER_BG']};
    color: {C['INK']};
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
/* Search results are plain text items (not delegate-painted cards), so the
   transparent-selection rule above would leave them with the palette's
   highlighted-text colour on a light fill — near-invisible. Give this list a
   visible selected fill and the brightest accent the board uses for text. */
QListWidget#searchResults::item {{
    padding: {s_md}px {s_lg}px;
    border-radius: {r_md}px;
}}
QListWidget#searchResults::item:selected {{
    background: {C['SEL_BG']};
    color: {C['ACCENT_DK']};
}}
QListWidget#searchResults::item:hover {{
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
/* The id selector outranks the attribute rule above, so a formCaption needs
   its own missing state or it would stay muted over an empty required field. */
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
   inside the field rather than as the platform's clipped marks. */
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
    the Description editor. Menlo on macOS (this app's home), with a
    Monospace style hint so any platform falls back to its fixed-width face."""
    from PySide6.QtGui import QFont
    f = QFont("Menlo")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(point_size if point_size is not None else type_size("section"))
    return f


def _is_checked(state) -> bool:
    """Robustly test a Qt.CheckStateRole value for 'checked' across PySide6
    versions: the role may come back as a Qt.CheckState enum or as the raw int
    2. (PySide6 6.11 stores/returns the enum, which is not int()-convertible via
    the old ``int(Qt.Checked)`` idiom.)"""
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
