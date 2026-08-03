"""ui/main_window.py — the top-level window (Bristol v18, warm card UI).

This module is now just the ``MainWindow`` shell: the toolbar (create / epic
filter / Bulk Change [Board tab only] / refresh), the tabbed views (Search,
Backlog, Board, Archive), and the right-hand inspector panel. The Kanban
model puts a task's tab in ``task.stage`` (backlog | active |
archive) and its manual order in ``task.sort_order``. The
pieces it composes live in sibling modules:

    theme.py         palette, stylesheet, COLUMNS, CARD_ROLE, small helpers
    schema_guard.py  ensure_schema_up_to_date()
    card_delegate.py CardDelegate (per-card QPainter rendering)
    record_dialog.py UnifiedRecordDialog (create/edit modal)
    kanban_column.py KanbanColumn (a populated column of cards)
    setup_wizard.py  first-run setup, also reachable from File → Setup…
    settings_tab.py  SettingsTab (board behaviour, stored in config.local.json)

Database logic is unchanged from the pre-split v17/v18 baseline; this was a pure
structural refactor to keep each file small enough for an external consultant
(Gemini / Copilot) to ingest and edit in one pass.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QIcon, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local: the one config.local.json reader/writer

from .attachments import AttachmentBar
from .links import LinkBar, remove_links_for_task
from .kanban_column import KanbanColumn
from .record_dialog import UnifiedRecordDialog
from .schema_guard import ensure_schema_up_to_date
from .settings_tab import SettingsTab
from .theme import (
    COLUMNS,
    FLEET_AGENTS,
    build_style_sheet,
    is_dark_scheme,
    set_scheme,
    _fmt_dt,
    _get_epic_badge,
    _utcnow,
    log_lines,
)

class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, initial_db: Path | None = None) -> None:
        super().__init__()
        self.conn = conn

        ensure_schema_up_to_date(self.conn)

        self.setWindowTitle("Bristol")
        # App icon on the window (Dock/taskbar when launched as a script; the
        # built .app gets its icon from setup.py's iconfile). The PNG sits at the
        # package root next to app.py.
        _icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
        self.setMinimumSize(1240, 780)
        # Open wide by default so the board and the inspector panel both
        # have room on launch.
        self.resize(1960, 1080)

        # Follow the OS light/dark setting with a warm orange palette in both
        # modes, and re-theme live when the OS flips (macOS auto-appearance
        # timer). Applied at the QApplication level so every modal dialog and
        # message box is themed too — the old code styled only the main window,
        # which is why dialogs fell through to the black system dark palette and
        # became unreadable.
        self._apply_theme()
        app = QApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

        self.current_epic_id = None

        self._build_menu_bar()

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(10)
        self.setCentralWidget(main_splitter)

        left_container = QWidget()
        left_container.setObjectName("leftContainer")
        outer_layout = QVBoxLayout(left_container)
        outer_layout.setContentsMargins(14, 14, 8, 14)
        outer_layout.setSpacing(10)
        main_splitter.addWidget(left_container)

        # Global navigation IS the tabs, so they sit at the very top of the page
        #. The page-specific controls (epic filter, Refresh, Clear
        # Done) were moved off this top strip and into the Board tab, above its
        # columns — built below. The one genuinely global action, Create, rides in
        # the tab bar's top-right corner: always reachable, and it reads the
        # active tab to default the new record's Stage.
        self.tabs = QTabWidget()

        self.global_create_btn = QPushButton("Create")
        self.global_create_btn.setObjectName("globalCreateBtn")
        self.global_create_btn.clicked.connect(self._open_global_create)
        self.tabs.setCornerWidget(self.global_create_btn, Qt.TopRightCorner)

        # Epic filter and Refresh are constructed here but placed in the Board
        # tab's own control row (built below). The epic filter still drives every
        # view (board, backlog, archive, search) through current_epic_id — it
        # just lives on the Board visually. The combo carries no caption; it
        # defaults to the self-describing "All Epics".
        self.epic_filter = QComboBox()
        # Don't let the combo auto-widen to its longest epic name; its width is
        # pinned to the Clear Done button once that exists. The
        # popup list still shows full names.
        self.epic_filter.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.epic_filter.currentIndexChanged.connect(self._on_epic_changed)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_board)

        outer_layout.addLayout(self._build_agent_strip())
        outer_layout.addWidget(self.tabs)

        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)

        search_left = QVBoxLayout()
        search_bar_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search issues, epics...")
        self.search_input.returnPressed.connect(self._execute_global_search)
        search_bar_layout.addWidget(self.search_input)

        search_go_btn = QPushButton("Find")
        search_go_btn.clicked.connect(self._execute_global_search)
        search_bar_layout.addWidget(search_go_btn)
        search_left.addLayout(search_bar_layout)

        self.hide_closed_checkbox = QCheckBox("Hide Closed Items")
        self.hide_closed_checkbox.setChecked(True)
        self.hide_closed_checkbox.stateChanged.connect(self._execute_global_search)
        search_left.addWidget(self.hide_closed_checkbox)

        self.search_results = QListWidget()
        self.search_results.setObjectName("searchResults")
        self.search_results.itemClicked.connect(self._on_search_item_clicked)
        self.search_results.itemDoubleClicked.connect(self._on_search_item_double_clicked)
        search_left.addWidget(self.search_results)

        search_widget_container = QWidget()
        search_widget_container.setLayout(search_left)
        search_layout.addWidget(search_widget_container, 1)
        self.tabs.addTab(search_widget, "Search")

        # BACKLOG — a single manually-ordered list (drag to reorder, saved) with
        # per-card checkboxes driving a bulk Activate / Delete bar.
        backlog_widget = QWidget()
        backlog_outer = QVBoxLayout(backlog_widget)
        self.backlog_column = KanbanColumn(self, self.conn, None, "Backlog (drag to reorder)",
                                           is_backlog=True)
        backlog_outer.addWidget(self.backlog_column)

        backlog_bar = QHBoxLayout()
        # Edit gates the whole bulk-select apparatus: in read mode
        # the backlog is just a draggable, reorderable list — the checkboxes and
        # action buttons only appear once the user opts into Edit.
        self._backlog_editing = False
        self.backlog_edit_btn = QPushButton("Edit")
        self.backlog_edit_btn.setObjectName("globalCreateBtn")
        self.backlog_edit_btn.setToolTip(
            "Show the bulk-select checkboxes to activate or delete cards. "
            "Dragging to reorder never needs Edit.")
        self.backlog_edit_btn.clicked.connect(self._toggle_backlog_edit)
        self.backlog_selall_btn = QPushButton("Select all")
        self.backlog_selall_btn.clicked.connect(lambda: self._set_all_backlog_checks(True))
        self.backlog_clear_btn = QPushButton("Clear")
        self.backlog_clear_btn.clicked.connect(lambda: self._set_all_backlog_checks(False))
        self.backlog_activate_btn = QPushButton("Activate →")
        self.backlog_activate_btn.setObjectName("globalCreateBtn")
        self.backlog_activate_btn.setToolTip(
            "Move checked cards to the active Board (appended to the bottom of "
            "their status column, in their current backlog order).")
        self.backlog_activate_btn.clicked.connect(self._bulk_activate_backlog)
        self.backlog_delete_btn = QPushButton("Delete")
        self.backlog_delete_btn.setObjectName("deleteBtn")
        self.backlog_delete_btn.clicked.connect(self._bulk_delete_backlog)
        backlog_bar.addWidget(self.backlog_edit_btn)
        backlog_bar.addWidget(self.backlog_selall_btn)
        backlog_bar.addWidget(self.backlog_clear_btn)
        backlog_bar.addStretch()
        backlog_bar.addWidget(self.backlog_activate_btn)
        backlog_bar.addWidget(self.backlog_delete_btn)
        backlog_outer.addLayout(backlog_bar)
        self.tabs.addTab(backlog_widget, "Backlog")

        # The selection-dependent backlog actions (Clear, Activate, Delete) are
        # inert and confusing when nothing is checked, so they stay hidden until
        # at least one card is ticked. "Select all" is shown while
        # editing as the entry point. A checkbox toggle emits itemChanged, so
        # that drives the visibility sync. Start in read mode: only
        # the Edit button shows and the checkbox gutter is hidden.
        self.backlog_column.list_widget.itemChanged.connect(self._sync_backlog_bar)
        self._set_backlog_read_mode()

        board_widget = QWidget()
        board_outer = QVBoxLayout(board_widget)
        board_outer.setSpacing(8)

        # Board control row: page-specific options, each sitting
        # above its column — All Epics (left, above To Do), Refresh (centre,
        # above Doing), Clear Done (right, above Done). Three equal-width cells so
        # each control lines up over its column.
        board_controls = QHBoxLayout()
        board_controls.setSpacing(12)

        left_cell = QHBoxLayout()
        left_cell.addWidget(self.epic_filter)
        left_cell.addStretch()

        mid_cell = QHBoxLayout()
        mid_cell.addStretch()
        mid_cell.addWidget(self.refresh_btn)
        mid_cell.addStretch()

        right_cell = QHBoxLayout()
        right_cell.addStretch()
        # "Clear Done" replaces the broken Bulk Change menu: it moves
        # every card in the Done column to the Archive in one click — the one
        # bulk action asked for, with no per-card selection to manage.
        self.clear_done_btn = QPushButton("Clear Done")
        self.clear_done_btn.setObjectName("bulkMenuBtn")
        self.clear_done_btn.setToolTip("Move every card in the Done column to the Archive.")
        self.clear_done_btn.clicked.connect(self._clear_done)
        right_cell.addWidget(self.clear_done_btn)

        # Pin the All Epics dropdown to the Clear Done button's width so the two
        # controls flanking the board control row match.
        self.epic_filter.setFixedWidth(self.clear_done_btn.sizeHint().width())

        board_controls.addLayout(left_cell, 1)
        board_controls.addLayout(mid_cell, 1)
        board_controls.addLayout(right_cell, 1)
        board_outer.addLayout(board_controls)

        board_columns = QHBoxLayout()
        board_columns.setSpacing(12)
        self.columns = {}
        for key, name in COLUMNS:
            col = KanbanColumn(self, self.conn, key, name)
            self.columns[key] = col
            board_columns.addWidget(col)
        board_outer.addLayout(board_columns)

        self._board_tab_index = self.tabs.addTab(board_widget, "Board")

        # ARCHIVE — a stripped-down line list (like Search), sorted by most
        # recently modified. Retired tickets, newest first.
        archive_widget = QWidget()
        archive_layout = QVBoxLayout(archive_widget)
        self.archive_results = QListWidget()
        self.archive_results.setObjectName("searchResults")
        self.archive_results.itemClicked.connect(self._on_archive_item_clicked)
        self.archive_results.itemDoubleClicked.connect(self._on_archive_item_double_clicked)
        archive_layout.addWidget(self.archive_results)
        self._archive_tab_index = self.tabs.addTab(archive_widget, "Archive")

        self.settings_tab = SettingsTab()
        self._settings_tab_index = self.tabs.addTab(self.settings_tab, "Settings")

        # Untitled group box: the "Properties Inspector" caption was
        # dropped — it overlapped the border below and added nothing.
        self.inspector_panel = QGroupBox("")
        inspector_layout = QVBoxLayout(self.inspector_panel)

        self.ins_title = QLabel("Select any entity to view profile summary...")
        self.ins_title.setWordWrap(True)
        _ins_title_font = QFont()
        _ins_title_font.setPointSize(12)
        _ins_title_font.setBold(True)
        self.ins_title.setFont(_ins_title_font)
        self.ins_title.setObjectName("inspectorTitle")
        self.ins_title.setStyleSheet("margin-bottom: 4px;")
        inspector_layout.addWidget(self.ins_title)

        # id of the task currently shown in the inspector, so the Post button
        # knows what to log against; None when an epic/sprint is selected.
        self.current_inspect_task_id = None

        self._desc_header = QLabel("Description")
        self._desc_header.setObjectName("sectionHeader")
        inspector_layout.addWidget(self._desc_header)
        self.ins_desc = QTextEdit()
        self.ins_desc.setReadOnly(True)
        inspector_layout.addWidget(self.ins_desc, 1)

        # Links — a ticket's relations, sitting between the Description and the
        # Log because a link is context for *reading* the ticket rather than a
        # note about working it. Clicking an issue link retargets the inspector
        # at that ticket, so a chain of related work is walkable in place.
        self.ins_links = LinkBar(self.conn, author="user")
        self.ins_links.on_open_issue = self._inspect_task
        inspector_layout.addWidget(self.ins_links)

        # Log — one list holding both kinds of entry, newest first: comments
        # posted by a person or an agent, and the mechanical field changes the
        # database triggers append. Read-only display (you post to it via the
        # field below, you don't free-edit it like the Description), sharing the
        # inspector space ~half-and-half.
        self._log_header = QLabel("Log")
        self._log_header.setObjectName("sectionHeader")
        inspector_layout.addWidget(self._log_header)

        # Two independent filters, both on by default. Checkboxes rather than a
        # segmented control, which would force exactly one kind to be showing.
        log_filter_row = QHBoxLayout()
        self.log_show_comments = QCheckBox("Comments")
        self.log_show_comments.setChecked(True)
        self.log_show_comments.toggled.connect(self._rerender_log)
        self.log_show_changes = QCheckBox("Changes")
        self.log_show_changes.setChecked(True)
        self.log_show_changes.toggled.connect(self._rerender_log)
        log_filter_row.addWidget(self.log_show_comments)
        log_filter_row.addWidget(self.log_show_changes)
        log_filter_row.addStretch(1)
        inspector_layout.addLayout(log_filter_row)

        self.ins_log = QTextEdit()
        self.ins_log.setReadOnly(True)
        inspector_layout.addWidget(self.ins_log, 1)

        post_row = QHBoxLayout()
        self.log_input = QLineEdit()
        self.log_input.setPlaceholderText("Post a brief progress note…")
        self.log_input.returnPressed.connect(self._post_issue_log)
        post_row.addWidget(self.log_input)
        self.post_log_btn = QPushButton("Post")
        self.post_log_btn.clicked.connect(self._post_issue_log)
        post_row.addWidget(self.post_log_btn)
        inspector_layout.addLayout(post_row)

        # Image attachments for the selected issue.
        self.ins_attachments = AttachmentBar(self.conn)
        inspector_layout.addWidget(self.ins_attachments)

        self._set_log_controls_enabled(False)

        self.ins_meta = QLabel("")
        self.ins_meta.setWordWrap(True)
        self.ins_meta.setObjectName("metaText")
        inspector_layout.addWidget(self.ins_meta)

        main_splitter.addWidget(self.inspector_panel)
        # Both panes are elastic (no max width — the user can widen the
        # inspector as far as they like). Open with a generous inspector
        # default so it isn't smooshed on launch; setSizes' ratio (~38% to the
        # inspector) is preserved as the splitter scales to the real window
        # width.
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([1180, 720])
        self._main_splitter = main_splitter

        self._load_dropdown_filters()
        self._refresh_board()

    def _stage_for_current_tab(self) -> str:
        """Default Stage for a new record, keyed to the tab Create was pressed on: Board → active, Archive → archive, everything else
        (Search, Backlog) → backlog."""
        idx = self.tabs.currentIndex()
        if idx == self._board_tab_index:
            return "active"
        if idx == getattr(self, "_archive_tab_index", -1):
            return "archive"
        return "backlog"

    def _sync_backlog_bar(self, *args) -> None:
        """Show the selection-dependent backlog actions only when editing AND
        ≥1 card is checked; "Select all" shows whenever editing as the entry
        point. In read mode only the Edit button shows."""
        editing = getattr(self, "_backlog_editing", False)
        self.backlog_selall_btn.setVisible(editing)
        has = editing and bool(self.backlog_column.checked_ids())
        for w in (self.backlog_clear_btn, self.backlog_activate_btn,
                  self.backlog_delete_btn):
            w.setVisible(has)

    def _set_backlog_read_mode(self) -> None:
        """Read mode: checkbox gutter hidden, only the Edit button
        shows. The list is still fully draggable/reorderable."""
        self._backlog_editing = False
        self.backlog_column.set_checkbox_mode(False)
        self.backlog_edit_btn.setText("Edit")
        self._sync_backlog_bar()

    def _enter_backlog_edit_mode(self) -> None:
        """Edit mode: reveal the per-card checkboxes and the
        Select all entry point; the button becomes Done."""
        self._backlog_editing = True
        self.backlog_column.set_checkbox_mode(True)
        self.backlog_edit_btn.setText("Done")
        self._sync_backlog_bar()

    def _toggle_backlog_edit(self) -> None:
        """The one button: Edit → show checkboxes; Done → hide and clear them."""
        if self._backlog_editing:
            self._set_backlog_read_mode()
        else:
            self._enter_backlog_edit_mode()

    # ----- The active agent, always on screen -------------------------------

    def _build_agent_strip(self) -> QHBoxLayout:
        """Who the next Claude session runs as, above the tabs.

        This is not a setting: it changes what the whole application means, so
        it is visible on every tab rather than filed behind one. Selecting an
        agent writes `active_agent` into the configuration and nothing else.
        """
        self.agent_combo = QComboBox()
        slugs = config_file.agent_slugs() or [a for a in FLEET_AGENTS if a != "user"]
        self.agent_combo.addItems(slugs)
        active = config_file.get("active_agent")
        if active in slugs:
            self.agent_combo.setCurrentText(active)
        self.agent_combo.setEnabled(bool(config_file.agent_slugs()))
        self.agent_combo.currentTextChanged.connect(self._set_active_agent)

        self.agent_status = QLabel()
        strip = QHBoxLayout()
        strip.addWidget(QLabel("Start next session as"))
        strip.addWidget(self.agent_combo)
        strip.addWidget(self.agent_status, 1)
        return strip

    def _set_active_agent(self, slug: str) -> None:
        try:
            config_file.update({"active_agent": slug})
        except OSError as exc:
            self.agent_status.setText(f"Not saved: {exc}")
            return
        self.agent_status.setText(f"Next session runs as {slug}")

    # ----- Menu bar ---------------------------------------------------------

    def _build_menu_bar(self) -> None:
        """The window's one menu: re-running first-run setup."""
        setup_action = QAction("Setup…", self)
        # // Qt reads "setup" as a preferences item and moves it into the macOS
        # // application menu unless the role is pinned.
        setup_action.setMenuRole(QAction.NoRole)
        setup_action.triggered.connect(self._open_setup_wizard)
        self.menuBar().addMenu("File").addAction(setup_action)

    def _open_setup_wizard(self) -> None:
        """Run setup again, over the installation this window already has open."""
        from .setup_wizard import run_setup

        db_path = run_setup(self)
        if db_path is None:
            return
        self.settings_tab.reload()
        QMessageBox.information(
            self, "Setup complete",
            f"Your installation is at {db_path}.\n\n"
            "Bristol opens it the next time it launches.")

    # ----- Theming (OS light/dark, warm orange both ways) -------------------

    def _apply_theme(self) -> None:
        """Point the palette at the current OS colour scheme and (re)apply the
        global stylesheet. Safe to call repeatedly — used at startup and on
        every scheme change."""
        app = QApplication.instance()
        set_scheme(is_dark_scheme(app) if app is not None else False)
        sheet = build_style_sheet()
        # Apply app-wide so child dialogs / message boxes inherit; fall back to
        # the window itself if there's somehow no application object.
        if app is not None:
            app.setStyleSheet(sheet)
        else:
            self.setStyleSheet(sheet)

    def _on_color_scheme_changed(self, *args) -> None:
        """OS switched between light and dark: re-theme, then repaint the
        QPainter-drawn cards (they read the live palette at paint time, so a
        board repaint is all that's needed)."""
        self._apply_theme()
        for col in getattr(self, "columns", {}).values():
            col.list_widget.viewport().update()
        if hasattr(self, "backlog_column"):
            self.backlog_column.list_widget.viewport().update()
        if hasattr(self, "archive_results"):
            self.archive_results.viewport().update()

    # ----- Clear Done (; replaces the broken Bulk Change menu) ----

    def _clear_done(self) -> None:
        """Move every card in the Done column (stage=active, status=done) to the
        Archive, appended to the top of the modified-ordered Archive. One button,
        no per-card selection — the only bulk action the board offers."""
        rows = self.conn.execute(
            "SELECT id FROM task WHERE stage='active' AND status='done'"
        ).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            QMessageBox.information(self, "Nothing to clear",
                                    "The Done column is empty.")
            return
        reply = QMessageBox.question(
            self, "Clear Done",
            f"Move {len(ids)} done card(s) to the Archive?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self._move_tasks_to_stage(ids, "archive")
        # Stamp the archival moment as closed_at — this is the timestamp that
        # orders the Archive. "Clear Done" is the canonical close
        # action, so it (re)sets closed_at to now for every card it sweeps, and
        # the Archive lists newest-closed first.
        ts = _utcnow()
        for tid in ids:
            self.conn.execute("UPDATE task SET closed_at=? WHERE id=?", (ts, tid))
        self.conn.commit()
        self._refresh_board()
        self._write_clear_done_report(ids)

    def _write_clear_done_report(self, ids: list[int]) -> None:
        """Write the analytic report for the batch that just left the board.

        Clearing Done is the board's only natural period boundary — a set of
        finished cards leaving together, at a moment the user chose — so it is
        where the report belongs. Runs AFTER the sweep has committed, so the
        cards are already archived with their closed_at set and the report
        describes the board as it now is.

        Everything here is advisory. The archive sweep is done and durable
        before this method is called; a missing notebook folder, an unmounted
        cloud drive, or a bug in the reports package must never turn a
        successful Clear Done into a failure the user has to reason about. So
        both the import and the call are guarded — a relocated .app may not
        carry the package at all.

        Success is deliberately silent: the report appearing in the notebook is
        its own confirmation, and a dialog after every sweep would be noise on
        the board's most-used button. Only a genuine failure speaks up, since
        that is the case where the user would otherwise go looking for a file
        that was never written.
        """
        try:
            from reports.generate import generate_report_safe
        except ImportError:
            try:
                from ..reports.generate import generate_report_safe  # type: ignore
            except ImportError:
                return  # reports package unavailable (e.g. a stripped bundle)

        result = generate_report_safe(self.conn, ids)
        if result.ok or result.skipped:
            return
        QMessageBox.warning(
            self, "Report not written",
            f"The cards were archived successfully, but the analytic report "
            f"could not be written.\n\n{result.error}")

    def _move_tasks_to_stage(self, ids: list[int], stage: str) -> None:
        """Set each task's stage, appended to the bottom of the destination list
        (backlog = one list; active = per status column). Shared by the Board
        Bulk Change and the Backlog Activate action. The change log records the
        tab move itself, from the database triggers on this connection."""
        for tid in ids:
            status_row = self.conn.execute(
                "SELECT status, COALESCE(stage,'backlog') FROM task WHERE id=?",
                (tid,)).fetchone()
            if status_row is None:
                continue
            status, prior_stage = status_row
            if stage == "active":
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task "
                    "WHERE stage='active' AND status=?", (status,)).fetchone()[0]
            else:
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?",
                    (stage,)).fetchone()[0]
            self.conn.execute(
                "UPDATE task SET stage=?, sort_order=? WHERE id=?",
                (stage, base + 1, tid))
        self.conn.commit()

    # ----- Backlog bulk actions -------------------------------

    def _set_all_backlog_checks(self, checked: bool) -> None:
        lw = self.backlog_column.list_widget
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(lw.count()):
            lw.item(i).setData(Qt.CheckStateRole, state)
        lw.viewport().update()

    def _bulk_activate_backlog(self) -> None:
        """Move checked backlog cards onto the active Board. They keep their
        relative backlog order and append to the bottom of their status column."""
        ids = self.backlog_column.checked_ids()
        if not ids:
            QMessageBox.information(self, "Nothing checked",
                                    "Tick one or more backlog cards first.")
            return
        self._move_tasks_to_stage(ids, "active")
        self._refresh_board()

    def _bulk_delete_backlog(self) -> None:
        ids = self.backlog_column.checked_ids()
        if not ids:
            QMessageBox.information(self, "Nothing checked",
                                    "Tick one or more backlog cards first.")
            return
        reply = QMessageBox.question(
            self, "Confirm delete",
            f"Permanently delete {len(ids)} backlog card(s)?",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        for tid in ids:
            self.conn.execute("DELETE FROM issue_log WHERE task_id=?", (tid,))
            self.conn.execute("DELETE FROM task_event WHERE task_id=?", (tid,))
            self.conn.execute("DELETE FROM attachment WHERE task_id=?", (tid,))
            remove_links_for_task(self.conn, tid)
            self.conn.execute("DELETE FROM task WHERE id=?", (tid,))
        self.conn.commit()
        self._refresh_board()

    # ----- Archive tab (stripped chronological list) -----------

    def _load_archive(self, epic_id: int | None) -> None:
        """Fill the Archive list with stage='archive' tasks, newest-CLOSED
        first — ordered by closed_at, the timestamp Clear Done stamps on
        archival. Cards archived by some other path that never got
        a closed_at fall back to updated_at so they still sort sanely. A
        stripped one-line-per-ticket view like Search."""
        self.archive_results.clear()
        query = (
            "SELECT t.id, t.title, t.status, COALESCE(t.record_type,'build'), "
            "COALESCE(t.closed_at, t.updated_at) AS closed "
            "FROM task t WHERE t.stage='archive'"
        )
        params: list = []
        if epic_id is not None:
            query += " AND t.epic_id = ?"
            params.append(epic_id)
        query += " ORDER BY closed DESC, t.id DESC"
        try:
            rows = self.conn.execute(query, tuple(params)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        for tid, title, status, rtype, closed in rows:
            kind = "Fix" if (rtype or "build").lower() == "fix" else "Build"
            when = _fmt_dt(closed)
            item = QListWidgetItem(f"[{when}] {kind}: {title} ({status})")
            item.setData(Qt.UserRole, (tid, "task"))
            self.archive_results.addItem(item)

    def _on_archive_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self._update_inspector(data[0], data[1])

    def _on_archive_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            dlg = UnifiedRecordDialog(self, self.conn, mode=data[1], record_id=data[0])
            if dlg.exec() == QDialog.Accepted:
                dlg.save_data()
                self._load_dropdown_filters()
                self._refresh_board()

    def _open_global_create(self):
        # A new task's default Stage follows the tab Create was pressed on
        #: Board → active, Archive → archive, Search/Backlog
        # → backlog. The user can still change Stage in the dialog.
        dlg = UnifiedRecordDialog(self, self.conn, mode="task", initial_status="todo",
                                  initial_stage=self._stage_for_current_tab(),
                                  epic_id=self.current_epic_id)
        if dlg.exec() == QDialog.Accepted:
            dlg.save_data(fallback_epic=self.current_epic_id)
            self._load_dropdown_filters()
            self._refresh_board()

    def _update_inspector(self, record_id: int, mode: str):
        try:
            if mode == "task":
                row = self.conn.execute(
                    "SELECT t.title, t.description, t.status, t.pressure, e.name, "
                    "COALESCE(t.assignee,'user'), COALESCE(t.reporter,'user'), COALESCE(t.estimate,''), e.id, "
                    "t.created_at, t.updated_at, COALESCE(t.record_type,'build') "
                    "FROM task t LEFT JOIN epic e ON t.epic_id = e.id WHERE t.id = ?", (record_id,)
                ).fetchone()
                if row:
                    (title, desc, status, pressure, epic_name, owner, originator,
                     estimate, epic_id, created_at, updated_at, record_type) = row
                    badge = _get_epic_badge(epic_name, epic_id)
                    rt_tag = "Fix" if (record_type or "build").lower() == "fix" else "Build"
                    # Surface the actual issue number so it can be referenced.
                    self.ins_title.setText(f"#{record_id} {badge}{title}")
                    self.ins_desc.setPlainText(desc or "(No description narrative provided.)")

                    self.current_inspect_task_id = record_id
                    self._render_issue_log(record_id)
                    self._set_log_controls_enabled(True)
                    self.ins_attachments.set_task(record_id)
                    self.ins_links.set_task(record_id)

                    stage_row = self.conn.execute(
                        "SELECT COALESCE(stage,'backlog') FROM task WHERE id=?", (record_id,)
                    ).fetchone()
                    stage_display = (stage_row[0] if stage_row else "backlog").capitalize()

                    self.ins_meta.setText(
                        f"<b>Issue #:</b> {record_id}<br>"
                        f"<b>Record Type:</b> {rt_tag}<br>"
                        f"<b>Stage:</b> {stage_display}<br>"
                        f"<b>Status:</b> {status}<br>"
                        f"<b>Effort:</b> {(estimate or 'not sized').upper()}<br>"
                        f"<b>Owner:</b> {owner}<br>"
                        f"<b>Originator:</b> {originator}<br>"
                        f"<b>Created:</b> {_fmt_dt(created_at)}<br>"
                        f"<b>Modified:</b> {_fmt_dt(updated_at)}<br>"
                        f"<b>Epic:</b> {epic_name or 'None'}"
                    )
            elif mode == "epic":
                row = self.conn.execute("SELECT name, description, type, status FROM epic WHERE id=?", (record_id,)).fetchone()
                if row:
                    name, desc, etype, estatus = row
                    self.ins_title.setText(f"[Epic #{record_id}] {name}")
                    self.ins_desc.setPlainText(desc or "(No details provided)")
                    self._clear_issue_log()
                    self.ins_meta.setText(f"<b>Type:</b> {etype}<br><b>Status:</b> {estatus}")
        except sqlite3.OperationalError:
            pass

    # ----- Issue Log (inspector) -------------------------------------------

    def _set_log_controls_enabled(self, enabled: bool) -> None:
        self.log_input.setEnabled(enabled)
        self.post_log_btn.setEnabled(enabled)
        if not enabled:
            self.log_input.clear()

    def _inspect_task(self, task_id: int) -> None:
        """Point the inspector at a ticket by id — how a clicked issue link
        navigates. Board selection is left alone; this is a read-through, not a
        move."""
        self._update_inspector(task_id, "task")

    def _clear_issue_log(self) -> None:
        self.current_inspect_task_id = None
        self.ins_log.setPlainText("(Select an issue to see its log.)")
        self._set_log_controls_enabled(False)
        if hasattr(self, "ins_attachments"):
            self.ins_attachments.set_task(None)
        if hasattr(self, "ins_links"):
            self.ins_links.set_task(None)

    def _rerender_log(self, _checked=None) -> None:
        """Redraw the log for whatever the inspector is showing — how the two
        filter checkboxes take effect."""
        if self.current_inspect_task_id is not None:
            self._render_issue_log(self.current_inspect_task_id)

    def _render_issue_log(self, task_id: int) -> None:
        lines = log_lines(
            self.conn, task_id,
            comments=self.log_show_comments.isChecked(),
            changes=self.log_show_changes.isChecked(),
        )
        if not lines:
            self.ins_log.setPlainText("(Nothing to show.)")
            return
        self.ins_log.setPlainText("\n".join(lines))

    def _post_issue_log(self) -> None:
        if self.current_inspect_task_id is None:
            return
        body = self.log_input.text().strip()
        if not body:
            return
        try:
            self.conn.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) VALUES (?,?,?,?)",
                (self.current_inspect_task_id, "user", body, _utcnow()),
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            return
        self.log_input.clear()
        self._render_issue_log(self.current_inspect_task_id)

    def _execute_global_search(self):
        self.search_results.clear()
        term = f"%{self.search_input.text().strip()}%"
        hide_closed = self.hide_closed_checkbox.isChecked()

        # Search is ordered by TYPE (tasks, then epics) then alphabetically —
        # the stable, browsable ordering. "Hide Closed Items" hides finished
        # work: archived tasks AND done tasks still on the active board (the
        # Done column), plus finished epics.
        try:
            task_query = (
                "SELECT t.id, t.title, t.status, COALESCE(t.record_type,'build') FROM task t "
                "WHERE (t.title LIKE ? OR t.description LIKE ?)"
            )
            if hide_closed:
                task_query += " AND t.stage != 'archive' AND t.status != 'done'"
            task_query += " ORDER BY t.title COLLATE NOCASE LIMIT 50"

            for row in self.conn.execute(task_query, (term, term)).fetchall():
                kind = "Fix" if (row[3] or "build").lower() == "fix" else "Build"
                item = QListWidgetItem(f"{kind}: {row[1]} ({row[2]})")
                item.setData(Qt.UserRole, (row[0], "task"))
                self.search_results.addItem(item)

            epic_query = "SELECT id, name, status FROM epic WHERE (name LIKE ? OR description LIKE ?)"
            if hide_closed:
                epic_query += " AND status NOT IN ('completed', 'done', 'on hold')"
            epic_query += " ORDER BY name COLLATE NOCASE LIMIT 50"

            for row in self.conn.execute(epic_query, (term, term)).fetchall():
                item = QListWidgetItem(f"Epic: {row[1]} [{row[2]}]")
                item.setData(Qt.UserRole, (row[0], "epic"))
                self.search_results.addItem(item)
        except sqlite3.OperationalError:
            pass

    def _on_search_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self._update_inspector(data[0], data[1])

    def _on_search_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            dlg = UnifiedRecordDialog(self, self.conn, mode=data[1], record_id=data[0])
            if dlg.exec() == QDialog.Accepted:
                dlg.save_data()
                self._load_dropdown_filters()
                self._refresh_board()

    def _load_dropdown_filters(self):
        self.epic_filter.blockSignals(True)
        old_epic = self.epic_filter.currentData()
        DONE_EPIC = ("completed", "done")

        self.epic_filter.clear()
        self.epic_filter.addItem("All Epics", None)
        try:
            for eid, name, estatus in self.conn.execute(
                "SELECT id, name, status FROM epic ORDER BY id"
            ).fetchall():
                # Done epics are always hidden from the filter now; the
                # "Show done epics" toggle was removed. To surface a mistakenly
                # completed epic, reactivate it from the Search tab.
                if (estatus or "").lower() in DONE_EPIC:
                    continue
                self.epic_filter.addItem(name, eid)
        except sqlite3.OperationalError:
            pass

        idx = self.epic_filter.findData(old_epic)
        if idx >= 0:
            self.epic_filter.setCurrentIndex(idx)
        self.epic_filter.blockSignals(False)

    def _on_epic_changed(self):
        self.current_epic_id = self.epic_filter.currentData()
        self._refresh_board()

    def _refresh_board(self):
        for col in self.columns.values():
            col.load_board_tasks(self.current_epic_id)
        self.backlog_column.load_backlog_tasks(self.current_epic_id)
        self._sync_backlog_bar()
        self._load_archive(self.current_epic_id)
        self._execute_global_search()
