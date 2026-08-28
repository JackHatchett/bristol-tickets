"""ui/main_window.py — the top-level window.

This module is the ``MainWindow`` shell: one full-width header bar carrying the
app's identity, the view tabs, Refresh and Create; the views those tabs switch between
(Search, Backlog, Board, Archive, Settings); and the right-hand inspector panel.
The header spans the window and the splitter sits under it, so nothing above the
board floats on an alignment of its own.

The Kanban model puts a task's tab in ``task.stage`` (backlog | active |
archive) and its manual order in ``task.sort_order``. The
pieces it composes live in sibling modules:

    theme.py         palette, stylesheet, COLUMNS, CARD_ROLE, small helpers
    filter_menu.py   FilterState and FilterMenu (what the board is showing)
    schema_guard.py  ensure_schema_up_to_date()
    card_delegate.py CardDelegate (per-card QPainter rendering)
    record_dialog.py UnifiedRecordDialog (create/edit modal)
    kanban_column.py KanbanColumn (a populated column of cards)
    detail_pane.py   DetailPane (the selected card, read and edited in place)
    dialogs.py       confirm(), choose(), notify() — every modal question
    setup_wizard.py  first-run setup, also reachable from File → Setup…
    settings_tab.py  SettingsTab (the next-session agent, board behaviour,
                     appearance — all stored in config.local.json)

Each file stays small enough for an external consultant to ingest and edit in
one pass.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QFrame,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local: the one config.local.json reader/writer

from .detail_pane import DetailPane
from .dialogs import confirm, notify
from .filter_menu import FilterMenu, FilterState, applied
from .links import remove_links_for_task
from .kanban_column import KanbanColumn
from .record_dialog import UnifiedRecordDialog
from .schema_guard import ensure_schema_up_to_date
from .settings_tab import SettingsTab
from .theme import (
    COLUMNS,
    LAYOUT,
    apply_scheme,
    build_style_sheet,
    is_dark_scheme,
    resolve_choice,
    set_scheme,
    space,
    _fmt_dt,
    _utcnow,
)

# How long the splitter may keep moving before its width is written to the
# configuration, so a drag lands as one save rather than a stream of them.
SPLITTER_SETTLE_MS = 800

# How many filter chips stand on the control row before the rest are counted.
# Past this the row would push the board's own controls around, and the panel
# is one click away.
CHIPS_SHOWN = 4

class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, initial_db: Path | None = None) -> None:
        super().__init__()
        self.conn = conn

        ensure_schema_up_to_date(self.conn)

        self.setWindowTitle("Bristol Tickets")
        # App icon on the window (Dock/taskbar when launched as a script; the
        # built .app gets its icon from setup.py's iconfile). The PNG sits at the
        # package root next to app.py.
        _icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
        self.setMinimumSize(LAYOUT["window_min_w"], LAYOUT["window_min_h"])
        # Open wide by default so the board and the inspector panel both
        # have room on launch.
        self.resize(LAYOUT["window_w"], LAYOUT["window_h"])

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

        self._build_menu_bar()

        # One full-width header spans the window, and the splitter sits under
        # it: identity, the view tabs, Refresh and Create all read as one bar
        # rather than floats on separate alignments.
        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.setCentralWidget(shell)

        # The pages the header switches between. Built before the header so a
        # tab button has something to select.
        self.pages = QStackedWidget()

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(space("lg"))

        left_container = QWidget()
        left_container.setObjectName("leftContainer")
        outer_layout = QVBoxLayout(left_container)
        outer_layout.setContentsMargins(space("xl"), space("lg"),
                                        space("lg"), space("lg"))
        outer_layout.setSpacing(space("lg"))
        main_splitter.addWidget(left_container)

        # Refresh reloads every view, so it belongs beside Create in the one
        # bar that spans every tab rather than on the Board.
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Reload every view from the database.")
        self.refresh_btn.clicked.connect(self._refresh_board)

        self.global_create_btn = QPushButton("Create")
        self.global_create_btn.setObjectName("globalCreateBtn")
        self.global_create_btn.clicked.connect(self._open_global_create)

        # The board's filter. One state narrows the board, the Backlog and
        # the Archive; the button opens the panel that sets it, and the chips
        # beside it say what is set without opening anything. The controls are
        # built here and placed in the Board tab's control row below.
        self.filters = FilterState()

        self.filter_btn = QPushButton("Filter")
        self.filter_btn.setObjectName("filterBtn")
        self.filter_btn.setToolTip(
            "Narrow the Board, the Backlog and the Archive to an assignee, an "
            "epic, or both.")
        self.filter_btn.clicked.connect(self._open_filter_menu)
        # Built on first use, against the board as it stands at that moment.
        self.filter_menu = None

        self.filter_clear_btn = QPushButton("Clear")
        self.filter_clear_btn.setObjectName("filterClear")
        self.filter_clear_btn.setCursor(Qt.PointingHandCursor)
        self.filter_clear_btn.setToolTip("Remove every filter.")
        self.filter_clear_btn.clicked.connect(self._clear_filters)

        self.chip_row = QHBoxLayout()
        self.chip_row.setContentsMargins(0, 0, 0, 0)
        self.chip_row.setSpacing(space("sm"))

        # The splitter and, at the window's right edge, the strip that brings a
        # collapsed detail pane back. The strip is outside the splitter so the
        # columns reflow into the whole reclaimed width while the pane is away.
        board_and_pane = QWidget()
        body_row = QHBoxLayout(board_and_pane)
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)
        body_row.addWidget(main_splitter, 1)
        self.pane_reveal = QPushButton("❮")
        self.pane_reveal.setObjectName("paneReveal")
        self.pane_reveal.setToolTip("Show the detail pane")
        self.pane_reveal.setCursor(Qt.PointingHandCursor)
        self.pane_reveal.setFixedWidth(space("2xl"))
        self.pane_reveal.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.pane_reveal.clicked.connect(lambda: self._set_pane_collapsed(False))
        self.pane_reveal.setVisible(False)
        body_row.addWidget(self.pane_reveal)

        shell_layout.addWidget(self._build_header())
        shell_layout.addWidget(board_and_pane, 1)
        outer_layout.addWidget(self.pages)

        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(space("lg"))

        search_bar_layout = QHBoxLayout()
        search_bar_layout.setSpacing(space("md"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search issues and epics")
        self.search_input.returnPressed.connect(self._execute_global_search)
        search_bar_layout.addWidget(self.search_input, 1)

        search_go_btn = QPushButton("Find")
        search_go_btn.clicked.connect(self._execute_global_search)
        search_bar_layout.addWidget(search_go_btn)

        self.hide_closed_checkbox = QCheckBox("Hide Closed Items")
        self.hide_closed_checkbox.setChecked(True)
        self.hide_closed_checkbox.stateChanged.connect(self._execute_global_search)
        search_bar_layout.addWidget(self.hide_closed_checkbox)
        search_layout.addLayout(search_bar_layout)

        self.search_count = QLabel("")
        self.search_count.setObjectName("formCaption")
        search_layout.addWidget(self.search_count)

        self.search_results = QListWidget()
        self.search_results.setObjectName("searchResults")
        self.search_results.itemClicked.connect(self._on_search_item_clicked)
        self.search_results.itemDoubleClicked.connect(self._on_search_item_double_clicked)
        search_layout.addWidget(self.search_results, 1)
        self._add_page(search_widget, "Search")

        # BACKLOG — a single manually-ordered list (drag to reorder, saved) with
        # per-card checkboxes driving a bulk Activate / Delete bar.
        backlog_widget = QWidget()
        backlog_outer = QVBoxLayout(backlog_widget)
        # The board's filter narrows this list too, and the control that sets it
        # is on the Board. A view that is holding cards back says so.
        self.backlog_filter_note = QLabel()
        self.backlog_filter_note.setObjectName("formCaption")
        backlog_outer.addWidget(self.backlog_filter_note)
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
        self.backlog_selall_btn = QPushButton("Select All")
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
        self._backlog_tab_index = self._add_page(backlog_widget, "Backlog")

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
        board_outer.setContentsMargins(0, 0, 0, 0)
        board_outer.setSpacing(space("lg"))

        # One control row above the columns, holding what applies to the whole
        # board and nothing beyond it. A single card in any column is created
        # from the master Create button, not from a per-column control. What
        # narrows the board reads left to right — the button, then what it is
        # narrowed to — and Clear Done sits at the far end, where a growing chip
        # row never moves it. Refresh is not here: it reloads every view, so it
        # lives in the header that spans every tab.
        board_controls = QHBoxLayout()
        board_controls.setSpacing(space("md"))
        board_controls.addWidget(self.filter_btn)
        board_controls.addLayout(self.chip_row)
        board_controls.addWidget(self.filter_clear_btn)
        board_controls.addStretch(1)
        self.clear_done_btn = QPushButton("Clear Done")
        self.clear_done_btn.setToolTip(
            "Move every card in the Done column to the Archive.")
        self.clear_done_btn.clicked.connect(self._clear_done)
        board_controls.addWidget(self.clear_done_btn)
        board_outer.addLayout(board_controls)

        board_columns = QHBoxLayout()
        board_columns.setSpacing(space("xl"))
        self.columns = {}
        for key, name in COLUMNS:
            col = KanbanColumn(self, self.conn, key, name)
            self.columns[key] = col
            board_columns.addWidget(col)
        board_outer.addLayout(board_columns)

        self._board_tab_index = self._add_page(board_widget, "Board")

        # ARCHIVE — a stripped-down line list (like Search), sorted by most
        # recently modified. Retired tickets, newest first.
        archive_widget = QWidget()
        archive_layout = QVBoxLayout(archive_widget)
        self.archive_filter_note = QLabel()
        self.archive_filter_note.setObjectName("formCaption")
        archive_layout.addWidget(self.archive_filter_note)
        self.archive_results = QListWidget()
        self.archive_results.setObjectName("searchResults")
        self.archive_results.itemClicked.connect(self._on_archive_item_clicked)
        self.archive_results.itemDoubleClicked.connect(self._on_archive_item_double_clicked)
        archive_layout.addWidget(self.archive_results)
        self._archive_tab_index = self._add_page(archive_widget, "Archive")

        self.settings_tab = SettingsTab(
            on_appearance_changed=self._preview_appearance)
        self._settings_tab_index = self._add_page(self.settings_tab, "Settings")

        # The detail pane: the selected card, read and edited in place. A pane
        # write refreshes the board; the pane's collapse control hands the
        # splitter work back here.
        self.detail_pane = DetailPane(
            self.conn,
            on_changed=self._on_pane_edit,
            on_collapse=lambda: self._set_pane_collapsed(True))
        main_splitter.addWidget(self.detail_pane)

        # Both panes are elastic (no max width — the user can widen the pane as
        # far as they like). The pane opens at the width it last held, and
        # collapsed if that is how it was left; both are stored in the
        # configuration and written back as the user moves things.
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        self._pane_collapsed = False
        self._detail_width = int(
            config_file.get(config_file.DETAIL_WIDTH, LAYOUT["split_detail"])
            or LAYOUT["split_detail"])
        main_splitter.setSizes(
            [LAYOUT["window_w"] - self._detail_width, self._detail_width])
        self._main_splitter = main_splitter

        # Geometry saves are debounced, and held off entirely until the window
        # finishes constructing, so building the window writes nothing.
        self._geometry_ready = False
        self._splitter_save_timer = QTimer(self)
        self._splitter_save_timer.setSingleShot(True)
        self._splitter_save_timer.setInterval(SPLITTER_SETTLE_MS)
        self._splitter_save_timer.timeout.connect(self._save_pane_geometry)
        main_splitter.splitterMoved.connect(self._on_splitter_moved)

        if bool(config_file.get(config_file.DETAIL_COLLAPSED, False)):
            self._set_pane_collapsed(True, save=False)

        self._sync_filter_row()
        self._refresh_board()
        self._geometry_ready = True

    def _stage_for_current_tab(self) -> str:
        """Default Stage for a new record, keyed to the tab Create was pressed
        on: Backlog → backlog, Archive → archive, everything else → active.

        A card lands on the Board unless the tab it was created from is one of
        the other two, which is the same default ``ticket_write.py add-task``
        carries."""
        idx = self.pages.currentIndex()
        if idx == getattr(self, "_backlog_tab_index", -1):
            return "backlog"
        if idx == getattr(self, "_archive_tab_index", -1):
            return "archive"
        return "active"

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

    # ----- The detail pane: collapse, reveal, and remembered geometry -------

    def _set_pane_collapsed(self, collapsed: bool, save: bool = True) -> None:
        """Collapse the pane to the window edge — the columns reflow into the
        reclaimed width — or bring it back at the width it last held."""
        if collapsed:
            sizes = self._main_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._detail_width = sizes[1]
            self.detail_pane.setVisible(False)
            self.pane_reveal.setVisible(True)
        else:
            self.detail_pane.setVisible(True)
            self.pane_reveal.setVisible(False)
            total = sum(self._main_splitter.sizes()) or LAYOUT["window_w"]
            width = max(LAYOUT["detail_min_w"],
                        min(self._detail_width, total - LAYOUT["column_min_w"]))
            self._main_splitter.setSizes([total - width, width])
        self._pane_collapsed = collapsed
        if save:
            self._save_pane_geometry()

    def _on_splitter_moved(self, *args) -> None:
        if not self._geometry_ready or self._pane_collapsed:
            return
        self._splitter_save_timer.start()

    def _save_pane_geometry(self) -> None:
        """Write the pane's width and collapsed state so both survive a
        restart. An unplaced clone has nowhere to write; the pane still works,
        it just opens at the defaults next time."""
        if not self._pane_collapsed:
            sizes = self._main_splitter.sizes()
            if len(sizes) > 1 and sizes[1] > 0:
                self._detail_width = sizes[1]
        try:
            config_file.update({
                config_file.DETAIL_WIDTH: self._detail_width,
                config_file.DETAIL_COLLAPSED: self._pane_collapsed,
            })
        except OSError:
            pass

    def _on_pane_edit(self) -> None:
        """A field changed from the pane: the board reflects it immediately."""
        self._refresh_board()

    def closeEvent(self, event):  # noqa: N802 (Qt override)
        """Flush a splitter save still waiting on its debounce, so a drag made
        just before quitting still survives the restart."""
        if self._splitter_save_timer.isActive():
            self._splitter_save_timer.stop()
            self._save_pane_geometry()
        super().closeEvent(event)

    # ----- What the board is showing ---------------------------------------

    def _open_filter_menu(self) -> None:
        """Open the panel under its button, over the board as it now stands."""
        if self.filter_menu is None:
            self.filter_menu = FilterMenu(self, self.conn, self.filters)
            self.filter_menu.changed.connect(self._on_filters_changed)
        self.filter_menu.open_under(self.filter_btn)

    def _on_filters_changed(self) -> None:
        """A filter moved: say so on the control row, and reload the views."""
        self._sync_filter_row()
        self._refresh_board()

    def _clear_filters(self) -> None:
        self.filters.clear()
        self._sync_menu()
        self._on_filters_changed()

    def _remove_filter(self, kind: str, value) -> None:
        """The one filter a chip stands for, removed where it is read."""
        self.filters.discard(kind, value)
        self._sync_menu()
        self._on_filters_changed()

    def _sync_menu(self) -> None:
        """Bring an open panel back in step with a state changed outside it."""
        if self.filter_menu is not None and self.filter_menu.isVisible():
            self.filter_menu.refresh()

    def _sync_filter_row(self) -> None:
        """The button's count and state, and one chip per filter that is set.

        The button carries the accent while anything is set, so a board showing
        four cards of forty never reads as a board with four cards on it.
        """
        count = self.filters.count()
        self.filter_btn.setText("Filter" if not count else f"Filter · {count}")
        self.filter_btn.setProperty("active", "true" if count else "false")
        self.filter_btn.style().unpolish(self.filter_btn)
        self.filter_btn.style().polish(self.filter_btn)
        self.filter_clear_btn.setVisible(bool(count))

        notice = "" if not count else (
            f"Filtered · {count} — the Filter button on the Board sets it.")
        for label in (self.backlog_filter_note, self.archive_filter_note):
            label.setText(notice)
            label.setVisible(bool(count))

        while self.chip_row.count():
            stale = self.chip_row.takeAt(0).widget()
            if stale is not None:
                stale.deleteLater()
        chips = applied(self.conn, self.filters)
        for kind, value, label in chips[:CHIPS_SHOWN]:
            chip = QPushButton(f"{label}  ✕")
            chip.setObjectName("filterChip")
            chip.setCursor(Qt.PointingHandCursor)
            chip.setToolTip("Remove this filter")
            chip.clicked.connect(
                lambda _checked=False, k=kind, v=value: self._remove_filter(k, v))
            self.chip_row.addWidget(chip)
        if len(chips) > CHIPS_SHOWN:
            rest = QLabel(f"+{len(chips) - CHIPS_SHOWN}")
            rest.setObjectName("formCaption")
            rest.setToolTip("Open Filter to see the rest.")
            self.chip_row.addWidget(rest)

    # ----- The header bar ---------------------------------------------------

    def _build_header(self) -> QWidget:
        """The one header bar: identity at the left, the view tabs beside it,
        Refresh and Create at the right, everything on one vertical centre line
        and closed by a single hairline. Every control here acts on every tab."""
        header = QWidget()
        header.setObjectName("appHeader")
        bar = QHBoxLayout(header)
        bar.setContentsMargins(space("xl"), space("md"), space("xl"),
                               space("sm"))
        bar.setSpacing(space("lg"))

        identity = QLabel("Bristol Tickets")
        identity.setObjectName("appIdentity")
        bar.addWidget(identity, 0, Qt.AlignVCenter)

        separator = QFrame()
        separator.setObjectName("headerRule")
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedWidth(1)
        bar.addWidget(separator, 0, Qt.AlignVCenter)

        self._tab_buttons: list[QPushButton] = []
        self._tab_row = QHBoxLayout()
        self._tab_row.setContentsMargins(0, 0, 0, 0)
        self._tab_row.setSpacing(0)
        bar.addLayout(self._tab_row)

        bar.addStretch(1)
        bar.addWidget(self.refresh_btn, 0, Qt.AlignVCenter)
        bar.addWidget(self.global_create_btn, 0, Qt.AlignVCenter)
        return header

    def _add_page(self, widget: QWidget, name: str) -> int:
        """Add a view and its tab. The tab is a flat button in the header: hover
        changes its state, and the selected one carries an accent underline."""
        index = self.pages.addWidget(widget)

        button = QPushButton(name)
        button.setObjectName("viewTab")
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda _checked, i=index: self._show_page(i))
        self._tab_row.addWidget(button)
        self._tab_buttons.append(button)
        if index == 0:
            self._show_page(0)
        return index

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for position, button in enumerate(self._tab_buttons):
            button.setChecked(position == index)

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
        notify(self, "Setup complete",
               f"Your installation is at {db_path}.\n\n"
               f"Bristol Tickets opens it the next time it launches.")

    # ----- Theming (OS light/dark, warm orange both ways) -------------------

    def _apply_theme(self) -> None:
        """Point the palette at the configured scheme and (re)apply the global
        stylesheet. Safe to call repeatedly — used at startup, on every OS
        colour-scheme change, and when the choice is edited in Settings.

        A stored family name resolves against the OS state, so 'follow the
        system' and a pinned scheme come down the same path.
        """
        app = QApplication.instance()
        choice = config_file.get(config_file.APPEARANCE_SCHEME,
                                 config_file.APPEARANCE_SCHEME_DEFAULT)
        # Applied app-wide so child dialogs and message boxes inherit; fall back
        # to the window itself if there's somehow no application object.
        apply_scheme(app, choice)
        if app is None:
            self.setStyleSheet(build_style_sheet())

    def _preview_appearance(self, choice: str) -> None:
        """Draw the app in a scheme the Settings tab is offering, before the
        configuration says so. Settings' Save is what makes the choice stick."""
        app = QApplication.instance()
        set_scheme(resolve_choice(
            choice, is_dark_scheme(app) if app is not None else False))
        sheet = build_style_sheet()
        if app is not None:
            app.setStyleSheet(sheet)
        else:
            self.setStyleSheet(sheet)
        self._repaint_cards()
        if hasattr(self, "detail_pane"):
            self.detail_pane.refresh_theme()

    def refresh_appearance(self) -> None:
        """Re-theme and repaint everything the scheme reaches.

        The QPainter-drawn cards read the live palette at paint time, so a
        viewport update is all they need; everything else is stylesheet-driven
        and re-themes on the sheet alone — except the pane's timeline, which
        bakes colours into its HTML and re-renders instead.
        """
        self._apply_theme()
        self._repaint_cards()
        if hasattr(self, "detail_pane"):
            self.detail_pane.refresh_theme()

    def _repaint_cards(self) -> None:
        """Update every viewport holding delegate-painted cards."""
        for col in getattr(self, "columns", {}).values():
            col.list_widget.viewport().update()
        if hasattr(self, "backlog_column"):
            self.backlog_column.list_widget.viewport().update()
        if hasattr(self, "archive_results"):
            self.archive_results.viewport().update()

    def _on_color_scheme_changed(self, *args) -> None:
        """OS switched between light and dark. It reaches the app only while the
        stored choice names a family; a pinned scheme resolves to itself."""
        self.refresh_appearance()

    # ----- Sweeping the Done column to the Archive -------------------------

    def _clear_done(self) -> None:
        """Move every card in the Done column (stage=active, status=done) to the
        Archive, appended to the top of the modified-ordered Archive. Reached
        from the Done column's own menu, with no per-card selection to manage —
        the one bulk action the board offers."""
        rows = self.conn.execute(
            "SELECT id FROM task WHERE stage='active' AND status='done'"
        ).fetchall()
        ids = [r[0] for r in rows]
        if not ids:
            notify(self, "Nothing to clear", "The Done column is empty.")
            return
        if not confirm(self, "Clear Done",
                       f"Move {len(ids)} done card(s) to the Archive?",
                       "Move to Archive"):
            return
        self._move_tasks_to_stage(ids, "archive")
        # Stamp the archival moment as closed_at — this is the timestamp that
        # orders the Archive. "Clear Done" is the canonical close action, so it
        # (re)sets closed_at to now for every card it sweeps, and the Archive
        # lists newest-closed first.
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
        notify(self, "Report not written",
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
            notify(self, "Nothing checked",
                   "Tick one or more backlog cards first.")
            return
        self._move_tasks_to_stage(ids, "active")
        self._refresh_board()

    def _bulk_delete_backlog(self) -> None:
        ids = self.backlog_column.checked_ids()
        if not ids:
            notify(self, "Nothing checked",
                   "Tick one or more backlog cards first.")
            return
        if not confirm(self, "Delete backlog cards",
                       f"Permanently delete {len(ids)} backlog card(s)? This "
                       f"cannot be undone.",
                       "Delete", destructive=True):
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

    def _load_archive(self, filters: FilterState) -> None:
        """Fill the Archive list with stage='archive' tasks, newest-CLOSED
        first — ordered by closed_at, the timestamp Clear Done stamps on
        archival. Cards archived by some other path that never got
        a closed_at fall back to updated_at so they still sort sanely. A
        stripped one-line-per-ticket view like Search."""
        self.archive_results.clear()
        narrow, params = filters.where("t")
        query = (
            "SELECT t.id, t.title, t.status, COALESCE(t.record_type,'build'), "
            "COALESCE(t.closed_at, t.updated_at) AS closed "
            "FROM task t WHERE t.stage='archive'" + narrow
        )
        query += " ORDER BY closed DESC, t.id DESC"
        try:
            rows = self.conn.execute(query, tuple(params)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        for tid, title, status, rtype, closed in rows:
            kind = "Fix" if (rtype or "build").lower() == "fix" else "Build"
            when = _fmt_dt(closed)
            item = QListWidgetItem(
                f"{kind}   #{tid}   {title}   ·   {status}   ·   {when}")
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
                self._refresh_board()

    def _open_global_create(self):
        # A new task's default Stage follows the tab Create was pressed on
        # (_stage_for_current_tab). The user can still change Stage in the
        # dialog.
        epic_id = self.filters.sole_epic()
        dlg = UnifiedRecordDialog(self, self.conn, mode="task", initial_status="todo",
                                  initial_stage=self._stage_for_current_tab(),
                                  epic_id=epic_id)
        if dlg.exec() == QDialog.Accepted:
            dlg.save_data(fallback_epic=epic_id)
            self._refresh_board()

    def _update_inspector(self, record_id: int, mode: str):
        """Point the detail pane at whatever a view selected."""
        if mode == "epic":
            self.detail_pane.show_epic(record_id)
        else:
            self.detail_pane.show_task(record_id)

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
                item = QListWidgetItem(
                    f"{kind}   #{row[0]}   {row[1]}   ·   {row[2]}")
                item.setData(Qt.UserRole, (row[0], "task"))
                self.search_results.addItem(item)

            epic_query = "SELECT id, name, status FROM epic WHERE (name LIKE ? OR description LIKE ?)"
            if hide_closed:
                epic_query += " AND status NOT IN ('completed', 'done', 'on hold')"
            epic_query += " ORDER BY name COLLATE NOCASE LIMIT 50"

            for row in self.conn.execute(epic_query, (term, term)).fetchall():
                item = QListWidgetItem(
                    f"Epic   #{row[0]}   {row[1]}   ·   {row[2]}")
                item.setData(Qt.UserRole, (row[0], "epic"))
                self.search_results.addItem(item)
        except sqlite3.OperationalError:
            pass
        found = self.search_results.count()
        self.search_count.setText(
            "No results" if not found
            else f"{found} result" + ("" if found == 1 else "s"))

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
                self._refresh_board()

    def _refresh_board(self):
        """Reload every view from the database, through the board's filter.

        Search is reloaded too and takes no filter: it is the one view whose
        job is to find a card the board is not showing.
        """
        for col in self.columns.values():
            col.load_board_tasks(self.filters)
        self.backlog_column.load_backlog_tasks(self.filters)
        self._sync_backlog_bar()
        self._load_archive(self.filters)
        self._execute_global_search()
