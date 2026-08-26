"""ui/filter_menu.py — what the board is showing, and the one control that
changes it.

Two things live here:

* ``FilterState`` — the ticked options and the SQL they mean. The board
  columns, the Backlog and the Archive each append its fragment to their own
  query, so one state narrows all three and no view carries a filter of its
  own.
* ``FilterMenu`` — the panel the Filter button opens: a section per facet, a
  checkbox row per option, and on every row the number of board cards that
  option matches. A row applies the moment it is clicked; there is nothing to
  confirm on the way out.

**Sections intersect and options within a section unite.** A card is shown when
it matches something ticked in every section that has anything ticked, which is
what makes two agents readable side by side and an agent inside an epic
readable at all.

**A count is conditional on the other sections.** It answers "how many cards
would this row show me, given what else is ticked", so a row reading 0 is a row
worth not clicking.

Search is outside all of this: a search that quietly skipped matches would be a
worse tool than an unfiltered one.
"""

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .theme import LAYOUT, space

# The two facets. Each is a key in the state and a section in the panel.
ASSIGNEE = "assignee"
EPIC = "epic"

# The epic statuses that keep an epic out of the panel. A finished epic is
# reactivated from the Search tab, not filtered for here.
FINISHED_EPICS = ("completed", "done")

# The option matching cards that carry no epic at all. Stored as None because
# that is what the column holds.
NO_EPIC_LABEL = "No epic"

# The scope every count is taken over: the Board. It is the view the button
# lives on and the one whose emptiness is felt.
COUNT_SCOPE = "SELECT COUNT(*) FROM task t WHERE t.stage='active'"


def name_width() -> int:
    """The room an option's name has on its row.

    What is left of the panel once its padding, the row's own, the tick box and
    the count have taken theirs. A name past it is elided and carried by the
    row's tooltip, so an epic named at length never pushes its count off the
    edge.
    """
    return LAYOUT["filter_menu_w"] - space("2xl") * 3 - space("lg")


class FilterState:
    """The ticked options, and the SQL fragment they mean.

    The fragment is appended to a query that already has a ``WHERE``, and the
    parameters it returns follow that query's own in order.
    """

    def __init__(self) -> None:
        self.assignees: set[str] = set()
        self.epics: set = set()  # epic ids; None is the no-epic option

    # ----- what is set ------------------------------------------------------

    def count(self) -> int:
        """How many options are ticked, across every section."""
        return len(self.assignees) + len(self.epics)

    def any_set(self) -> bool:
        return bool(self.assignees or self.epics)

    def holds(self, kind: str, value) -> bool:
        return value in (self.assignees if kind == ASSIGNEE else self.epics)

    def sole_epic(self) -> int | None:
        """The one real epic this state names, or None.

        A new card defaults to the epic being filtered for only while exactly
        one is named — two epics name no default, and the no-epic option names
        the absence of one.
        """
        if len(self.epics) != 1:
            return None
        only = next(iter(self.epics))
        return only if isinstance(only, int) else None

    # ----- changing it ------------------------------------------------------

    def toggle(self, kind: str, value) -> None:
        chosen = self.assignees if kind == ASSIGNEE else self.epics
        chosen.symmetric_difference_update({value})

    def discard(self, kind: str, value) -> None:
        (self.assignees if kind == ASSIGNEE else self.epics).discard(value)

    def clear(self) -> None:
        self.assignees.clear()
        self.epics.clear()

    # ----- what it means to a query ----------------------------------------

    def where(self, alias: str = "t") -> tuple[str, list]:
        """The fragment and its parameters. Empty strings when nothing is set."""
        clauses: list[str] = []
        params: list = []
        if self.assignees:
            names = sorted(self.assignees)
            marks = ", ".join("?" * len(names))
            clauses.append(f"COALESCE({alias}.assignee, 'user') IN ({marks})")
            params.extend(names)
        if self.epics:
            ids = sorted(e for e in self.epics if e is not None)
            either: list[str] = []
            if ids:
                either.append(f"{alias}.epic_id IN ({', '.join('?' * len(ids))})")
                params.extend(ids)
            if None in self.epics:
                either.append(f"{alias}.epic_id IS NULL")
            clauses.append("(" + " OR ".join(either) + ")")
        if not clauses:
            return "", []
        return " AND " + " AND ".join(clauses), params


# ---------------------------------------------------------------------------
# The options a board offers, and what each one would show
# ---------------------------------------------------------------------------

def _rows(conn: sqlite3.Connection, query: str, params=()) -> list:
    try:
        return conn.execute(query, params).fetchall()
    except sqlite3.OperationalError:
        return []


def assignee_options(conn: sqlite3.Connection, state: FilterState) -> list[tuple]:
    """Every owner the board holds, as ``(value, label)``.

    ``user`` is offered always, as the owner a card carries when nothing else
    claims it. An option that is ticked is offered even where the board no
    longer holds a card for it, so it can be un-ticked.
    """
    present = {row[0] for row in _rows(
        conn, "SELECT DISTINCT COALESCE(assignee, 'user') FROM task "
              "WHERE stage='active'")}
    present.update({"user"}, state.assignees)
    rest = sorted(name for name in present if name != "user")
    return [(name, name) for name in ["user", *rest]]


def epic_options(conn: sqlite3.Connection, state: FilterState) -> list[tuple]:
    """Every epic in play, as ``(value, label)``, plus the no-epic option.

    Order is the epic table's, so the panel reads in the order the board was
    built. The no-epic option is offered where the board holds a card with no
    epic, or where it is already ticked.
    """
    options = [(eid, name) for eid, name, status in _rows(
        conn, "SELECT id, name, status FROM epic ORDER BY id")
        if (status or "").lower() not in FINISHED_EPICS]
    orphans = _rows(
        conn, "SELECT COUNT(*) FROM task WHERE stage='active' AND epic_id IS NULL")
    if (orphans and orphans[0][0]) or None in state.epics:
        options.append((None, NO_EPIC_LABEL))
    return options


def option_count(conn: sqlite3.Connection, state: FilterState,
                 kind: str, value) -> int:
    """How many board cards this one option matches, under the other sections."""
    probe = FilterState()
    probe.assignees = {value} if kind == ASSIGNEE else set(state.assignees)
    probe.epics = {value} if kind == EPIC else set(state.epics)
    where, params = probe.where("t")
    found = _rows(conn, COUNT_SCOPE + where, tuple(params))
    return found[0][0] if found else 0


def applied(conn: sqlite3.Connection, state: FilterState) -> list[tuple]:
    """Each ticked option as ``(kind, value, label)``, in the panel's order."""
    chips = [(ASSIGNEE, value, label)
             for value, label in assignee_options(conn, state)
             if state.holds(ASSIGNEE, value)]
    chips += [(EPIC, value, label)
              for value, label in epic_options(conn, state)
              if state.holds(EPIC, value)]
    return chips


# ---------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------

class _FacetRow(QWidget):
    """One option: a box, its name, and its count — the whole row a click."""

    def __init__(self, label: str, checked: bool, on_toggle) -> None:
        super().__init__()
        self.setObjectName("facetRow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(label)

        self.box = QCheckBox()
        self.box.setChecked(checked)
        room = name_width()
        self.box.setText(QFontMetrics(self.box.font()).elidedText(
            label, Qt.ElideRight, room))
        self.box.setMaximumWidth(room + space("2xl"))
        self.box.toggled.connect(lambda _checked: on_toggle())

        self.count = QLabel("")
        self.count.setObjectName("facetCount")
        self.count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.count.setMinimumWidth(space("2xl"))

        row = QHBoxLayout(self)
        row.setContentsMargins(space("md"), space("sm"), space("md"), space("sm"))
        row.setSpacing(space("md"))
        row.addWidget(self.box)
        row.addStretch(1)
        row.addWidget(self.count)

    def set_count(self, found: int) -> None:
        self.count.setText(str(found))

    def mousePressEvent(self, event):  # noqa: N802 (Qt override)
        """A click anywhere on the row is a click on its box."""
        self.box.toggle()


class FilterMenu(QWidget):
    """The panel under the Filter button. ``changed`` fires on every toggle."""

    changed = Signal()

    def __init__(self, parent, conn: sqlite3.Connection, state: FilterState) -> None:
        super().__init__(parent, Qt.Popup)
        self.conn = conn
        self.state = state
        self._rows: list[tuple[str, object, _FacetRow]] = []

        # The popup is a transparent frame holding one panel, so the panel's
        # rounded corners are drawn against nothing rather than against the
        # square corners of a window.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame()
        panel.setObjectName("filterMenu")
        panel.setFixedWidth(LAYOUT["filter_menu_w"])
        outer.addWidget(panel)

        body = QVBoxLayout(panel)
        body.setContentsMargins(space("lg"), space("lg"), space("lg"), space("lg"))
        body.setSpacing(space("md"))

        title = QLabel("Filter")
        title.setObjectName("filterTitle")
        self.clear_btn = QPushButton("Clear all")
        self.clear_btn.setObjectName("filterClear")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.clear_btn)
        body.addLayout(head)

        self._sections = QVBoxLayout()
        self._sections.setContentsMargins(0, 0, 0, 0)
        self._sections.setSpacing(space("lg"))
        holder = QWidget()
        holder.setLayout(self._sections)

        scroll = QScrollArea()
        scroll.setObjectName("filterScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(LAYOUT["filter_menu_max_h"])
        scroll.setWidget(holder)
        body.addWidget(scroll)

        footer = QLabel("Counts are cards on the Board.")
        footer.setObjectName("formCaption")
        body.addWidget(footer)

    # ----- opening ----------------------------------------------------------

    def open_under(self, anchor: QWidget) -> None:
        """Build the panel over the board as it now stands, under ``anchor``."""
        self._build()
        self.adjustSize()
        corner = anchor.mapToGlobal(anchor.rect().bottomLeft())
        left, top = corner.x(), corner.y() + space("sm")
        screen = self.screen() or anchor.screen()
        if screen is not None:
            room = screen.availableGeometry()
            left = max(room.left(), min(left, room.right() - self.width()))
            top = min(top, room.bottom() - self.height())
        self.move(left, top)
        self.show()

    def keyPressEvent(self, event):  # noqa: N802 (Qt override)
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    # ----- contents ---------------------------------------------------------

    def _build(self) -> None:
        """Fill the panel with the options the board currently offers."""
        self._rows.clear()
        while self._sections.count():
            item = self._sections.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for kind, heading, options in (
            (ASSIGNEE, "Assignee", assignee_options(self.conn, self.state)),
            (EPIC, "Epic", epic_options(self.conn, self.state)),
        ):
            self._sections.addWidget(self._section(kind, heading, options))
        self.refresh()

    def _section(self, kind: str, heading: str, options: list[tuple]) -> QWidget:
        section = QWidget()
        column = QVBoxLayout(section)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(space("xs"))

        label = QLabel(heading.upper())
        label.setObjectName("facetHeading")
        column.addWidget(label)

        for value, caption in options:
            row = _FacetRow(caption, self.state.holds(kind, value),
                            lambda k=kind, v=value: self._toggled(k, v))
            column.addWidget(row)
            self._rows.append((kind, value, row))
        return section

    def refresh(self) -> None:
        """Re-read every count and every tick from the state."""
        for kind, value, row in self._rows:
            row.box.blockSignals(True)
            row.box.setChecked(self.state.holds(kind, value))
            row.box.blockSignals(False)
            row.set_count(option_count(self.conn, self.state, kind, value))
        self.clear_btn.setEnabled(self.state.any_set())

    def _toggled(self, kind: str, value) -> None:
        self.state.toggle(kind, value)
        self.refresh()
        self.changed.emit()

    def _clear(self) -> None:
        self.state.clear()
        self.refresh()
        self.changed.emit()
