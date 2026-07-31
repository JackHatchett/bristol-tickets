"""ui/kanban_column.py — one scrollable column of task cards.

``KanbanColumn`` is a labelled QListWidget that renders task cards via
``CardDelegate``. In the Kanban model it populates itself two ways:

* BOARD columns (``status_key`` = todo|doing|done): the tasks whose
  ``stage='active'`` and whose ``status`` matches this column, in manual
  ``sort_order``. Cards drag *between* columns (which rewrites ``status`` and
  drops them at the bottom of the destination) and *within* a column (which
  rewrites ``sort_order`` to the dropped position). Multi-select feeds the
  toolbar's "Bulk Change" (move selected → Backlog / Archive).

* the BACKLOG column (``is_backlog=True``): every ``stage='backlog'`` task as a
  single manually-ordered list. Cards drag to reorder (persisted); a per-card
  checkbox drives the bulk Activate / Delete bar beneath it.

Sprints are gone, so there is no active-sprint filtering and no archive column
here (the Archive tab is a plain chronological list built in main_window).

The parent (MainWindow) is expected to expose ``_refresh_board`` and
``_update_inspector``; both are called defensively via ``hasattr``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .card_delegate import CardDelegate
from .record_dialog import UnifiedRecordDialog
from .theme import CARD_ROLE, _is_checked, _utcnow


class _DndListWidget(QListWidget):
    """A QListWidget that routes drops back to its owning KanbanColumn so the
    move is written to the database. A drop from THIS list is a reorder (rewrite
    sort_order to the dropped position); a drop from another list is a
    cross-column move (rewrite status, append to the bottom). Without this an
    inter-list drag would only rearrange cards visually and be lost on refresh."""

    def __init__(self, column: "KanbanColumn"):
        super().__init__()
        self._column = column

    def dropEvent(self, event):  # noqa: N802 (Qt override)
        self._column._handle_drop(event)


class KanbanColumn(QWidget):
    def __init__(self, parent, conn, status_key: str | None, display_name: str,
                 is_backlog: bool = False):
        super().__init__(parent)
        self.conn = conn
        self.status_key = status_key
        self.is_backlog = is_backlog
        self._main_window_ref = parent

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        header = QLabel(display_name)
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("padding: 2px 4px;")
        root.addWidget(header)

        self.list_widget = _DndListWidget(self)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDropIndicatorShown(True)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDrop)
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setMouseTracking(True)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.setSpacing(0)
        self.list_widget.setItemDelegate(
            CardDelegate(self.list_widget, show_checkbox=is_backlog))
        self.list_widget.itemDoubleClicked.connect(self._edit_task_modal)
        self.list_widget.itemClicked.connect(self._inspect_task)
        root.addWidget(self.list_widget)

    # ----- loading ---------------------------------------------------------

    _SELECT = (
        "SELECT t.id, t.title, t.pressure, e.name, e.id, t.status, "
        "COALESCE(t.assignee,'user'), COALESCE(t.estimate,''), "
        "COALESCE(t.record_type,'build') FROM task t "
        "LEFT JOIN epic e ON t.epic_id = e.id "
    )

    def load_board_tasks(self, epic_id: int | None):
        """BOARD column: stage='active' tasks in this status column, manual order."""
        self.list_widget.clear()
        query = self._SELECT + "WHERE t.stage='active' AND t.status = ?"
        params = [self.status_key]
        if epic_id is not None:
            query += " AND t.epic_id = ?"
            params.append(epic_id)
        query += " ORDER BY t.sort_order ASC, t.id ASC"
        for row in self.conn.execute(query, tuple(params)).fetchall():
            self._add_item(*row)

    def load_backlog_tasks(self, epic_id: int | None):
        """BACKLOG column: every stage='backlog' task as one manual list."""
        self.list_widget.clear()
        query = self._SELECT + "WHERE t.stage='backlog'"
        params = []
        if epic_id is not None:
            query += " AND t.epic_id = ?"
            params.append(epic_id)
        query += " ORDER BY t.sort_order ASC, t.id ASC"
        for row in self.conn.execute(query, tuple(params)).fetchall():
            self._add_item(*row)

    def _add_item(self, task_id, title, pressure, epic_name, epic_id, _status,
                  owner, estimate, record_type):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, task_id)
        item.setData(CARD_ROLE, {
            "issue_id": task_id,
            "title": title or "",
            "pressure": pressure or 0,
            "epic_name": (epic_name or "") if epic_id else "",
            "owner": owner or "user",
            "estimate": (estimate or "").upper(),
            "record_type": (record_type or "build").lower(),
        })
        if self.is_backlog:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setData(Qt.CheckStateRole, Qt.Unchecked)
        item.setToolTip(title)
        self.list_widget.addItem(item)

    # ----- bulk-select checkbox helpers (backlog) --------------------------

    def checked_ids(self) -> list[int]:
        ids = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if _is_checked(it.data(Qt.CheckStateRole)):
                tid = it.data(Qt.UserRole)
                if tid is not None:
                    ids.append(tid)
        return ids

    def selected_ids(self) -> list[int]:
        return [it.data(Qt.UserRole) for it in self.list_widget.selectedItems()
                if it.data(Qt.UserRole) is not None]

    def set_checkbox_mode(self, enabled: bool) -> None:
        """Show/hide the per-card bulk-select checkboxes at runtime (Backlog
        Edit toggle). Reordering by drag never needs this; only
        selecting for a bulk action does, so the checkboxes stay hidden until
        the user hits Edit. Exiting clears every check so no hidden checked
        state survives back into read mode. Relayout is required because the
        checkbox gutter changes each card's width/height."""
        delegate = self.list_widget.itemDelegate()
        if hasattr(delegate, "show_checkbox"):
            delegate.show_checkbox = enabled
        if not enabled:
            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setData(Qt.CheckStateRole, Qt.Unchecked)
        self.list_widget.doItemsLayout()
        self.list_widget.viewport().update()

    # ----- drag & drop -----------------------------------------------------

    def _ordered_ids(self) -> list[int]:
        """This column's task ids in current visual (== DB sort_order) order."""
        return [self.list_widget.item(i).data(Qt.UserRole)
                for i in range(self.list_widget.count())]

    def _drop_row(self, event) -> int:
        """The insertion row implied by the drop point, accounting for whether
        the indicator sits above or below the item under the cursor."""
        pos = event.position().toPoint()
        idx = self.list_widget.indexAt(pos)
        row = idx.row()
        if row < 0:
            return self.list_widget.count()
        if self.list_widget.dropIndicatorPosition() == QAbstractItemView.BelowItem:
            row += 1
        return row

    def _handle_drop(self, event):
        source = event.source()
        dragged = []
        sel = getattr(source, "selectedItems", None)
        if callable(sel):
            dragged = [it.data(Qt.UserRole) for it in sel()
                       if it.data(Qt.UserRole) is not None]
        if not dragged:
            cur = getattr(source, "currentItem", lambda: None)()
            if cur is not None and cur.data(Qt.UserRole) is not None:
                dragged = [cur.data(Qt.UserRole)]
        if not dragged:
            event.ignore()
            return

        if source is self.list_widget:
            self._reorder_within(dragged, self._drop_row(event))
        else:
            self._accept_external(dragged)
        event.acceptProposedAction()
        if hasattr(self._main_window_ref, "_refresh_board"):
            QTimer.singleShot(0, self._main_window_ref._refresh_board)

    def _reorder_within(self, dragged: list[int], drop_row: int):
        """Persist a within-column reorder: rebuild this column's id order with
        the dragged cards moved to the drop position, then rewrite sort_order to
        that sequence (0..n-1)."""
        ids = self._ordered_ids()
        dset = set(dragged)
        dragged_ordered = [i for i in ids if i in dset]  # keep prior relative order
        remaining = [i for i in ids if i not in dset]
        if drop_row >= len(ids):
            insert_at = len(remaining)
        else:
            target = ids[drop_row]
            if target in dset:
                insert_at = len([i for i in ids[:drop_row] if i not in dset])
            else:
                insert_at = remaining.index(target)
        new_order = remaining[:insert_at] + dragged_ordered + remaining[insert_at:]
        for pos, tid in enumerate(new_order):
            self.conn.execute("UPDATE task SET sort_order=? WHERE id=?", (pos, tid))
        self.conn.commit()

    def _accept_external(self, dragged: list[int]):
        """A cross-column drop onto a BOARD column: set each card's status to
        this column and append it to the bottom of this column's order. (Backlog
        does not accept external drops — status_key is None there.)"""
        if not self.status_key:
            return
        ts = _utcnow()
        closed = ts if self.status_key == "done" else None
        base = self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM task "
            "WHERE stage='active' AND status=?", (self.status_key,)
        ).fetchone()[0]
        for offset, tid in enumerate(dragged, start=1):
            # The change log records this drag by itself — the database triggers
            # installed on this connection append one entry per changed field,
            # and updated_at is derived from the newest of them.
            self.conn.execute(
                "UPDATE task SET status=?, stage='active', sort_order=?, "
                "closed_at=? WHERE id=?",
                (self.status_key, base + offset, closed, tid),
            )
        self.conn.commit()

    # ----- click / edit ----------------------------------------------------

    def _edit_task_modal(self, item: QListWidgetItem):
        task_id = item.data(Qt.UserRole)
        if task_id is None:
            return
        dlg = UnifiedRecordDialog(self, self.conn, mode="task", record_id=task_id)
        if dlg.exec() == QDialog.Accepted:
            dlg.save_data()
            if hasattr(self._main_window_ref, "_refresh_board"):
                self._main_window_ref._refresh_board()

    def _inspect_task(self, item: QListWidgetItem):
        task_id = item.data(Qt.UserRole)
        if task_id and hasattr(self._main_window_ref, "_update_inspector"):
            self._main_window_ref._update_inspector(task_id, "task")
