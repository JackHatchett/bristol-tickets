"""ui/attachments.py — image attachments for tasks/issues.

An attachment is an image a user pins to a task from the create/edit modal's
comment poster or the Properties Inspector's poster. The file bytes live in a
git-ignored, per-instance images directory that sits next to the tickets DB
(``data/<instance>/tickets/images/``); the database stores only the *filename*,
never an absolute path — so no user-specific path is ever written into the DB or
the tracked repo. The directory is derived at runtime from the live sqlite
connection's own file, keeping this module mechanism-only and path-agnostic.

Remove is a soft-delete: the file is moved into ``images/_trash/`` rather than
destroyed, and the DB link is dropped either way so the UI never shows a
dangling row.
"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .dialogs import confirm, notify
from .theme import LAYOUT, space

THUMB_MAX = 160  # longest edge of an inline thumbnail, in px

IMAGE_FILTER = (
    "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tiff *.tif *.heic);;All files (*)"
)


# ---------------------------------------------------------------------------
# Storage helpers (path-agnostic: everything is derived from the connection)
# ---------------------------------------------------------------------------

def images_dir(conn: sqlite3.Connection) -> Path | None:
    """The per-instance images directory (created on demand), resolved from the
    connection's own database file so nothing is hardcoded. Returns None for an
    in-memory / pathless DB."""
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
        db_file = row[2] if row else None
    except sqlite3.OperationalError:
        db_file = None
    if not db_file:
        return None
    d = Path(db_file).resolve().parent / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def attachment_path(conn: sqlite3.Connection, filename: str) -> Path | None:
    """Resolve a stored attachment filename to its on-disk path (or None if the
    images dir can't be resolved). The file may not exist — the caller checks."""
    d = images_dir(conn)
    if d is None:
        return None
    return d / filename


def _safe_name(name: str) -> str:
    keep = "-_.() "
    cleaned = "".join(c if (c.isalnum() or c in keep) else "_" for c in name).strip()
    return cleaned or "image"


def list_attachments(conn: sqlite3.Connection, task_id: int | None):
    if task_id is None:
        return []
    try:
        return conn.execute(
            "SELECT id, filename, original_name FROM attachment "
            "WHERE task_id=? ORDER BY id",
            (task_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def add_attachment(conn: sqlite3.Connection, task_id: int | None, source_path: str):
    """Copy ``source_path`` into the images dir under a unique, predictable name
    and record it. Returns the stored filename, or None on failure."""
    if task_id is None:
        return None
    d = images_dir(conn)
    if d is None:
        return None
    src = Path(source_path)
    if not src.is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    base = _safe_name(src.name)
    dest = d / f"task{task_id}_{stamp}_{base}"
    i = 1
    while dest.exists():  # rare same-second collision
        dest = d / f"task{task_id}_{stamp}_{i}_{base}"
        i += 1
    try:
        shutil.copy2(src, dest)
    except OSError:
        return None
    conn.execute(
        "INSERT INTO attachment (task_id, filename, original_name, created_at) "
        "VALUES (?,?,?,?)",
        (task_id, dest.name, src.name, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return dest.name


def remove_attachment(conn: sqlite3.Connection, attachment_id: int) -> None:
    """Drop the attachment record and move its file into ``images/_trash/`` (a
    recoverable soft-delete). If the move fails, the DB link is still removed so
    the UI never shows a dangling entry."""
    row = conn.execute(
        "SELECT filename FROM attachment WHERE id=?", (attachment_id,)
    ).fetchone()
    if row:
        d = images_dir(conn)
        if d is not None:
            src = d / row[0]
            if src.exists():
                trash = d / "_trash"
                trash.mkdir(parents=True, exist_ok=True)
                target = trash / src.name
                n = 1
                while target.exists():
                    target = trash / f"{src.stem}_{n}{src.suffix}"
                    n += 1
                try:
                    shutil.move(str(src), str(target))
                except OSError:
                    pass
    conn.execute("DELETE FROM attachment WHERE id=?", (attachment_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Clickable thumbnail + enlarged-preview modal
# ---------------------------------------------------------------------------

class _ClickableThumb(QLabel):
    """A QLabel that shows a scaled pixmap and emits ``clicked`` on release."""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("attachThumb")
        self.setCursor(Qt.PointingHandCursor)
        self.setAlignment(Qt.AlignCenter)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class ImagePreviewDialog(QDialog):
    """A modal that shows an attached image at full size (scrollable) with
    Close and Delete actions. ``exec()`` returns ``QDialog.Accepted`` only when
    the user deleted the image, so the caller knows to refresh."""

    def __init__(self, image_path: Path, display_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(display_name or "Image preview")
        self.setMinimumSize(LAYOUT["preview_min_w"], LAYOUT["preview_min_h"])
        self._deleted = False

        v = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        pix = QPixmap(str(image_path)) if image_path and image_path.exists() else QPixmap()
        if pix.isNull():
            img_label.setText(
                f"Image file is unavailable:\n{display_name}\n\n"
                "(it may have been moved to images/_trash)"
            )
            img_label.setObjectName("metaText")
        else:
            img_label.setPixmap(pix)
        scroll.setWidget(img_label)
        v.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        delete_btn = QPushButton("Delete Image")
        delete_btn.setObjectName("attachRemoveBtn")
        delete_btn.clicked.connect(self._confirm_delete)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        v.addLayout(buttons)

    def deleted(self) -> bool:
        return self._deleted

    def _confirm_delete(self) -> None:
        if confirm(
            self, "Delete image",
            "Remove this attachment? The file moves to images/_trash "
            "(recoverable), and the link is dropped.",
            "Remove", destructive=True,
        ):
            self._deleted = True
            self.accept()


# ---------------------------------------------------------------------------
# Reusable widget — embedded by both the record dialog and the inspector
# ---------------------------------------------------------------------------

class AttachmentBar(QWidget):
    """An 'Attach image' button over a list of the current task's attachments,
    each with an ✕ remove button. Call ``set_task(task_id)`` to point it at a
    task (or None to disable/clear). Attachments only apply to an existing
    (saved) task, mirroring the Issue Log poster."""

    def __init__(self, conn: sqlite3.Connection, parent=None) -> None:
        super().__init__(parent)
        self.conn = conn
        self.task_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("sm"))

        self.attach_btn = QPushButton("Attach Image")
        self.attach_btn.setToolTip("Attach an image file to this issue")
        self.attach_btn.clicked.connect(self._pick)
        # Sized to its text, not stretched across the pane — vertical space on
        # these forms is the scarce resource, and a full-width button spends
        # horizontal space to buy nothing.
        self.attach_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(self.attach_btn, 0, Qt.AlignLeft)

        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(space("xs"))
        layout.addLayout(self._list_layout)

    def set_task(self, task_id: int | None) -> None:
        self.task_id = task_id
        self.attach_btn.setEnabled(task_id is not None)
        self._refresh()

    def _pick(self) -> None:
        if self.task_id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose an image to attach", "", IMAGE_FILTER
        )
        if not path:
            return
        if add_attachment(self.conn, self.task_id, path) is None:
            notify(self, "Attach failed", "Could not attach that file.")
        self._refresh()

    def _clear_list(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _refresh(self) -> None:
        self._clear_list()
        for att_id, filename, original in list_attachments(self.conn, self.task_id):
            display = original or filename
            path = attachment_path(self.conn, filename)

            entry = QWidget()
            col = QVBoxLayout(entry)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(space("sm"))

            # Thumbnail, above the filename (clickable → enlarged modal).
            thumb = _ClickableThumb()
            pix = QPixmap(str(path)) if path and path.exists() else QPixmap()
            if pix.isNull():
                thumb.setText("(image unavailable)")
                thumb.setObjectName("metaText")
                thumb.setCursor(Qt.ArrowCursor)
            else:
                thumb.setPixmap(
                    pix.scaled(
                        THUMB_MAX,
                        THUMB_MAX,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
                thumb.setToolTip("Click to view full size")
                thumb.clicked.connect(
                    lambda a=att_id, p=path, d=display: self._open_preview(a, p, d)
                )
            col.addWidget(thumb, 0, Qt.AlignLeft)

            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(space("md"))
            name = QLabel(display)
            name.setToolTip(filename)
            rl.addWidget(name, 1)
            x = QPushButton("X")
            x.setObjectName("attachRemoveBtn")
            x.setFixedWidth(space("2xl"))
            x.setToolTip("Remove attachment (moves the file to images/_trash)")
            x.clicked.connect(lambda _=False, a=att_id: self._remove(a))
            rl.addWidget(x)
            col.addWidget(row)

            self._list_layout.addWidget(entry)

    def _open_preview(self, attachment_id: int, path: Path, display: str) -> None:
        dlg = ImagePreviewDialog(path, display, self)
        dlg.exec()
        if dlg.deleted():
            self._remove(attachment_id)

    def _remove(self, attachment_id: int) -> None:
        remove_attachment(self.conn, attachment_id)
        self._refresh()
