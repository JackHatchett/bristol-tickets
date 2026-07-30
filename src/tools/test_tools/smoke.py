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

    schema = TOOLS / "bristol" / "schema.sql"
    if schema.exists():
        from PySide6.QtCore import Qt

        from ui.main_window import MainWindow

        mconn = sqlite3.connect(":memory:")
        mconn.executescript(schema.read_text())

        def _seed(title, stage, status, sort_order, priority=0):
            mconn.execute(
                "INSERT INTO task (title, description, status, stage, sort_order, "
                "priority, record_type, assignee, reporter, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?, 'build','user','user','2026-07-08','2026-07-08')",
                (title, "d", status, stage, sort_order, priority))
            return mconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        _seed("active todo", "active", "todo", 0, 50)
        b1 = _seed("backlog one", "backlog", "todo", 0, 90)
        b2 = _seed("backlog two", "backlog", "todo", 1, 80)
        _seed("archived", "archive", "done", 0)
        mconn.commit()

        win = MainWindow(mconn)
        if hasattr(win, "handoff_note_edit"):
            raise SmokeFailure("Handoff tab still present — it is retired")
        tab_names = {win.tabs.tabText(i) for i in range(win.tabs.count())}
        if "Handoff" in tab_names:
            raise SmokeFailure("Handoff tab still present — it is retired")
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
        from PySide6.QtWidgets import QMessageBox
        mconn.execute("UPDATE task SET status='done' WHERE id=?", (b1,))
        mconn.commit()
        _orig_q = QMessageBox.question
        QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
        _prior_reports_dir = _os.environ.get("BRISTOL_REPORTS_DIR")
        with tempfile.TemporaryDirectory() as reports_tmp:
            _os.environ["BRISTOL_REPORTS_DIR"] = reports_tmp
            try:
                win._refresh_board()
                win._clear_done()
            finally:
                QMessageBox.question = _orig_q
                if _prior_reports_dir is None:
                    _os.environ.pop("BRISTOL_REPORTS_DIR", None)
                else:
                    _os.environ["BRISTOL_REPORTS_DIR"] = _prior_reports_dir
            written = sorted(Path(reports_tmp).glob("bristol_report_*.md"))
            if not written:
                raise SmokeFailure("Clear Done did not write an analytic report")
            body = written[0].read_text(encoding="utf-8")
            for required in ("# Bristol Report", "#### Executive Summary",
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

        # Create-modal Stage follows the active tab.
        win.tabs.setCurrentIndex(win._board_tab_index)
        if win._stage_for_current_tab() != "active":
            raise SmokeFailure("Create from Board should default Stage=active")
        win.tabs.setCurrentIndex(win._archive_tab_index)
        if win._stage_for_current_tab() != "archive":
            raise SmokeFailure("Create from Archive should default Stage=archive")
        win.tabs.setCurrentIndex(0)  # Search
        if win._stage_for_current_tab() != "backlog":
            raise SmokeFailure("Create from Search should default Stage=backlog")
        win._sync_backlog_bar()  # must not raise with nothing checked
        ok.append("Create-modal Stage follows active tab; backlog bar sync runs")

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
        # area, and the short fields are dealt across two columns so the body is
        # rarely tall enough to need scrolling in the first place.
        from PySide6.QtWidgets import QScrollArea
        if not isinstance(getattr(guard_dlg, "_scroll", None), QScrollArea):
            raise SmokeFailure("record dialog body is not inside a scroll area")
        scrolled = guard_dlg._scroll.widget()
        btn_parent = guard_dlg.button_box.parentWidget()
        if btn_parent is scrolled or (btn_parent and btn_parent.isAncestorOf(scrolled)
                                      and btn_parent is not guard_dlg):
            raise SmokeFailure("button row is inside the scroll area — it can scroll away")
        if guard_dlg.left_form.rowCount() == 0 or guard_dlg.right_form.rowCount() == 0:
            raise SmokeFailure("metadata fields are not split across two columns")
        for w in (guard_dlg.stage_combo, guard_dlg.status_combo, guard_dlg.owner_edit,
                  guard_dlg.epic_combo, guard_dlg.priority_spin):
            if guard_dlg._row_form.get(w) is None:
                raise SmokeFailure(f"{w!r} was not placed in a column form")
        guard_dlg._update_visible_fields()  # must not raise across either column
        ok.append("Record dialog scrolls, pins its buttons, splits fields in two columns")

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
        bar._pending += [("issue", lb, "", ""), ("uri", None, "https://x.test", "X")]
        if not bar.has_pending():
            raise SmokeFailure("LinkBar did not buffer links for an unsaved ticket")
        le = _seed_link_task("Echo")
        bar.flush_pending(le)
        if bar.has_pending() or sorted(x["kind"] for x in list_links(lc, le)) != [
                "issue", "uri"]:
            raise SmokeFailure("flush_pending did not write the buffered links")
        ok.append("Links: symmetric issue edge, uri links, pending buffer")
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


TARGETS = {
    "bristol": check_bristol,
    "test_control": check_test_control,
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
