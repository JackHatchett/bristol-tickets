"""ui/main_window.py — the top-level window.

This module is the ``MainWindow`` shell: one top bar, drawn in the Mac's title
bar, carrying the views as a segmented control and Create at a fixed place at
its right; the views that control switches between (Search, Backlog, Board,
Archive); the Settings modal its Settings button opens over the window; and the
right-hand inspector panel.

The Kanban model puts a task's tab in ``task.stage`` (backlog | active |
archive) and its manual order in ``task.sort_order``. The
pieces it composes live in sibling modules:

    theme.py         re-exports tokens, palettes, themes, style_sheet,
                     board_terms and ticket_log
    filter_menu.py   FilterState and FilterMenu (what the board is showing)
    schema_guard.py  ensure_schema_up_to_date()
    card_delegate.py CardDelegate (per-card QPainter rendering)
    record_dialog.py UnifiedRecordDialog (create/edit modal)
    kanban_column.py KanbanColumn (a populated column of cards)
    detail_pane.py   DetailPane (the selected card, read and edited in place)
    dialogs.py       confirm(), choose(), notify() — every modal question
    board_write.py   write() — a control's write, committed or rolled back
    setup_wizard.py  first-run setup, also reachable from File → Setup…
    settings_modal.py SettingsModal (Agents, Skills and the Settings
                     sections, over a scrim)
    settings_tab.py  SettingsTab (the next-session agent, board behaviour,
                     appearance — all stored in config.local.json)
    theme_manager.py ThemeManagerDialog (the themes on offer, edited)
    palette_form.py  PaletteForm (one palette, a row per colour)
    skills_tab.py    SkillsTab (what a session can load, and importing one)
    agents_tab.py    AgentsTab (who is in the fleet, created and edited by form)

Each file stays small enough for an external consultant to ingest and edit in
one pass.
"""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path

import config_file  # bristol-local: the one config.local.json reader/writer
from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons, mac_window
from .agents_tab import AgentsTab
from .board_write import write
from .detail_pane import DetailPane
from .dialogs import confirm, notify
from .filter_menu import Facet, FilterMenu, FilterState, applied
from .kanban_column import KanbanColumn
from .links import remove_links_for_task
from .record_dialog import UnifiedRecordDialog
from .results_table import ResultsTable, magnifier_icon
from .schema_guard import ensure_schema_up_to_date
from .settings_modal import SettingsModal
from .settings_tab import SettingsTab
from .settled_combo import SettledComboBox
from .skills_tab import SkillsTab
from .switch import Switch
from .theme import (
    COLUMNS,
    LAYOUT,
    C,
    _fmt_dt,
    appearance_choice,
    apply_scheme,
    build_style_sheet,
    fill_agents,
    live_scheme,
    set_scheme,
    space,
    style_application,
)

# How long the splitter may keep moving before its width is written to the
# configuration, so a drag lands as one save rather than a stream of them.
SPLITTER_SETTLE_MS = 800

# How often the window asks the database whether another connection wrote to
# it. Short enough that a card closed elsewhere leaves To Do while the user is
# still looking, long enough that the check costs nothing.
BOARD_POLL_MS = 2000

# How long the search field waits after the last key before it searches, so a
# word typed quickly is one search rather than one per letter.
SEARCH_SETTLE_MS = 250


def _kind(record_type: str | None) -> str:
    return "Fix" if (record_type or "build").lower() == "fix" else "Build"


def _status_word(status: str | None) -> str:
    """A stored status as the board's column names it."""
    words = {"todo": "To Do", "doing": "Doing", "done": "Done"}
    return words.get(status or "", (status or "").replace("_", " ").title())


class _HeaderBar(QWidget):
    """The top bar. Where it stands in the title bar its empty stretches move
    the window when dragged and zoom it when double-clicked, as a title bar's
    do."""

    def mousePressEvent(self, event: QMouseEvent) -> None:
        handle = self.window().windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and handle is not None:
            handle.startSystemMove()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        window = self.window()
        window.showNormal() if window.isMaximized() else window.showMaximized()


# The views drawn as an icon at the top bar's right, and their icons from
# ui/icons/. Every other view is its name at the bar's centre.
ICON_VIEWS = {"Search": "search"}

# How many filter chips stand in the filter row before the rest are counted.
# Past this the row would push the board's own controls around, and the panel
# is one click away.
CHIPS_SHOWN = 4


class MainWindow(QMainWindow):
    def __init__(self, conn: sqlite3.Connection, initial_db: Path | None = None) -> None:
        super().__init__()
        self.conn = conn

        ensure_schema_up_to_date(self.conn)

        self.setWindowTitle("Bristol Tickets")
        # The window's own icon; a built .app takes its icon from setup.py's
        # iconfile instead. The PNG sits at the package root next to app.py.
        _icon_path = Path(__file__).resolve().parent.parent / "icon.png"
        if _icon_path.exists():
            self.setWindowIcon(QIcon(str(_icon_path)))
        self.setMinimumSize(LAYOUT["window_min_w"], LAYOUT["window_min_h"])
        # Open wide by default so the board and the inspector panel both
        # have room on launch.
        self.resize(LAYOUT["window_w"], LAYOUT["window_h"])

        # Follow the OS light/dark setting with a warm orange palette in both
        # modes, and re-theme live when it flips. Applied at the QApplication
        # level, so every modal dialog is drawn in the palette too.
        self._apply_theme()
        app = QApplication.instance()
        if app is not None:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._on_color_scheme_changed)

        # The top bar shares the title bar's band; the window title names the
        # app, so the bar carries only the views and the commands.
        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.setCentralWidget(shell)

        # The pages the top bar switches between. Built before the bar so
        # a segment has something to select.
        self.pages = QStackedWidget()

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(space("lg"))

        left_container = QWidget()
        left_container.setObjectName("leftContainer")
        outer_layout = QVBoxLayout(left_container)
        outer_layout.setContentsMargins(space("lg"), space("lg"), space("lg"), space("lg"))
        outer_layout.setSpacing(space("lg"))
        main_splitter.addWidget(left_container)

        # Refresh and Create are the top bar's commands, at its right on every
        # view. Refresh reloads every view at once; Create is faded on a view
        # with no cards rather than dropped.
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("toolbarButton")
        self.refresh_btn.setAccessibleName("Refresh")
        self.refresh_btn.setIconSize(QSize(LAYOUT["header_icon"], LAYOUT["header_icon"]))
        self.refresh_btn.clicked.connect(self._refresh_board)

        self.global_create_btn = QPushButton()
        self.global_create_btn.setObjectName("toolbarCreate")
        self.global_create_btn.setAccessibleName("Create")
        self.global_create_btn.clicked.connect(self._open_global_create)
        self.global_create_btn.setIconSize(QSize(LAYOUT["header_icon"], LAYOUT["header_icon"]))

        # Settings is a modal over the window rather than a view; its button
        # stands checked while the modal is open.
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("toolbarToggle")
        self.settings_btn.setAccessibleName("Settings")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.settings_btn.setIconSize(QSize(LAYOUT["header_icon"], LAYOUT["header_icon"]))
        # Toggled rather than clicked, as a view's button is: an assistive
        # tool presses a checkable button by toggling it, which emits no click.
        self.settings_btn.toggled.connect(self._settings_toggled)

        # The board's filter. One state narrows the board, the Backlog and
        # the Archive; the button opens the panel that sets it, and the chips
        # say what is set without opening anything. The controls are
        # built here and placed on the Board below: the button on the columns'
        # header line, the chips in the filter row above the columns.
        self.filters = FilterState()

        self.filter_btn = QPushButton("Filter")
        self.filter_btn.setObjectName("filterBtn")
        self.filter_btn.setToolTip(
            "Narrow the Board, the Backlog and the Archive to an assignee, an epic, or both."
        )
        self.filter_btn.clicked.connect(self._open_filter_menu)
        # Built on first use, against the board as it stands at that moment.
        self.filter_menu = None

        self.filter_clear_btn = QPushButton("Clear")
        self.filter_clear_btn.setObjectName("link")
        self.filter_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filter_clear_btn.setToolTip("Remove every filter.")
        self.filter_clear_btn.clicked.connect(self._clear_filters)

        self.chip_row = QHBoxLayout()
        self.chip_row.setContentsMargins(0, 0, 0, 0)
        self.chip_row.setSpacing(space("sm"))

        # The splitter and, at the window's right edge, the strip that brings a
        # collapsed detail pane back. The strip is outside the splitter so the
        # columns reflow into the whole reclaimed width while the pane is away.
        board_and_pane = QWidget()
        # The body is one rounded surface under the top bar, inset from the
        # window's sides and foot; every view and the detail pane sit on it.
        board_and_pane.setObjectName("bodySurface")
        board_and_pane.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body_row = QHBoxLayout(board_and_pane)
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)
        body_row.addWidget(main_splitter, 1)
        self.pane_reveal = QPushButton()
        self.pane_reveal.setObjectName("paneReveal")
        icons.tint(self.pane_reveal, "chevron-left", size=14)
        self.pane_reveal.setToolTip("Show the detail pane")
        self.pane_reveal.setAccessibleName("Show the detail pane")
        self.pane_reveal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pane_reveal.setFixedWidth(space("2xl"))
        self.pane_reveal.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.pane_reveal.clicked.connect(lambda: self._set_pane_collapsed(False))
        self.pane_reveal.setVisible(False)
        body_row.addWidget(self.pane_reveal)

        self._header_in_title_bar = self._merge_title_bar()
        shell_layout.addWidget(self._build_header())
        body_inset = QHBoxLayout()
        # The top bar's right end keeps the same inset, so Settings stands
        # over the body's right edge.
        body_inset.setContentsMargins(space("xl"), 0, space("xl"), space("xl"))
        body_inset.addWidget(board_and_pane)
        shell_layout.addLayout(body_inset, 1)
        outer_layout.addWidget(self.pages)

        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(space("lg"))

        search_bar_layout = QHBoxLayout()
        search_bar_layout.setSpacing(space("md"))
        # A search field: a leading glass, a clear button, and results that
        # follow the typing after a short pause.
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchField")
        self.search_input.setPlaceholderText("Search cards and epics")
        self.search_input.setClearButtonEnabled(True)
        self._search_glass = self.search_input.addAction(
            magnifier_icon(C["INK_SOFT"]), QLineEdit.ActionPosition.LeadingPosition
        )
        self._search_settle = QTimer(self)
        self._search_settle.setSingleShot(True)
        self._search_settle.setInterval(SEARCH_SETTLE_MS)
        self._search_settle.timeout.connect(self._execute_global_search)
        self.search_input.textChanged.connect(lambda _text: self._search_settle.start())
        self.search_input.returnPressed.connect(self._execute_global_search)
        search_bar_layout.addWidget(self.search_input, 1)

        self.hide_closed_switch = Switch("Hide Closed Items")
        self.hide_closed_switch.setChecked(True)
        self.hide_closed_switch.toggled.connect(lambda _on: self._execute_global_search())
        search_bar_layout.addWidget(self.hide_closed_switch)
        search_layout.addLayout(search_bar_layout)

        self.search_count = QLabel("")
        self.search_count.setObjectName("metaText")
        search_layout.addWidget(self.search_count)

        self.search_results = ResultsTable(["Type", "#", "Title", "Status", "Closed"], stretch=2)
        self.search_results.picked.connect(self._update_inspector)
        self.search_results.opened.connect(self._open_record)
        search_layout.addWidget(self.search_results, 1)
        self._search_tab_index = self._add_page(search_widget, "Search")

        # BACKLOG — a single manually-ordered list (drag to reorder, saved) with
        # per-card checkboxes driving a bulk Activate / Delete bar.
        backlog_widget = QWidget()
        backlog_outer = QVBoxLayout(backlog_widget)
        # The board's filter narrows this list too, and the control that sets it
        # is on the Board. A view that is leaving cards out says so.
        self.backlog_filter_note = QLabel()
        self.backlog_filter_note.setObjectName("metaText")
        backlog_outer.addWidget(self.backlog_filter_note)
        self.backlog_column = KanbanColumn(
            self, self.conn, None, "Backlog (drag to reorder)", is_backlog=True
        )
        backlog_outer.addWidget(self.backlog_column)

        backlog_bar = QHBoxLayout()
        # Activate is the bar's one Primary button, the action it exists for;
        # Edit, Select All and Clear are Secondary, and Delete is Danger.
        # Edit gates the whole bulk-select apparatus: in read mode
        # the backlog is just a draggable, reorderable list — the checkboxes and
        # action buttons only appear once the user opts into Edit.
        self._backlog_editing = False
        self.backlog_edit_btn = QPushButton("Edit")
        self.backlog_edit_btn.setToolTip(
            "Show the bulk-select checkboxes to activate or delete cards. "
            "Dragging to reorder never needs Edit."
        )
        self.backlog_edit_btn.clicked.connect(self._toggle_backlog_edit)
        self.backlog_selall_btn = QPushButton("Select All")
        self.backlog_selall_btn.clicked.connect(lambda: self._set_all_backlog_checks(True))
        self.backlog_clear_btn = QPushButton("Clear")
        self.backlog_clear_btn.clicked.connect(lambda: self._set_all_backlog_checks(False))
        self.backlog_activate_btn = QPushButton("Activate →")
        self.backlog_activate_btn.setObjectName("globalCreateBtn")
        self.backlog_activate_btn.setToolTip(
            "Move checked cards to the active Board (appended to the bottom of "
            "their status column, in their current backlog order)."
        )
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

        # What the board is narrowed to: one chip per filter and Clear, in a row
        # above the columns that is shown only while a filter is set, so an
        # unfiltered board starts at the columns' header lines. A single card
        # is created from the master Create button, not from a per-column
        # control; sweeping the Done column is Settings' Clear Done.
        self.filter_row = QWidget()
        filter_row_layout = QHBoxLayout(self.filter_row)
        filter_row_layout.setContentsMargins(0, 0, 0, 0)
        filter_row_layout.setSpacing(space("md"))
        filter_row_layout.addLayout(self.chip_row)
        filter_row_layout.addWidget(self.filter_clear_btn)
        filter_row_layout.addStretch(1)
        board_outer.addWidget(self.filter_row)

        board_columns = QHBoxLayout()
        board_columns.setSpacing(space("lg"))
        self.columns = {}
        for key, name in COLUMNS:
            col = KanbanColumn(self, self.conn, key, name)
            self.columns[key] = col
            board_columns.addWidget(col)
        # The Filter button applies to the whole board, and sits at the right
        # end of the header line the columns share.
        self.columns[COLUMNS[-1][0]].add_to_header(self.filter_btn)
        board_outer.addLayout(board_columns)

        self._board_tab_index = self._add_page(board_widget, "Board")

        # ARCHIVE — a stripped-down line list (like Search), sorted by most
        # recently modified. Retired tickets, newest first.
        archive_widget = QWidget()
        archive_layout = QVBoxLayout(archive_widget)
        self.archive_filter_note = QLabel()
        self.archive_filter_note.setObjectName("metaText")
        archive_layout.addWidget(self.archive_filter_note)
        self.archive_results = ResultsTable(["Type", "#", "Title", "Status", "Archived"], stretch=2)
        self.archive_results.picked.connect(self._update_inspector)
        self.archive_results.opened.connect(self._open_record)
        archive_layout.addWidget(self.archive_results)
        self._archive_tab_index = self._add_page(archive_widget, "Archive")

        # Everything that configures Bristol: the fleet's two pages and the
        # Settings sections, in one modal over the window.
        self.agents_tab = AgentsTab()
        self.skills_tab = SkillsTab(self.conn, on_ticket_filed=self._refresh_board)
        self.settings_tab = SettingsTab(
            on_appearance_changed=self._preview_appearance,
            conn=self.conn,
            on_board_changed=self._refresh_board,
        )
        self.settings_modal = SettingsModal(
            self,
            self.agents_tab,
            self.skills_tab,
            self.settings_tab,
            on_closed=lambda: self.settings_btn.setChecked(False),
        )
        # The two Agent pickers write one key, and each shows the other's
        # choice: Settings writes it first, then the top bar re-reads it.
        self.settings_tab.next_agent.picked.connect(lambda _slug: self._load_agent_picker())
        self._load_agent_picker()
        self._tint_header()
        # After every tab exists, since the View menu lists them.
        self._build_menu_bar()

        # The detail pane: the selected card, read and edited in place. A pane
        # write refreshes the board; the pane's collapse control hands the
        # splitter work back here.
        self.detail_pane = DetailPane(
            self.conn,
            on_changed=self._on_pane_edit,
            on_collapse=lambda: self._set_pane_collapsed(True),
        )
        main_splitter.addWidget(self.detail_pane)

        # Both panes are elastic (no max width — the user can widen the pane as
        # far as they like). The pane opens at the width it last had, and
        # collapsed if that is how it was left; both are stored in the
        # configuration and written back as the user moves things.
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        self._pane_collapsed = False
        stored_width = config_file.get(config_file.DETAIL_WIDTH, LAYOUT["split_detail"])
        self._detail_width = (
            int(stored_width) if isinstance(stored_width, (int, str)) else LAYOUT["split_detail"]
        ) or LAYOUT["split_detail"]
        main_splitter.setSizes([LAYOUT["window_w"] - self._detail_width, self._detail_width])
        self._main_splitter = main_splitter

        # Another session or the command line writing the board is seen within
        # a poll: SQLite's data_version moves only on a commit made through some
        # other connection, so this window's own writes never trigger a reload.
        self._data_version = self._read_data_version()
        self._board_watch = QTimer(self)
        self._board_watch.setInterval(BOARD_POLL_MS)
        self._board_watch.timeout.connect(self._reload_if_changed)
        self._board_watch.start()

        # Geometry saves are debounced, and put off entirely until the window
        # finishes constructing, so building the window writes nothing.
        self._geometry_ready = False
        self._splitter_save_timer = QTimer(self)
        self._splitter_save_timer.setSingleShot(True)
        self._splitter_save_timer.setInterval(SPLITTER_SETTLE_MS)
        self._splitter_save_timer.timeout.connect(self._save_pane_geometry)
        main_splitter.splitterMoved.connect(self._on_splitter_moved)

        if bool(config_file.get(config_file.DETAIL_COLLAPSED, False)):
            self._set_pane_collapsed(True, save=False)

        # The window opens on the Board: the active work is what a launch is
        # for, and the tab row keeps the order it reads in. Selected once, after
        # every page and the pane exist, so no other tab is selected on the way
        # here and the pane starts in the state that page wants.
        self._show_page(self._board_tab_index)

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

    def _sync_backlog_bar(self, *args: object) -> None:
        """Show the selection-dependent backlog actions only when editing AND
        ≥1 card is checked; "Select all" shows whenever editing as the entry
        point. In read mode only the Edit button shows."""
        editing = getattr(self, "_backlog_editing", False)
        self.backlog_selall_btn.setVisible(editing)
        has = editing and bool(self.backlog_column.checked_ids())
        for w in (self.backlog_clear_btn, self.backlog_activate_btn, self.backlog_delete_btn):
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
        reclaimed width — or bring it back at the width it last had."""
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
            width = max(
                LAYOUT["detail_min_w"], min(self._detail_width, total - LAYOUT["column_min_w"])
            )
            self._main_splitter.setSizes([total - width, width])
        self._pane_collapsed = collapsed
        if save:
            self._save_pane_geometry()

    def _on_splitter_moved(self, *args: object) -> None:
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
            config_file.update(
                {
                    config_file.DETAIL_WIDTH: self._detail_width,
                    config_file.DETAIL_COLLAPSED: self._pane_collapsed,
                }
            )
        except OSError:
            pass

    def _on_pane_edit(self) -> None:
        """A field changed from the pane: the board reflects it immediately."""
        self._refresh_board()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Leave nothing behind: a splitter save still waiting on its debounce,
        so a drag made just before quitting survives the restart."""
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
        """A filter moved: say so in the filter row, and reload the views."""
        self._sync_filter_row()
        self._refresh_board()

    def _clear_filters(self) -> None:
        self.filters.clear()
        self._sync_menu()
        self._on_filters_changed()

    def _remove_filter(self, kind: str, value: Facet) -> None:
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
        self.filter_row.setVisible(bool(count))

        notice = (
            "" if not count else (f"Filtered · {count} — the Filter button on the Board sets it.")
        )
        for label in (self.backlog_filter_note, self.archive_filter_note):
            label.setText(notice)
            label.setVisible(bool(count))

        while self.chip_row.count():
            taken = self.chip_row.takeAt(0)
            stale = taken.widget() if taken is not None else None
            if stale is not None:
                stale.deleteLater()
        chips = applied(self.conn, self.filters)
        for kind, value, label in chips[:CHIPS_SHOWN]:
            chip = QPushButton(label)
            chip.setObjectName("filterChip")
            # The way to remove the filter sits after its name.
            chip.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            icons.tint(chip, "x", "NEUTRAL_TX")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip("Remove this filter")
            chip.clicked.connect(lambda _checked=False, k=kind, v=value: self._remove_filter(k, v))
            self.chip_row.addWidget(chip)
        if len(chips) > CHIPS_SHOWN:
            rest = QLabel(f"+{len(chips) - CHIPS_SHOWN}")
            rest.setObjectName("metaText")
            rest.setToolTip("Open Filter to see the rest.")
            self.chip_row.addWidget(rest)

    # ----- The top bar -----------------------------------------------------

    def _merge_title_bar(self) -> bool:
        """Draw the window's own top bar in the title bar, where the platform
        can: the content runs up under a title bar with no background of its
        own, so the traffic lights and the top bar share one band in the
        window's color. Where AppKit can be asked, the band is the tall one a
        Mac app with a toolbar has, the lights at its centre and the system
        title hidden (``_tall_title_bar``). Returns whether the band is
        shared."""
        self._tall_title_bar = False
        expanded = getattr(Qt.WindowType, "ExpandedClientAreaHint", None)
        clear = getattr(Qt.WindowType, "NoTitleBarBackgroundHint", None)
        if sys.platform != "darwin" or expanded is None or clear is None:
            return False
        self.setWindowFlag(expanded, True)
        self.setWindowFlag(clear, True)
        # The layout reaches the window's top edge rather than stopping at the
        # area the title bar leaves.
        self.setAttribute(Qt.WA_LayoutOnEntireRect, True)
        self.setAttribute(Qt.WA_ContentsMarginsRespectsSafeArea, False)
        self._tall_title_bar = mac_window.tall_title_bar(self)
        return True

    def _build_header(self) -> QWidget:
        """The one top bar: the app's mark and name at its left where the
        system title is hidden, the views at its centre, and Refresh and Create
        at its right, then Settings. Every view shows it the same."""
        header = _HeaderBar()
        header.setObjectName("appHeader")
        # A QWidget subclass paints its stylesheet background only when asked.
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bar = QHBoxLayout(header)
        bar.setSpacing(space("lg"))
        if self._tall_title_bar:
            header.setFixedHeight(mac_window.TALL_TITLE_BAR)
            bar.setContentsMargins(LAYOUT["traffic_lights_tall_w"], 0, space("xl"), 0)
        elif self._header_in_title_bar:
            header.setFixedHeight(LAYOUT["title_bar_h"])
            bar.setContentsMargins(LAYOUT["traffic_lights_w"], 0, space("xl"), 0)
        else:
            header.setFixedHeight(mac_window.TALL_TITLE_BAR)
            bar.setContentsMargins(space("xl"), 0, space("xl"), 0)

        # The app names itself where the platform's title is not drawn.
        identity = QWidget()
        identity_row = QHBoxLayout(identity)
        identity_row.setContentsMargins(0, 0, 0, 0)
        identity_row.setSpacing(space("md"))
        self._mark = QLabel()
        self._mark.setPixmap(icons.mark(LAYOUT["header_mark_h"]))
        title = QLabel("Bristol Tickets")
        title.setObjectName("regionTitle")
        identity_row.addWidget(self._mark, 0, Qt.AlignmentFlag.AlignVCenter)
        identity_row.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)

        views = QWidget()
        views.setObjectName("viewTabs")
        self._tab_row = QHBoxLayout(views)
        self._tab_row.setContentsMargins(0, 0, 0, 0)
        self._tab_row.setSpacing(space("sm"))
        self._tab_buttons: list[QPushButton] = []
        # Exclusive, so the open view cannot be switched off by a second press
        # and exactly one view is always the one shown.
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)

        # The views stand at the bar's centre whatever is either side of them:
        # the two sides are given the same width.
        left = QWidget()
        left_row = QHBoxLayout(left)
        left_row.setContentsMargins(0, 0, 0, 0)
        left_row.addWidget(identity, 0, Qt.AlignmentFlag.AlignVCenter)
        left_row.addStretch(1)
        # Hidden once it has a parent: a parentless widget made visible
        # would open as a window of its own.
        identity.setHidden(self._header_in_title_bar and not self._tall_title_bar)
        right = QWidget()
        right_row = QHBoxLayout(right)
        right_row.setContentsMargins(0, 0, 0, 0)
        right_row.setSpacing(space("md"))
        right_row.addStretch(1)
        # Search is a view drawn as an icon here, before the commands;
        # _add_page seats it. Settings, which opens the modal, ends the bar.
        self._icon_slots = {"Search": QHBoxLayout()}
        # The agent the next session starts as, chosen here without a trip
        # into Settings. The agent's name in the box says what it picks.
        self.agent_picker = SettledComboBox()
        self.agent_picker.setObjectName("toolbarPicker")
        self.agent_picker.setAccessibleName("Agent")
        self.agent_picker.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.agent_picker.picked.connect(self._choose_agent)
        right_row.addWidget(self.agent_picker, 0, Qt.AlignmentFlag.AlignVCenter)
        right_row.addLayout(self._icon_slots["Search"])
        right_row.addWidget(self.refresh_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        right_row.addWidget(self.global_create_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        right_row.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        for side in (left, right):
            side.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(left, 1)
        bar.addWidget(views, 0, Qt.AlignmentFlag.AlignVCenter)
        bar.addWidget(right, 1)
        return header

    def _load_agent_picker(self) -> None:
        """Offer the configured agents in the top bar, opened on the active one,
        the same list Settings' Agent picker offers."""
        slugs = config_file.agent_slugs()
        active = config_file.get("active_agent")
        if isinstance(active, str) and active and active not in slugs:
            slugs = [active, *slugs]
        self.agent_picker.clear()
        fill_agents(self.agent_picker, slugs)
        if active in slugs:
            self.agent_picker.setCurrentIndex(self.agent_picker.findData(active))
        self.agent_picker.setEnabled(bool(slugs))

    def _choose_agent(self, slug: str) -> None:
        """Write the chosen agent as active_agent, as Settings' picker does, and
        bring that picker to the same choice."""
        try:
            config_file.update({"active_agent": slug})
        except OSError as exc:
            notify(self, "Agent Not Saved", str(exc))
            return
        self.settings_tab.reload_agents()

    def _tint_header(self) -> None:
        """Draw the top bar's icons in the theme's colors: Refresh, Settings
        and the icon views in the soft ink, an open icon view and Settings
        while its modal is open in the accent, and Create's plus in the color
        drawn on the accent. The other views are words alone."""
        for button in getattr(self, "_tab_buttons", []):
            name = ICON_VIEWS.get(button.accessibleName())
            if name:
                button.setIcon(icons.toggle_icon(name, C["INK_SOFT"], C["ACCENT"]))
        if hasattr(self, "settings_btn"):
            self.settings_btn.setIcon(icons.toggle_icon("settings", C["INK_SOFT"], C["ACCENT"]))
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setIcon(icons.icon("refresh-cw", C["INK_SOFT"]))
            self.global_create_btn.setIcon(icons.icon("plus", C["ON_ACCENT"]))

    def _add_page(self, widget: QWidget, name: str) -> int:
        """Add a view and its button in the top bar."""
        index = self.pages.addWidget(widget)

        # Search is an icon at the bar's right; every other view is its name
        # at the centre.
        icon_view = name in ICON_VIEWS
        button = QPushButton("" if icon_view else name)
        button.setAccessibleName(name)
        button.setObjectName("toolbarToggle" if icon_view else "viewTab")
        button.setCheckable(True)
        button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        if icon_view:
            button.setIconSize(QSize(LAYOUT["header_icon"], LAYOUT["header_icon"]))
        # Toggled rather than clicked: an assistive tool presses a checkable
        # button by toggling it, which emits no click, and a pointer click
        # toggles it as well.
        button.toggled.connect(lambda checked, i=index: checked and self._show_page(i))
        self._tab_group.addButton(button)
        if icon_view:
            self._icon_slots[name].addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            self._tab_row.addWidget(button)
        self._tab_buttons.append(button)
        return index

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for position, button in enumerate(self._tab_buttons):
            button.setChecked(position == index)

    def _open_settings(self, tab: str | None = None) -> None:
        """Open the Settings modal over the window, on ``tab`` or the tab it
        was last left on."""
        if self.settings_btn.isChecked():
            self.settings_modal.open_modal(tab)
            return
        if tab is not None:
            self.settings_modal.show_tab(tab)
        self.settings_btn.setChecked(True)

    def _settings_toggled(self, checked: bool) -> None:
        """The Settings button opens the modal checked and closes it
        unchecked; the modal unchecks it whichever way it closes."""
        if checked:
            self.settings_modal.open_modal()
        else:
            self.settings_modal.close_modal()

    # ----- Menu bar ---------------------------------------------------------

    def _action(
        self,
        menu: QMenu,
        text: str,
        slot: Callable[[], object],
        shortcut: str | QKeySequence.StandardKey | None = None,
        role: QAction.MenuRole = QAction.MenuRole.NoRole,
    ) -> QAction:
        """One menu item. Every item states its role, because Qt otherwise
        moves an item whose title merely resembles About, Settings or Quit
        into the application menu."""
        action = QAction(text, self)
        action.setMenuRole(role)
        if shortcut is not None:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda _checked=False: slot())
        menu.addAction(action)
        return action

    def _build_menu_bar(self) -> None:
        """The Mac menu bar: the application menu (About, Settings…, Quit, which
        Qt files there by role), then File, Edit, View, Window and Help."""
        bar = self.menuBar()

        file_menu = bar.addMenu("File")
        self._action(file_menu, "New Card", self._open_global_create, QKeySequence.StandardKey.New)
        self._action(file_menu, "Reload", self._refresh_board, QKeySequence.StandardKey.Refresh)
        file_menu.addSeparator()
        self._action(file_menu, "Setup…", self._open_setup_wizard)
        file_menu.addSeparator()
        self._action(file_menu, "Close Window", self.close, QKeySequence.StandardKey.Close)
        # Filed in the application menu by their roles.
        self._action(
            file_menu, "About Bristol Tickets", self._show_about, role=QAction.MenuRole.AboutRole
        )
        self._action(
            file_menu,
            "Settings…",
            self._open_settings,
            QKeySequence.StandardKey.Preferences,
            QAction.MenuRole.PreferencesRole,
        )
        self._action(
            file_menu,
            "Quit Bristol Tickets",
            self._quit,
            QKeySequence.StandardKey.Quit,
            QAction.MenuRole.QuitRole,
        )

        edit_menu = bar.addMenu("Edit")
        for text, method, key in (
            ("Undo", "undo", QKeySequence.StandardKey.Undo),
            ("Redo", "redo", QKeySequence.StandardKey.Redo),
            (None, None, None),
            ("Cut", "cut", QKeySequence.StandardKey.Cut),
            ("Copy", "copy", QKeySequence.StandardKey.Copy),
            ("Paste", "paste", QKeySequence.StandardKey.Paste),
            ("Select All", "selectAll", QKeySequence.StandardKey.SelectAll),
        ):
            if text is None or method is None:
                edit_menu.addSeparator()
                continue
            self._action(edit_menu, text, lambda m=method: self._edit_focused(m), key)

        view_menu = bar.addMenu("View")
        for number, button in enumerate(self._tab_buttons, start=1):
            self._action(
                view_menu,
                button.accessibleName(),
                lambda i=number - 1: self._show_page(i),
                f"Ctrl+{number}" if number <= 9 else None,
            )
        view_menu.addSeparator()
        self._action(
            view_menu,
            "Show or Hide Details",
            lambda: self._set_pane_collapsed(not self._pane_collapsed),
            "Ctrl+Alt+I",
        )

        window_menu = bar.addMenu("Window")
        self._action(window_menu, "Minimize", self.showMinimized, "Ctrl+M")
        self._action(
            window_menu,
            "Zoom",
            lambda: self.showNormal() if self.isMaximized() else self.showMaximized(),
        )

        help_menu = bar.addMenu("Help")
        self._action(help_menu, "Bristol Tickets Help", self._open_help)

    def _quit(self) -> None:
        """Quit the application, or close this window where there is none."""
        app = QApplication.instance()
        if app is not None:
            app.quit()
        else:
            self.close()

    def _edit_focused(self, method: str) -> None:
        """Send an Edit menu command to the field that has the keyboard."""
        widget = QApplication.focusWidget()
        handler = getattr(widget, method, None)
        if callable(handler):
            handler()

    def _show_about(self) -> None:
        import payload  # bristol-local

        root = config_file.project_root()
        release = payload.version(root) if root is not None else None
        notify(
            self,
            "About Bristol Tickets",
            f"Bristol Tickets {release}" if release else "Bristol Tickets",
            "Close",
        )

    def _open_help(self) -> None:
        """The README the project ships, which is the guide to the app."""
        root = config_file.project_root()
        readme = root / "README.md" if root is not None else None
        if readme is not None and readme.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(readme)))

    def _open_setup_wizard(self) -> None:
        """Run setup again, over the installation this window already has open."""
        from .setup_wizard import run_setup

        db_path = run_setup(self)
        if db_path is None:
            return
        self.settings_tab.reload()
        notify(
            self,
            "Setup complete",
            f"Your installation is at {db_path}.\n\n"
            f"Bristol Tickets opens it the next time it launches.",
        )

    # ----- Theming (OS light/dark, warm orange both ways) -------------------

    def _apply_theme(self) -> None:
        """Point the palette at the configured scheme and (re)apply the global
        stylesheet. Safe to call repeatedly — used at startup, on every OS
        colour-scheme change, and when the choice is edited in Settings.

        A stored family name resolves against the OS state, so 'follow the
        system' and a pinned scheme come down the same path.
        """
        app = QApplication.instance()
        app = app if isinstance(app, QApplication) else None
        theme, mode = self._stored_appearance()
        # Applied app-wide so child dialogs and message boxes inherit; fall back
        # to the window itself if there's somehow no application object. The
        # collection goes down with it, so a stored choice naming a theme the
        # user added resolves to that theme rather than falling back.
        apply_scheme(
            app,
            theme,
            mode,
            config_file.get(config_file.APPEARANCE_THEMES),
            config_file.get(config_file.APPEARANCE_CUSTOM),
        )
        if app is None:
            self.setStyleSheet(build_style_sheet())

    def _stored_appearance(self) -> tuple[str, str]:
        """The theme and mode the configuration gives."""
        return appearance_choice(
            config_file.get(config_file.APPEARANCE_THEME),
            config_file.get(config_file.APPEARANCE_MODE),
            config_file.get(config_file.APPEARANCE_SCHEME),
        )

    def _preview_appearance(self, theme: str, mode: str) -> None:
        """Draw the app in the theme and mode the Settings tab is offering,
        before the configuration says so."""
        self._previewed = (theme, mode)
        app = QApplication.instance()
        app = app if isinstance(app, QApplication) else None
        set_scheme(live_scheme(app, theme, mode))
        if app is not None:
            style_application(app)
        else:
            self.setStyleSheet(build_style_sheet())
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
        """Update every viewport containing delegate-painted cards."""
        for col in getattr(self, "columns", {}).values():
            col.list_widget.viewport().update()
        if hasattr(self, "backlog_column"):
            self.backlog_column.list_widget.viewport().update()
        if hasattr(self, "archive_results"):
            self.archive_results.viewport().update()
        if hasattr(self, "_search_glass"):
            self._search_glass.setIcon(magnifier_icon(C["INK_SOFT"]))
        icons.retint()
        self._tint_header()

    def _on_color_scheme_changed(self, *args: object) -> None:
        """OS switched between light and dark. It reaches the app only while the
        mode is Follow System; a pinned mode resolves the same either way.

        Settings draws a choice before writing it, and releasing a pinned mode
        raises this signal inside that drawing. While the choice drawn is not
        yet the one stored, the redraw is of the choice drawn: the stored one
        would pin the platform back to the mode being left.
        """
        previewed = getattr(self, "_previewed", None)
        if previewed is not None and previewed != self._stored_appearance():
            self._preview_appearance(*previewed)
        else:
            self.refresh_appearance()

    def _move_tasks_to_stage(self, ids: list[int], stage: str) -> None:
        """Set each task's stage, appended to the bottom of the destination list
        (backlog = one list; active = per status column). Shared by the Board
        Bulk Change and the Backlog Activate action. The change log records the
        tab move itself, from the database triggers on this connection."""
        for tid in ids:
            status_row = self.conn.execute(
                "SELECT status, COALESCE(stage,'backlog') FROM task WHERE id=?", (tid,)
            ).fetchone()
            if status_row is None:
                continue
            status, prior_stage = status_row
            if stage == "active":
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task "
                    "WHERE stage='active' AND status=?",
                    (status,),
                ).fetchone()[0]
            else:
                base = self.conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) FROM task WHERE stage=?", (stage,)
                ).fetchone()[0]
            self.conn.execute(
                "UPDATE task SET stage=?, sort_order=? WHERE id=?", (stage, base + 1, tid)
            )
        self.conn.commit()

    # ----- Backlog bulk actions -------------------------------

    def _set_all_backlog_checks(self, checked: bool) -> None:
        lw = self.backlog_column.list_widget
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(lw.count()):
            lw.item(i).setData(Qt.ItemDataRole.CheckStateRole, state)
        lw.viewport().update()

    def _bulk_activate_backlog(self) -> None:
        """Move checked backlog cards onto the active Board. They keep their
        relative backlog order and append to the bottom of their status column."""
        ids = self.backlog_column.checked_ids()
        if not ids:
            notify(self, "Nothing checked", "Tick one or more backlog cards first.")
            return
        self._move_tasks_to_stage(ids, "active")
        self._refresh_board()

    def _bulk_delete_backlog(self) -> None:
        ids = self.backlog_column.checked_ids()
        if not ids:
            notify(self, "Nothing checked", "Tick one or more backlog cards first.")
            return
        if not confirm(
            self,
            "Delete backlog cards",
            f"Permanently delete {len(ids)} backlog card(s)? This cannot be undone.",
            "Delete",
            destructive=True,
        ):
            return

        def delete() -> None:
            for tid in ids:
                self.conn.execute("DELETE FROM issue_log WHERE task_id=?", (tid,))
                self.conn.execute("DELETE FROM task_event WHERE task_id=?", (tid,))
                self.conn.execute("DELETE FROM attachment WHERE task_id=?", (tid,))
                remove_links_for_task(self.conn, tid)
                self.conn.execute("DELETE FROM task WHERE id=?", (tid,))

        write(self.conn, self, f"The deletion of {len(ids)} backlog card(s)", delete)
        self._refresh_board()

    # ----- Archive tab (stripped chronological list) -----------

    def _load_archive(self, filters: FilterState) -> None:
        """Fill the Archive list with stage='archive' tasks, newest-ARCHIVED
        first — ordered by the stage move into the archive, which the change
        log records. Cards archived before that log existed fall back to
        updated_at so they still sort sanely. closed_at is not read here: it is
        when the work finished, which is a different moment and is what the
        reports measure to. A stripped one-line-per-ticket view like Search."""
        narrow, params = filters.where("t")
        query = (
            "SELECT t.id, t.title, t.status, COALESCE(t.record_type,'build'), "
            "COALESCE((SELECT MAX(e.at) FROM task_event e "
            "          WHERE e.task_id = t.id AND e.field='stage' "
            "            AND e.to_value='archive'), t.updated_at) AS archived "
            "FROM task t WHERE t.stage='archive'" + narrow
        )
        query += " ORDER BY archived DESC, t.id DESC"
        try:
            rows = self.conn.execute(query, tuple(params)).fetchall()
        except sqlite3.OperationalError:
            rows = []
        self.archive_results.set_rows(
            (
                (
                    _kind(rtype),
                    (f"#{tid}", tid),
                    title,
                    _status_word(status),
                    (_fmt_dt(archived), archived or ""),
                ),
                (tid, "task"),
            )
            for tid, title, status, rtype, archived in rows
        )

    def _open_record(self, record_id: int, mode: str) -> None:
        """Edit a record a results table was double-clicked on."""
        dlg = UnifiedRecordDialog(self, self.conn, mode=mode, record_id=record_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.save_data()
            self._refresh_board()

    def _open_global_create(self) -> None:
        # A new task's default Stage follows the tab Create was pressed on
        # (_stage_for_current_tab). The user can still change Stage in the
        # dialog.
        epic_id = self.filters.sole_epic()
        dlg = UnifiedRecordDialog(
            self,
            self.conn,
            mode="task",
            initial_status="todo",
            initial_stage=self._stage_for_current_tab(),
            epic_id=epic_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.save_data(fallback_epic=epic_id)
            self._refresh_board()

    def _update_inspector(self, record_id: int, mode: str) -> None:
        """Point the detail pane at whatever a view selected."""
        if mode == "epic":
            self.detail_pane.show_epic(record_id)
        else:
            self.detail_pane.show_task(record_id)

    def _execute_global_search(self) -> None:
        self._search_settle.stop()
        found_rows = []
        term = f"%{self.search_input.text().strip()}%"
        hide_closed = self.hide_closed_switch.isChecked()

        # Search is ordered by TYPE (tasks, then epics) then alphabetically —
        # the stable, browsable ordering. "Hide Closed Items" hides finished
        # work: archived tasks AND done tasks still on the active board (the
        # Done column), plus finished epics.
        try:
            task_query = (
                "SELECT t.id, t.title, t.status, COALESCE(t.record_type,'build'), "
                "t.closed_at FROM task t "
                "WHERE (t.title LIKE ? OR t.description LIKE ?)"
            )
            if hide_closed:
                task_query += " AND t.stage != 'archive' AND t.status != 'done'"
            task_query += " ORDER BY t.title COLLATE NOCASE LIMIT 50"

            for tid, title, status, rtype, closed in self.conn.execute(
                task_query, (term, term)
            ).fetchall():
                found_rows.append(
                    (
                        (
                            _kind(rtype),
                            (f"#{tid}", tid),
                            title,
                            _status_word(status),
                            (_fmt_dt(closed) if closed else "", closed or ""),
                        ),
                        (tid, "task"),
                    )
                )

            epic_query = (
                "SELECT id, name, status FROM epic WHERE (name LIKE ? OR description LIKE ?)"
            )
            if hide_closed:
                epic_query += " AND status NOT IN ('completed', 'done', 'on hold')"
            epic_query += " ORDER BY name COLLATE NOCASE LIMIT 50"

            for eid, name, status in self.conn.execute(epic_query, (term, term)).fetchall():
                found_rows.append(
                    (
                        ("Epic", (f"#{eid}", eid), name, _status_word(status), ("", "")),
                        (eid, "epic"),
                    )
                )
        except sqlite3.OperationalError:
            pass
        self.search_results.set_rows(found_rows)
        found = self.search_results.count()
        self.search_count.setText(
            "No results" if not found else f"{found} result" + ("" if found == 1 else "s")
        )

    def _read_data_version(self) -> int | None:
        try:
            return self.conn.execute("PRAGMA data_version").fetchone()[0]
        except sqlite3.Error:
            return None

    def _reload_if_changed(self) -> None:
        """Reload every view when another connection has committed to the
        board since the last look."""
        version = self._read_data_version()
        if version is None or version == self._data_version:
            return
        self._data_version = version
        self._refresh_board()

    def _refresh_board(self) -> None:
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
        # Skills are not in the database and take no filter; they are
        # reloaded here so one reload means the same thing on every tab.
        self.skills_tab.reload()
