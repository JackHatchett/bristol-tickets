"""ui — the PySide6 widgets for Bristol Tickets.

Import graph (bottom-up, no cycles):

    theme            (constants, stylesheet, helpers)  ← imported by everything
    schema_guard     (on-launch migration)             ← imported by main_window
    card_delegate    → theme
    record_dialog    → theme
    kanban_column    → theme, card_delegate, record_dialog
    main_window      → theme, schema_guard, kanban_column, record_dialog

Public entry point:
    from ui.main_window import MainWindow
"""

from .main_window import MainWindow

__all__ = ["MainWindow"]
