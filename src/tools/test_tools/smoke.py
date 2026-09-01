#!/usr/bin/env python3
"""smoke.py — runtime-error smoke checks for the fleet's PySide6 GUI tools.

What it is: a fast "does it still build and run" check that goes beyond
``py_compile``. It constructs each GUI's real widgets on Qt's offscreen platform
and reports any import error, signal/slot mismatch, or construction-time
exception. What it is NOT: a visual check — offscreen paints nothing, so how a
window *looks* still needs a real display (the packaged Mac app).

Targets live in ``TARGETS`` below. Each is checked in its OWN subprocess because
every GUI tool ships a top-level package named ``ui`` (and its own ``app.py``),
which cannot coexist in one interpreter. Run everything, or one target:

    bash run_smoke.sh                 # provision env + check all targets
    bash run_smoke.sh bristol         # just one
    python3 smoke.py --target test_control   # single target, in-process

Exit code 0 = all green; non-zero = at least one target failed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sqlite3
import sys
from pathlib import Path

from qt_headless import TOOLS, offscreen_app, tool_on_path


class SmokeFailure(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Per-tool checks. Each runs in its own process with a clean sys.path, so it may
# freely ``import ui`` as that one tool's package. Return None; raise on failure.
# ---------------------------------------------------------------------------

def check_bristol() -> list[str]:
    import importlib
    import pkgutil
    import tempfile

    ok: list[str] = []
    tool_on_path("bristol")
    offscreen_app()

    import ui  # bristol/ui

    for mod in pkgutil.iter_modules(ui.__path__):
        importlib.import_module(f"ui.{mod.name}")
    ok.append("all ui.* modules import")

    from PySide6.QtGui import QColor, QPixmap

    from ui.attachments import AttachmentBar, ImagePreviewDialog

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE attachment(id INTEGER PRIMARY KEY, task_id INT, "
        "filename TEXT, original_name TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO attachment(task_id,filename,original_name,created_at) "
        "VALUES (7,'missing.png','missing.png','x')"
    )
    conn.commit()
    bar = AttachmentBar(conn)
    bar.set_task(7)  # _refresh over a file that isn't on disk (placeholder path)
    ok.append("AttachmentBar refresh (missing-file placeholder)")

    ImagePreviewDialog(Path("/does/not/exist.png"), "missing.png")
    tmp = Path(tempfile.gettempdir()) / "smoke_real.png"
    pm = QPixmap(320, 200)
    pm.fill(QColor("steelblue"))
    pm.save(str(tmp))
    dlg = ImagePreviewDialog(tmp, "smoke_real.png")
    if dlg.deleted():
        raise SmokeFailure("fresh ImagePreviewDialog should not report deleted()")
    ok.append("ImagePreviewDialog builds (missing + real image)")

    # The appearance manager, before anything paints. An incomplete scheme is a
    # KeyError in the middle of a paint, so it is named here instead.
    import ui.theme as theme

    gaps = theme.check_schemes()
    if gaps:
        raise SmokeFailure("incomplete colour scheme — " + "; ".join(gaps))
    ok.append(f"all {len(theme.SCHEMES)} colour schemes carry the same keys")

    for value, _caption in theme.CHOICES:
        for dark in (False, True):
            name = theme.resolve_choice(value, dark)
            if name not in theme.SCHEMES:
                raise SmokeFailure(f"choice {value!r} resolves to no scheme")
            theme.set_scheme(name)
            if theme.current_scheme() != name or not theme.build_style_sheet():
                raise SmokeFailure(f"scheme {name!r} does not become live")
    if theme.resolve_choice("a_scheme_from_a_newer_build", False) \
            != theme.FAMILIES[theme.DEFAULT_CHOICE][0]:
        raise SmokeFailure("an unrecognised scheme name does not fall back")
    theme.set_scheme(theme.resolve_choice(theme.DEFAULT_CHOICE, False))
    ok.append("every offered choice resolves, applies and renders a stylesheet")

    for scale in (theme.SPACE, theme.RADIUS, theme.TYPE):
        if not all(isinstance(step, int) and step > 0 for step in scale.values()):
            raise SmokeFailure("a token scale holds something that is not a size")
    ok.append("the spacing, radius and type scales are whole sizes")

    # Every question and every notice comes from ui/dialogs.py, so none of them
    # arrives as the platform's own box with its glyph and its button ranks.
    import ui.dialogs as dialogs

    strays = sorted(
        source.name for source in Path(ui.__path__[0]).glob("*.py")
        if "QMessageBox" in source.read_text(encoding="utf-8")
    )
    if strays:
        raise SmokeFailure("QMessageBox reached " + ", ".join(strays)
                           + " — confirmations come from ui/dialogs.py")
    box = dialogs.Modal(None, "Title", "Body",
                        [("Cancel", dialogs.ORDINARY, False),
                         ("Delete", dialogs.DESTRUCTIVE, True)])
    if box.choice() is not False:
        raise SmokeFailure("a closed confirmation does not land on the way out")
    ok.append("every confirmation and notice comes from ui/dialogs.py")

    # The card painter reads tokens rather than holding literals, so a change to
    # a scale must reach it with no edit there.
    from ui.card_delegate import CardDelegate

    delegate = CardDelegate()
    before = (delegate.PAD, delegate.GAP, delegate.MARGIN)
    theme.SPACE["lg"] += 5
    try:
        if delegate.PAD == before[0]:
            raise SmokeFailure("the card painter does not read the spacing scale")
    finally:
        theme.SPACE["lg"] -= 5
    if (delegate.PAD, delegate.GAP, delegate.MARGIN) != before:
        raise SmokeFailure("the card painter did not follow the scale back")
    ok.append("the card painter's geometry follows the token scales")

    # Paint a card under every scheme. A palette key the painter reads and a
    # scheme lacks surfaces here rather than on the user's board.
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtWidgets import QStyleOptionViewItem

    class _Cell:
        def __init__(self, payload):
            self._payload = payload

        def data(self, role):
            from ui.theme import CARD_ROLE
            return self._payload if role == CARD_ROLE else None

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 260, 140)
    cell = _Cell({"title": "A card", "pressure": 85, "issue_id": 1,
                  "record_type": "fix", "epic_name": "An epic",
                  "owner": "user", "estimate": "M"})
    for name in theme.SCHEMES:
        theme.set_scheme(name)
        pixmap = QPixmap(260, 140)
        painter = QPainter(pixmap)
        try:
            CardDelegate(show_checkbox=True).paint(painter, option, cell)
        finally:
            painter.end()
    theme.set_scheme(theme.resolve_choice(theme.DEFAULT_CHOICE, False))
    ok.append("a card paints under every scheme")

    schema = TOOLS / "bristol" / "schema.sql"
    if schema.exists():
        from PySide6.QtCore import Qt

        from ui.main_window import MainWindow

        mconn = sqlite3.connect(":memory:")
        mconn.executescript(schema.read_text())

        def _seed(title, stage, status, sort_order, pressure=0):
            mconn.execute(
                "INSERT INTO task (title, description, status, stage, sort_order, "
                "pressure, record_type, assignee, reporter, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?, 'build','user','user','2026-07-08','2026-07-08')",
                (title, "d", status, stage, sort_order, pressure))
            return mconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        _seed("active todo", "active", "todo", 0, 50)
        b1 = _seed("backlog one", "backlog", "todo", 0, 90)
        b2 = _seed("backlog two", "backlog", "todo", 1, 80)
        _seed("archived", "archive", "done", 0)
        mconn.commit()

        win = MainWindow(mconn)
        if hasattr(win, "handoff_note_edit"):
            raise SmokeFailure("Handoff tab still present — it is retired")
        tab_names = {b.text() for b in win._tab_buttons}
        if "Handoff" in tab_names:
            raise SmokeFailure("Handoff tab still present — it is retired")
        if len(win._tab_buttons) != win.pages.count():
            raise SmokeFailure("a view exists with no tab, or a tab with no view")
        if sum(1 for b in win._tab_buttons if b.isChecked()) != 1:
            raise SmokeFailure("exactly one view tab is selected at a time")
        if mconn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='handoff'"
        ).fetchone():
            raise SmokeFailure("handoff table survived schema_guard")
        ok.append("MainWindow builds; Handoff tab and table are gone")

        # Kanban stage model: tabs populate from task.stage.
        win._refresh_board()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("Board To Do should show the one active/todo task")
        if win.backlog_column.list_widget.count() != 2:
            raise SmokeFailure("Backlog should show two backlog tasks")
        if win.archive_results.count() != 1:
            raise SmokeFailure("Archive should show one archived task")
        ok.append("Board/Backlog/Archive populate by stage")

        # Where a control sits says what it reaches. Refresh reloads every
        # view, so it is in the header beside Create and reachable from any
        # tab; Clear Done touches the Board alone, so it is on the board's
        # control row; a column header carries no control at all, which is
        # what keeps the three names and counts on one line.
        from PySide6.QtWidgets import QPushButton

        header_bar = win.centralWidget().layout().itemAt(0).widget()
        header_layout = header_bar.layout()
        header_buttons = [
            header_layout.itemAt(i).widget().text()
            for i in range(header_layout.count())
            if isinstance(header_layout.itemAt(i).widget(), QPushButton)]
        if header_buttons[-2:] != ["Refresh", "Create"]:
            raise SmokeFailure(
                f"header should end on Refresh then Create, got {header_buttons}")
        if header_layout.getContentsMargins()[3] <= 0:
            raise SmokeFailure("the header's controls sit on its closing hairline")
        board_row = win.pages.widget(win._board_tab_index).layout().itemAt(0).layout()
        board_buttons = [
            board_row.itemAt(i).widget().text()
            for i in range(board_row.count())
            if isinstance(board_row.itemAt(i).widget(), QPushButton)]
        if board_buttons[-1] != "Clear Done":
            raise SmokeFailure(
                f"Clear Done should end the board's control row, got {board_buttons}")
        for key, column in win.columns.items():
            if column.findChildren(QPushButton):
                raise SmokeFailure(f"the {key} column header carries a control")
        win._show_page(0)
        win.refresh_btn.click()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("Refresh did not reload the board from another tab")
        win._show_page(win._board_tab_index)
        ok.append("Refresh and Create are the header's; Clear Done is the "
                  "board's; a column header holds no control")

        # ---- What the board is showing ------------------------------------
        # One filter state narrows the board, the Backlog and the Archive and
        # leaves Search alone; the control row says what it holds.
        import ui.filter_menu as fm

        mconn.execute(
            "INSERT INTO epic (name, status) VALUES ('An epic', 'in progress')")
        live_epic = mconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        mconn.execute(
            "INSERT INTO epic (name, status) VALUES ('A closed epic', 'completed')")
        theirs = _seed("theirs", "active", "todo", 1)
        mconn.execute("UPDATE task SET assignee='librarian', epic_id=? WHERE id=?",
                      (live_epic, theirs))
        mconn.commit()
        win._refresh_board()
        if win.columns["todo"].list_widget.count() != 2:
            raise SmokeFailure("an unfiltered board should hold every active card")

        owners = [value for value, _caption in fm.assignee_options(mconn, win.filters)]
        if owners[0] != "user" or "librarian" not in owners:
            raise SmokeFailure("the assignee facet does not offer the board's owners")
        offered = [value for value, _caption in fm.epic_options(mconn, win.filters)]
        if live_epic not in offered or None not in offered:
            raise SmokeFailure("the epic facet offers neither the epic nor the cards without one")
        if len(offered) != 2:
            raise SmokeFailure("the epic facet offers a finished epic")

        win.filters.toggle(fm.ASSIGNEE, "librarian")
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("an assignee filter did not narrow the board")
        if win.backlog_column.list_widget.count() != 0:
            raise SmokeFailure("an assignee filter did not reach the Backlog")
        if win.archive_results.count() != 0:
            raise SmokeFailure("an assignee filter did not reach the Archive")
        if win.search_results.count() == 0:
            raise SmokeFailure("a filter reached Search, which must find anything")
        if win.filter_btn.text() != "Filter · 1" \
                or win.filter_btn.property("active") != "true":
            raise SmokeFailure("the Filter button does not carry what is set")
        if win.filter_clear_btn.isHidden():
            raise SmokeFailure("no Clear stands beside a filter that is set")
        if win.chip_row.count() != 1:
            raise SmokeFailure("a set filter is not on the control row as a chip")
        if win.backlog_filter_note.isHidden() or win.archive_filter_note.isHidden():
            raise SmokeFailure("a view holding cards back does not say so")

        win.filters.toggle(fm.ASSIGNEE, "user")
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 2:
            raise SmokeFailure("two options in one section should unite, not intersect")

        win.filters.toggle(fm.EPIC, live_epic)
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("two sections should intersect")
        if win.filters.sole_epic() != live_epic:
            raise SmokeFailure("one epic filter does not name a new card's epic")
        if fm.option_count(mconn, win.filters, fm.ASSIGNEE, "user") != 0 \
                or fm.option_count(mconn, win.filters, fm.ASSIGNEE, "librarian") != 1:
            raise SmokeFailure("a count ignores what the other section holds")
        win.filters.toggle(fm.EPIC, None)
        if win.filters.sole_epic() is not None:
            raise SmokeFailure("two epic options still named a default epic")
        win.filters.toggle(fm.EPIC, None)

        if len(fm.applied(mconn, win.filters)) != 3:
            raise SmokeFailure("the chips do not stand for every filter set")
        win._remove_filter(fm.EPIC, live_epic)
        if win.filters.holds(fm.EPIC, live_epic):
            raise SmokeFailure("removing a chip did not remove its filter")
        win._clear_filters()
        if win.filters.any_set() or win.chip_row.count():
            raise SmokeFailure("Clear left a filter behind")
        if win.filter_btn.text() != "Filter" \
                or win.filter_btn.property("active") != "false":
            raise SmokeFailure("the Filter button still reads as set")
        if not win.backlog_filter_note.isHidden() \
                or not win.archive_filter_note.isHidden():
            raise SmokeFailure("a view still says it is holding cards back")

        # The panel builds a row per option, and a click anywhere on a row is a
        # click on its box.
        panel = fm.FilterMenu(win, mconn, win.filters)
        panel._build()
        rows = {(kind, value) for kind, value, _row in panel._rows}
        if (fm.ASSIGNEE, "librarian") not in rows or (fm.EPIC, live_epic) not in rows:
            raise SmokeFailure("the filter panel does not build a row per option")
        moved: list[int] = []
        panel.changed.connect(lambda: moved.append(1))
        row = next(r for k, v, r in panel._rows if (k, v) == (fm.ASSIGNEE, "librarian"))
        row.mousePressEvent(None)
        if not win.filters.holds(fm.ASSIGNEE, "librarian") or not moved:
            raise SmokeFailure("a click on a row did not set the filter and report it")
        panel._clear()
        if win.filters.any_set():
            raise SmokeFailure("Clear all left a filter behind")

        win._on_filters_changed()
        mconn.execute("DELETE FROM task WHERE id=?", (theirs,))
        mconn.commit()
        win._refresh_board()
        ok.append("Filter: facets, conditional counts, union within a section, "
                  "intersection across them, chips and Clear")

        win.backlog_column._reorder_within([b2], 0)
        first = mconn.execute(
            "SELECT id FROM task WHERE stage='backlog' ORDER BY sort_order").fetchone()[0]
        if first != b2:
            raise SmokeFailure("backlog drag-reorder did not persist sort_order")
        ok.append("Backlog drag-reorder persists")

        lw = win.backlog_column.list_widget
        for i in range(lw.count()):
            if lw.item(i).data(Qt.UserRole) == b1:
                lw.item(i).setData(Qt.CheckStateRole, Qt.Checked)
        win._bulk_activate_backlog()
        st = mconn.execute("SELECT stage, status FROM task WHERE id=?", (b1,)).fetchone()
        if tuple(st) != ("active", "todo"):
            raise SmokeFailure("Backlog Activate did not move the card to the active board")
        ok.append("Backlog Activate → Board")

        # Clear Done: moves every Done card to the Archive, then writes the
        # analytic report. Confirm dialog is auto-accepted so the headless run
        # doesn't block.
        #
        # BRISTOL_REPORTS_DIR is redirected to a temp folder for the duration.
        # Without it the report resolver would find the real config and this
        # test would write a bogus report into the user's actual notebook —
        # a smoke check must not leave anything behind outside its sandbox.
        import os as _os
        import ui.main_window as mw
        mconn.execute("UPDATE task SET status='done' WHERE id=?", (b1,))
        mconn.commit()
        # The confirmation is a modal, so the answer is stubbed at the name the
        # window calls rather than left to block an offscreen run.
        _orig_confirm = mw.confirm
        mw.confirm = lambda *a, **k: True
        _prior_reports_dir = _os.environ.get("BRISTOL_REPORTS_DIR")
        with tempfile.TemporaryDirectory() as reports_tmp:
            _os.environ["BRISTOL_REPORTS_DIR"] = reports_tmp
            try:
                win._refresh_board()
                win._clear_done()
            finally:
                mw.confirm = _orig_confirm
                if _prior_reports_dir is None:
                    _os.environ.pop("BRISTOL_REPORTS_DIR", None)
                else:
                    _os.environ["BRISTOL_REPORTS_DIR"] = _prior_reports_dir
            written = sorted(Path(reports_tmp).glob("bristol_report_*.md"))
            if not written:
                raise SmokeFailure("Clear Done did not write an analytic report")
            body = written[0].read_text(encoding="utf-8")
            for required in ("# Bristol Tickets Report",
                             "#### Executive Summary",
                             "#### Headline Metrics", "#### Ledger"):
                if required not in body:
                    raise SmokeFailure(f"report is missing its {required!r} section")
            if not (Path(reports_tmp) / "_index.md").exists():
                raise SmokeFailure("Clear Done did not write the reports _index.md")
        moved = mconn.execute("SELECT stage FROM task WHERE id=?", (b1,)).fetchone()[0]
        if moved != "archive":
            raise SmokeFailure("Clear Done did not move the Done card to Archive")
        ok.append("Clear Done → Archive + analytic report written")

        # The transition log must capture the moves the UI just made, since
        # cycle time and work-item age are computed from nothing else. The moves
        # exercised above (Backlog Activate, Clear Done) are both *stage*
        # transitions — neither touches status — so `field='stage'` is the
        # invariant to assert here. Asserting `field='status'` was checking for
        # events these paths never produce.
        events = mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE field='stage'").fetchone()[0]
        if not events:
            raise SmokeFailure("no task_event rows written by UI board moves")
        swept = mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE field='stage' AND to_value='archive'"
        ).fetchone()[0]
        if not swept:
            raise SmokeFailure("Clear Done archived a card without logging the transition")
        ok.append(f"transition log records stage moves ({events} events)")

        # Create-modal Stage follows the active view, and lands on the board
        # from anywhere that is neither the Backlog nor the Archive — the same
        # default ticket_write.py add-task carries.
        win._show_page(win._board_tab_index)
        if win._stage_for_current_tab() != "active":
            raise SmokeFailure("Create from Board should default Stage=active")
        win._show_page(win._archive_tab_index)
        if win._stage_for_current_tab() != "archive":
            raise SmokeFailure("Create from Archive should default Stage=archive")
        win._show_page(win._backlog_tab_index)
        if win._stage_for_current_tab() != "backlog":
            raise SmokeFailure("Create from Backlog should default Stage=backlog")
        win._show_page(0)  # Search
        if win._stage_for_current_tab() != "active":
            raise SmokeFailure("Create away from the Backlog and Archive tabs "
                               "should default Stage=active")
        from ui.record_dialog import UnifiedRecordDialog as _RecordDialog
        if _RecordDialog(win, mconn, mode="task").stage_combo.currentData() \
                != "active":
            raise SmokeFailure("the Create dialog defaults a card to somewhere "
                               "other than the board")
        win._sync_backlog_bar()  # must not raise with nothing checked
        ok.append("Create-modal Stage follows active tab, and defaults to the board")

        # The detail pane edits in place: a status flipped from the pane takes
        # the same write path as a drag or a dialog save — the row moves and
        # the change-log triggers record it. Collapse must round-trip without
        # touching the configuration (save=False).
        pane = win.detail_pane
        pane.show_task(b2)
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("doing"))
        moved_status = mconn.execute(
            "SELECT status FROM task WHERE id=?", (b2,)).fetchone()[0]
        if moved_status != "doing":
            raise SmokeFailure("a pane status edit did not reach the database")
        logged = mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE task_id=? AND field='status' "
            "AND to_value='doing'", (b2,)).fetchone()[0]
        if not logged:
            raise SmokeFailure("a pane edit was not recorded by the change-log triggers")
        win._set_pane_collapsed(True, save=False)
        if not win.detail_pane.isHidden():
            raise SmokeFailure("collapsing did not hide the detail pane")
        if win.pane_reveal.isHidden():
            raise SmokeFailure("the reveal strip did not appear for a collapsed pane")
        win._set_pane_collapsed(False, save=False)
        if win.detail_pane.isHidden():
            raise SmokeFailure("expanding did not bring the detail pane back")
        ok.append("Detail pane edits write through the shared path; collapse round-trips")

        # A typed block reason: what KIND of thing stopped the card, never which
        # card. It writes from the pane like any other field, the change log
        # records it, and Done clears it — a finished card is not blocked.
        pane.show_task(b2)
        pane.block_combo.setCurrentIndex(pane.block_combo.findData("capability"))
        if mconn.execute("SELECT block_reason FROM task WHERE id=?",
                         (b2,)).fetchone()[0] != "capability":
            raise SmokeFailure("a pane block-reason edit did not reach the database")
        if not mconn.execute(
                "SELECT COUNT(*) FROM task_event WHERE task_id=? AND "
                "field='block_reason' AND to_value='capability'", (b2,)).fetchone()[0]:
            raise SmokeFailure("a block reason was not recorded by the change-log triggers")
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("done"))
        if mconn.execute("SELECT block_reason FROM task WHERE id=?",
                         (b2,)).fetchone()[0] is not None:
            raise SmokeFailure("a card moved to done kept its block reason")
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("doing"))
        # The two vocabularies are separate copies on purpose — the viewer
        # depends on no package outside itself — so they are checked against
        # each other rather than trusted to stay in step.
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "_ct", TOOLS / "ticket_tools" / "create_tickets.py")
        _ct = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_ct)
        from ui.theme import BLOCK_REASON_CHOICES
        viewer_set = tuple(v for v, _ in BLOCK_REASON_CHOICES if v is not None)
        if viewer_set != tuple(_ct.BLOCK_REASONS):
            raise SmokeFailure(
                f"block-reason vocabularies drifted: viewer {viewer_set} vs "
                f"CLI {tuple(_ct.BLOCK_REASONS)}")
        if not _ct.BLOCK_REASONS_NEEDING_USER <= set(_ct.BLOCK_REASONS):
            raise SmokeFailure("a reason the status scripts surface is not in the vocabulary")
        ok.append("Blocked: a typed reason writes from the pane, logs, clears on "
                  "done, and both vocabularies agree")

        # Unsaved-changes guard: clean dialog is not dirty and closes
        # freely; a field edit flips it dirty.
        from ui.record_dialog import UnifiedRecordDialog
        guard_dlg = UnifiedRecordDialog(win, mconn, mode="task", record_id=b1)
        if guard_dlg._is_dirty():
            raise SmokeFailure("freshly-loaded record dialog should not be dirty")
        if not guard_dlg._confirm_discard():
            raise SmokeFailure("clean dialog should close without prompting")
        guard_dlg.title_edit.setText(guard_dlg.title_edit.text() + " edited")
        if not guard_dlg._is_dirty():
            raise SmokeFailure("edited record dialog should read dirty")
        ok.append("Record dialog unsaved-changes guard detects edits")

        # Overflow guard: a tall ticket must not push the save button off the
        # screen. The body scrolls; the button row is pinned outside the scroll
        # area; and every field is a formCaption above its control in a
        # sectioned grid — the design system's vocabulary, never a QFormLayout.
        from PySide6.QtWidgets import QFormLayout, QLabel, QScrollArea
        if not isinstance(getattr(guard_dlg, "_scroll", None), QScrollArea):
            raise SmokeFailure("record dialog body is not inside a scroll area")
        scrolled = guard_dlg._scroll.widget()
        btn_parent = guard_dlg.button_box.parentWidget()
        if btn_parent is scrolled or (btn_parent and btn_parent.isAncestorOf(scrolled)
                                      and btn_parent is not guard_dlg):
            raise SmokeFailure("button row is inside the scroll area — it can scroll away")
        if guard_dlg.findChildren(QFormLayout):
            raise SmokeFailure("record dialog lays out fields in a QFormLayout")
        for w in (guard_dlg.stage_combo, guard_dlg.status_combo, guard_dlg.owner_edit,
                  guard_dlg.epic_combo, guard_dlg.pressure_spin,
                  guard_dlg.estimate_combo, guard_dlg.originator_edit,
                  guard_dlg.title_edit, guard_dlg.desc_edit):
            cell = w.parentWidget()
            if not any(lbl.objectName() == "formCaption"
                       for lbl in cell.findChildren(QLabel)):
                raise SmokeFailure(f"{w!r} has no formCaption above it")
        headers = {lbl.text() for lbl in guard_dlg.findChildren(QLabel)
                   if lbl.objectName() == "sectionHeader"}
        for name in ("Record", "Placement", "Links", "Log", "Attachments"):
            if name not in headers:
                raise SmokeFailure(f"record dialog is missing the {name} section header")
        guard_dlg._update_visible_fields()  # must not raise
        ok.append("Record dialog scrolls, pins its buttons, captions fields in sections")

        # Required-field guard. A titleless save used to close the dialog and
        # write nothing, silently destroying whatever Description had been typed
        # — so the assertions that matter are that OK cannot be pressed, that
        # accept() refuses even if something calls it directly, and that the
        # empty field is marked.
        from PySide6.QtWidgets import QDialog
        req_dlg = UnifiedRecordDialog(win, mconn, mode="task")
        if req_dlg.ok_button.isEnabled():
            raise SmokeFailure("OK is clickable on a dialog with no title")
        if not req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("empty required title is not marked fieldMissing")
        req_dlg.desc_edit.setPlainText("a description the user would hate to lose")
        req_dlg.accept()
        if req_dlg.result() == QDialog.Accepted:
            raise SmokeFailure("accept() closed the dialog with a missing title")
        if req_dlg.desc_edit.toPlainText() != "a description the user would hate to lose":
            raise SmokeFailure("the refused accept discarded the Description")
        req_dlg.title_edit.setText("Now it has a title")
        if not req_dlg.ok_button.isEnabled():
            raise SmokeFailure("OK stayed disabled after the title was filled in")
        if req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("fieldMissing did not clear once the title was filled in")
        req_dlg.title_edit.setText("   ")
        if req_dlg.ok_button.isEnabled():
            raise SmokeFailure("whitespace-only title counted as a title")
        req_dlg.type_combo.setCurrentText("Epic")  # required label changes with kind
        if req_dlg.ok_button.isEnabled():
            raise SmokeFailure("switching kind re-enabled OK with an empty name")
        ok.append("Record dialog blocks save while a required field is empty")

        # One field, everywhere a person types more than a word. A one-line
        # field scrolls sideways and hides what came before, so the shared one
        # wraps, grows to its ceiling and then scrolls vertically.
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtTest import QTest

        from ui.growing_edit import GrowingTextEdit
        from ui.links import AddLinkDialog

        link_dlg = AddLinkDialog(win)
        for name, field in (("record title", req_dlg.title_edit),
                            ("record log composer", req_dlg.log_post_input),
                            ("detail-pane composer", win.detail_pane.comment_input),
                            ("link address", link_dlg.uri_input),
                            ("link caption", link_dlg.label_input)):
            if not isinstance(field, GrowingTextEdit):
                raise SmokeFailure(f"the {name} field is not the shared growing field")

        field = GrowingTextEdit(max_lines=4)
        field.setFixedWidth(180)
        field.show()
        shut = field.height()
        field.setText("a sentence long enough to wrap several times over " * 4)
        grown = field.height()
        line = QFontMetrics(field.font()).lineSpacing()
        if grown <= shut:
            raise SmokeFailure("the shared field did not grow with its text")
        if grown > shut + line * 4:
            raise SmokeFailure("the shared field grew past its ceiling")
        if field.horizontalScrollBarPolicy() != Qt.ScrollBarAlwaysOff:
            raise SmokeFailure("the shared field can still scroll sideways")
        posted = []
        field.submitted.connect(lambda: posted.append(True))
        QTest.keyClick(field, Qt.Key_Return)
        if not posted:
            raise SmokeFailure("Return did not post from the shared field")
        before = field.toPlainText()
        QTest.keyClick(field, Qt.Key_Return, Qt.ShiftModifier)
        if field.toPlainText() == before:
            raise SmokeFailure("Shift+Return did not open a line")
        ok.append("every typing surface is one field that grows, wraps and posts on Return")

        # Links. The property worth guarding is that an issue link is ONE
        # symmetric row: it must read from both ends, refuse a duplicate offered
        # in either direction, and vanish from both tickets on a single delete.
        # That is the whole reason two mirrored rows were rejected, so a
        # regression here is the regression that matters.
        from ui.links import (
            LinkBar,
            add_issue_link,
            add_uri_link,
            list_links,
            remove_link,
            remove_links_for_task,
        )
        lc = sqlite3.connect(":memory:")
        lc.executescript(schema.read_text())

        def _seed_link_task(title):
            lc.execute("INSERT INTO task (title, status, stage, record_type) "
                       "VALUES (?, 'todo', 'active', 'build')", (title,))
            return lc.execute("SELECT last_insert_rowid()").fetchone()[0]

        la, lb, ld = (_seed_link_task("Alpha"), _seed_link_task("Beta"),
                      _seed_link_task("Delta"))
        lc.commit()
        issue_ends = lambda t: [x["other_id"] for x in list_links(lc, t)
                                if x["kind"] == "issue"]

        if add_issue_link(lc, la, lb) is not None:
            raise SmokeFailure("add_issue_link refused a valid pair")
        if issue_ends(la) != [lb] or issue_ends(lb) != [la]:
            raise SmokeFailure("issue link is not visible from both tickets")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("issue link wrote more than one row — it must be symmetric")
        if lc.execute("SELECT task_id, other_id FROM task_link").fetchone() != (
                min(la, lb), max(la, lb)):
            raise SmokeFailure("issue link row is not normalized low->high")
        if not (add_issue_link(lc, la, lb) and add_issue_link(lc, lb, la)):
            raise SmokeFailure("duplicate issue link was accepted")
        if not (add_issue_link(lc, la, la) and add_issue_link(lc, la, 9999)):
            raise SmokeFailure("self-link or missing-ticket link was accepted")

        # A dependency is the same single row carrying a direction: it must
        # still be one row, read as 'blocks' from one end and 'blocked-by' from
        # the other, and retype in place rather than spawning a second row.
        if add_issue_link(lc, la, lb, relation="blocks") is not None:
            raise SmokeFailure("retyping an existing link to 'blocks' was refused")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("retyping a link wrote a second row")
        rel = lambda t: [x["relation"] for x in list_links(lc, t)
                         if x["kind"] == "issue"]
        if rel(la) != ["blocks"] or rel(lb) != ["blocked-by"]:
            raise SmokeFailure("a 'blocks' link does not read from both ends")
        if lc.execute("SELECT task_id, other_id FROM task_link").fetchone() != (la, lb):
            raise SmokeFailure("a 'blocks' row lost its direction to normalization")
        # The same dependency restated from the far end is the same one row: it
        # reports the pair as already linked and changes nothing. What must not
        # happen is a second row or a flipped direction.
        add_issue_link(lc, lb, la, relation="blocked-by")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("'blocked-by' from the far end wrote a second row")
        if rel(la) != ["blocks"]:
            raise SmokeFailure("'blocked-by' did not store the same directed row")
        if add_issue_link(lc, la, lb, relation="related") is not None:
            raise SmokeFailure("retyping back to 'related' was refused")
        if rel(la) != ["related"]:
            raise SmokeFailure("retyping back to 'related' did not take")

        if add_uri_link(lc, la, "obsidian://open?vault=V&file=n.md", "note") is not None:
            raise SmokeFailure("add_uri_link refused a valid address")
        if not add_uri_link(lc, la, "   "):
            raise SmokeFailure("blank address was accepted")
        rendered = list_links(lc, la)
        if [x["kind"] for x in rendered] != ["issue", "uri"]:
            raise SmokeFailure("list_links should return issue links before uri links")
        if rendered[0]["other_title"] != "Beta" or rendered[1]["label"] != "note":
            raise SmokeFailure("list_links did not resolve the far title / label")

        remove_link(lc, rendered[0]["id"])
        if issue_ends(lb) or len(list_links(lc, la)) != 1:
            raise SmokeFailure("one delete must clear an issue link from both tickets")
        add_issue_link(lc, la, ld)
        remove_links_for_task(lc, ld)
        lc.commit()
        if list_links(lc, ld) or len(list_links(lc, la)) != 1:
            raise SmokeFailure("deleting a task left links pointing at it")

        # Links entered while a ticket is still being created buffer in the
        # widget and are written once the INSERT yields an id.
        bar = LinkBar(lc, allow_pending=True)
        bar.set_task(None)
        bar._pending += [("issue", lb, "", "", "blocked-by"),
                         ("uri", None, "https://x.test", "X", "related")]
        if not bar.has_pending():
            raise SmokeFailure("LinkBar did not buffer links for an unsaved ticket")
        le = _seed_link_task("Echo")
        bar.flush_pending(le)
        if bar.has_pending() or sorted(x["kind"] for x in list_links(lc, le)) != [
                "issue", "uri"]:
            raise SmokeFailure("flush_pending did not write the buffered links")
        if rel(le) != ["blocked-by"]:
            raise SmokeFailure("flush_pending dropped a buffered link's relation")
        ok.append("Links: one directed edge, related/blocks types, uri links, "
                  "pending buffer")

        # A finished blocker's closing comment reaches the ticket it blocked.
        # The properties that matter are that it is a read of two live rows —
        # so editing the blocker's last comment changes what the blocked ticket
        # shows and nothing is written onto it — that only finished blockers
        # that said something contribute, that several arrive in the order they
        # closed, and that the viewer and the CLI read the same thing.
        from ui.links import carried_summaries

        def _close(task_id, at):
            lc.execute("UPDATE task SET status='done', closed_at=? WHERE id=?",
                       (at, task_id))

        def _say(task_id, body):
            lc.execute("INSERT INTO issue_log (task_id, author, body, created_at) "
                       "VALUES (?,'chief_of_staff',?,?)", (task_id, body, "2026-02-01"))

        # The three that finish close in an order matching neither their ids
        # ascending nor descending, so an id-ordered read cannot pass by luck.
        hb = _seed_link_task("Blocked one")
        hp1, hp2, hp3, hp4, hp5 = (_seed_link_task("Parent one"),
                                   _seed_link_task("Parent two"),
                                   _seed_link_task("Parent three"),
                                   _seed_link_task("Parent four"),
                                   _seed_link_task("Parent five"))
        for parent in (hp1, hp2, hp3, hp4, hp5):
            if add_issue_link(lc, parent, hb, relation="blocks") is not None:
                raise SmokeFailure("a blocks link between fresh tickets was refused")
        _say(hp1, "an earlier note")
        _say(hp1, "one closing")
        _close(hp1, "2026-01-03")
        _say(hp2, "two closing")
        _close(hp2, "2026-01-01")
        _say(hp3, "three closing")
        _close(hp3, "2026-01-02")
        _close(hp4, "2026-01-04")          # done having said nothing
        _say(hp5, "five is still open")    # not done — carries nothing
        lc.commit()

        got = carried_summaries(lc, hb)
        if [e["id"] for e in got] != [hp2, hp3, hp1]:
            raise SmokeFailure("carried summaries are not the finished blockers "
                               "in the order they closed")
        if [e["body"] for e in got] != ["two closing", "three closing", "one closing"]:
            raise SmokeFailure("a carried summary is not the blocker's own last comment")
        if lc.execute("SELECT COUNT(*) FROM issue_log WHERE task_id=?",
                      (hb,)).fetchone()[0]:
            raise SmokeFailure("a carried summary was copied onto the blocked ticket")
        _say(hp1, "one closing, corrected")
        lc.commit()
        if carried_summaries(lc, hb)[2]["body"] != "one closing, corrected":
            raise SmokeFailure("editing the blocker's last comment did not reach "
                               "the blocked ticket — the summary is a copy, not a join")
        if carried_summaries(lc, hp5):
            raise SmokeFailure("a ticket blocking nothing carried a summary")

        # The viewer shows it without the reader opening those tickets, and
        # shows no empty section on a ticket nothing finished ahead of.
        from ui.detail_pane import DetailPane
        hpane = DetailPane(lc)
        hpane.show_task(hb)
        if not hpane.handoff_view.isVisibleTo(hpane) \
                or not hpane._handoff_header.isVisibleTo(hpane):
            raise SmokeFailure("the detail pane hid the carried summaries of a "
                               "ticket that has them")
        shown = hpane.handoff_view.toPlainText()
        if "one closing, corrected" not in shown or "two closing" not in shown:
            raise SmokeFailure("the detail pane did not render both carried summaries")
        if "five is still open" in shown:
            raise SmokeFailure("the detail pane carried an unfinished blocker's comment")
        # Sized to what it holds, like the description above it: a section left
        # at a widget's default height shows a heading and clips the handoff.
        one = _seed_link_task("Blocked two")
        add_issue_link(lc, hp2, one, relation="blocks")
        lc.commit()
        tall = hpane.handoff_view.height()
        hpane.show_task(one)
        if not hpane.handoff_view.height() < tall:
            raise SmokeFailure("the carried-summaries section is not sized to its "
                               "content — three summaries take the height of one")
        hpane.show_task(hp5)
        if hpane.handoff_view.isVisibleTo(hpane) \
                or hpane._handoff_header.isVisibleTo(hpane):
            raise SmokeFailure("the detail pane showed an empty carried-summaries section")

        # The status scripts read this through status_common, which is the one
        # copy both front ends call, so the two readers are compared rather than
        # trusted to stay in step.
        _spec_cs = _ilu.spec_from_file_location(
            "_cs", TOOLS / "ticket_tools" / "status_common.py")
        _cs = _ilu.module_from_spec(_spec_cs); _spec_cs.loader.exec_module(_cs)
        cli = [(row[0], row[4]) for row in _cs.carried_summaries(lc, hb)]
        if cli != [(e["id"], e["body"]) for e in carried_summaries(lc, hb)]:
            raise SmokeFailure(f"carried-summary readers drifted: CLI {cli} vs viewer")
        ok.append("Carried summaries: finished blockers only, in closing order, "
                  "joined live, shown in the pane, and both readers agree")

        # First-run setup. The properties worth guarding are that a cancelled
        # wizard writes nothing, that a finished one produces a board, a
        # config with no placeholders left in it and a pointer, and that the
        # window offers the menu route back to it.
        import ui.setup_wizard as wiz

        root = TOOLS.parent.parent
        menu_actions = [a.text() for m in win.menuBar().actions() if m.menu()
                        for a in m.menu().actions()]
        if "Setup…" not in menu_actions:
            raise SmokeFailure("no menu route back to first-run setup")
        ok.append("File → Setup… is on the menu bar")

        if wiz.project_root() != root:
            raise SmokeFailure("setup wizard cannot find the clone it lives in")
        if not wiz.needs_setup(None) and not (root / "config" / "config.local.json").exists():
            raise SmokeFailure("a clone with no config and no board should need setup")
        if wiz.needs_setup(schema):  # any existing file stands in for a board
            raise SmokeFailure("an existing board should not trigger setup")

        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = Path(scratch) / "clone"
            (scratch_root / "config").mkdir(parents=True)
            (scratch_root / "src").mkdir()
            (scratch_root / "src" / "app.md").write_text("marker\n")
            (scratch_root / "config" / "config.example.json").write_text(
                (root / "config" / "config.example.json").read_text(encoding="utf-8"),
                encoding="utf-8")

            cfg = wiz.build_config(
                root=scratch_root,
                instance_dir=scratch_root / "data" / "tester",
                slug="tester",
                agents=["chief_of_staff", "librarian"],
                notebook="",
                zotero="",
            )
            if set(cfg["agents"]) - {"_notes", "chief_of_staff", "librarian"}:
                raise SmokeFailure("unchosen agents survived into the config")
            if cfg["active_agent"] != "chief_of_staff":
                raise SmokeFailure("active_agent was not set from the chosen agents")
            if "markdown_notebook" in cfg or "zotero" in cfg:
                raise SmokeFailure("a skipped integration was written into the config")
            blob = json.dumps(cfg)
            for token in ("<your-instance>", "/path/to/project", "/path/to/notebook",
                          "/path/to/Zotero"):
                if token in blob:
                    raise SmokeFailure(f"placeholder {token!r} survived into the config")
            if cfg["important_paths"]["tickets_db"] != "data/tester/tickets/tickets.db":
                raise SmokeFailure("tickets_db does not point at the new instance")
            ok.append("build_config fills every placeholder and drops what was skipped")

            # The whole flow, driven through the wizard's own pages: a scratch
            # clone with no pointer and no config is exactly the fresh-install
            # state, and Finish is the only thing that writes.
            import config_file

            pointer = Path(scratch) / "instance.json"
            written_config = scratch_root / "config" / "config.local.json"
            _orig_pointer = wiz.instance.pointer_path
            _orig_config_path = config_file.path
            wiz.instance.pointer_path = lambda: pointer
            config_file.path = lambda: written_config
            try:
                wizard = wiz.SetupWizard(scratch_root)
                # A machine with no configuration and no pointer opens on the
                # operating system's user name, which is the first-run default.
                if wizard.instance_page.slug_edit.text() != wiz.default_slug():
                    raise SmokeFailure("a first run did not open on the default name")
                if wizard.instance_page.folder.value() != \
                        str(scratch_root / "data" / wiz.default_slug()):
                    raise SmokeFailure("a first run did not open on the clone's "
                                       "own data folder")
                wizard.instance_page.slug_edit.setText("tester")
                if wizard.instance_page.instance_dir() != scratch_root / "data" / "tester":
                    raise SmokeFailure("the data folder did not follow the instance name")
                if not wizard.agents_page.boxes:
                    raise SmokeFailure("the agents page offers no agents")
                for slug_name, box in wizard.agents_page.boxes.items():
                    box.setChecked(slug_name in ("chief_of_staff", "librarian"))
                wizard.summary_page.initializePage()
                if "tester" not in wizard.summary_page.body.text():
                    raise SmokeFailure("the summary does not name what will be written")
                if pointer.exists() or (scratch_root / "data").exists():
                    raise SmokeFailure("the wizard wrote something before Finish")
                wizard.accept()
                db = wizard.db_path
            finally:
                wiz.instance.pointer_path = _orig_pointer
                config_file.path = _orig_config_path
            if db is None or not db.exists():
                raise SmokeFailure("setup did not provision a board")
            fresh = sqlite3.connect(db)
            if not fresh.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='task'"
            ).fetchone():
                raise SmokeFailure("the provisioned board has no task table")
            if fresh.execute("SELECT COUNT(*) FROM task").fetchone()[0]:
                raise SmokeFailure("setup seeded rows; an empty board is the first state")
            fresh.close()
            if not (scratch_root / "config" / "config.local.json").exists():
                raise SmokeFailure("setup did not write config.local.json")
            if not (scratch_root / "data" / "tester" / "personal").is_dir():
                raise SmokeFailure("setup did not create a chosen agent's data folder")
            if (scratch_root / "data" / "tester" / "career").exists():
                raise SmokeFailure("setup created a folder for an agent that was not chosen")
            written = json.loads(pointer.read_text())
            if written["instance_slug"] != "tester" or \
                    Path(written["data_root"]) != scratch_root / "data":
                raise SmokeFailure("the instance pointer does not name the new instance")
            ok.append("Setup wizard writes nothing until Finish, then folders, "
                      "an empty board, config and pointer")

            # Adoption. The installation the run above created is now an
            # existing one, which is exactly the state a second run meets. The
            # properties worth guarding are that the wizard sees it, asks
            # nothing it does not need, leaves the board and the config alone,
            # and treats the pointer as the one thing Finish decides.
            adopted_db = scratch_root / "data" / "tester" / "tickets" / "tickets.db"
            seeded = sqlite3.connect(adopted_db)
            seeded.execute("INSERT INTO task (title, status) VALUES ('adopted', 'todo')")
            seeded.commit()
            seeded.close()
            config_before = (scratch_root / "config" / "config.local.json").read_bytes()
            pointer_before = pointer.read_text()
            pointer.write_text(json.dumps({
                "repo_root": str(scratch_root),
                "data_root": str(Path(scratch) / "elsewhere"),
                "instance_slug": "other",
                "config_path": str(scratch_root / "config" / "config.local.json"),
            }) + "\n")

            wiz.instance.pointer_path = lambda: pointer
            config_file.path = lambda: written_config
            try:
                second = wiz.SetupWizard(scratch_root)
                # Setup opens on the installation the configuration declares,
                # not on the operating system's user name and not on the
                # installation the pointer happens to be aimed at.
                if second.instance_page.slug_edit.text() != "tester":
                    raise SmokeFailure("setup did not open on the configured "
                                       "installation")
                if second.instance_page.folder.value() != \
                        str(scratch_root / "data" / "tester"):
                    raise SmokeFailure("setup did not open on the configured "
                                       "installation's folder")
                if "other" not in second.instance_page.disagreement.text():
                    raise SmokeFailure("a configuration and a pointer naming "
                                       "different installations were reconciled "
                                       "silently")
                second.instance_page.slug_edit.setText("tester")
                second.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                if not second.instance_page.adopting():
                    raise SmokeFailure("a folder holding a board was not seen as an installation")
                if second.instance_page.nextId() != wiz.PAGE_SUMMARY:
                    raise SmokeFailure("adoption still asks the pages only creation needs")
                second.summary_page.initializePage()
                summary = second.summary_page.body.text() + \
                    second.summary_page.pointer_note.text()
                if "other" not in summary or "tester" not in summary:
                    raise SmokeFailure("the summary does not name both the old and the "
                                       "new installation")
                # Both sides are named as an installation folder, so the reader
                # compares two paths of one kind rather than a data root
                # against a folder beneath one.
                if str(Path(scratch) / "elsewhere" / "other") not in summary:
                    raise SmokeFailure("the summary names the old installation by "
                                       "its data root, not by its own folder")

                # Adopting the installation the app already opens must not say
                # it stops opening it.
                third_pointer = json.loads(pointer.read_text())
                pointer.write_text(json.dumps({
                    **third_pointer,
                    "data_root": str(scratch_root / "data"),
                    "instance_slug": "tester",
                }) + "\n")
                same = wiz.SetupWizard(scratch_root)
                same.instance_page.slug_edit.setText("tester")
                same.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                same.summary_page.initializePage()
                if "stops opening" in same.summary_page.pointer_note.text():
                    raise SmokeFailure("the summary says it stops opening the "
                                       "installation it is about to open")
                pointer.write_text(json.dumps(third_pointer) + "\n")

                # Leaving the pointer alone writes nothing at all.
                second.summary_page.take_over.setChecked(False)
                second.accept()
                if pointer.read_text() == pointer_before:
                    raise SmokeFailure("an unchecked pointer option still rewrote the pointer")
                if second.db_path != adopted_db:
                    raise SmokeFailure("adoption did not return the board it adopted")

                # Taking it over writes the pointer, and only the pointer.
                third = wiz.SetupWizard(scratch_root)
                third.instance_page.slug_edit.setText("tester")
                third.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                third.summary_page.initializePage()
                third.accept()
            finally:
                wiz.instance.pointer_path = _orig_pointer
                config_file.path = _orig_config_path

            adopted = json.loads(pointer.read_text())
            if adopted["instance_slug"] != "tester" or \
                    Path(adopted["data_root"]) != scratch_root / "data":
                raise SmokeFailure("adoption did not point the app at the installation")
            if (scratch_root / "config" / "config.local.json").read_bytes() != config_before:
                raise SmokeFailure("adoption rewrote the configuration it was told to leave")
            kept = sqlite3.connect(adopted_db)
            titles = [r[0] for r in kept.execute("SELECT title FROM task")]
            kept.close()
            if titles != ["adopted"]:
                raise SmokeFailure("adoption ran the schema against the board it adopted")
            ok.append("Adoption leaves the board and the config alone, and writes "
                      "only the pointer the summary offers")

            # Settings and the active agent, against the config the wizard just
            # wrote. The property that matters is that both read and write that
            # one file, and that a key this build does not offer survives a save.
            from ui.settings_tab import SettingsTab

            _orig_path = config_file.path
            config_file.path = lambda: written_config
            try:
                config_file.update({"a_key_from_a_newer_build": {"kept": True}})
                tab = SettingsTab()
                if tab.new_ticket.currentData() != "active":
                    raise SmokeFailure("Settings did not load the stored board setting")
                tab.new_ticket.setCurrentIndex(tab.new_ticket.findData("backlog"))
                if config_file.get(config_file.NEW_TICKET_STAGE) != "backlog":
                    raise SmokeFailure("Settings did not write the board setting")
                if config_file.get("a_key_from_a_newer_build.kept") is not True:
                    raise SmokeFailure("a Settings write dropped an unrecognised key")
                # Work Scope: the whole queue by default, and One Ticket — the
                # position that changes anything — reaches the file.
                if tab.work_scope.currentData() is not True:
                    raise SmokeFailure("Work Scope did not default to the whole queue")
                tab.work_scope.setCurrentIndex(tab.work_scope.findData(False))
                if config_file.get(config_file.WORK_WHOLE_QUEUE) is not False:
                    raise SmokeFailure("Settings did not write the work scope")
                if tab.appearance.currentData() != \
                        config_file.APPEARANCE_SCHEME_DEFAULT:
                    raise SmokeFailure("Settings did not load the stored scheme")
                previewed: list[str] = []
                tab._on_appearance_changed = previewed.append
                tab.appearance.setCurrentIndex(tab.appearance.findData("cool_dark"))
                if previewed != ["cool_dark"]:
                    raise SmokeFailure("picking a scheme did not apply it live")
                if config_file.get(config_file.APPEARANCE_SCHEME) != "cool_dark":
                    raise SmokeFailure("picking a scheme did not write it")
                if hasattr(tab, "save_btn"):
                    raise SmokeFailure("a Save button still stands on Settings")
                tab.suggested_commit.setChecked(
                    not config_file.get(config_file.SUGGESTED_COMMIT, True))
                if config_file.get(config_file.SUGGESTED_COMMIT) is not \
                        tab.suggested_commit.isChecked():
                    raise SmokeFailure("toggling the commit box did not write it")
                # Seating a stored value is not a choice, so reload writes nothing.
                marker = config_file.get(config_file.APPEARANCE_SCHEME)
                config_file.update({config_file.APPEARANCE_SCHEME: "warm_light"})
                tab.reload()
                if config_file.get(config_file.APPEARANCE_SCHEME) != "warm_light":
                    raise SmokeFailure("reloading Settings wrote a value back")
                config_file.update({config_file.APPEARANCE_SCHEME: marker})
                # The next-session agent is a field on this page like every
                # other: it loads from the configuration, moves only on a
                # deliberate choice, and reaches the file on that choice.
                picker = tab.next_agent
                if picker.currentText() not in config_file.agent_slugs():
                    raise SmokeFailure("the agent picker does not show a configured agent")
                if picker.currentText() != config_file.get("active_agent"):
                    raise SmokeFailure("the agent picker opens on an agent that is not active")
                if not picker.isEnabled():
                    raise SmokeFailure("the agent picker is not selectable")
                if picker.count() != len(config_file.agent_slugs()):
                    raise SmokeFailure("the agent picker lists agents this installation does not configure")

                # A wheel gesture and an arrow key while it holds focus leave
                # the value and write nothing.
                from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
                from PySide6.QtGui import QKeyEvent, QWheelEvent
                before = picker.currentText()
                chosen: list[str] = []
                picker.picked.connect(chosen.append)
                picker.wheelEvent(QWheelEvent(
                    QPointF(0, 0), QPointF(0, 0), QPoint(0, 0), QPoint(0, -120),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))
                picker.keyPressEvent(QKeyEvent(
                    QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
                if picker.currentText() != before or chosen:
                    raise SmokeFailure(
                        "a wheel gesture or an arrow key moved the agent picker")

                # Loading a value is not a choice; choosing one is.
                picker.setCurrentText("librarian")
                if chosen:
                    raise SmokeFailure("loading a value into the agent picker wrote it")
                picker.activated.emit(picker.findText("librarian"))
                if chosen != ["librarian"]:
                    raise SmokeFailure("choosing an agent did not report the choice")
                if config_file.get("active_agent") != "librarian":
                    raise SmokeFailure("choosing an agent did not write it")

                agent_win = MainWindow(mconn)
                if hasattr(agent_win, "agent_combo"):
                    raise SmokeFailure("an agent control still stands in the header")
                if agent_win._tab_buttons[-1].text() != "Settings":
                    raise SmokeFailure("no Settings tab alongside the board tabs")
            finally:
                config_file.path = _orig_path
            ok.append("Settings writes each choice as it is made, and a load is "
                      "not a choice")

            # Skills: the page reads one listing and files the judgment as a
            # card. The loader is stubbed, so what is checked is the page —
            # what it groups, what it says a skill carries, and what it writes.
            import importlib.util as _ilu
            import json as _json

            from ui.skills_tab import SkillsTab

            # The row's words come from the loader, so the stub listing is
            # worded by the loader too and the two cannot drift apart.
            _spec = _ilu.spec_from_file_location(
                "smoke_skills", TOOLS / "skill_tools" / "skills.py")
            _loader = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_loader)

            listing = {
                "skills": [
                    {"name": "native-one", "directory": "native-one",
                     "description": "A native skill.", "origin": "native",
                     "root": "native", "repo": "", "commit": "", "license": "MIT",
                     "license_source": "", "files": 1, "scripts": [],
                     "holders": [], "file_list": ["SKILL.md"],
                     "path": "/nowhere/native-one", "source_url": ""},
                    {"name": "with-code", "directory": "with-code",
                     "description": "An installed skill carrying scripts.",
                     "origin": "someone/repo@abc1234", "root": "installed",
                     "repo": "https://github.com/someone/repo",
                     "commit": "abc1234def", "license": "Apache-2.0",
                     "license_source": "SKILL.md", "files": 4,
                     "scripts": ["scripts/run.py"],
                     "holders": ["chief_of_staff"],
                     "file_list": ["SKILL.md", "references/a.md", "assets/b.txt",
                                   "scripts/run.py"],
                     "path": "/nowhere/with-code",
                     "source_url": "https://github.com/someone/repo/tree/abc1234def/skills/with-code"},
                    {"name": "waiting", "directory": "waiting",
                     "description": "A skill nothing has read.",
                     "origin": "someone/other@0000000", "root": "quarantined",
                     "repo": "https://github.com/someone/other",
                     "commit": "0000000aaa", "license": "MIT",
                     "license_source": "SKILL.md", "files": 2, "scripts": [],
                     "holders": [], "file_list": ["SKILL.md", "references/x.md"],
                     "path": "/nowhere/waiting",
                     "source_url": "https://github.com/someone/other/tree/0000000aaa/waiting"},
                ],
                "agents": {"chief_of_staff": ["with-code"], "librarian": []},
            }
            for _record in listing["skills"]:
                _record["said_origin"] = _loader.origin_phrase(_record)
                _record["said_contents"] = _loader.contents_phrase(_record)
                _record["said_holders"] = _loader.holders_phrase(
                    _record["holders"])
            calls: list[tuple] = []

            def _stub_run(self, *args):
                calls.append(args)
                if args[:2] == ("list", "--json"):
                    return 0, _json.dumps(listing), ""
                return 0, f"stub ran {' '.join(args)}", ""

            _orig_run = SkillsTab._run
            SkillsTab._run = _stub_run
            try:
                stab = SkillsTab(mconn)
                texts = [stab.list.item(i).text()
                         for i in range(stab.list.count())]
                rows = [t.splitlines()[0] for t in texts]
                if rows[0] != "Quarantined" or rows[2] != "waiting":
                    raise SmokeFailure("Skills does not put quarantined skills first")
                # The page says what it is for before it is used: what Import
                # does, and what quarantine is.
                from ui.skills_tab import IMPORT_NOTE, QUARANTINE_NOTE
                if rows[1] != QUARANTINE_NOTE:
                    raise SmokeFailure("the Quarantined section does not say what quarantine is")
                if stab.import_note.text() != IMPORT_NOTE:
                    raise SmokeFailure("the page does not say what Import does")
                for phrase in ("quarantine", "no session can use it",
                               "chief_of_staff"):
                    if phrase not in IMPORT_NOTE:
                        raise SmokeFailure(
                            f"the Import note does not say {phrase!r}")
                # A quarantined row names the card that will decide it.
                if "No card asks for it yet" not in texts[2]:
                    raise SmokeFailure("a quarantined row does not name its card")
                # Every value below the name says what it is, so nothing on the
                # row has to be recognised to be read.
                coded_row = [t for t in texts if t.startswith("with-code")][0]
                native_row = [t for t in texts if t.startswith("native-one")][0]
                facts = coded_row.splitlines()[1]
                if "Held by chief_of_staff" not in facts:
                    raise SmokeFailure("Skills does not say the agents are the holders")
                if "Downloaded from someone/repo@abc1234" not in facts:
                    raise SmokeFailure("Skills does not say where a skill was downloaded from")
                if "Came with Bristol" not in native_row.splitlines()[1]:
                    raise SmokeFailure("Skills still expects the reader to know 'native'")
                if "Held by no agent" not in native_row.splitlines()[1]:
                    raise SmokeFailure("Skills leaves an unheld skill's holders unsaid")
                # A skill carrying code does not read like one that carries none,
                # and a count agrees with the noun beside it.
                coded = [s for s in listing["skills"] if s["scripts"]][0]
                plain = [s for s in listing["skills"] if not s["scripts"]][0]
                if coded["said_contents"] == plain["said_contents"]:
                    raise SmokeFailure("Skills describes code and no code identically")
                if "no code" not in plain["said_contents"]:
                    raise SmokeFailure("Skills does not say when a skill carries no code")
                if _loader.contents_phrase({"files": 1, "scripts": []}) != "one file, no code":
                    raise SmokeFailure("a count and its noun disagree in number")
                # A description longer than the list is cut visibly rather than
                # running under the right-hand edge.
                long_one = dict(plain, name="long-one",
                                description="word " * 400, holders=[])
                long_one["said_holders"] = _loader.holders_phrase([])
                listing["skills"].append(long_one)
                stab.reload()
                drawn = [t for t in
                         (stab.list.item(i).text() for i in range(stab.list.count()))
                         if t.startswith("long-one")][0].splitlines()[2]
                if len(drawn) >= len(long_one["description"]):
                    raise SmokeFailure("Skills does not cut a long description to the row")
                listing["skills"].remove(long_one)
                stab.reload()

                # There is no trust control: the user has no basis on which to
                # press one, and saying so on the card is the whole route.
                if hasattr(stab, "trust_btn"):
                    raise SmokeFailure("the page still offers a trust override")
                if hasattr(stab, "attach_btn") or hasattr(stab, "detach_btn"):
                    raise SmokeFailure("attaching is still on the tab's bottom row")
                stab._select("native-one")
                if stab.remove_btn.isEnabled():
                    raise SmokeFailure("a native skill can be removed from the app")
                stab._select("with-code")
                if not stab.open_btn.isEnabled():
                    raise SmokeFailure("a selected skill cannot be opened")

                # The bottom row narrows the list three ways, and they narrow
                # together.
                from ui.skills_tab import (
                    ANY_AGENT,
                    ANY_SOURCE,
                    CAME_WITH,
                    NO_AGENT,
                    SkillDialog,
                )

                def _named():
                    return [stab.list.item(i).text().splitlines()[0]
                            for i in range(stab.list.count())
                            if stab.list.item(i).data(Qt.UserRole)]

                stab.search.setText("scripts")
                if _named() != ["with-code"]:
                    raise SmokeFailure(f"the text filter does not narrow: {_named()}")
                stab.search.clear()
                stab.source.setCurrentText(CAME_WITH)
                if _named() != ["native-one"]:
                    raise SmokeFailure(f"the source filter does not narrow: {_named()}")
                stab.source.setCurrentText(ANY_SOURCE)
                stab.holder.setCurrentText("chief_of_staff")
                if _named() != ["with-code"]:
                    raise SmokeFailure(f"the agent filter does not narrow: {_named()}")
                stab.holder.setCurrentText(NO_AGENT)
                if "with-code" in _named():
                    raise SmokeFailure("the no-agent filter keeps a held skill")
                stab.holder.setCurrentText(ANY_AGENT)
                if len(_named()) != 3:
                    raise SmokeFailure("clearing the filters does not restore the list")

                # A skill opens, and that is where its agents are chosen.
                writes: list[tuple] = []

                def _dialog_run(*args):
                    writes.append(args)
                    return 0, f"stub ran {' '.join(args)}", ""

                coded_record = [s for s in listing["skills"]
                                if s["name"] == "with-code"][0]
                dlg = SkillDialog(None, coded_record,
                                  ["chief_of_staff", "librarian"],
                                  "---\nname: with-code\n---\nthe body",
                                  _dialog_run)
                if "the body" not in dlg.body.toPlainText():
                    raise SmokeFailure("a skill's view does not show its SKILL.md")
                if dlg.body.toPlainText() != dlg.body.toPlainText() or not dlg.body.isReadOnly():
                    raise SmokeFailure("a skill's view offers to edit published source")
                if dlg.files.count() != len(coded_record["file_list"]):
                    raise SmokeFailure("a skill's view does not list its files")
                if dlg.source_btn is None or coded_record["source_url"] not in dlg.source_btn.toolTip():
                    raise SmokeFailure("a downloaded skill's view has no link to its source")
                if not dlg.boxes["chief_of_staff"].isChecked() or dlg.boxes["librarian"].isChecked():
                    raise SmokeFailure("the tick boxes do not carry who holds the skill")
                dlg.boxes["librarian"].setChecked(True)
                dlg.boxes["chief_of_staff"].setChecked(False)
                if ("attach", "with-code", "--agent", "librarian") not in writes:
                    raise SmokeFailure("ticking an agent did not attach through the loader")
                if ("detach", "with-code", "--agent", "chief_of_staff") not in writes:
                    raise SmokeFailure("unticking an agent did not detach through the loader")

                # A native skill opens and reads, and offers no edit either.
                native = SkillDialog(None, listing["skills"][0],
                                     ["chief_of_staff"], "native text",
                                     _dialog_run)
                if not native.body.isReadOnly() or native.files.count() != 1:
                    raise SmokeFailure("a native skill's view does not read")
                if native.source_btn is not None:
                    raise SmokeFailure("a native skill's view offers a source it has none of")

                # The judgment is a card, and the card is chief_of_staff's.
                before = mconn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
                task_id = stab._file_card(listing["skills"][2])
                row = mconn.execute(
                    "SELECT title, assignee, reporter, status, stage, description "
                    "FROM task WHERE id=?", (task_id,)).fetchone()
                if mconn.execute("SELECT COUNT(*) FROM task").fetchone()[0] != before + 1:
                    raise SmokeFailure("importing a skill filed no card")
                if row[1] != "chief_of_staff" or row[2] != "user":
                    raise SmokeFailure("the import card is not chief_of_staff's")
                if (row[3], row[4]) != ("todo", "active"):
                    raise SmokeFailure("the import card did not land on the board")
                if "waiting" not in row[0] or "two files, no code" not in row[5]:
                    raise SmokeFailure("the import card does not name the skill and what it carries")

                # An import reports the skill, where it came from, what is in
                # it and the card that decides it, in that order.
                report = stab.status.text()
                if report:
                    raise SmokeFailure("the page reports before anything ran")
                stab.address.setText("https://github.com/someone/other/tree/main/waiting")
                stab._import()
                report = stab.status.text()
                places = [report.find(bit) for bit in
                          ("waiting", "Downloaded from someone/other@0000000",
                           "two files, no code", "chief_of_staff")]
                if -1 in places or places != sorted(places):
                    raise SmokeFailure(
                        f"the import report does not say the four things in order: {report!r}")
                if "#" not in report:
                    raise SmokeFailure("the import report names no card")

            finally:
                SkillsTab._run = _orig_run
            ok.append("Skills reads one listing, says what it is for, narrows "
                      "three ways, and attaches from a skill's own view")

            skills_win = MainWindow(mconn)
            names = [b.text() for b in skills_win._tab_buttons]
            if "Skills" not in names or names.index("Skills") > names.index("Settings"):
                raise SmokeFailure("no Skills tab before Settings")
            ok.append("the Skills tab stands in the header")
    else:
        ok.append("(skipped MainWindow build — schema.sql not found)")
    return ok


def check_test_control() -> list[str]:
    ok: list[str] = []
    tool_on_path("test_control")
    offscreen_app()

    import app as tc_app  # test_control/app.py

    conn = sqlite3.connect(":memory:")
    tc_app._provision_schema(conn, is_fresh=True)
    ok.append("schema provisions + seeds on a fresh DB")

    from ui.main_window import TestControlWindow

    TestControlWindow(conn)
    ok.append("TestControlWindow builds against the seeded DB")
    return ok


RESIDENT_CORE_CAP = 1500


def check_governing_docs() -> list[str]:
    ok: list[str] = []
    root = Path(__file__).resolve().parents[3]

    core = root / "src" / "app.md"
    words = len(core.read_text().split())
    if words > RESIDENT_CORE_CAP:
        raise SmokeFailure(
            f"src/app.md is {words} words, over the {RESIDENT_CORE_CAP}-word cap by "
            f"{words - RESIDENT_CORE_CAP}. Move a rule to the file that owns it "
            f"(src/templates/identity_template.md, the style contract)."
        )
    ok.append(f"resident core is {words} words, within the {RESIDENT_CORE_CAP} cap")
    return ok


def declared_scripts(skill_md: Path) -> list[str]:
    """The `metadata.bristol.scripts` a skill declares, as written.

    Read line by line rather than with a YAML parser, for the same reason the
    loader reads frontmatter that way: the file is read as far as the closing
    delimiter and no further, and no dependency is added to run a smoke check.
    """
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for line in lines[1:]:
        if line.strip() == "---":
            return []
        if line.startswith("  bristol.scripts:"):
            return line.split(":", 1)[1].split()
    return []


def check_skill_declarations() -> list[str]:
    """Every script a native skill declares is on disk.

    A skill names a command in a sentence, and prose is not checkable. The
    declaration is what makes a renamed or deleted tool a failure here rather
    than a command that does not run halfway through a task.
    """
    root = Path(__file__).resolve().parents[3]
    skills = sorted((root / "src" / "skills").glob("*/SKILL.md"))
    if not skills:
        raise SmokeFailure("no native skills found; the skills root moved")

    missing: dict[str, list[str]] = {}
    declared = 0
    for skill_md in skills:
        for rel in declared_scripts(skill_md):
            declared += 1
            if not (root / rel).is_file():
                missing.setdefault(rel, []).append(skill_md.parent.name)
    if missing:
        # Reported by tool rather than by skill: a renamed tool is one edit, and
        # what the person fixing it needs is every skill that names it.
        lines = [f"{rel} — declared by {', '.join(sorted(names))}"
                 for rel, names in sorted(missing.items())]
        raise SmokeFailure(
            "a skill declares a script that is not there:\n  " + "\n  ".join(lines))

    holders = sum(1 for s in skills if declared_scripts(s))
    return [f"{declared} declared scripts across {holders} skills are all on disk"]


def _tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split("\n")
    return [root / n for n in out if n.strip()]


# The one tracked file whose whole job is to name a person.
ATTRIBUTION_FILE = "LICENSE"


def check_published_files() -> list[str]:
    ok: list[str] = []
    root = Path(__file__).resolve().parents[3]

    def git_cfg(key: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), "config", key], capture_output=True, text=True
        ).stdout.strip()

    reader = root / "src" / "tools" / "config_tools" / "read_config.py"
    declared = subprocess.run(
        [sys.executable, str(reader), "--expanduser", "drives.local_home.path"],
        capture_output=True, text=True,
    ).stdout.strip()
    home = Path(declared or "~").expanduser()
    needles = {s for s in (git_cfg("user.name"), git_cfg("user.email"),
                           str(home), home.name) if len(s) > 2}
    # A repository's own address is a published fact, and it names the account
    # that hosts it. Clone lines are masked before the scan for that reason.
    origin = git_cfg("remote.origin.url")
    published = {u for u in (origin, origin.removesuffix(".git")) if len(u) > 2}

    hits: list[str] = []
    for path in _tracked_files(root):
        if path.name == ATTRIBUTION_FILE or not path.exists():
            continue
        try:
            text = path.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for url in published:
            text = text.replace(url, "")
        rel = path.relative_to(root)
        for needle in needles:
            if needle.lower() in text.lower():
                hits.append(f"{rel}: {needle}")
        for m in re.finditer(r"/Users/[A-Za-z0-9._-]+", text):
            hits.append(f"{rel}: {m.group(0)}")

    if hits:
        raise SmokeFailure(
            "tracked files carry this installation's identity, which belongs in "
            "the git-ignored /config:\n  " + "\n  ".join(sorted(set(hits))[:20])
        )
    ok.append(
        f"{len(needles)} identity strings and every absolute home path are absent "
        f"from tracked files outside {ATTRIBUTION_FILE} and the repository's own "
        f"clone address"
    )
    return ok


def check_payload() -> list[str]:
    """The tree a built .app carries: what it installs, what an update replaces,
    and what an abandoned setup takes back.

    No Qt and no bundle: `payload` is plain file copying, so the check builds a
    source tree, installs it, uses it, updates it and undoes it in a temp
    folder.
    """
    import tempfile

    ok: list[str] = []
    tool_on_path("bristol")
    import payload

    if any(name in payload.PUBLISHED_FILES for name in
           ("config/config.local.json", "data")) or "data" in payload.PUBLISHED_DIRS:
        raise SmokeFailure(
            "a published name covers an installation's own files — a release "
            "would ship one user's board and an update would overwrite the next "
            "one's"
        )
    ok.append("no published name reaches config.local.json or data/")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "carried"
        (source / "src").mkdir(parents=True)
        (source / "config").mkdir()
        (source / "docs").mkdir()
        (source / "src" / "app.md").write_text("# app.md\n")
        (source / "src" / "VERSION").write_text("1.0.0\n")
        (source / "AGENTS.md").write_text("read src/app.md\n")
        (source / "config" / "config.example.json").write_text("{}\n")
        (source / "src" / "__pycache__").mkdir()
        (source / "src" / "__pycache__" / "x.pyc").write_bytes(b"junk")

        target = root / "Bristol"
        payload.stage(source, target)
        if not payload.installed_at(target) or payload.version(target) != "1.0.0":
            raise SmokeFailure("a staged tree is not a readable installation")
        if (target / "src" / "__pycache__").exists():
            raise SmokeFailure("staging carried a cache folder into the install")
        ok.append("install writes the published tree and no build leavings")

        (target / "data" / "someone" / "tickets").mkdir(parents=True)
        (target / "data" / "someone" / "tickets" / "tickets.db").write_bytes(b"BOARD")
        (target / "config" / "config.local.json").write_text('{"active_agent":"x"}')

        (source / "src" / "VERSION").write_text("1.1.0\n")
        (source / "src" / "app.md").write_text("# app.md — newer\n")
        payload.stage(source, target)
        if payload.version(target) != "1.1.0":
            raise SmokeFailure("an update did not raise the installed version")
        if "newer" not in (target / "src" / "app.md").read_text():
            raise SmokeFailure("an update did not replace the machinery")
        if (target / "data" / "someone" / "tickets" / "tickets.db").read_bytes() != b"BOARD":
            raise SmokeFailure("an update destroyed the board")
        if (target / "config" / "config.local.json").read_text() != '{"active_agent":"x"}':
            raise SmokeFailure("an update destroyed the configuration")
        ok.append("update replaces the machinery and leaves the board and config")

        fresh = root / "Fresh"
        payload.stage(source, fresh)
        payload.unstage(fresh)
        if fresh.exists():
            raise SmokeFailure("an abandoned setup left a folder behind")

        used = root / "Used"
        used.mkdir()
        (used / "theirs.txt").write_text("mine")
        payload.stage(source, used)
        payload.unstage(used)
        if not (used / "theirs.txt").exists() or (used / "src").exists():
            raise SmokeFailure(
                "undoing a placement either took the user's own file or left "
                "the tree"
            )
        ok.append("an abandoned setup undoes itself without touching what was there")

    # The folders and the board a run creates are undone on the same rule the
    # tree placement follows: only what this run put there, and never a folder
    # something else has written into.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        kept = root / "data" / "theirs"
        kept.mkdir(parents=True)
        (kept / "notes.txt").write_text("mine")
        created: list[Path] = []
        placed: list[Path] = []
        payload.make_dirs([root / "data" / "mine" / "tickets", kept], created)
        board = root / "data" / "mine" / "tickets" / "tickets.db"
        board.write_text("")
        placed.append(board)
        if kept in created:
            raise SmokeFailure("a folder that already existed was recorded as created")
        payload.unmake(created, placed)
        if (root / "data" / "mine").exists():
            raise SmokeFailure("undoing a run left the folders it created")
        if not (kept / "notes.txt").exists():
            raise SmokeFailure("undoing a run took a folder it did not create")
        ok.append("an abandoned run undoes the folders and board it created")

    # schema.sql ships beside the code in a source tree and one folder above
    # it in a build, and a board cannot be provisioned without it.
    with tempfile.TemporaryDirectory() as tmp:
        # Resolved, because schema_path resolves what it is given and the
        # comparison below is against a path this test built.
        # // macOS hands out temp directories under /var, which is a symlink to
        # // /private/var, so an unresolved expectation never matches there while
        # // it matches everywhere /tmp is a real directory.
        root = Path(tmp).resolve()
        source_ui = root / "bristol" / "ui"
        source_ui.mkdir(parents=True)
        (root / "bristol" / "schema.sql").write_text("-- schema\n")
        found = payload.schema_path(source_ui / "setup_wizard.py")
        if found != root / "bristol" / "schema.sql":
            raise SmokeFailure("schema.sql is not found from a source tree")

        resources = root / "App.app" / "Contents" / "Resources"
        (resources / "lib" / "python3.13" / "ui").mkdir(parents=True)
        (resources / "schema.sql").write_text("-- schema\n")
        found = payload.schema_path(
            resources / "lib" / "python3.13" / "ui" / "setup_wizard.py")
        if found != resources / "schema.sql":
            raise SmokeFailure("schema.sql is not found inside a built bundle")

        bare = root / "bare" / "ui"
        bare.mkdir(parents=True)
        if payload.schema_path(bare / "setup_wizard.py") is not None:
            raise SmokeFailure("a missing schema.sql was reported as found")
    ok.append("schema.sql resolves from a source tree and from inside a bundle")

    # A bundle keeps only the Qt modules slim.py names, so a module imported
    # anywhere in the app and absent from that list ships an app that starts
    # and then cannot import it.
    import re as _re

    import slim

    imported = set()
    for source_file in (TOOLS / "bristol").rglob("*.py"):
        if any(part in ("dist", "build", ".eggs", "__pycache__")
               for part in source_file.parts):
            continue
        for match in _re.finditer(r"PySide6\.(Qt[A-Za-z]+)",
                                  source_file.read_text(encoding="utf-8")):
            imported.add(match.group(1))
    missing = sorted(imported - set(slim.MODULES))
    if missing:
        raise SmokeFailure(
            f"the app imports {', '.join(missing)}, which a slimmed bundle "
            "does not carry — add them to slim.MODULES"
        )
    ok.append(f"a slimmed bundle carries every Qt module the app imports "
              f"({len(imported)})")

    return ok


def check_config_resolution() -> list[str]:
    """Which configuration file the app reads.

    The instance pointer outranks the tree the app runs from, so a pointer left
    by an installation that is gone would make every configured field read as
    absent while a good configuration sat beside the running code.
    """
    import tempfile

    ok: list[str] = []
    tool_on_path("bristol")
    import config_file
    import instance

    orig_get_path = instance.get_path
    orig_project_root = config_file.project_root
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            live = root / "config" / "config.local.json"
            live.write_text('{"active_agent": "chief_of_staff", '
                            '"agents": {"chief_of_staff": {}, "librarian": {}}}')
            config_file.project_root = lambda: root

            gone = root / "removed" / "config" / "config.local.json"
            instance.get_path = lambda key: gone if key == "config_path" else None
            if config_file.path() != live:
                raise SmokeFailure(
                    "a pointer naming a config that is not there won over the "
                    "one beside the running tree")
            if config_file.agent_slugs() != ["chief_of_staff", "librarian"]:
                raise SmokeFailure("the configured agents did not survive a stale pointer")
            ok.append("a stale instance pointer does not hide the configuration in use")

            other = root / "elsewhere" / "config.local.json"
            other.parent.mkdir(parents=True)
            other.write_text("{}")
            instance.get_path = lambda key: other if key == "config_path" else None
            if config_file.path() != other:
                raise SmokeFailure("a pointer naming a real config was ignored")
            ok.append("a pointer naming a config that exists still wins")
    finally:
        instance.get_path = orig_get_path
        config_file.project_root = orig_project_root

    return ok


TARGETS = {
    "bristol": check_bristol,
    "payload": check_payload,
    "config_resolution": check_config_resolution,
    "test_control": check_test_control,
    "governing_docs": check_governing_docs,
    "skill_declarations": check_skill_declarations,
    "published_files": check_published_files,
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _run_one_inprocess(name: str) -> int:
    fn = TARGETS.get(name)
    if fn is None:
        print(f"SMOKE FAIL: unknown target '{name}'")
        return 2
    try:
        for line in fn():
            print(f"ok  [{name}] {line}")
    except Exception as exc:  # noqa: BLE001 — a smoke check catching everything is the point
        import traceback

        print(f"SMOKE FAIL [{name}]: {exc.__class__.__name__}: {exc}")
        traceback.print_exc()
        return 1
    return 0


def _orchestrate(names: list[str]) -> int:
    rc = 0
    for name in names:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--target", name],
            capture_output=True,
            text=True,
        )
        sys.stdout.write(proc.stdout)
        if proc.stderr.strip():
            sys.stderr.write(proc.stderr)
        rc = rc or proc.returncode
    print("SMOKE OK" if rc == 0 else "SMOKE FAILED")
    return rc


def main() -> None:
    ap = argparse.ArgumentParser(description="Runtime-error smoke checks for the GUI tools.")
    ap.add_argument("targets", nargs="*", help="targets to check (default: all)")
    ap.add_argument("--target", help="run exactly one target IN THIS process (used by the orchestrator)")
    args = ap.parse_args()

    if args.target:
        sys.exit(_run_one_inprocess(args.target))

    names = args.targets or list(TARGETS)
    unknown = [n for n in names if n not in TARGETS]
    if unknown:
        sys.exit(f"smoke: unknown target(s): {', '.join(unknown)}. Known: {', '.join(TARGETS)}")
    sys.exit(_orchestrate(names))


if __name__ == "__main__":
    main()
