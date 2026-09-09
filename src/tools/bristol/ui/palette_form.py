"""ui/palette_form.py — a whole palette as a form: one row per colour.

Every colour a theme defines gets a row — a caption, a block of the colour
itself, and the hex value — so a palette is edited in one place rather than
through a picker at a time. The manage-themes dialog is what holds this form;
what the rows are and what each key colours is ``ui/README.md``.

Two things happen as a row is edited. The block repaints, and whoever holds the
form is told, so the running app can re-theme and the reading of what is
unreadable can be taken again. The form itself never refuses a value and never
saves one: it holds what the rows say, and ``complaints()`` states what stands
between that and a palette that works.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .theme import (
    C,
    LAYOUT,
    REFERENCE_DARK_PALETTE,
    REFERENCE_PALETTE,
    palette_rows,
    contrast_complaints,
    key_caption,
    radius,
    space,
)


def is_colour(text: str) -> bool:
    """True for a hex colour a palette can hold: ``#RRGGBB``, or ``#AARRGGBB``
    for the one key that carries its own alpha."""
    body = text.strip()
    if not body.startswith("#"):
        return False
    digits = body[1:]
    if len(digits) not in (6, 8):
        return False
    try:
        int(digits, 16)
    except ValueError:
        return False
    return True


class ColourRow:
    """One key's caption, swatch and hex field, and the value they share."""

    def __init__(self, key: str, value: str, on_change) -> None:
        self.key = key
        self._on_change = on_change

        self.caption = QLabel(key_caption(key))
        self.caption.setToolTip(key)

        # The swatch shows the value being edited, so its fill is data rather
        # than a styling choice and is the one colour here not read from `C`.
        self.swatch = QPushButton()
        self.swatch.setFixedWidth(LAYOUT["palette_swatch_w"])
        self.swatch.setCursor(Qt.PointingHandCursor)
        self.swatch.setToolTip("Pick this colour")
        self.swatch.clicked.connect(self._pick)

        self.hex = QLineEdit(value)
        self.hex.setFixedWidth(LAYOUT["palette_hex_w"])
        self.hex.setAlignment(Qt.AlignCenter)
        self.hex.setToolTip("The colour as hex — type it, or use the swatch.")
        self.hex.textChanged.connect(self._typed)

        self._paint_swatch(value)

    # ----- the value -------------------------------------------------------

    def value(self) -> str:
        """What the field holds, whether or not it is a colour yet."""
        return self.hex.text().strip()

    def valid(self) -> bool:
        return is_colour(self.value())

    def set_value(self, value: str) -> None:
        self.hex.setText(value)

    # ----- editing ---------------------------------------------------------

    def _pick(self) -> None:
        """Open the platform colour picker on the current value.

        The one key written ``#AARRGGBB`` carries its own alpha, so its picker
        offers the alpha slider and its value comes back in the same spelling.
        """
        current = QColor(self.value()) if self.valid() else QColor(Qt.white)
        title = f"{key_caption(self.key)} colour"
        with_alpha = len(self.value().lstrip("#")) == 8
        if with_alpha:
            chosen = QColorDialog.getColor(current, self.swatch, title,
                                           QColorDialog.ShowAlphaChannel)
        else:
            chosen = QColorDialog.getColor(current, self.swatch, title)
        if not chosen.isValid():
            return
        self.set_value(chosen.name(
            QColor.HexArgb if with_alpha else QColor.HexRgb))

    def _typed(self, text: str) -> None:
        ok = is_colour(text)
        # The border every empty required field in this app carries, reused for
        # a value that is not a colour: same fault, same mark.
        self.hex.setProperty("fieldMissing", not ok)
        self.hex.style().unpolish(self.hex)
        self.hex.style().polish(self.hex)
        if ok:
            self._paint_swatch(text.strip())
        self._on_change()

    def _paint_swatch(self, value: str) -> None:
        self.swatch.setStyleSheet(
            f"background-color: {value};"
            f"border: 1px solid {C['BORDER']};"
            f"border-radius: {radius('md')}px;"
            f"min-height: {space('xl')}px;"
        )


class PaletteForm(QWidget):
    """A scrolling form over one palette. ``palette()`` is what the rows hold.

    ``on_change`` is called every time a row is edited, so whoever holds the
    form can re-theme the running app and re-read what is unreadable. Seating a
    palette with ``set_palette()`` never calls it: showing a stored value is not
    someone editing one.
    """

    def __init__(self, palette: dict | None = None, on_change=None,
                 parent=None, dark: bool = False) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self._seating = True

        self.rows: dict[str, ColourRow] = {}
        form = QWidget()
        grid = QGridLayout(form)
        grid.setContentsMargins(0, 0, space("lg"), 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("md"))
        # The caption, its swatch and its hex sit together at the left, with
        # the slack in a column of its own: a row whose label is a window's
        # width from its control is a row nobody can follow across.
        grid.setColumnMinimumWidth(0, LAYOUT["palette_caption_w"])
        grid.setColumnStretch(3, 1)

        base = complete_palette(palette, dark)
        line = 0
        for group, keys in palette_rows():
            label = QLabel(group)
            label.setObjectName("sectionHeader")
            label.setContentsMargins(0, space("lg") if line else 0, 0, 0)
            grid.addWidget(label, line, 0, 1, 3)
            line += 1
            for key in keys:
                row = ColourRow(key, base[key], self._changed)
                self.rows[key] = row
                grid.addWidget(row.caption, line, 0)
                grid.addWidget(row.swatch, line, 1)
                grid.addWidget(row.hex, line, 2)
                line += 1
        grid.setRowStretch(line, 1)

        scroll = QScrollArea()
        scroll.setObjectName("paletteScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(form)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(scroll)

        self._seating = False

    # ----- what the rows hold ----------------------------------------------

    def palette(self) -> dict[str, str]:
        """Every row that holds a colour. A row that does not is left out
        rather than stored empty."""
        return {key: row.value() for key, row in self.rows.items()
                if row.valid()}

    def set_palette(self, palette: dict | None, dark: bool = False) -> None:
        """Show ``palette``, without any of it reading as an edit. ``dark`` is
        which half it is, which is what a key it does not carry is filled
        from."""
        was = self._seating
        self._seating = True
        try:
            base = complete_palette(palette, dark)
            for key, row in self.rows.items():
                row.set_value(base[key])
        finally:
            self._seating = was

    def broken(self) -> list[str]:
        """The caption of every field that is not a colour."""
        return sorted(key_caption(key) for key, row in self.rows.items()
                      if not row.valid())

    def unreadable(self) -> list[str]:
        """Every pair of text and surface this palette puts under the readable
        ratio, named."""
        return contrast_complaints(self.palette())

    def complaints(self) -> list[str]:
        """What stands between these rows and a palette that works: a field
        that is not a colour, then every pair that has fallen under the
        readable ratio."""
        lines = []
        broken = self.broken()
        if broken:
            lines.append(f"Not a hex colour: {', '.join(broken)}. "
                         "A colour is #RRGGBB.")
        lines.extend(self.unreadable())
        return lines

    def ground(self) -> str:
        """The colour this palette puts behind text, for whoever draws a line
        that has to stay readable against it."""
        row = self.rows.get("CANVAS")
        return row.value() if row is not None and row.valid() else C["CANVAS"]

    # ----- editing ---------------------------------------------------------

    def _changed(self) -> None:
        if self._seating or self._on_change is None:
            return
        self._on_change()


def complete_palette(palette: dict | None, dark: bool = False) -> dict[str, str]:
    """``palette`` with a value for every key the reference palette defines, so
    a form always opens on something complete.

    ``dark`` is which half is being completed. A dark half completes against
    the reference dark palette, because a dark palette wearing light values for
    the keys it lacks is the half-lit state a dark half is turned on whole to
    avoid. A light half with nothing in it opens on the live palette, which is
    the theme in front of the user.
    """
    base = dict(REFERENCE_DARK_PALETTE if dark else REFERENCE_PALETTE)
    source = palette or (REFERENCE_DARK_PALETTE if dark else C)
    base.update({key: value for key, value in source.items() if key in base})
    return base
