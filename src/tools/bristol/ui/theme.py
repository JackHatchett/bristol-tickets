"""ui/theme.py — shared visual constants, palettes, stylesheet, and helpers.

This module holds everything the other UI modules agree on: the column
definitions, the custom item-data role, the warm colour palettes (a light and a
dark variant), the global Qt stylesheet builder, and a few small stateless
helper functions. It imports nothing from the rest of the package, so it is the
safe bottom of the import graph — every other ui module may import from here,
and this module imports from none of them.

Theming model
--------------------------------
The app follows the OS light/dark setting. Rather than binding colour names at
import time (which can't be re-pointed live), every consumer reads the current
palette out of the single mutable dict ``C``. ``set_scheme(dark)`` swaps ``C``'s
contents in place, and ``build_style_sheet()`` renders the global Qt stylesheet
from whatever ``C`` currently holds. Because ``C`` is mutated in place, a module
that did ``from .theme import C`` keeps seeing live values — so a repaint after a
scheme change is all it takes for QPainter-drawn widgets (the cards) to re-theme,
and a single ``app.setStyleSheet(build_style_sheet())`` re-themes everything
stylesheet-driven, including child dialogs and message boxes.
"""

from __future__ import annotations

from datetime import datetime, timezone

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
# Palettes — a warm light and a warm dark, both orange-based
# ---------------------------------------------------------------------------
# Every key here is read somewhere in the stylesheet or the card delegate. The
# two dicts MUST carry the same keys so a scheme swap never leaves a hole.
LIGHT = {
    "INK":          "#3d3325",  # primary text (warm near-black)
    "INK_SOFT":     "#7c6f5b",  # secondary text
    "CANVAS":       "#faf6ef",  # app / dialog background
    "SURFACE":      "#fffdf9",  # card / input surface
    "BORDER":       "#e7dcc6",  # hairline borders
    "ACCENT":       "#ea580c",  # primary orange
    "ACCENT_DK":    "#c2410c",  # deeper orange — bright accent text
    "AMBER_BG":     "#fef3c7",  # epic pill background
    "AMBER_TX":     "#92400e",  # epic pill text
    "BUILD_BG":     "#e4eee6",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#3f6f4f",  # Build record-type pill text
    "FIX_BG":       "#fbe2db",  # Fix record-type pill background (rust)
    "FIX_TX":       "#b23b26",  # Fix record-type pill text
    "SEL_BG":       "#fff1e2",  # selected card fill
    "HOVER_BG":     "#fffaf2",  # hovered card fill
    "HOVER_BORDER": "#f0c99a",  # hovered card border
    "TAB_BG":       "#f1ebdd",  # unselected tab background
    "LIST_BG":      "#fbf6ee",  # kanban list / scroll area background
    "BTN_BG":       "#fff4e8",  # normal button fill
    "BTN_BORDER":   "#f7c99a",  # normal button border
    "BTN_HOVER":    "#ffe9d2",  # button hover fill
    "BTN_PRESSED":  "#ffddb8",  # button pressed fill
    "CREATE_HOVER": "#f2680f",  # accent (Create) button hover fill
    "DELETE_BG":    "#e0563b",  # delete button fill
    "DELETE_HOVER": "#cf4a30",  # delete button hover fill
    "MISSING":      "#d61f1f",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#f3ece0",  # unclickable button fill
    "DISABLED_TX":  "#b3a389",  # unclickable button text
}

DARK = {
    "INK":          "#f2e6d5",  # primary text (warm near-white)
    "INK_SOFT":     "#b89f7d",  # secondary text
    "CANVAS":       "#17120c",  # app / dialog background (deep warm)
    "SURFACE":      "#241c14",  # card / input surface (dark warm)
    "BORDER":       "#463724",  # hairline borders
    "ACCENT":       "#f97316",  # primary orange (brighter for dark)
    "ACCENT_DK":    "#fdba74",  # light orange — bright accent text on dark
    "AMBER_BG":     "#3a2a10",  # epic pill background (dark amber)
    "AMBER_TX":     "#fcd34d",  # epic pill text (bright amber)
    "BUILD_BG":     "#1e2a1e",  # Build record-type pill background (calm green)
    "BUILD_TX":     "#8fca9a",  # Build record-type pill text
    "FIX_BG":       "#3a1f18",  # Fix record-type pill background (rust)
    "FIX_TX":       "#f0a58e",  # Fix record-type pill text
    "SEL_BG":       "#3a2914",  # selected card fill
    "HOVER_BG":     "#2a2115",  # hovered card fill
    "HOVER_BORDER": "#7a5a33",  # hovered card border
    "TAB_BG":       "#2c2418",  # unselected tab background
    "LIST_BG":      "#1c160f",  # kanban list / scroll area background
    "BTN_BG":       "#33281b",  # normal button fill
    "BTN_BORDER":   "#6b4f2e",  # normal button border
    "BTN_HOVER":    "#40311f",  # button hover fill
    "BTN_PRESSED":  "#4a3826",  # button pressed fill
    "CREATE_HOVER": "#fb8b3d",  # accent (Create) button hover fill
    "DELETE_BG":    "#b3432c",  # delete button fill
    "DELETE_HOVER": "#c94d33",  # delete button hover fill
    "MISSING":      "#ff5449",  # required-but-empty field border (bright red)
    "DISABLED_BG":  "#241c14",  # unclickable button fill
    "DISABLED_TX":  "#6b5b45",  # unclickable button text
}

# The single live palette every consumer reads from. Starts light; the app
# calls set_scheme() at startup and on every OS colour-scheme change.
C: dict[str, str] = dict(LIGHT)


def set_scheme(dark: bool) -> None:
    """Point the live palette ``C`` at the light or dark variant, in place, so
    existing ``from .theme import C`` references keep seeing current values."""
    C.clear()
    C.update(DARK if dark else LIGHT)


def is_dark_scheme(app) -> bool:
    """True when the OS/Qt colour scheme is Dark. Guarded so it degrades to
    light on Qt builds too old to report a scheme (pre-6.5)."""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def build_style_sheet() -> str:
    """Render the global Qt stylesheet from the live palette ``C``."""
    return f"""
QMainWindow, QWidget#leftContainer, QDialog {{
    background-color: {C['CANVAS']};
    color: {C['INK']};
}}
QSplitter::handle {{
    background-color: {C['CANVAS']};
}}
QTabWidget::pane {{
    border: 1px solid {C['BORDER']};
    border-radius: 10px;
    background-color: {C['SURFACE']};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {C['TAB_BG']};
    color: {C['INK_SOFT']};
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: {C['SURFACE']};
    color: {C['ACCENT']};
    border: 1px solid {C['BORDER']};
    border-bottom: 2px solid {C['ACCENT']};
}}
QGroupBox {{
    font-weight: 600;
    border: 1px solid {C['BORDER']};
    border-radius: 10px;
    background-color: {C['SURFACE']};
    margin-top: 14px;
    padding: 12px;
    color: {C['INK']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: {C['ACCENT']};
}}
QListWidget {{
    background-color: {C['LIST_BG']};
    border: 1px solid {C['BORDER']};
    border-radius: 10px;
    padding: 4px;
    outline: 0;
}}
QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: transparent; }}
/* Search results are plain text items (not delegate-painted cards), so the
   transparent-selection rule above would leave them with the palette's
   highlighted-text colour on a light fill — near-invisible. Give this list a
   visible selected fill and the brightest orange the board uses for text. */
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
    border-radius: 7px;
    padding: 6px 8px;
    color: {C['INK']};
    selection-background-color: {C['ACCENT']};
    selection-color: white;
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
QComboBox QAbstractItemView {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BORDER']};
    selection-background-color: {C['ACCENT']};
    selection-color: white;
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QLabel {{ color: {C['INK']}; background: transparent; }}
QLabel#inspectorTitle {{ color: {C['ACCENT']}; }}
QLabel#sectionHeader {{ color: {C['INK_SOFT']}; font-weight: 600; }}
QLabel#metaText {{ color: {C['INK_SOFT']}; }}
/* A link row reads as text, not a control: full width, left-aligned, accented,
   underlined on hover so it is obviously clickable. */
QPushButton#linkRow {{
    background: transparent;
    border: none;
    padding: 2px 0px;
    text-align: left;
    color: {C['ACCENT']};
}}
QPushButton#linkRow:hover {{ color: {C['ACCENT_DK']}; text-decoration: underline; }}
QCheckBox {{ color: {C['INK']}; background: transparent; }}
QMenu {{
    background-color: {C['SURFACE']};
    color: {C['INK']};
    border: 1px solid {C['BORDER']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{ padding: 6px 22px 6px 14px; border-radius: 5px; }}
QMenu::item:selected {{ background-color: {C['SEL_BG']}; color: {C['ACCENT_DK']}; }}
QMenu::separator {{ height: 1px; background: {C['BORDER']}; margin: 4px 8px; }}
QPushButton {{
    background-color: {C['BTN_BG']};
    border: 1px solid {C['BTN_BORDER']};
    border-radius: 7px;
    padding: 6px 14px;
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
    color: white;
    border: none;
}}
QPushButton#globalCreateBtn:hover {{ background-color: {C['CREATE_HOVER']}; }}
QPushButton#bulkMenuBtn {{
    color: {C['INK_SOFT']};
    font-weight: 600;
}}
QPushButton#deleteBtn {{
    background-color: {C['DELETE_BG']};
    color: white;
    border: none;
}}
QPushButton#deleteBtn:hover {{ background-color: {C['DELETE_HOVER']}; }}
"""


# ---------------------------------------------------------------------------
# Tiny stateless helpers
# ---------------------------------------------------------------------------
def _mono_font(point_size: int = 12):
    """A monospace font so mad-lib templates and their fill-in blanks line up in
    the Description editor. Menlo on macOS (this app's home), with a
    Monospace style hint so any platform falls back to its fixed-width face."""
    from PySide6.QtGui import QFont
    f = QFont("Menlo")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(point_size)
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


def _priority_color(priority: int) -> QColor:
    if priority >= 70:
        return QColor("#dc2626")   # high — red
    if priority >= 40:
        return QColor("#d97706")   # medium — amber
    return QColor("#0f9d58")       # low — green
