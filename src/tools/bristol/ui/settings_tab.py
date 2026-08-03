"""ui/settings_tab.py — the Settings tab: choices about how the board behaves.

Every field here reads and writes ``config/config.local.json`` through
``config_file``, the same helper the setup wizard uses, so a choice has one
home. A key this build does not offer is left exactly as it was on save.

The active agent is deliberately absent: it changes what the whole application
means, so it lives on the main window where it is always visible.
"""

from __future__ import annotations

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

# What each stored value is called on screen.
CROSS_AGENT_CHOICES = [
    ("active", "The Board — where the assignee will see it"),
    ("backlog", "The Backlog — to be picked up whenever"),
]


class SettingsTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.cross_agent = QComboBox()
        for value, caption in CROSS_AGENT_CHOICES:
            self.cross_agent.addItem(caption, value)

        form = QFormLayout()
        form.addRow("A card one agent files for another goes to", self.cross_agent)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        self.status = QLabel()
        self.status.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.status, 1)

        self.location = QLabel()
        self.location.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.location)
        layout.addStretch(1)

        self.reload()

    def reload(self) -> None:
        """Show what the configuration currently says."""
        target = config_file.path()
        placed = target is not None and target.exists()
        stored = config_file.get(
            config_file.CROSS_AGENT_STAGE, config_file.CROSS_AGENT_STAGE_DEFAULT
        )
        index = self.cross_agent.findData(stored)
        self.cross_agent.setCurrentIndex(index if index >= 0 else 0)
        self.setEnabled(placed)
        self.location.setText(
            f"Stored in {target}" if placed
            else "No configuration file yet — run File → Setup…"
        )
        self.status.clear()

    def _save(self) -> None:
        try:
            written = config_file.update(
                {config_file.CROSS_AGENT_STAGE: self.cross_agent.currentData()}
            )
        except OSError as exc:
            self.status.setText(f"Not saved: {exc}")
            return
        self.status.setText(f"Saved to {written.name}")
