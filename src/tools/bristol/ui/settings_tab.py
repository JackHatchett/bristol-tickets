"""ui/settings_tab.py — the Settings tab: choices about how the board behaves
and how it looks.

Every field here reads and writes ``config/config.local.json`` through
``config_file``, the same helper the setup wizard uses, so a choice has one
home. A key this build does not offer is left exactly as it was on save.

The appearance choice applies the moment it is picked, so the scheme can be
compared against the board it themes; Save is what commits it to the
configuration.

The active agent is deliberately absent: it changes what the whole application
means, so it lives on the main window where it is always visible.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import config_file  # bristol-local; see module docstring

from .theme import CHOICES as APPEARANCE_CHOICES
from .theme import space

# What each stored value is called on screen.
CROSS_AGENT_CHOICES = [
    ("active", "The Board — where the assignee will see it"),
    ("backlog", "The Backlog — to be picked up whenever"),
]


class SettingsTab(QWidget):
    def __init__(self, parent=None, on_appearance_changed=None) -> None:
        super().__init__(parent)

        # Called when the scheme picker moves, so the window it lives in can
        # re-theme itself. Absent in a bare construction (the smoke check), where
        # there is no window to re-theme.
        self._on_appearance_changed = on_appearance_changed

        self.cross_agent = QComboBox()
        for value, caption in CROSS_AGENT_CHOICES:
            self.cross_agent.addItem(caption, value)

        self.appearance = QComboBox()
        for value, caption in APPEARANCE_CHOICES:
            self.appearance.addItem(caption, value)
        self.appearance.currentIndexChanged.connect(self._preview_appearance)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        form.setHorizontalSpacing(space("xl"))
        form.setVerticalSpacing(space("lg"))
        form.addRow("A card one agent files for another goes to", self.cross_agent)
        form.addRow("Colour scheme", self.appearance)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("globalCreateBtn")
        self.save_btn.clicked.connect(self._save)
        self.status = QLabel()
        self.status.setObjectName("formCaption")
        self.status.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.setSpacing(space("lg"))
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.status, 1)

        # Where the answers are stored. A path the user may go looking for on
        # disk renders as a path rather than as a sentence.
        self.location_caption = QLabel("Stored in")
        self.location_caption.setObjectName("formCaption")
        self.location = QLabel()
        self.location.setObjectName("pathRow")
        self.location.setWordWrap(True)
        self.location.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(space("xl"))
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.location_caption)
        layout.addWidget(self.location)
        layout.addStretch(1)

        self.reload()

    def _preview_appearance(self) -> None:
        """Apply the picked scheme to the running app without writing anything."""
        if self._on_appearance_changed is not None:
            self._on_appearance_changed(self.appearance.currentData())

    def reload(self) -> None:
        """Show what the configuration currently says."""
        target = config_file.path()
        placed = target is not None and target.exists()
        stored = config_file.get(
            config_file.CROSS_AGENT_STAGE, config_file.CROSS_AGENT_STAGE_DEFAULT
        )
        index = self.cross_agent.findData(stored)
        self.cross_agent.setCurrentIndex(index if index >= 0 else 0)
        scheme = config_file.get(
            config_file.APPEARANCE_SCHEME, config_file.APPEARANCE_SCHEME_DEFAULT
        )
        scheme_index = self.appearance.findData(scheme)
        self.appearance.blockSignals(True)
        self.appearance.setCurrentIndex(scheme_index if scheme_index >= 0 else 0)
        self.appearance.blockSignals(False)
        self.setEnabled(placed)
        self.location.setText(
            str(target) if placed
            else "No configuration file yet — run File → Setup…"
        )
        self.status.clear()

    def _save(self) -> None:
        try:
            written = config_file.update({
                config_file.CROSS_AGENT_STAGE: self.cross_agent.currentData(),
                config_file.APPEARANCE_SCHEME: self.appearance.currentData(),
            })
        except OSError as exc:
            self.status.setText(f"Not saved: {exc}")
            return
        self.status.setText(f"Saved to {written.name}")
