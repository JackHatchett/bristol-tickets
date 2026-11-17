"""ui/icons.py — the app's icons, drawn in the theme's colors.

Every icon is a Lucide SVG in ``ui/icons/`` (ISC; ``ui/icons/LICENSE``), drawn
with ``currentColor`` replaced by the color asked for, so an icon takes the
theme's ink in light and in dark. The app's mark is the ticket from the app
icon, without its tile, in ``ui/icons/bristol_mark.png``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICON_DIR = Path(__file__).resolve().parent / "icons"

# Drawn at twice the size asked for, so an icon is sharp on a Retina screen.
_RATIO = 2


@lru_cache(maxsize=None)
def _svg(name: str) -> str:
    return (ICON_DIR / f"{name}.svg").read_text(encoding="utf-8")


def pixmap(name: str, color: str, size: int = 16) -> QPixmap:
    """The icon ``name`` drawn in ``color`` at ``size`` device-independent
    pixels."""
    source = _svg(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(source.encode("utf-8")))
    image = QPixmap(size * _RATIO, size * _RATIO)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size * _RATIO, size * _RATIO))
    painter.end()
    image.setDevicePixelRatio(_RATIO)
    return image


def icon(name: str, color: str, size: int = 16) -> QIcon:
    """The icon ``name`` in one color."""
    return QIcon(pixmap(name, color, size))


def toggle_icon(name: str, off: str, on: str, size: int = 16) -> QIcon:
    """The icon ``name`` in ``off`` and, for a checked button, in ``on``."""
    result = QIcon()
    result.addPixmap(pixmap(name, off, size), QIcon.Normal, QIcon.Off)
    result.addPixmap(pixmap(name, on, size), QIcon.Normal, QIcon.On)
    return result


def mark(height: int) -> QPixmap:
    """The app's mark at ``height`` device-independent pixels."""
    image = QPixmap(str(ICON_DIR / "bristol_mark.png"))
    if image.isNull():
        return image
    image = image.scaledToHeight(height * _RATIO, Qt.SmoothTransformation)
    image.setDevicePixelRatio(_RATIO)
    return image
