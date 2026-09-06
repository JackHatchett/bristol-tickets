"""ui/theme_builder.py — the theme builder: one form over a whole palette.

The Theme picker's Custom option opens this. It offers one row per colour the
palette defines — a caption, a block of the colour itself, and the hex value —
seeded from the theme in force, so building one starts from something that
already works rather than from nothing.

Three things happen as a row is edited. The block repaints, the running app
re-themes so the palette is judged against the board it colours, and the
contrast notice under the form re-reads: every pair of text and the surface it
sits on that has fallen under the readable ratio, named. Saving is never
refused for one — a palette is the user's to choose — but it never happens
silently either.

What the rows are and what each key colours: ``ui/README.md``. The palette this
dialog returns is a plain dict, and ``settings_tab`` is what stores it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .dialogs import confirm
from .theme import (
    C,
    CONTRAST_MIN,
    LAYOUT,
    REFERENCE_SCHEME,
    SCHEMES,
    builder_rows,
    contrast_complaints,
    key_caption,
    radius,
    readable_on,
    space,
)


def _is_colour(text: str) -> bool:
    """True for a hex colour this palette can hold: ``#RRGGBB``, or
    ``#AARRGGBB`` for the one key that carries its own alpha."""
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


class _ColourRow:
    """One key's caption, swatch and hex field, and the value they share."""

    def __init__(self, key: str, value: str, on_change) -> None:
        self.key = key
        self._on_change = on_change

        self.caption = QLabel(key_caption(key))
        self.caption.setToolTip(key)

        # The swatch shows the value being edited, so its fill is data rather
        # than a styling choice and is the one colour here not read from `C`.
        self.swatch = QPushButton()
        self.swatch.setFixedWidth(LAYOUT["builder_swatch_w"])
        self.swatch.setCursor(Qt.PointingHandCursor)
        self.swatch.setToolTip("Pick this colour")
        self.swatch.clicked.connect(self._pick)

        self.hex = QLineEdit(value)
        self.hex.setFixedWidth(LAYOUT["builder_hex_w"])
        self.hex.setAlignment(Qt.AlignCenter)
        self.hex.setToolTip("The colour as hex — type it, or use the swatch.")
        self.hex.textChanged.connect(self._typed)

        self._paint_swatch(value)

    # ----- the value -------------------------------------------------------

    def value(self) -> str:
        """What the field holds, whether or not it is a colour yet."""
        return self.hex.text().strip()

    def valid(self) -> bool:
        return _is_colour(self.value())

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
        ok = _is_colour(text)
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


class ThemeBuilderDialog(QDialog):
    """The whole palette as a form. ``palette()`` is what was built.

    ``on_preview`` is called with the palette every time a row becomes a valid
    colour, so the running app can draw in it while it is being built. It is
    absent where there is no app to re-theme.
    """

    def __init__(self, seed: dict | None = None, parent=None,
                 on_preview=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Theme Builder")
        self.setModal(True)
        self.setMinimumSize(LAYOUT["builder_min_w"], LAYOUT["builder_min_h"])
        self._on_preview = on_preview

        # The theme in force is the seed, so a build starts from something that
        # already works. A key it lacks comes from the reference scheme.
        base = dict(SCHEMES[REFERENCE_SCHEME])
        base.update({key: value for key, value in (seed or C).items()
                     if key in base})

        heading = QLabel("Theme Builder")
        heading.setObjectName("dialogHeading")

        blurb = QLabel(
            "Every colour the board draws with, seeded from the theme in "
            "force. The app follows each change as you make it."
        )
        blurb.setObjectName("formCaption")
        blurb.setWordWrap(True)

        self.rows: dict[str, _ColourRow] = {}
        form = QWidget()
        grid = QGridLayout(form)
        grid.setContentsMargins(0, 0, space("lg"), 0)
        grid.setHorizontalSpacing(space("lg"))
        grid.setVerticalSpacing(space("md"))
        # The caption, its swatch and its hex sit together at the left, with
        # the slack in a column of its own: a row whose label is a window's
        # width from its control is a row nobody can follow across.
        grid.setColumnMinimumWidth(0, LAYOUT["builder_caption_w"])
        grid.setColumnStretch(3, 1)
        line = 0
        for group, keys in builder_rows():
            label = QLabel(group)
            label.setObjectName("sectionHeader")
            label.setContentsMargins(0, space("lg") if line else 0, 0, 0)
            grid.addWidget(label, line, 0, 1, 3)
            line += 1
            for key in keys:
                row = _ColourRow(key, base[key], self._changed)
                self.rows[key] = row
                grid.addWidget(row.caption, line, 0)
                grid.addWidget(row.swatch, line, 1)
                grid.addWidget(row.hex, line, 2)
                line += 1
        grid.setRowStretch(line, 1)

        scroll = QScrollArea()
        scroll.setObjectName("builderScroll")
        scroll.setWidgetResizable(True)
        scroll.setWidget(form)

        self.notice = QLabel()
        self.notice.setObjectName("formCaption")
        self.notice.setWordWrap(True)
        self.notice.setTextInteractionFlags(Qt.TextSelectableByMouse)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setObjectName("globalCreateBtn")
        self.save_button.setText("Save Theme")
        self.save_button.setAutoDefault(False)
        cancel = buttons.button(QDialogButtonBox.Cancel)
        cancel.setAutoDefault(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(space("xl"), space("xl"), space("xl"),
                                  space("xl"))
        column.setSpacing(space("lg"))
        column.addWidget(heading)
        column.addWidget(blurb)
        column.addWidget(scroll, 1)
        column.addWidget(self.notice)
        column.addWidget(buttons)

        # Raised while the notice is first read, so seating the seed does not
        # re-theme the app before anything has been edited.
        self._seating = True
        try:
            self._read_notice()
        finally:
            self._seating = False

    # ----- what was built --------------------------------------------------

    def palette(self) -> dict[str, str]:
        """Every row that holds a colour, as the palette to store. A row that
        does not is left at its seeded value rather than stored empty."""
        return {key: row.value() for key, row in self.rows.items()
                if row.valid()}

    def unreadable(self) -> list[str]:
        """The contrast complaints the current form carries."""
        return contrast_complaints(self.palette())

    # ----- editing ---------------------------------------------------------

    def _changed(self) -> None:
        self._read_notice()
        if self._seating or self._on_preview is None:
            return
        self._on_preview(self.palette())

    def _read_notice(self) -> None:
        """State what stands between this palette and a working one: a field
        that is not a colour, then every pair of text and surface that has
        fallen under the readable ratio."""
        broken = [key_caption(key) for key, row in self.rows.items()
                  if not row.valid()]
        lines = []
        if broken:
            lines.append(
                f"Not a hex colour: {', '.join(sorted(broken))}. "
                "A colour is #RRGGBB.")
        lines.extend(self.unreadable())
        self.notice.setText("\n".join(lines) if lines else
                            f"Every pair of text and surface clears "
                            f"{CONTRAST_MIN}:1.")
        # Drawn against the canvas the palette currently names, so the line that
        # says what is unreadable never becomes the unreadable thing.
        ground = self.rows["CANVAS"].value() if "CANVAS" in self.rows else C["CANVAS"]
        self.notice.setStyleSheet(f"color: {readable_on(ground)};")

    def accept(self) -> None:
        """Save, having said what fails rather than refusing quietly.

        A palette under the readable ratio is still the user's to choose, so
        this names every pair that fails and asks once. A field that is not a
        colour is a different thing — nothing to save — and sends the form back.
        """
        broken = [key_caption(key) for key, row in self.rows.items()
                  if not row.valid()]
        if broken:
            self._read_notice()
            return
        failures = self.unreadable()
        if failures and not confirm(
            self, "Some text will be hard to read",
            "This palette puts these under "
            f"{CONTRAST_MIN}:1:\n\n" + "\n".join(f"• {line}" for line in failures)
            + "\n\nSave it anyway?",
            "Save Anyway",
        ):
            return
        super().accept()
