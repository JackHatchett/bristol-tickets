"""ui/icons.py — the app's icons, drawn in the theme's colors.

Every icon is a Lucide SVG in ``ui/icons/`` (ISC; ``ui/icons/LICENSE``), drawn
with ``currentColor`` replaced by the color asked for, so an icon takes the
theme's ink in light and in dark. The app's mark is the ticket from the app
icon, without its tile, in ``ui/icons/bristol_mark.png``.
"""

from __future__ import annotations

import weakref
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


def _render(name: str, color: str, width: int, height: int,
            view: tuple[float, float, float, float] | None) -> QPixmap:
    """``name`` in ``color`` on a ``width`` × ``height`` device-pixel canvas,
    showing the part of the 24-unit drawing ``view`` names, or all of it."""
    source = _svg(name).replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(source.encode("utf-8")))
    if view is not None:
        renderer.setViewBox(QRectF(*view))
    image = QPixmap(width, height)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    return image


def pixmap(name: str, color: str, size: int = 16) -> QPixmap:
    """The icon ``name`` drawn in ``color`` at ``size`` device-independent
    pixels."""
    image = _render(name, color, size * _RATIO, size * _RATIO, None)
    image.setDevicePixelRatio(_RATIO)
    return image


def image_file(name: str, color: str, width: int, height: int,
               view: tuple[float, float, float, float] | None = None) -> str | None:
    """The icon ``name`` in ``color`` as an image file a style sheet can point
    at, ``width`` × ``height`` device-independent pixels, with the ``@2x`` copy
    a Retina screen reads beside it. Kept in the system's temporary folder,
    once per name, color and size. Returns None when nothing can be written,
    and the style sheet then leaves the rule out."""
    try:
        from PySide6.QtCore import QDir

        folder = Path(QDir.tempPath()) / "bristol_tickets_ui"
        stem = f"lucide_{name}_{color.lstrip('#')}_{width}x{height}"
        target = folder / f"{stem}.png"
        sharp = folder / f"{stem}@2x.png"
        if target.exists() and sharp.exists():
            return str(target)
        folder.mkdir(parents=True, exist_ok=True)
        if not _render(name, color, width * _RATIO, height * _RATIO,
                       view).save(str(sharp)):
            return None
        if not _render(name, color, width, height, view).save(str(target)):
            return None
        return str(target)
    except Exception:  # noqa: BLE001 — an arrow is never worth failing a paint
        return None


def icon(name: str, color: str, size: int = 16) -> QIcon:
    """The icon ``name`` in one color."""
    return QIcon(pixmap(name, color, size))


def toggle_icon(name: str, off: str, on: str, size: int = 16) -> QIcon:
    """The icon ``name`` in ``off`` and, for a checked button, in ``on``."""
    result = QIcon()
    result.addPixmap(pixmap(name, off, size), QIcon.Normal, QIcon.Off)
    result.addPixmap(pixmap(name, on, size), QIcon.Normal, QIcon.On)
    return result


# Buttons whose only face is an icon in a theme color, so a change of theme or
# mode redraws them: button -> (icon name, theme color key, size).
_TINTED: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def tint(button, name: str, key: str = "INK_SOFT", size: int = 14) -> None:
    """Give ``button`` the icon ``name`` in the theme color ``key``, and keep
    it in that color when the theme or the mode changes."""
    from .theme import C

    _TINTED[button] = (name, key, size)
    button.setIcon(icon(name, C[key], size))


def retint() -> None:
    """Redraw every button ``tint`` gave an icon, in the colors now live."""
    from .theme import C

    for button, (name, key, size) in list(_TINTED.items()):
        try:
            button.setIcon(icon(name, C[key], size))
        except RuntimeError:  # its widget is already gone
            _TINTED.pop(button, None)


def mark(height: int) -> QPixmap:
    """The app's mark at ``height`` device-independent pixels."""
    image = QPixmap(str(ICON_DIR / "bristol_mark.png"))
    if image.isNull():
        return image
    image = image.scaledToHeight(height * _RATIO, Qt.SmoothTransformation)
    image.setDevicePixelRatio(_RATIO)
    return image
