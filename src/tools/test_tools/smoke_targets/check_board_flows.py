"""smoke_targets/check_board_flows.py — the `board_flows` smoke target, run by smoke.py.

Drives Bristol Tickets' core board flows through its real window on Qt's
offscreen platform, the way a person at the window works them: create a card,
edit its title and description, move it between columns and reorder a column,
link two cards and see the link from both, attach an image, close a card to
done, search by title, pick an agent in the top bar and see Settings agree, and
change a setting and read it back after the window is rebuilt. Each flow asserts
on the board database, read through a second connection so only what was
committed counts, and on the widgets. A failure gives the flow and the step.

Everything the window writes lands in one temporary folder: the board, its
images and the configuration, with ``HOME`` and ``XDG_CONFIG_HOME`` pointed
there too. The installation's own ``config/config.local.json`` is compared
before and after, and a run that changed it fails.

Three inputs are supplied rather than performed. A drag runs a nested loop of
the platform's own that no script can steer, so a drop is handed to the column
as the event a finished drag delivers. The image comes from a stand-in for the
operating system's file picker. A list is opened and its row clicked, as a
person chooses from it.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

from qt_headless import PROJECT_ROOT, TOOLS, offscreen_app, tool_on_path
from smoke_targets.failure import SmokeFailure

if TYPE_CHECKING:
    from PySide6.QtWidgets import QDialog

# How long one window may take to open after the step that opens it, and to
# close after the step that answers it, before the step fails rather than hangs.
MODAL_WAIT_S = 5.0

# The seeded board: a standing workstream, one project and two cards to reorder
# and link.
PROJECT_EPIC = "Board Flows"
FIRST_CARD = "Seeded first"
SECOND_CARD = "Seeded second"

NEW_TITLE = "Card made by the board flows"
EDITED_TITLE = "Card edited by the board flows"
EDITED_DESCRIPTION = "A description typed into the record window."


class _Run:
    """The flow and step in progress, and what went wrong outside a step's
    own code: a notice the app raised, or an exception a slot threw."""

    def __init__(self) -> None:
        self.flow = ""
        self.notices: list[str] = []
        self.slot_errors: list[str] = []


RUN = _Run()


@contextmanager
def _step(name: str):
    """Run one step; any failure in it, or any notice or slot exception it
    caused, fails the target with the flow and the step."""
    from PySide6.QtWidgets import QApplication

    RUN.notices.clear()
    RUN.slot_errors.clear()
    try:
        yield
        QApplication.processEvents()
        if RUN.slot_errors:
            raise SmokeFailure(f"the app raised {RUN.slot_errors[0]}")
        if RUN.notices:
            raise SmokeFailure(f"the app showed a notice: {RUN.notices[0]}")
    except SmokeFailure as exc:
        raise SmokeFailure(f"{RUN.flow}, step '{name}': {exc}") from None
    except Exception as exc:
        raise SmokeFailure(f"{RUN.flow}, step '{name}': {exc.__class__.__name__}: {exc}") from exc


def _settle() -> None:
    from PySide6.QtWidgets import QApplication

    for _ in range(3):
        QApplication.processEvents()


def _through_modal(open_it, answer) -> None:
    """Run ``open_it``, which opens a modal window and waits on it, and answer
    that window with ``answer(window)`` once it is up."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    seen: dict = {}
    deadline = time.monotonic() + MODAL_WAIT_S

    def close_if_still_open() -> None:
        window = seen["window"]
        if window.isVisible():
            seen.setdefault("error", SmokeFailure(f"'{window.windowTitle()}' did not close"))
            window.done(0)

    def poll() -> None:
        window = cast("QDialog | None", QApplication.activeModalWidget())
        if window is None:
            if time.monotonic() < deadline:
                QTimer.singleShot(10, poll)
            return
        seen["window"] = window
        try:
            answer(window)
        except Exception as exc:
            seen["error"] = exc
            window.done(0)
            return
        QTimer.singleShot(int(MODAL_WAIT_S * 1000), close_if_still_open)

    QTimer.singleShot(0, poll)
    open_it()
    _settle()
    if "error" in seen:
        raise seen["error"]
    if "window" not in seen:
        raise SmokeFailure("no window opened")


def _click(widget) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    if not widget.isEnabled():
        raise SmokeFailure(f"'{widget.text() or widget.accessibleName()}' is not enabled")
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton)


def _type(field, text: str) -> None:
    """Replace what a text field contains with ``text``, typed."""
    from PySide6.QtTest import QTest

    field.setFocus()
    field.selectAll()
    field.clear()
    QTest.keyClicks(field, text)


def _choose(combo, value) -> None:
    """Open a picker's list and click the row whose value is ``value``."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    index = combo.findData(value)
    if index < 0:
        raise SmokeFailure(f"the picker offers no {value!r}")
    combo.showPopup()
    _settle()
    view = combo.view()
    rect = view.visualRect(combo.model().index(index, combo.modelColumn()))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
    _settle()
    if combo.currentData() != value:
        raise SmokeFailure(f"choosing {value!r} left the picker on {combo.currentData()!r}")


def _item(column, task_id: int):
    from PySide6.QtCore import Qt

    view = column.list_widget
    for row in range(view.count()):
        if view.item(row).data(Qt.ItemDataRole.UserRole) == task_id:
            return view.item(row)
    return None


def _ids(column) -> list[int]:
    from PySide6.QtCore import Qt

    view = column.list_widget
    return [view.item(row).data(Qt.ItemDataRole.UserRole) for row in range(view.count())]


def _click_card(column, task_id: int, double: bool = False) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    item = _item(column, task_id)
    if item is None:
        raise SmokeFailure(f"#{task_id} is not in the {column.status_key or 'backlog'} column")
    view = column.list_widget
    view.scrollToItem(item)
    point = view.visualItemRect(item).center()
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    if double:
        # A view opens what it was pressed on, so the second press follows a first.
        QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=point)
    _settle()


class _Drop:
    """The event a finished drag delivers to the list it ends on: where it
    landed and which list it came from."""

    def __init__(self, source, point) -> None:
        self._source = source
        self._point = point
        self.accepted = False

    def source(self):
        return self._source

    def position(self):
        from PySide6.QtCore import QPointF

        return QPointF(self._point)

    def acceptProposedAction(self) -> None:  # noqa: N802 (the name a drop event has)
        self.accepted = True

    def ignore(self) -> None:
        self.accepted = False


def _drag(from_column, task_id: int, to_column, onto_id: int | None = None) -> None:
    """Pick ``task_id`` up in ``from_column`` and drop it on ``to_column``,
    on the card ``onto_id`` or below the last card."""
    item = _item(from_column, task_id)
    if item is None:
        raise SmokeFailure(f"#{task_id} is not in the {from_column.status_key} column")
    source = from_column.list_widget
    source.clearSelection()
    source.setCurrentItem(item)
    item.setSelected(True)
    target = to_column.list_widget
    if onto_id is None:
        point = target.viewport().rect().bottomLeft()
        point.setY(point.y() - 1)
    else:
        onto = _item(to_column, onto_id)
        if onto is None:
            raise SmokeFailure(f"#{onto_id} is not in the {to_column.status_key} column")
        point = target.visualItemRect(onto).center()
    drop = _Drop(source, point)
    target.dropEvent(drop)
    if not drop.accepted:
        raise SmokeFailure("the column refused the drop")
    _settle()


def _row(look: sqlite3.Connection, task_id: int, *fields: str):
    row = look.execute(f"SELECT {', '.join(fields)} FROM task WHERE id=?", (task_id,)).fetchone()
    if row is None:
        raise SmokeFailure(f"#{task_id} is not on the board")
    return row


def _link_rows(link_bar) -> list[str]:
    """The tooltip of every row a link bar lists: 'Ticket #N' for a card."""
    from PySide6.QtWidgets import QWidget

    tips = []
    for index in range(link_bar.rows.count()):
        row = link_bar.rows.row(index)
        if row is None:
            continue
        tips += [
            w.toolTip() for w in row.findChildren(QWidget) if w.toolTip().startswith("Ticket #")
        ]
    return tips


def _provision(folder: Path) -> Path:
    """A board built from schema.sql, with a standing workstream, one project
    and two cards."""
    db = folder / "tickets" / "tickets.db"
    db.parent.mkdir(parents=True)
    conn = sqlite3.connect(db)
    conn.executescript((TOOLS / "bristol" / "schema.sql").read_text())
    conn.execute(
        "INSERT INTO epic (name, type, status, owner) VALUES ('Upkeep','standing','active','user')"
    )
    conn.execute(
        "INSERT INTO epic (name, type, status, owner) VALUES (?, 'project', 'active', 'user')",
        (PROJECT_EPIC,),
    )
    epic = conn.execute("SELECT id FROM epic WHERE name=?", (PROJECT_EPIC,)).fetchone()[0]
    for order, title in enumerate((FIRST_CARD, SECOND_CARD)):
        conn.execute(
            "INSERT INTO task (epic_id, title, description, status, stage, sort_order, "
            "record_type, assignee, reporter, created_at, updated_at) "
            "VALUES (?, ?, 'd', 'todo', 'active', ?, 'build', 'user', 'user', "
            "'2026-11-20', '2026-11-20')",
            (epic, title, order),
        )
    conn.commit()
    conn.close()
    return db


def check_board_flows() -> list[str]:
    ok: list[str] = []
    sandbox = Path(tempfile.mkdtemp(prefix="bristol_board_flows_"))
    real_config = PROJECT_ROOT / "config" / "config.local.json"
    real_before = real_config.read_bytes() if real_config.is_file() else None
    try:
        _flows(sandbox, ok)
    finally:
        real_after = real_config.read_bytes() if real_config.is_file() else None
        shutil.rmtree(sandbox, ignore_errors=True)
    if real_after != real_before:
        raise SmokeFailure("the run changed the installation's config/config.local.json")
    ok.append("the installation's configuration is as it was")
    return ok


def _flows(sandbox: Path, ok: list[str]) -> None:
    # Every place the window resolves a file from points into the sandbox
    # before any of its modules is imported.
    os.environ["HOME"] = str(sandbox)
    os.environ["XDG_CONFIG_HOME"] = str(sandbox / ".config")
    config = sandbox / "config" / "config.local.json"
    config.parent.mkdir(parents=True)
    shutil.copyfile(PROJECT_ROOT / "config" / "config.example.json", config)
    db = _provision(sandbox)

    tool_on_path("bristol")
    app = offscreen_app()

    import config_file

    config_file.path = lambda: config

    import ui.attachments as attachments_module
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtTest import QTest
    from ui.main_window import MainWindow
    from ui.theme import install_typeface

    install_typeface(app)

    # A notice the app raises is recorded for the step to fail on, rather than
    # opened over a window nobody is there to close.
    def _record_notice(_parent, title, body, *_args, **_kwargs) -> None:
        RUN.notices.append(f"{title}: {body}")

    for name, module in list(sys.modules.items()):
        if name.startswith("ui.") and getattr(module, "notify", None) is not None:
            vars(module)["notify"] = _record_notice

    def _record_slot_error(kind, value, _tb) -> None:
        RUN.slot_errors.append(f"{kind.__name__}: {value}")

    sys.excepthook = _record_slot_error

    look = sqlite3.connect(db)
    conn = sqlite3.connect(db, timeout=10)
    win = MainWindow(conn, initial_db=db)
    win.show()
    _settle()
    todo, doing, done = win.columns["todo"], win.columns["doing"], win.columns["done"]
    first = look.execute("SELECT id FROM task WHERE title=?", (FIRST_CARD,)).fetchone()[0]
    second = look.execute("SELECT id FROM task WHERE title=?", (SECOND_CARD,)).fetchone()[0]
    project = look.execute("SELECT id FROM epic WHERE name=?", (PROJECT_EPIC,)).fetchone()[0]

    # ----- create ------------------------------------------------------------
    RUN.flow = "create a card"
    with _step("fill and save the record window"):

        def fill_new(dialog) -> None:
            _type(dialog.title_edit, NEW_TITLE)
            _choose(dialog.epic_combo, project)
            _click(dialog.ok_button)

        _through_modal(lambda: _click(win.global_create_btn), fill_new)
    with _step("the board has the card"):
        row = look.execute(
            "SELECT id, status, stage, epic_id FROM task WHERE title=?", (NEW_TITLE,)
        ).fetchone()
        if row is None:
            raise SmokeFailure("no card with the title typed")
        card, status, stage, epic_id = row
        if (status, stage, epic_id) != ("todo", "active", project):
            raise SmokeFailure(f"it was stored {status}, {stage}, epic {epic_id}")
    with _step("the To Do column shows it"):
        if _item(todo, card) is None:
            raise SmokeFailure(f"#{card} is not in To Do")
    ok.append("create: the record window's card is stored in To Do and drawn there")

    # ----- edit --------------------------------------------------------------
    RUN.flow = "edit a card"
    with _step("double-click the card and retype its title and description"):

        def retype(dialog) -> None:
            _type(dialog.title_edit, EDITED_TITLE)
            _type(dialog.desc_edit, EDITED_DESCRIPTION)
            _click(dialog.ok_button)

        _through_modal(lambda: _click_card(todo, card, double=True), retype)
    with _step("the board has the new text"):
        title, description = _row(look, card, "title", "description")
        if (title, description) != (EDITED_TITLE, EDITED_DESCRIPTION):
            raise SmokeFailure(f"it stored {title!r} and {description!r}")
    with _step("the card and the detail pane show it"):
        from ui.card_delegate import CARD_ROLE

        item = _item(todo, card)
        if item is None or item.data(CARD_ROLE)["title"] != EDITED_TITLE:
            raise SmokeFailure("the card on the board still has the old title")
        _click_card(todo, card)
        if win.detail_pane.title.text() != f"#{card} {EDITED_TITLE}":
            raise SmokeFailure(f"the pane's title reads {win.detail_pane.title.text()!r}")
        if win.detail_pane.desc.toPlainText() != EDITED_DESCRIPTION:
            raise SmokeFailure("the pane's description is not the one typed")
    ok.append("edit: a retyped title and description are stored and drawn")

    # ----- move and reorder --------------------------------------------------
    RUN.flow = "move and reorder"
    with _step("drop the card on Doing"):
        _drag(todo, card, doing)
        status, stage = _row(look, card, "status", "stage")
        if (status, stage) != ("doing", "active"):
            raise SmokeFailure(f"it was stored {status}, {stage}")
        if _item(doing, card) is None or _item(todo, card) is not None:
            raise SmokeFailure("the card is not drawn in Doing alone")
    with _step("drop the second seeded card on the first"):
        if _ids(todo)[:2] != [first, second]:
            raise SmokeFailure(f"To Do opened in the order {_ids(todo)}")
        _drag(todo, second, todo, onto_id=first)
        stored = [
            r[0]
            for r in look.execute(
                "SELECT id FROM task WHERE stage='active' AND status='todo' ORDER BY sort_order, id"
            )
        ]
        if stored[:2] != [second, first]:
            raise SmokeFailure(f"the stored order is {stored}")
        if _ids(todo)[:2] != [second, first]:
            raise SmokeFailure(f"To Do is drawn in the order {_ids(todo)}")
    ok.append("move and reorder: a drop between columns and within one is stored and drawn")

    # ----- link --------------------------------------------------------------
    RUN.flow = "link two cards"
    with _step("add a link from the first seeded card to the second"):
        _click_card(todo, first)

        def link_to_second(dialog) -> None:
            _type(dialog.issue_input, str(second))
            _click(dialog.add_button)

        _through_modal(lambda: _click(win.detail_pane.links.add_btn), link_to_second)
    with _step("the board has the link"):
        found = look.execute(
            "SELECT COUNT(*) FROM task_link WHERE "
            "(task_id=? AND other_id=?) OR (task_id=? AND other_id=?)",
            (first, second, second, first),
        ).fetchone()[0]
        if found != 1:
            raise SmokeFailure(f"{found} link rows join the two cards")
    with _step("each card's pane lists the other"):
        if _link_rows(win.detail_pane.links) != [f"Ticket #{second}"]:
            raise SmokeFailure(f"the first card's pane lists {_link_rows(win.detail_pane.links)}")
        _click_card(todo, second)
        if _link_rows(win.detail_pane.links) != [f"Ticket #{first}"]:
            raise SmokeFailure(f"the second card's pane lists {_link_rows(win.detail_pane.links)}")
    ok.append("link: a link added in the pane is stored once and listed from both cards")

    # ----- attach ------------------------------------------------------------
    RUN.flow = "attach an image"
    source = sandbox / "picked" / "screen.png"
    source.parent.mkdir()
    picture = QPixmap(40, 30)
    picture.fill(QColor("#336699"))
    picture.save(str(source))

    class _Picker:
        @staticmethod
        def getOpenFileName(*_args, **_kwargs):  # noqa: N802 (the name QFileDialog's has)
            return str(source), ""

    real_picker = attachments_module.QFileDialog
    attachments_module.QFileDialog = _Picker
    try:
        with _step("choose an image with Add Image"):
            _click(win.detail_pane.attachments.attach_btn)
    finally:
        attachments_module.QFileDialog = real_picker
    with _step("the board has the attachment and its file"):
        rows = look.execute(
            "SELECT filename, original_name FROM attachment WHERE task_id=?", (second,)
        ).fetchall()
        if len(rows) != 1 or rows[0][1] != "screen.png":
            raise SmokeFailure(f"the card has the attachment rows {rows}")
        if not (db.parent / "images" / rows[0][0]).is_file():
            raise SmokeFailure("the image was not copied beside the board")
        if not source.is_file():
            raise SmokeFailure("the picked file was moved rather than copied")
    with _step("the pane lists it"):
        if win.detail_pane.attachments.rows.count() != 1:
            raise SmokeFailure(f"the pane lists {win.detail_pane.attachments.rows.count()}")
    ok.append("attach: a picked image is copied beside the board, stored and listed")

    # ----- search ------------------------------------------------------------
    RUN.flow = "search by title"
    with _step("type a title into Search"):
        search_tab = next(b for b in win._tab_buttons if b.accessibleName() == "Search")
        _click(search_tab)
        win.search_input.setFocus()
        QTest.keyClicks(win.search_input, "edited by the board")
        QTest.keyClick(win.search_input, Qt.Key.Key_Return)
        _settle()
        lines = [win.search_results.row_text(r) for r in range(win.search_results.count())]
        if len(lines) != 1 or f"#{card}" not in lines[0] or EDITED_TITLE not in lines[0]:
            raise SmokeFailure(f"the results are {lines}")
    with _step("a title nothing has finds nothing"):
        _type(win.search_input, "no card is called this")
        QTest.keyClick(win.search_input, Qt.Key.Key_Return)
        _settle()
        if win.search_results.count() or win.search_count.text() != "No results":
            raise SmokeFailure(f"it reports {win.search_count.text()!r}")
        board_tab = next(b for b in win._tab_buttons if b.accessibleName() == "Board")
        _click(board_tab)
    ok.append("search: a title finds its card and an unknown one finds nothing")

    # ----- close to done -----------------------------------------------------
    RUN.flow = "close a card to done"
    with _step("set the card's status to Done in the pane"):
        _click_card(doing, card)
        _choose(win.detail_pane.status_combo, "done")
        _settle()
    with _step("the board has it done"):
        status, stage, closed_at = _row(look, card, "status", "stage", "closed_at")
        if (status, stage) != ("done", "active") or not closed_at:
            raise SmokeFailure(f"it was stored {status}, {stage}, closed {closed_at!r}")
    with _step("the Done column shows it"):
        if _item(done, card) is None or _item(doing, card) is not None:
            raise SmokeFailure("the card is not drawn in Done alone")
    ok.append("close: a project card set to Done is stored closed and waits in Done")

    # ----- agent -------------------------------------------------------------
    RUN.flow = "pick an agent"
    picker = win.agent_picker
    slugs = [picker.itemData(i) for i in range(picker.count())]
    other = next((s for s in slugs if s and s != picker.currentData()), None)
    with _step("choose another agent in the top bar"):
        if other is None:
            raise SmokeFailure(f"the picker offers only {slugs}")
        _choose(picker, other)
        if config_file.get("active_agent") != other:
            raise SmokeFailure(f"the configuration says {config_file.get('active_agent')!r}")
    with _step("Settings shows the same agent"):
        _click(win.settings_btn)
        _settle()
        if not win.settings_modal.isVisible():
            raise SmokeFailure("Settings did not open")
        shown = win.settings_tab.next_agent.currentData()
        if shown != other:
            raise SmokeFailure(f"Settings' Agent picker shows {shown!r}")
    ok.append(f"agent: {other} chosen in the top bar is stored and shown in Settings")

    # ----- setting -----------------------------------------------------------
    RUN.flow = "change a setting"
    with _step("set Ticket Destination to the Backlog"):
        win.settings_modal.show_tab("Sessions")
        _settle()
        _choose(win.settings_tab.new_ticket, "backlog")
        if config_file.get(config_file.NEW_TICKET_STAGE) != "backlog":
            raise SmokeFailure(f"the configuration says {config_file.get('board')!r}")
        win.settings_modal.close_modal()
    with _step("a rebuilt window reads it back"):
        win.close()
        conn.close()
        _settle()
        fresh = sqlite3.connect(db, timeout=10)
        rebuilt = MainWindow(fresh, initial_db=db)
        rebuilt.show()
        _settle()
        _click(rebuilt.settings_btn)
        _settle()
        rebuilt.settings_modal.show_tab("Sessions")
        if rebuilt.settings_tab.new_ticket.currentData() != "backlog":
            raise SmokeFailure(
                f"the rebuilt window shows {rebuilt.settings_tab.new_ticket.currentData()!r}"
            )
        if rebuilt.agent_picker.currentData() != other:
            raise SmokeFailure(f"the rebuilt top bar shows {rebuilt.agent_picker.currentData()!r}")
        rebuilt.settings_modal.close_modal()
        rebuilt.close()
        fresh.close()
    ok.append("setting: a choice made in Settings survives the window being rebuilt")
    look.close()
