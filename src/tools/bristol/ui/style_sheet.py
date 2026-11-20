"""ui/style_sheet.py — the typeface, the global Qt stylesheet, and the call that
styles the application.

``build_style_sheet()`` renders the stylesheet from whatever the live palette
``C`` contains and from the token scales, so a single
``app.setStyleSheet(build_style_sheet())`` re-themes everything
stylesheet-driven, child dialogs and message boxes included. ``apply_scheme()``
is the one call that installs the collection, makes a scheme live and styles
the application. What each scheme key means and which token governs which
element is the styling contract in ``ui/README.md``.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPalette

from .themes import C, live_scheme, register_collection, set_scheme
from .tokens import LAYOUT, control_height, radius, space, type_size

# The app's one typeface, Inter, under the SIL Open Font License; its files and
# the licence ship in ui/fonts/. Bundled so the text looks the same on every Mac,
# whatever fonts that Mac has.
TYPEFACE = "Inter"
FONT_DIR = Path(__file__).resolve().parent / "fonts"


def install_typeface(app) -> bool:
    """Register the bundled typeface and make it the application's font, at
    ``TYPE["body"]``. Returns whether the typeface took; the size is set either
    way.

    Every font built with ``QFont()`` afterwards starts from it, and the style
    sheet names sizes and weights only, so one call sets the face everywhere.
    The monospace face kept for templates is set by name and stays.
    """
    from PySide6.QtGui import QFontDatabase

    families: set[str] = set()
    for file in sorted(FONT_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(file))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    font = app.font()
    font.setPointSize(type_size("body"))
    installed = TYPEFACE in families
    if installed:
        font.setFamily(TYPEFACE)
    app.setFont(font)
    return installed


def apply_scheme(
    app,
    theme: str | None,
    mode: str | None,
    stored: dict | None = None,
    legacy_custom: dict | None = None,
) -> None:
    """Install the collection, resolve a theme and a mode against the OS state,
    make the scheme live, and style ``app``.

    Every window the application opens is styled by this one call, so it runs
    before the first window is built rather than inside any of them.

    ``stored`` is the differences the configuration carries and ``legacy_custom``
    the palette a build that offered one Custom option wrote. Both go in first,
    because a stored choice can name a theme only the collection has.
    """
    register_collection(stored, legacy_custom)
    set_scheme(live_scheme(app, theme, mode))
    if app is not None:
        from .popups import install as install_popups

        install_popups(app)
        from .scroll_bars import install as install_scroll_bars

        install_scroll_bars(app)
        if app.font().family() != TYPEFACE:
            install_typeface(app)
        style_application(app)


def style_application(app) -> None:
    """Draw ``app`` in the live palette: the style sheet, and the one colour a
    style sheet cannot set, a field's placeholder text, which takes Tertiary
    Text."""
    palette = app.palette()
    placeholder = QColor(C["INK_FAINT"])
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        palette.setColor(group, QPalette.ColorRole.PlaceholderText, placeholder)
    app.setPalette(palette)
    app.setStyleSheet(build_style_sheet())


def chevron_image(colour: str, direction: str = "down") -> str | None:
    """Lucide's chevron in the given colour and direction (``down`` or ``up``),
    as an image file the stylesheet can point a combo box's or spin box's arrow
    at. Returns None when nothing can be written, in which case the arrow rule
    is left out.
    """
    from .icons import image_file

    # The chevron's own part of Lucide's 24-unit drawing, stroke included, at
    # the arrow's width-to-height ratio.
    return image_file(f"chevron-{direction}", colour, space("lg"), space("md"), (4, 7, 16, 10))


def check_mark_side() -> int:
    """The side of a checkbox's check, in device-independent pixels: the box,
    SPACE lg, less a pixel each side."""
    return space("lg") - 2


def check_image(colour: str) -> str | None:
    """Lucide's check in the given colour, as an image file the stylesheet
    points a checked checkbox indicator at. Returns None when nothing can be
    written, in which case the checked state is a plain accent fill."""
    from .icons import image_file

    side = check_mark_side()
    return image_file("check", colour, side, side, (3, 3, 18, 18))


def build_style_sheet() -> str:
    """Render the global Qt stylesheet from the live palette ``C`` and the token
    scales, so a scheme swap and a token change both reach every styled widget."""
    r_sm, r_md, r_lg = radius("sm"), radius("md"), radius("lg")
    chevron = chevron_image(C["INK_SOFT"])
    chevron_up = chevron_image(C["INK_SOFT"], "up")
    check = check_image(C["ON_ACCENT"])
    arrow_rule = (
        f"QComboBox::down-arrow, QDateEdit::down-arrow {{ image: url({chevron}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}"
        if chevron
        else ""
    )
    spin_arrow_rule = (
        f"QSpinBox::up-arrow {{ image: url({chevron_up}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}\n"
        f"QSpinBox::down-arrow {{ image: url({chevron}); "
        f"width: {space('lg')}px; height: {space('md')}px; }}"
        if chevron and chevron_up
        else ""
    )
    check_rule = f"image: url({check});" if check else ""
    ctl = control_height() - 2  # inside the 1px border every control draws
    tb_ctl = LAYOUT["toolbar_control_h"] - 2
    tb_box = LAYOUT["toolbar_box_w"] - 2

    def _ink(alpha: float) -> str:
        ink = C["INK"].lstrip("#")[-6:]
        r, g, b = (int(ink[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"

    ink_06, ink_10, ink_14 = _ink(0.06), _ink(0.10), _ink(0.14)
    s_xs, s_sm, s_md, s_lg, s_xl, s_2xl = (
        space("xs"),
        space("sm"),
        space("md"),
        space("lg"),
        space("xl"),
        space("2xl"),
    )
    return f"""
QMainWindow, QDialog {{
    background-color: {C["CANVAS"]};
    color: {C["INK"]};
}}
/* The board side of the body and the splitter's gap take the body's surface. */
QWidget#leftContainer, QSplitter::handle {{
    background: transparent;
}}
/* The top bar: the window's own background; the body surface below it is what
   ends it. */
QWidget#appHeader {{
    background-color: {C["CANVAS"]};
}}
/* The body: one rounded surface under the top bar, containing every view and
   the detail pane. */
QWidget#bodySurface {{
    background-color: {C["SURFACE"]};
    border-radius: {radius("xl")}px;
}}
/* A region's name: the app's beside its mark, a board column's. */
QLabel#regionTitle {{
    color: {C["INK"]};
    font-size: {type_size("title")}pt;
    font-weight: 600;
}}
/* A view in the top bar: its name on the bar, a faint fill on
   hover, and the open one in the accent on a faint fill of its own. */
QPushButton#viewTab {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    padding: 0px {s_lg}px;
    color: {C["INK_SOFT"]};
    font-weight: 600;
}}
QPushButton#viewTab:hover {{
    background-color: {ink_06};
    color: {C["INK"]};
}}
QPushButton#viewTab:checked {{
    background-color: {ink_10};
    color: {C["ACCENT_DK"]};
}}
QPushButton#viewTab:focus {{
    border-color: {C["ACCENT"]};
}}
/* The top bar's icon buttons — Search, Refresh, Settings — each its icon in a
   faint box; an open view's box takes the accent's edge. */
QPushButton#toolbarButton, QPushButton#toolbarToggle {{
    background-color: {ink_06};
    border: 1px solid {ink_14};
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    min-width: {tb_box}px;
    max-width: {tb_box}px;
    padding: 0px;
}}
QPushButton#toolbarButton:hover, QPushButton#toolbarToggle:hover {{
    background-color: {ink_14};
}}
QPushButton#toolbarToggle:checked {{
    background-color: {ink_10};
    border-color: {C["ACCENT"]};
}}
QPushButton#toolbarButton:focus, QPushButton#toolbarToggle:focus {{
    border-color: {C["ACCENT"]};
}}
/* The top bar's Agent picker: a picker in the top bar's own box, an ink_06
   face with an ink_14 edge, at the top bar's height, its text the body text
   every picker carries. */
QComboBox#toolbarPicker {{
    background-color: {ink_06};
    border: 1px solid {ink_14};
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    padding: 0px {s_md}px;
    color: {C["INK"]};
    font-size: {type_size("body")}pt;
    font-weight: 400;
}}
QComboBox#toolbarPicker:hover {{ background-color: {ink_14}; }}
QComboBox#toolbarPicker:on {{ background-color: {ink_10}; }}
QComboBox#toolbarPicker:focus {{ border-color: {C["ACCENT"]}; }}
/* The top bar's Create: the primary button at the top bar's height. Where a
   view has no cards it is faded by an opacity effect rather than turned grey,
   as the Mac dims a toolbar item it has no use for. */
QPushButton#toolbarCreate, QPushButton#toolbarCreate:disabled {{
    background-color: {C["ACCENT"]};
    color: {C["ON_ACCENT"]};
    border: 1px solid {C["ACCENT"]};
    border-radius: {r_md}px;
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    min-width: {tb_box}px;
    max-width: {tb_box}px;
    padding: 0px;
}}
QPushButton#toolbarCreate:hover {{
    background-color: {C["CREATE_HOVER"]};
    border-color: {C["CREATE_HOVER"]};
}}
/* A list is a well of rows a person clicks or ticks, so it carries the edge
   everything clickable carries: its fill alone sits too close to the window's
   to be found. An editable list whose rows are widgets is the same well. */
QListWidget, QFrame#rowList {{
    background-color: {C["LIST_BG"]};
    color: {C["INK"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
    outline: 0;
}}
/* A board column is a container: a faint ink tint from its header line to its
   last card, with no edge, so the column reads as one stack and a card
   scrolling up passes under the header inside it. The list in it is clear. */
QFrame#boardColumn {{
    background-color: {ink_06};
    border: none;
    border-radius: {r_lg}px;
}}
QListWidget#columnCards {{
    background: transparent;
    border: none;
    padding: 0px;
}}
/* A column's name, a step above a card's title, and its count beside it. */
QLabel#columnName {{
    color: {C["INK"]};
    font-size: {type_size("section")}pt;
    font-weight: 600;
}}
QLabel#columnCount {{
    color: {C["INK_SOFT"]};
    font-size: {type_size("body")}pt;
}}
/* The detail pane is a sidebar surface: the one raised region right of the
   splitter, separated from the board canvas by a hairline. */
QWidget#detailPane {{
    background-color: {C["SURFACE"]};
    border-left: 1px solid {C["BORDER"]};
    border-top-right-radius: {radius("xl")}px;
    border-bottom-right-radius: {radius("xl")}px;
}}
QScrollArea#detailScroll, QScrollArea#detailScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
/* The hairline under a section header in the detail pane. */
QFrame#sectionRule {{ background-color: {C["BORDER"]}; border: none; }}
QPushButton#paneReveal {{
    border-left: 1px solid {C["BORDER"]};
    border-radius: 0px;
}}
/* A path the user may need to find on disk reads as a path. */
QLabel#pathRow {{
    background-color: {C["LIST_BG"]};
    border: 1px solid transparent;
    border-radius: {r_md}px;
    padding: {s_md}px {s_lg}px;
    color: {C["INK"]};
    font-size: {type_size("body")}pt;
}}
QLabel#pathRow[fieldMissing="true"] {{
    color: {C["MISSING"]};
    border-color: {C["MISSING"]};
}}
QLabel#sectionHeader[fieldMissing="true"] {{ color: {C["MISSING"]}; }}
QLabel#formCaption {{ color: {C["INK_SOFT"]}; }}
/* The filter panel: one raised surface under the Filter button, containing a
   section per facet and one row per option. A row is a whole click target, so
   it takes the pointer fill a card does. */
QFrame#filterMenu {{
    background-color: {C["SURFACE"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_lg}px;
}}
QLabel#facetHeading {{
    color: {C["INK_SOFT"]};
    font-size: {type_size("caption")}pt;
    font-weight: 600;
}}
QWidget#facetRow {{ border-radius: {r_md}px; }}
QWidget#facetRow:hover {{ background-color: {C["HOVER_BG"]}; }}
QScrollArea#filterScroll, QScrollArea#filterScroll > QWidget > QWidget,
QScrollArea#paletteScroll, QScrollArea#paletteScroll > QWidget > QWidget,
QScrollArea#recordScroll, QScrollArea#recordScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}
QPushButton#link:disabled {{
    color: {C["DISABLED_TX"]};
    text-decoration: none;
}}
/* The Filter button sits on the columns' header line at the top bar's control
   height, its word padded as a top-bar control is. */
QPushButton#filterBtn {{
    min-height: {tb_ctl}px;
    max-height: {tb_ctl}px;
    padding: 0px {s_md}px;
}}
/* The Filter button takes the accent while it is leaving something out, so a
   narrowed board never reads as an empty one. */
QPushButton#filterBtn[active="true"] {{
    background-color: {C["SEL_BG"]};
    border: 1px solid {C["ACCENT"]};
    color: {C["ACCENT_DK"]};
}}
/* One applied filter, removable where it is read. */
QPushButton#filterChip {{
    background-color: {C["NEUTRAL_BG"]};
    color: {C["NEUTRAL_TX"]};
    border: 1px solid transparent;
    border-radius: {r_sm}px;
    padding: {s_sm}px {s_lg}px;
    font-weight: 400;
}}
QPushButton#filterChip:focus {{ border-color: {C["ACCENT"]}; }}
QPushButton#filterChip:hover {{
    background-color: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
}}
/* A scroll bar is chrome: a slim handle on an empty groove, so a column that
   overflows does not gain a heavy black rail down its edge. It keeps SPACE sm
   from what it scrolls, drawn as an empty strip on the content's side. */
QScrollBar:vertical {{
    background: transparent;
    width: {s_lg + s_sm}px;
    margin: 0px 0px 0px {s_sm}px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: {s_lg + s_sm}px;
    margin: {s_sm}px 0px 0px 0px;
}}
/* Where the content is already inset from the viewport's edge by SPACE sm — a
   board card by its margin, text by its document margin — that inset is the
   gap, and the bar adds none. */
QListWidget#columnCards QScrollBar:vertical, QTextEdit QScrollBar:vertical {{
    width: {s_lg}px;
    margin: 0px;
}}
/* A column's bar runs level with its cards at rest, each end a card's margin in
   from the edge where cards scroll out of sight. */
QListWidget#columnCards QScrollBar:vertical {{
    margin: {s_sm}px 0px {s_sm}px 0px;
}}
QTextEdit QScrollBar:horizontal {{
    height: {s_lg}px;
    margin: 0px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {C["BORDER"]};
    border-radius: {r_sm}px;
    min-height: {s_2xl}px;
    min-width: {s_2xl}px;
}}
QScrollBar::handle:hover {{ background: {C["INK_SOFT"]}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
/* The setup wizard is the same application: the ground it draws on, the type
   its pages are titled in, and the buttons it is driven by all come from here. */
QWizard {{ background-color: {C["CANVAS"]}; }}
/* Direct children only: the header band, the page container and the button
   row. A field inside a page is not matched, so the input rules still win. */
QWizard > QWidget {{ background-color: {C["CANVAS"]}; }}
QWizardPage {{ background-color: {C["CANVAS"]}; }}
QWizardPage > QLabel {{ font-size: {type_size("body")}pt; }}

QListWidget::item {{ border: none; }}
QListWidget::item:selected {{ background: transparent; }}
/* Search results and the theme list are plain text items (not
   delegate-painted cards), so the transparent-selection rule above would leave
   them with the palette's highlighted-text colour on a light fill —
   near-invisible. Give these lists a visible selected fill and the brightest
   accent the board uses for text. */
QListWidget#textList::item {{
    padding: {s_md}px {s_lg}px;
    border-radius: {r_md}px;
    border-left: 3px solid transparent;
}}
/* The selected row also carries an accent bar, because a scheme's hover and
   selection fills sit close enough that a hovered row would otherwise read as
   a second selection. */
QListWidget#textList::item:selected {{
    background: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
    border-left: 3px solid {C["ACCENT"]};
}}
QListWidget#textList::item:hover:!selected {{
    background: {C["HOVER_BG"]};
}}
/* The Search and Archive results: a table read as a list, with a header per
   fact and alternate rows, and the selection in the accent the lists use. */
QTableWidget#resultsTable {{
    background-color: {C["LIST_BG"]};
    alternate-background-color: {C["SURFACE"]};
    color: {C["INK"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_lg}px;
    outline: 0;
}}
QTableWidget#resultsTable::item {{ padding: {s_sm}px {s_md}px; border: none; }}
QTableWidget#resultsTable::item:selected {{
    background-color: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
}}
QHeaderView::section {{
    background-color: {C["CANVAS"]};
    color: {C["INK_SOFT"]};
    border: none;
    border-bottom: 1px solid {C["BORDER"]};
    padding: {s_sm}px {s_md}px;
    font-weight: 600;
}}
QComboBox, QLineEdit, QAbstractSpinBox, QTextEdit {{
    background-color: {C["SURFACE"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_md}px;
    padding: {s_md}px {s_md}px;
    color: {C["INK"]};
    selection-background-color: {C["ACCENT"]};
    selection-color: {C["ON_ACCENT"]};
}}
/* A picker is a button that opens a list, so it takes the control face. */
QComboBox, QDateEdit {{
    background-color: {C["BTN_BG"]};
    border: 1px solid {C["BTN_BORDER"]};
}}
QComboBox:hover, QDateEdit:hover {{ background-color: {C["BTN_HOVER"]}; }}
QComboBox:on {{ background-color: {C["BTN_PRESSED"]}; }}
QComboBox:focus, QLineEdit:focus, QAbstractSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {C["ACCENT"]};
}}
/* A required field that is currently empty. Set via the dynamic property
   fieldMissing=true (see record_dialog._refresh_required_state), and repeated
   for :focus so the accent border does not paint over the warning while the
   user is typing in — or deleting out of — the very field that is missing. */
QLineEdit[fieldMissing="true"], QTextEdit[fieldMissing="true"],
QLineEdit[fieldMissing="true"]:focus, QTextEdit[fieldMissing="true"]:focus {{
    border: 2px solid {C["MISSING"]};
}}
QLabel[fieldMissing="true"] {{ color: {C["MISSING"]}; }}
/* A formCaption carries its own missing state. */
QLabel#formCaption[fieldMissing="true"] {{ color: {C["MISSING"]}; }}
/* A picker opens this app's own list rather than the platform's menu: a raised
   surface with a rounded corner, room around every option, and the same
   selected fill a list row takes. popups.py makes its window transparent so
   the corner is the one drawn here, and as wide as its longest option. */
QComboBox {{ combobox-popup: 0; }}
QComboBox QAbstractItemView {{
    background-color: {C["SURFACE"]};
    color: {C["INK"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
    outline: 0;
    selection-background-color: {C["SEL_BG"]};
    selection-color: {C["ACCENT_DK"]};
}}
QComboBox QAbstractItemView::item {{
    min-height: {s_2xl}px;
    padding: {s_xs}px {s_lg}px;
    border-radius: {r_md}px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {C["HOVER_BG"]};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
}}
/* A growing text field takes slimmer vertical padding, so one line of it is
   one control tall (growing_edit.py fixes the height). */
QTextEdit[growing="true"] {{ padding: {s_sm}px {s_md}px; }}
/* A picker reads as a picker: the drop-down carries a chevron of its own. */
QComboBox::drop-down, QDateEdit::drop-down {{
    border: none;
    width: {s_2xl}px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
{arrow_rule}
/* The spin box steps with the same chevrons every picker carries, drawn
   inside the field. */
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: padding;
    width: {s_2xl}px;
    border: none;
    background: transparent;
}}
QSpinBox::up-button {{ subcontrol-position: top right; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; }}
{spin_arrow_rule}
QLabel {{ color: {C["INK"]}; background: transparent; }}
QLabel#inspectorTitle {{ color: {C["ACCENT_DK"]}; }}
QLabel#sectionHeader {{ color: {C["INK_SOFT"]}; font-weight: 600; }}
/* The one thing a confirmation or a notice says first: the largest text in a
   modal that carries no icon, since the words are all it has. */
QLabel#dialogHeading {{
    color: {C["INK"]};
    font-size: {type_size("section")}pt;
    font-weight: 600;
}}
QLabel#metaText {{ color: {C["INK_SOFT"]}; }}
/* The Settings modal: a dialog's canvas at the body's corner, over the scrim. */
QFrame#settingsModal {{
    background-color: {C["CANVAS"]};
    border-radius: {radius("xl")}px;
}}
/* A tab of its side nav: its name with no face, a hover fill under the
   pointer, and the open tab chosen as a picker's item is. */
QPushButton#settingsNav {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {r_md}px;
    min-height: {ctl}px;
    max-height: {ctl}px;
    padding: 0px {s_lg}px;
    text-align: left;
    color: {C["INK"]};
    font-weight: 400;
}}
QPushButton#settingsNav:hover {{ background-color: {C["HOVER_BG"]}; }}
QPushButton#settingsNav:checked {{
    background-color: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
    font-weight: 600;
}}
QPushButton#settingsNav:focus {{ border-color: {C["ACCENT"]}; }}
/* A link: accent text with no surface, underlined under the pointer and with
   focus. A link row, Clear All in the filter panel, a skill's source. */
QPushButton#link {{
    background: transparent;
    border: none;
    padding: {s_xs}px 0px;
    text-align: left;
    color: {C["ACCENT_DK"]};
    font-weight: 400;
}}
QPushButton#link:hover, QPushButton#link:focus {{ text-decoration: underline; }}
/* A quiet icon button: an icon with no face until the pointer is over it, for
   an action that sits beside what it acts on — the ✕ that removes a link, an
   attachment or a variable, the folder that picks one. The pane's collapse
   control and the strip that brings it back are the same button. */
QPushButton#quietIcon, QPushButton#paneToggle, QPushButton#paneReveal {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {r_md}px;
    padding: {s_xs}px;
    color: {C["INK_SOFT"]};
    font-weight: 400;
}}
QPushButton#quietIcon:hover, QPushButton#paneToggle:hover,
QPushButton#paneReveal:hover {{
    background-color: {C["HOVER_BG"]};
    color: {C["INK"]};
}}
QPushButton#quietIcon:focus, QPushButton#paneToggle:focus {{
    border-color: {C["ACCENT"]};
}}
QCheckBox {{
    color: {C["INK"]};
    background: transparent;
    spacing: {s_md}px;
    padding: {s_xs}px 0px;
}}
/* The checkbox is the scheme's own control: a surface with an accent
   hairline, an accent fill when checked — never the platform's indicator. */
QCheckBox::indicator {{
    width: {s_lg}px;
    height: {s_lg}px;
    border: 1px solid {C["ACCENT"]};
    border-radius: {r_sm}px;
    background-color: {C["SURFACE"]};
}}
QCheckBox::indicator:hover {{ border-color: {C["ACCENT"]}; }}
QCheckBox::indicator:checked {{
    background-color: {C["ACCENT"]};
    border-color: {C["ACCENT"]};
    {check_rule}
}}
QMenu {{
    background-color: {C["SURFACE"]};
    color: {C["INK"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_lg}px;
    padding: {s_sm}px;
}}
/* A menu is the picker's open list: the same corner, pad and option. */
QMenu::item {{
    min-height: {s_2xl}px;
    padding: {s_xs}px {s_lg}px;
    border-radius: {r_md}px;
}}
QMenu::item:selected {{ background-color: {C["SEL_BG"]}; color: {C["ACCENT_DK"]}; }}
QMenu::separator {{ height: 1px; background: {C["BORDER"]}; margin: {s_sm}px {s_md}px; }}
QPushButton {{
    background-color: {C["BTN_BG"]};
    border: 1px solid {C["BTN_BORDER"]};
    border-radius: {r_md}px;
    padding: {s_md}px {s_lg}px;
    font-weight: 400;
    color: {C["INK"]};
}}
QPushButton:hover {{ background-color: {C["BTN_HOVER"]}; }}
QPushButton:pressed {{ background-color: {C["BTN_PRESSED"]}; }}
QPushButton:focus {{ border-color: {C["ACCENT"]}; }}
/* A button kept unclickable until its form is valid must LOOK unclickable —
   Qt's default disabled rendering is barely distinguishable under this
   stylesheet, which would read as "the button is broken". */
QPushButton:disabled {{
    background-color: {C["DISABLED_BG"]};
    border: 1px solid {C["BORDER"]};
    color: {C["DISABLED_TX"]};
}}
QPushButton::menu-indicator {{ width: 0px; image: none; }}
QPushButton#globalCreateBtn {{
    background-color: {C["ACCENT"]};
    color: {C["ON_ACCENT"]};
    border: 1px solid {C["ACCENT"]};
}}
QPushButton#globalCreateBtn:hover {{
    background-color: {C["CREATE_HOVER"]};
    border-color: {C["CREATE_HOVER"]};
}}
QPushButton#globalCreateBtn:focus, QPushButton#toolbarCreate:focus {{
    border-color: {C["ON_ACCENT"]};
}}
/* The id selector outranks the generic :disabled rule, so the primary button
   needs its own unclickable look or it would stay accent-filled while dead. */
QPushButton#globalCreateBtn:disabled {{
    background-color: {C["DISABLED_BG"]};
    border: 1px solid {C["BORDER"]};
    color: {C["DISABLED_TX"]};
}}
/* A segmented control: its segments share the control face and join into one
   control; the chosen one takes the selection fill and the accent text. */
QPushButton#segment {{
    border-radius: 0px;
    padding: 0px {s_lg}px;
}}
QPushButton#segment[position="middle"], QPushButton#segment[position="last"] {{
    border-left: none;
}}
QPushButton#segment[position="first"] {{
    border-top-left-radius: {r_md}px;
    border-bottom-left-radius: {r_md}px;
}}
QPushButton#segment[position="last"] {{
    border-top-right-radius: {r_md}px;
    border-bottom-right-radius: {r_md}px;
}}
QPushButton#segment:checked {{
    background-color: {C["SEL_BG"]};
    color: {C["ACCENT_DK"]};
}}
/* A button whose window contains something that is not on disk. */
QPushButton[missing="true"] {{
    border: 1px solid {C["MISSING"]};
    color: {C["MISSING"]};
}}
/* A destructive action is an ordinary button whose words are red, as the Mac
   marks one; the fill stays the plain button's. */
QPushButton#deleteBtn {{
    color: {C["DELETE_BG"]};
}}
QPushButton#deleteBtn:hover {{
    color: {C["DELETE_HOVER"]};
}}
/* The + and − under an editable list: two square buttons joined at their
   shared edge. */
/* One height for every control that can share a row. Padding and border are
   zeroed vertically and the height is fixed outright, so a field, a picker, a
   date and a button beside each other line up to the pixel. */
QPushButton, QLineEdit, QComboBox, QAbstractSpinBox {{
    min-height: {ctl}px;
    max-height: {ctl}px;
    padding-top: 0px;
    padding-bottom: 0px;
}}
/* Text-like buttons are not controls on a row: they keep their own height. */
QPushButton#link, QPushButton#filterChip, QPushButton#paneToggle,
QPushButton#paneReveal, QPushButton#quietIcon, QPushButton#exampleLink {{
    min-height: 0px;
    max-height: 9999px;
}}
QPushButton#link, QPushButton#exampleLink {{ padding: {s_xs}px 0px; }}
QPushButton#quietIcon {{ padding: {s_xs}px; }}
QPushButton#paneToggle, QPushButton#paneReveal {{ padding: {s_xs}px {s_md}px; }}
QPushButton#filterChip {{ padding: {s_sm}px {s_lg}px; }}
/* An example under a field: Tertiary Text, as a placeholder is, and a link
   on hover because it opens the page it shows. */
QPushButton#exampleLink {{
    background: transparent;
    border: none;
    text-align: left;
    color: {C["INK_FAINT"]};
    font-weight: 400;
}}
QPushButton#exampleLink:hover, QPushButton#exampleLink:focus {{ color: {C["ACCENT_DK"]}; text-decoration: underline; }}
"""


def _mono_font(point_size: int | None = None):
    """A monospace font so mad-lib templates and their fill-in blanks line up in
    the Description editor. Menlo, with a Monospace style hint behind it."""
    from PySide6.QtGui import QFont

    f = QFont("Menlo")
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(point_size if point_size is not None else type_size("section"))
    return f
