"""ui/settings_modal.py — Settings, drawn by the app over its own window.

Everything that configures Bristol Tickets is one modal: a panel over a scrim
that tints the window, a side nav down its left, and the open tab's page to
its right under the tab's name. The tabs are the fleet's two pages, Agents and
Skills, then the Settings sections ``settings_tab.SECTIONS`` names.

The modal is a frameless window of its own, application-modal and laid
exactly over it, following it as it moves and resizes. Being a window rather
than a widget inside the main one, it is what the accessibility tree and the
keyboard reach while it is open, and the board behind it takes no input. It
closes on its ✕, on Escape, and on a click on the scrim.

A window that one of its pages opens — an agent's form, a skill, Manage Themes,
a folders window — takes the panel's place: the panel hides while that window
is shown, the scrim stays, and the panel comes back on the same tab when the
window closes, however it closed. A question or a notice (``dialogs.Modal``)
and a file picker (``QFileDialog``) are asked over the panel instead, because
they answer a question the page put and the page is what they are about.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QKeySequence, QMouseEvent, QPainter, QPaintEvent, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons, mac_window
from .dialogs import Modal
from .settings_tab import SECTIONS, SettingsTab
from .theme import LAYOUT, scrim, space

# The fleet's pages, before the Settings sections in the side nav.
FLEET_TABS = ["Agents", "Skills"]


class _DialogWatch(QObject):
    """Hides the panel while a window one of its pages opened is shown."""

    def __init__(self, modal: SettingsModal) -> None:
        super().__init__(modal)
        self._modal = modal
        self._open: set[int] = set()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        kind = event.type()
        if kind in (QEvent.Type.Show, QEvent.Type.Hide) and self._takes_place(obj):
            if kind == QEvent.Type.Show:
                self._open.add(id(obj))
            else:
                self._open.discard(id(obj))
            self._modal.panel.setVisible(not self._open)
        return False

    def _takes_place(self, obj: QObject) -> bool:
        """A window opened from a page of the panel, other than a question the
        page asks over it."""
        if not isinstance(obj, QDialog) or isinstance(obj, (Modal, QFileDialog)):
            return False
        parent = obj.parentWidget()
        while parent is not None:
            if parent is self._modal.panel:
                return True
            parent = parent.parentWidget()
        return False


class SettingsModal(QWidget):
    """The scrim over the window, and the Settings panel centred on it."""

    def __init__(
        self,
        window: QWidget,
        agents: QWidget,
        skills: QWidget,
        settings: SettingsTab,
        on_closed: Callable[[], object] | None = None,
    ) -> None:
        super().__init__(
            window,
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self._window = window
        self._settings = settings
        self._on_closed = on_closed
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowTitle("Settings")
        # The scrim is painted, translucent, over the window behind.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        self.panel = QFrame(self)
        self.panel.setObjectName("settingsModal")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # The side nav: one checkable row per tab, exactly one of them open.
        nav = QWidget()
        nav.setFixedWidth(LAYOUT["settings_nav_w"])
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(space("xs"))
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.tabs: dict[str, QPushButton] = {}
        for name in FLEET_TABS + SECTIONS:
            button = QPushButton(name)
            button.setObjectName("settingsNav")
            button.setAccessibleName(name)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            # Toggled rather than clicked, so an accessibility press opens it.
            button.toggled.connect(lambda checked, n=name: checked and self.show_tab(n))
            self._group.addButton(button)
            nav_layout.addWidget(button)
            self.tabs[name] = button
        nav_layout.addStretch(1)

        # The open tab's name, and the ✕ that closes the modal, over its page.
        self.heading = QLabel()
        self.heading.setObjectName("dialogHeading")
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("quietIcon")
        icons.tint(self.close_btn, "x")
        self.close_btn.setAccessibleName("Close Settings")
        self.close_btn.setAutoDefault(False)
        self.close_btn.clicked.connect(lambda _checked=False: self.close_modal())
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.heading, 1, Qt.AlignmentFlag.AlignVCenter)
        head.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self.pages = QStackedWidget()
        self._page_for = {"Agents": agents, "Skills": skills}
        for page in (agents, skills, settings):
            self.pages.addWidget(page)
        for name in SECTIONS:
            self._page_for[name] = settings

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(space("xl"))
        content.addLayout(head)
        content.addWidget(self.pages, 1)

        body = QHBoxLayout(self.panel)
        body.setContentsMargins(space("xl"), space("xl"), space("xl"), space("xl"))
        body.setSpacing(space("2xl"))
        body.addWidget(nav)
        body.addLayout(content, 1)

        self._watch = _DialogWatch(self)
        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape.setContext(Qt.ShortcutContext.WindowShortcut)
        escape.activated.connect(self.close_modal)

        window.installEventFilter(self)
        self.hide()
        self.tabs["Agents"].setChecked(True)

    # ----- opening and closing ---------------------------------------------

    def open_modal(self, tab: str | None = None) -> None:
        """Cover the window and show the panel, on ``tab`` or the tab it was
        last left on."""
        if tab is not None:
            self.tabs[tab].setChecked(True)
        self._fit()
        self.panel.show()
        self.show()
        mac_window.clear_backing(self)
        self.raise_()
        self.activateWindow()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self._watch)
        self.tabs[self.current_tab()].setFocus()

    def close_modal(self) -> None:
        if self.isHidden():
            return
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self._watch)
        self.hide()
        self._window.activateWindow()
        if self._on_closed is not None:
            self._on_closed()

    def current_tab(self) -> str:
        return next(name for name, b in self.tabs.items() if b.isChecked())

    def show_tab(self, name: str) -> None:
        """Open one tab: its page, and the section where the page is
        Settings'."""
        page = self._page_for[name]
        if page is self._settings:
            self._settings.show_section(name)
        self.pages.setCurrentWidget(page)
        self.heading.setText(name)
        if not self.tabs[name].isChecked():
            self.tabs[name].setChecked(True)

    # ----- geometry and paint ----------------------------------------------

    def _fit(self) -> None:
        """Cover the whole window, and centre the panel in it at its size, or
        inside the window's inset where the window is smaller."""
        self.setGeometry(self._window.geometry())
        inset = space("2xl")
        width = min(LAYOUT["settings_w"], self.width() - 2 * inset)
        height = min(LAYOUT["settings_h"], self.height() - 2 * inset)
        self.panel.setGeometry(
            (self.width() - width) // 2, (self.height() - height) // 2, width, height
        )

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if (
            obj is self._window
            and event.type() in (QEvent.Type.Resize, QEvent.Type.Move)
            and not self.isHidden()
        ):
            self._fit()
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(scrim()))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """A click on the scrim, outside the panel, closes the modal."""
        if self.panel.isVisible() and not self.panel.geometry().contains(
            event.position().toPoint()
        ):
            self.close_modal()
            return
        super().mousePressEvent(event)
