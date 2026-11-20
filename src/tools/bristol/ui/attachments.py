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
dangling row. The storage is ``attachment_store`` beside ``app.py``; this
module is the widgets over it.
"""

from __future__ import annotations

import sqlite3
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
    QVBoxLayout,
    QWidget,
)

from .dialogs import RowList, add_button, confirm, notify
from .theme import LAYOUT, space

THUMB_MAX = 160  # longest edge of an inline thumbnail, in px

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tiff *.tif *.heic);;All files (*)"


# Storage is ``attachment_store``, which the command line shares.
from attachment_store import (  # noqa: E402,F401  (bristol-local)
    add_attachment,
    attachment_path,
    images_dir,
    list_attachments,
    remove_attachment,
)

# ---------------------------------------------------------------------------
# Clickable thumbnail + enlarged-preview modal
# ---------------------------------------------------------------------------


class _ClickableThumb(QLabel):
    """A QLabel that shows a scaled pixmap and emits ``clicked`` on release."""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("attachThumb")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
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
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        delete_btn.setObjectName("deleteBtn")
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
            self,
            "Delete image",
            "Remove this attachment? The file moves to images/_trash "
            "(recoverable), and the link is dropped.",
            "Remove",
            destructive=True,
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

        self.rows = RowList()
        layout.addWidget(self.rows)

        self.attach_btn = add_button("Add Image", self._pick, "Attach an image file to this card")
        layout.addWidget(self.attach_btn, 0, Qt.AlignmentFlag.AlignLeft)

    def set_task(self, task_id: int | None) -> None:
        self.task_id = task_id
        self.attach_btn.setEnabled(task_id is not None)
        self._refresh()

    def _pick(self) -> None:
        if self.task_id is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose an image to attach", "", IMAGE_FILTER)
        if not path:
            return
        if add_attachment(self.conn, self.task_id, path) is None:
            notify(self, "Attach failed", "Could not attach that file.")
        self._refresh()

    def _refresh(self) -> None:
        self.rows.clear()
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
                thumb.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                thumb.setPixmap(
                    pix.scaled(
                        THUMB_MAX,
                        THUMB_MAX,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                thumb.setToolTip("Click to view full size")
                if path is not None:
                    thumb.clicked.connect(
                        lambda a=att_id, p=path, d=display: self._open_preview(a, p, d)
                    )
            col.addWidget(thumb, 0, Qt.AlignmentFlag.AlignLeft)

            name = QLabel(display)
            name.setToolTip(filename)
            col.addWidget(name)

            self.rows.add_row(
                entry,
                "Remove attachment",
                lambda a=att_id, d=display: self._confirm_remove(a, d),
                align=Qt.AlignmentFlag.AlignBottom,
            )

    def _open_preview(self, attachment_id: int, path: Path, display: str) -> None:
        dlg = ImagePreviewDialog(path, display, self)
        dlg.exec()
        if dlg.deleted():
            self._remove(attachment_id)

    def _confirm_remove(self, attachment_id: int, display: str) -> None:
        if confirm(
            self,
            "Remove this attachment?",
            f"{display} is dropped from this card and the file moves "
            f"to images/_trash, where it can be recovered.",
            "Remove",
            destructive=True,
        ):
            self._remove(attachment_id)

    def _remove(self, attachment_id: int) -> None:
        remove_attachment(self.conn, attachment_id)
        self._refresh()
