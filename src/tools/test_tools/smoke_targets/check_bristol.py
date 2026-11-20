"""smoke_targets/check_bristol.py — the `bristol` smoke target, run by smoke.py."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from qt_headless import TOOLS, offscreen_app, tool_on_path
from smoke_targets.failure import SmokeFailure

# The board size the speed checks run on: the user's own, rounded up.
SPEED_BOARD_CARDS = 600

# Seconds each timed action may take. Measured on the user's Mac on 2026-11-19
# after #1440: an agent choice 0.02 s, a theme change 0.6 s, a Settings reload
# 0.14 s. Each limit leaves room for a slower machine and none lets back the
# re-theming reload #1440 removed.
SPEED_LIMITS = {
    "open": 15.0,
    "refresh": 5.0,
    "theme": 6.0,
    "agent": 0.5,
    "reload": 1.0,
}


def check_bristol() -> list[str]:
    import importlib
    import pkgutil

    ok: list[str] = []
    tool_on_path("bristol")
    app = offscreen_app()

    import ui  # bristol/ui

    for mod in pkgutil.iter_modules(ui.__path__):
        importlib.import_module(f"ui.{mod.name}")
    ok.append("all ui.* modules import")

    # One typeface, bundled: the app's font becomes it at the type scale's body
    # size, and a font built afterwards starts from it.
    from PySide6.QtGui import QFont as _QFont
    from ui import theme as _theme

    _size = float(_theme.type_size("body"))
    if not _theme.install_typeface(app):
        raise SmokeFailure(f"the bundled {_theme.TYPEFACE} did not register from {_theme.FONT_DIR}")
    if app.font().family() != _theme.TYPEFACE or app.font().pointSizeF() != _size:
        raise SmokeFailure(
            f"the app font is {app.font().family()} {app.font().pointSizeF()}pt, "
            f"not {_theme.TYPEFACE} at the body size, {_size}pt"
        )
    if _QFont().family() != _theme.TYPEFACE:
        raise SmokeFailure("a font built after the install does not start from the typeface")
    if not (_theme.FONT_DIR / "LICENSE.txt").is_file():
        raise SmokeFailure("the typeface ships without its licence")
    ok.append(f"{_theme.TYPEFACE} is bundled with its licence and is the app's font")

    # One icon set: every icon the app draws is a Lucide file, and the arrow,
    # check and glass images come from it in the color asked for.
    from ui import icons as _icons

    for _name in (
        "search",
        "plus",
        "refresh-cw",
        "settings",
        "x",
        "check",
        "chevron-down",
        "chevron-up",
        "chevron-left",
        "chevron-right",
    ):
        if 'class="lucide lucide-' + _name + '"' not in _icons._svg(_name):
            raise SmokeFailure(f"the {_name} icon is not Lucide's")
    for _path in (
        _theme.chevron_image("#123456"),
        _theme.chevron_image("#123456", "up"),
        _theme.check_image("#123456"),
    ):
        if (
            not _path
            or "lucide_" not in _path
            or not Path(_path.replace(".png", "@2x.png")).is_file()
        ):
            raise SmokeFailure(
                f"a style sheet image is not drawn from Lucide at both densities: {_path}"
            )
    from ui.results_table import magnifier_icon as _glass

    if _glass("#123456").isNull():
        raise SmokeFailure("the search glass draws nothing")
    ok.append("every icon is Lucide's, the style sheet's arrows and check included")

    from PySide6.QtGui import QColor, QPixmap
    from ui.attachments import AttachmentBar, ImagePreviewDialog

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE attachment(id INTEGER PRIMARY KEY, task_id INT, "
        "filename TEXT, original_name TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO attachment(task_id,filename,original_name,created_at) "
        "VALUES (7,'missing.png','missing.png','x')"
    )
    conn.commit()
    bar = AttachmentBar(conn)
    bar.set_task(7)  # _refresh over a file that isn't on disk (placeholder path)
    ok.append("AttachmentBar refresh (missing-file placeholder)")

    # A removal asks first, and a declined question removes nothing. The
    # question is a modal, so the answer is supplied rather than clicked.
    import ui.attachments as _attachments
    from PySide6.QtWidgets import QPushButton as _QPushButton

    def _remove_button(widget):
        for button in widget.findChildren(_QPushButton):
            if button.objectName() == "quietIcon":
                return button
        raise SmokeFailure("the attachment row has no remove button")

    _asked: list[str] = []
    _said = [False]
    _real_confirm = _attachments.confirm

    def _answer(parent, title, body, *args, **kwargs):
        _asked.append(f"{title} {body}")
        return _said[0]

    _attachments.confirm = _answer
    try:
        _remove_button(bar).click()
        if not _asked:
            raise SmokeFailure("removing an attachment asked nothing")
        if "missing.png" not in _asked[-1]:
            raise SmokeFailure(f"the question does not name the attachment: {_asked[-1]!r}")
        if not conn.execute("SELECT COUNT(*) FROM attachment").fetchone()[0]:
            raise SmokeFailure("a declined question removed the attachment")
        _said[0] = True
        _remove_button(bar).click()
        if conn.execute("SELECT COUNT(*) FROM attachment").fetchone()[0]:
            raise SmokeFailure("an accepted question left the attachment")
    finally:
        _attachments.confirm = _real_confirm
    ok.append("an attachment's ✕ asks by name, and removes only on an accept")

    ImagePreviewDialog(Path("/does/not/exist.png"), "missing.png")
    tmp = Path(tempfile.gettempdir()) / "smoke_real.png"
    pm = QPixmap(320, 200)
    pm.fill(QColor("steelblue"))
    pm.save(str(tmp))
    dlg = ImagePreviewDialog(tmp, "smoke_real.png")
    if dlg.deleted():
        raise SmokeFailure("fresh ImagePreviewDialog should not report deleted()")
    ok.append("ImagePreviewDialog builds (missing + real image)")

    # The appearance manager, before anything paints. An incomplete scheme is a
    # KeyError in the middle of a paint, so it is named here instead.
    import ui.theme as theme

    gaps = theme.check_schemes()
    if gaps:
        raise SmokeFailure("incomplete colour scheme — " + "; ".join(gaps))
    ok.append(f"all {len(theme.SCHEMES)} colour schemes carry the same keys")

    # Every shipped scheme clears the readable ratio on every pair the builder
    # checks, so a palette that does not is the user's rather than this build's.
    for name, palette in theme.SCHEMES.items():
        unreadable = theme.contrast_complaints(palette)
        if unreadable:
            raise SmokeFailure(f"shipped scheme {name!r} — " + "; ".join(unreadable))
    ok.append("every shipped scheme clears the contrast floor on every text pair and state mark")

    # Every key a palette defines gets a field, and every field a caption.
    placed = [key for _heading, keys in theme.palette_rows() for key in keys]
    if sorted(placed) != sorted(theme.REFERENCE_PALETTE):
        raise SmokeFailure("a palette form does not offer one field per colour")
    if len(placed) != len(set(placed)):
        raise SmokeFailure("a palette form offers a colour twice")
    uncaptioned = [key for key in placed if key not in theme.KEY_CAPTIONS]
    if uncaptioned:
        raise SmokeFailure("no caption for " + ", ".join(uncaptioned))
    ok.append(f"a palette form offers all {len(placed)} colours, each captioned")

    # The contrast reader, against the two ends of the scale and a palette built
    # to fail one named pair.
    if round(theme.contrast_ratio("#ffffff", "#000000"), 1) != 21.0:
        raise SmokeFailure("black on white does not read as 21:1")
    if round(theme.contrast_ratio("#808080", "#808080"), 1) != 1.0:
        raise SmokeFailure("a colour on itself does not read as 1:1")
    if theme.contrast_ratio("#80ffffff", "#000000") != theme.contrast_ratio("#ffffff", "#000000"):
        raise SmokeFailure("an alpha channel changed a contrast reading")
    washed = dict(theme.REFERENCE_PALETTE)
    washed["INK_SOFT"] = washed["CANVAS"]
    named = theme.contrast_complaints(washed)
    if not any("Secondary Text" in line and "Window Background" in line for line in named):
        raise SmokeFailure("a failing pair is not named by contrast_complaints")
    if any("Unclickable" in line for line in theme.contrast_complaints(washed)):
        raise SmokeFailure("the deliberately grey pair is being checked")
    faint = dict(theme.REFERENCE_PALETTE)
    faint["BTN_BORDER"] = faint["CANVAS"]
    if not any(
        "Interactive Edge" in line and "under 3:1" in line
        for line in theme.contrast_complaints(faint)
    ):
        raise SmokeFailure("an edge under 3:1 is not named by contrast_complaints")
    ok.append("the contrast reader names the pair that fails, by its caption")

    # The collection: what this build ships, plus the differences an
    # installation carries. A theme nobody has touched is in no stored key,
    # which is what lets the themes a later release ships reach an installation
    # already in use.
    shipped = theme.shipped_collection()
    collection = theme.register_collection(None, None)
    if set(collection) != set(shipped):
        raise SmokeFailure("an untouched installation does not get every shipped theme")
    if any(collection[name] != shipped[name] for name in shipped):
        raise SmokeFailure("an untouched installation alters a shipped theme")
    if theme.collection_differences(collection):
        raise SmokeFailure("an untouched collection stores a difference")
    names = [record["name"] for record in collection.values()]
    if names != sorted(names, key=str.casefold):
        raise SmokeFailure("the collection is not ordered by name")
    used = theme.resolve_collection({"edited": {theme.DEFAULT_THEME: {"name": "Mine"}}})
    if set(used) != set(shipped):
        raise SmokeFailure("a configuration in use does not receive a shipped theme")
    if used[theme.DEFAULT_THEME]["name"] != "Mine":
        raise SmokeFailure("a stored rename did not reach the collection")
    ok.append(
        f"the collection resolves all {len(collection)} shipped themes and stores only what differs"
    )

    # A palette built when the picker offered one Custom option is an ordinary
    # theme in the collection, deletable like any other.
    if any(value == theme.LEGACY_CUSTOM_THEME for value, _caption in theme.THEME_CHOICES):
        raise SmokeFailure("the Theme picker still offers a Custom entry")
    migrated = theme.resolve_collection(None, {"INK": "#101010"})
    record = migrated.get(theme.LEGACY_CUSTOM_THEME)
    if record is None or record["light"]["INK"] != "#101010" or record["dark"] is not None:
        raise SmokeFailure("a palette from the one Custom option did not migrate")
    theme.install_collection(migrated)
    if theme.appearance_choice(None, None, theme.LEGACY_CUSTOM_THEME) != (
        theme.LEGACY_CUSTOM_THEME,
        theme.LIGHT_MODE,
    ):
        raise SmokeFailure("a stored Custom choice does not name the migrated theme")
    if theme.LEGACY_CUSTOM_THEME in theme.resolve_collection(
        {"deleted": [theme.LEGACY_CUSTOM_THEME]}, {"INK": "#101010"}
    ):
        raise SmokeFailure("the migrated Custom theme cannot be deleted")
    collection = theme.register_collection(None, None)
    ok.append("a palette from the one Custom option becomes a theme like any other")

    # The manage-themes window, driven by its own methods: a theme added,
    # renamed, edited and deleted, a shipped theme's edit living only in the
    # configuration, a restore putting the shipped values back, and the last
    # theme refusing to go.
    from PySide6.QtWidgets import QDialog
    from ui.theme_manager import ThemeManagerDialog

    manager = ThemeManagerDialog(collection, theme.DEFAULT_THEME)
    if manager.form.rows["INK"].value() != collection[theme.DEFAULT_THEME]["light"]["INK"]:
        raise SmokeFailure("manage themes did not open on the theme in force")
    added = manager.add("Test Theme")
    if manager.themes()[added]["light"] != collection[theme.DEFAULT_THEME]["light"]:
        raise SmokeFailure("a theme added is not seeded from the theme in hand")
    manager.rename("Test Theme Renamed")
    if manager.themes()[added]["name"] != "Test Theme Renamed":
        raise SmokeFailure("a theme renamed did not take the name")
    if manager.selected() != added or added not in manager.themes():
        raise SmokeFailure("a rename moved the theme it renamed")
    # A theme added takes its id from the name it is saved under, so the
    # configuration reads as the list it contains.
    named = ThemeManagerDialog(collection, theme.DEFAULT_THEME)
    fresh = named.add()
    named.rename("Sea Glass")
    named.accept()
    if "sea_glass" not in named.themes():
        raise SmokeFailure("a theme added is not stored under its own name")
    if fresh in named.themes() and fresh != "sea_glass":
        raise SmokeFailure("a theme added is stored under its placeholder too")
    if named.selected() != "sea_glass":
        raise SmokeFailure("renaming a fresh theme lost the selection")
    manager.rename(collection[theme.DEFAULT_THEME]["name"])
    if not manager.name_problem():
        raise SmokeFailure("a name already in the list is not refused")
    manager.rename("")
    if manager.name_problem() or manager.name.property("fieldMissing"):
        raise SmokeFailure("an empty name is marked before any save was tried")
    manager.accept()
    if manager.result() == QDialog.DialogCode.Accepted:
        raise SmokeFailure("a save with an empty theme name closed the window")
    if not manager.name_problem() or not manager.name.property("fieldMissing"):
        raise SmokeFailure("an empty name is not refused once a save is tried")
    manager.rename("Test Theme Renamed")
    if manager.name_problem():
        raise SmokeFailure("a name in neither fault is refused")

    manager.select(theme.DEFAULT_THEME)
    manager.form.rows["INK"].set_value("#123456")
    stored = theme.collection_differences(manager.themes())
    if (
        stored.get("edited", {}).get(theme.DEFAULT_THEME, {}).get("light", {}).get("INK")
        != "#123456"
    ):
        raise SmokeFailure("an edit to a shipped theme is not stored as a difference")
    if added not in stored.get("added", {}):
        raise SmokeFailure("a theme added is not stored")
    if set(stored.get("edited", {})) != {theme.DEFAULT_THEME}:
        raise SmokeFailure("a theme nobody edited is stored as edited")
    if theme._SHIPPED_SCHEMES[theme.REFERENCE_SCHEME]["INK"] == "#123456":
        raise SmokeFailure("an edit reached what the build ships")
    if theme.shipped_collection()[theme.DEFAULT_THEME]["light"]["INK"] == "#123456":
        raise SmokeFailure("an edit reached the shipped collection")

    if not manager.delete():
        raise SmokeFailure("a theme refused to be deleted")
    if theme.DEFAULT_THEME in manager.themes():
        raise SmokeFailure("a theme deleted is still in the list")
    in_force = manager.theme_in_force()
    if in_force == theme.DEFAULT_THEME or in_force not in manager.themes():
        raise SmokeFailure("deleting the theme in force left the app on it")

    manager.restore_shipped()
    after = manager.themes()
    if after.get(theme.DEFAULT_THEME, {}).get("light") != shipped[theme.DEFAULT_THEME]["light"]:
        raise SmokeFailure("Restore Shipped Themes did not put the shipped values back")
    if added not in after:
        raise SmokeFailure("Restore Shipped Themes removed a theme the user added")
    restored = theme.collection_differences(after)
    if restored.get("edited") or restored.get("deleted"):
        raise SmokeFailure("a restored collection still stores a shipped difference")

    solo_id = theme.DEFAULT_THEME
    solo = ThemeManagerDialog({solo_id: shipped[solo_id]}, solo_id)
    if solo.delete():
        raise SmokeFailure("the last theme was deleted")
    if solo_id not in solo.themes():
        raise SmokeFailure("the last theme left the list")
    if "The last theme cannot be deleted." not in solo.complaints():
        raise SmokeFailure("the last theme's refusal is not said out loud")
    ok.append("manage themes adds, renames, edits, deletes and restores, and keeps the last theme")

    # The dark half: turned on whole, edited as its own set of rows, stored and
    # resolved back, and removed without leaving the theme half-lit.
    halves = ThemeManagerDialog(collection, theme.DEFAULT_THEME)
    seeded_from = collection[theme.DEFAULT_THEME]
    half_id = halves.add("Half Test")
    if not halves.remove_dark_half():
        raise SmokeFailure("a theme with a dark half refused to drop it")
    if halves.has_dark() or halves.showing() != theme.LIGHT_MODE:
        raise SmokeFailure("a dark half removed is still on the theme")
    if halves.set_half(theme.DARK_MODE):
        raise SmokeFailure("a light-only theme showed a dark half")
    if halves.form.rows["CANVAS"].value() != seeded_from["light"]["CANVAS"]:
        raise SmokeFailure("a light-only theme does not show its light half")
    if not halves.add_dark_half():
        raise SmokeFailure("a light-only theme refused a dark half")
    if halves.showing() != theme.DARK_MODE:
        raise SmokeFailure("a dark half turned on is not the half on screen")
    dark = halves.themes()[half_id]["dark"]
    if sorted(dark) != sorted(theme.REFERENCE_PALETTE):
        raise SmokeFailure("a dark half was seeded short of a colour")
    if [key for key, value in dark.items() if not str(value).strip()]:
        raise SmokeFailure("a dark half was seeded with a colour left empty")
    if dark != theme.REFERENCE_DARK_PALETTE:
        raise SmokeFailure("a dark half was seeded from something not dark")
    if halves.form.rows["CANVAS"].value() != theme.REFERENCE_DARK_PALETTE["CANVAS"]:
        raise SmokeFailure("the rows do not show the half that is on screen")
    if halves.form.complaints():
        raise SmokeFailure("a dark half seeded whole opens a form that complains")
    # The dark half's own canvas as its own text colour: unreadable against the
    # half it belongs to, and perfectly readable against the light one, so a
    # notice reading the wrong half says nothing here.
    halves.form.rows["INK"].set_value(theme.REFERENCE_DARK_PALETTE["CANVAS"])
    if not any("Primary Text" in line for line in halves.form.unreadable()):
        raise SmokeFailure("the dark half is not read against itself")
    if "Primary Text" not in halves.notice.text():
        raise SmokeFailure("the notice does not carry the dark half's failure")
    halves.form.rows["INK"].set_value("#fedcba")
    if not halves.set_half(theme.LIGHT_MODE):
        raise SmokeFailure("a theme with both halves refused its light one")
    both = halves.themes()[half_id]
    if both["dark"]["INK"] != "#fedcba":
        raise SmokeFailure("an edit to the dark half did not stay on it")
    if both["light"]["INK"] == "#fedcba":
        raise SmokeFailure("an edit to the dark half reached the light one")
    if halves.form.rows["CANVAS"].value() != seeded_from["light"]["CANVAS"]:
        raise SmokeFailure("the light half did not come back to the rows")
    # A half stored is a half resolved: what the configuration carries comes
    # back as the same palette rather than as one completed from the light.
    kept = theme.resolve_collection(theme.collection_differences(halves.themes()))
    if kept[half_id]["dark"] != both["dark"]:
        raise SmokeFailure("a dark half stored does not resolve back whole")
    theme.install_collection(halves.themes())
    if not theme.theme_has_dark(half_id):
        raise SmokeFailure("a theme given a dark half reports none")
    if theme.resolve_scheme(half_id, theme.DARK_MODE, False) != f"{half_id}_dark":
        raise SmokeFailure("a theme with a dark half does not draw it in Dark")
    if not halves.remove_dark_half():
        raise SmokeFailure("a dark half edited refused to be removed")
    if halves.themes()[half_id]["dark"] is not None:
        raise SmokeFailure("a dark half removed is still stored")
    if theme.collection_differences(halves.themes())["added"][half_id]["dark"]:
        raise SmokeFailure("a theme stores a dark half it no longer has")
    theme.install_collection(halves.themes())
    if theme.theme_has_dark(half_id):
        raise SmokeFailure("a theme reports a dark half it no longer has")
    for mode in (theme.DARK_MODE, theme.SYSTEM_MODE):
        for os_dark in (False, True):
            if theme.resolve_scheme(half_id, mode, os_dark) != f"{half_id}_light":
                raise SmokeFailure(
                    f"a stored mode of {mode!r} did not fall back to Light "
                    "when the half it named was gone"
                )
    collection = theme.register_collection(None, None)
    ok.append(
        "a dark half is seeded whole, edited on its own, stored and "
        "resolved back, and removed without leaving a half-lit theme"
    )

    # The palette form under it: a value that is not a colour never reaches a
    # palette, and what fails is named rather than silently saved.
    cool = collection["cool"]
    form_check = ThemeManagerDialog(collection, "cool")
    if form_check.form.rows["INK"].value() != cool["light"]["INK"]:
        raise SmokeFailure("the palette form did not seed from the theme selected")
    if sorted(form_check.form.palette()) != sorted(theme.REFERENCE_PALETTE):
        raise SmokeFailure("the palette form hands back an incomplete palette")
    if form_check.form.complaints():
        raise SmokeFailure("a shipped palette seeds a form that complains")
    form_check.form.rows["INK_SOFT"].set_value("not a colour")
    if form_check.form.rows["INK_SOFT"].valid():
        raise SmokeFailure("the palette form accepts a value that is not a colour")
    if "INK_SOFT" in form_check.form.palette():
        raise SmokeFailure("a value that is not a colour reaches the palette")
    if "Secondary Text" not in form_check.notice.text():
        raise SmokeFailure("the field that cannot be read is not named")
    form_check.form.rows["INK_SOFT"].set_value(cool["light"]["CANVAS"])
    if not any("Secondary Text" in line for line in form_check.form.unreadable()):
        raise SmokeFailure("a pair that fails contrast is not named")
    if "Secondary Text" not in form_check.notice.text():
        raise SmokeFailure("the notice does not carry the failure")
    form_check.form.rows["CANVAS"].set_value("#000000")
    if theme.readable_on("#000000") != "#ffffff" or theme.readable_on("#ffffff") != "#000000":
        raise SmokeFailure("readable_on does not turn with the ground under it")
    if "#ffffff" not in form_check.notice.styleSheet():
        raise SmokeFailure("the notice is not drawn to stay readable on the canvas")
    ok.append("the palette form seeds, validates and names what fails")

    theme.register_collection(None, None)
    theme.set_scheme(theme.resolve_scheme(theme.DEFAULT_THEME, theme.DEFAULT_MODE, False))

    # Every theme against every mode, in both OS states: each pair names a
    # complete scheme that goes live and renders a sheet.
    for value, _caption in theme.theme_choices(collection):
        for mode, _mode_caption in theme.MODE_CHOICES:
            for dark in (False, True):
                name = theme.resolve_scheme(value, mode, dark)
                if name not in theme.SCHEMES:
                    raise SmokeFailure(f"theme {value!r} in {mode!r} resolves to no scheme")
                theme.set_scheme(name)
                if theme.current_scheme() != name or not theme.build_style_sheet():
                    raise SmokeFailure(f"scheme {name!r} does not become live")
    if (
        theme.resolve_scheme("a_theme_from_a_newer_build", theme.LIGHT_MODE, False)
        != theme.THEMES[theme.DEFAULT_THEME][0]
    ):
        raise SmokeFailure("an unrecognised theme name does not fall back")
    ok.append("every theme and mode pair resolves, applies and renders a stylesheet")

    # Every popup list is drawn one way: a menu takes the picker's open list's
    # corner and pad, and its options the picker's options' height, pad and corner.
    sheet = theme.build_style_sheet()

    def _rule(selector: str) -> dict[str, str]:
        found = re.search(r"(?m)^" + re.escape(selector) + r" \{\{?\s*([^}]*)\}", sheet)
        if not found:
            raise SmokeFailure(f"the style sheet has no {selector} rule")
        return {
            k.strip(): v.strip()
            for k, _, v in (d.partition(":") for d in found.group(1).split(";"))
            if v.strip()
        }

    popup_keys = ("border-radius", "padding")
    option_keys = ("min-height", "padding", "border-radius")
    combo, menu = _rule("QComboBox QAbstractItemView"), _rule("QMenu")
    combo_item, menu_item = _rule("QComboBox QAbstractItemView::item"), _rule("QMenu::item")
    for keys, a, b, what in (
        (popup_keys, combo, menu, "list"),
        (option_keys, combo_item, menu_item, "option"),
    ):
        differ = [k for k in keys if a.get(k) != b.get(k)]
        if differ:
            raise SmokeFailure(f"a menu's {what} departs from a picker's on {', '.join(differ)}")
    ok.append("a menu is drawn as a picker's open list, its options as the picker's")

    # A collection that has lost the default still has a fallback, so deleting
    # Pumpkin is an ordinary deletion rather than the one that breaks the app.
    without_default = theme.resolve_collection({"deleted": [theme.DEFAULT_THEME]})
    theme.install_collection(without_default)
    if theme.default_theme() not in theme.THEMES:
        raise SmokeFailure("a collection without the default has no fallback")
    theme.set_scheme("a_scheme_that_is_gone")
    if theme.current_scheme() not in theme.SCHEMES or not theme.build_style_sheet():
        raise SmokeFailure("a scheme that is gone does not fall back to a live one")
    if theme.check_schemes():
        raise SmokeFailure("a collection without the default is incomplete")
    collection = theme.register_collection(None, None)
    ok.append("a collection that has lost the default theme still resolves and draws")

    # A theme with no dark half is an ordinary theme: it offers Light alone and
    # draws its light palette whatever the mode and the OS say.
    light_only = "dark_half_none"
    theme.THEMES[light_only] = (theme.REFERENCE_SCHEME, None)
    try:
        if theme.theme_has_dark(light_only):
            raise SmokeFailure("a theme with no dark member reports one")
        if not theme.theme_has_dark(theme.DEFAULT_THEME):
            raise SmokeFailure("a theme with both halves reports no dark member")
        for mode, _caption in theme.MODE_CHOICES:
            for dark in (False, True):
                if theme.resolve_scheme(light_only, mode, dark) != theme.REFERENCE_SCHEME:
                    raise SmokeFailure(f"a theme with no dark half went dark in {mode!r}")
    finally:
        theme.THEMES.pop(light_only, None)
    ok.append("a theme with no dark half refuses Dark and Follow System")

    # Every value the one older key could contain comes up as the appearance it
    # named, and the two current keys win wherever they say anything.
    theme.install_collection(theme.resolve_collection(None, {"INK": "#101010"}))
    for legacy, expected in theme.LEGACY_APPEARANCE.items():
        if theme.appearance_choice(None, None, legacy) != expected:
            raise SmokeFailure(f"stored appearance {legacy!r} did not migrate")
    if theme.appearance_choice("cool", theme.DARK_MODE, "warm_light") != ("cool", theme.DARK_MODE):
        raise SmokeFailure("a stored theme and mode lost to the older key")
    if theme.appearance_choice(None, None, "a_scheme_from_a_newer_build") != (
        theme.DEFAULT_THEME,
        theme.DEFAULT_MODE,
    ):
        raise SmokeFailure("an unreadable stored appearance does not default")
    if theme.appearance_choice("warm", "sideways", None) != ("warm", theme.DEFAULT_MODE):
        raise SmokeFailure("an unreadable stored mode does not default")
    if theme.appearance_choice("a_theme_that_was_deleted", theme.DARK_MODE, None) != (
        theme.DEFAULT_THEME,
        theme.DEFAULT_MODE,
    ):
        raise SmokeFailure("a stored choice naming a deleted theme does not default")
    ok.append(
        f"all {len(theme.LEGACY_APPEARANCE)} older appearance values "
        "migrate to the appearance they named"
    )

    theme.register_collection(None, None)
    theme.set_scheme(theme.resolve_scheme(theme.DEFAULT_THEME, theme.DEFAULT_MODE, False))

    for scale in (theme.SPACE, theme.RADIUS, theme.TYPE):
        if not all(isinstance(step, int) and step > 0 for step in scale.values()):
            raise SmokeFailure("a token scale contains something that is not a size")
    ok.append("the spacing, radius and type scales are whole sizes")

    # Every question and every notice comes from ui/dialogs.py, so no module
    # in the package names QMessageBox.
    import ui.dialogs as dialogs

    strays = sorted(
        source.name
        for source in Path(ui.__path__[0]).glob("*.py")
        if "QMessageBox" in source.read_text(encoding="utf-8")
    )
    if strays:
        raise SmokeFailure(
            "QMessageBox reached " + ", ".join(strays) + " — confirmations come from ui/dialogs.py"
        )
    box = dialogs.Modal(
        None,
        "Title",
        "Body",
        [("Cancel", dialogs.ORDINARY, False), ("Delete", dialogs.DESTRUCTIVE, True)],
    )
    if box.choice() is not False:
        raise SmokeFailure("a closed confirmation does not land on the way out")
    ok.append("every confirmation and notice comes from ui/dialogs.py")

    # The card painter reads tokens rather than containing literals, so a change to
    # a scale must reach it with no edit there.
    from ui.card_delegate import CardDelegate

    delegate = CardDelegate()
    before = (delegate.PAD, delegate.GAP, delegate.MARGIN)
    theme.SPACE["lg"] += 5
    try:
        if delegate.PAD == before[0]:
            raise SmokeFailure("the card painter does not read the spacing scale")
    finally:
        theme.SPACE["lg"] -= 5
    if (delegate.PAD, delegate.GAP, delegate.MARGIN) != before:
        raise SmokeFailure("the card painter did not follow the scale back")
    ok.append("the card painter's geometry follows the token scales")

    # Paint a card under every scheme. A palette key the painter reads and a
    # scheme lacks surfaces here rather than on the user's board.
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtWidgets import QStyleOptionViewItem

    class _Cell:
        def __init__(self, payload):
            self._payload = payload

        def data(self, role):
            from ui.theme import CARD_ROLE

            return self._payload if role == CARD_ROLE else None

    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 260, 140)
    cell = _Cell(
        {
            "title": "A card",
            "tier": "max",
            "issue_id": 1,
            "record_type": "fix",
            "epic_name": "An epic",
            "owner": "user",
            "estimate": "M",
        }
    )
    for name in theme.SCHEMES:
        theme.set_scheme(name)
        pixmap = QPixmap(260, 140)
        painter = QPainter(pixmap)
        try:
            CardDelegate(show_checkbox=True).paint(painter, option, cell)
        finally:
            painter.end()
    theme.set_scheme(theme.resolve_scheme(theme.DEFAULT_THEME, theme.DEFAULT_MODE, False))
    ok.append("a card paints under every scheme")
    if CardDelegate(show_checkbox=True).CHECK_BOX != _theme.space("lg"):
        raise SmokeFailure("the Backlog's bulk-select box is not the Bristol Checkbox's SPACE lg")
    ok.append("the bulk-select box is the Bristol Checkbox's size")

    schema = TOOLS / "bristol" / "schema.sql"
    if schema.exists():
        from PySide6.QtCore import Qt
        from ui.main_window import MainWindow

        mconn = sqlite3.connect(":memory:")
        mconn.executescript(schema.read_text())

        def _seed(title, stage, status, sort_order, tier=None):
            mconn.execute(
                "INSERT INTO task (title, description, status, stage, sort_order, "
                "tier, record_type, assignee, reporter, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?, 'build','user','user','2026-07-08','2026-07-08')",
                (title, "d", status, stage, sort_order, tier),
            )
            return mconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        _seed("active todo", "active", "todo", 0, "max")
        b1 = _seed("backlog one", "backlog", "todo", 0, "standard")
        b2 = _seed("backlog two", "backlog", "todo", 1)
        _seed("archived", "archive", "done", 0)
        mconn.commit()

        win = MainWindow(mconn)
        if hasattr(win, "handoff_note_edit"):
            raise SmokeFailure("Handoff tab still present — it is retired")
        tab_names = {b.accessibleName() for b in win._tab_buttons}
        if "Handoff" in tab_names:
            raise SmokeFailure("Handoff tab still present — it is retired")
        if len(win._tab_buttons) != win.pages.count():
            raise SmokeFailure("a view exists with no tab, or a tab with no view")
        if sum(1 for b in win._tab_buttons if b.isChecked()) != 1:
            raise SmokeFailure("exactly one view tab is selected at a time")
        if mconn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='handoff'"
        ).fetchone():
            raise SmokeFailure("handoff table survived schema_guard")
        ok.append("MainWindow builds; Handoff tab and table are gone")

        # One Primary button per window: the Backlog bar's is Activate.
        _primary = [
            button.text()
            for button in (
                win.backlog_edit_btn,
                win.backlog_selall_btn,
                win.backlog_clear_btn,
                win.backlog_activate_btn,
                win.backlog_delete_btn,
            )
            if button.objectName() == "globalCreateBtn"
        ]
        if _primary != [win.backlog_activate_btn.text()]:
            raise SmokeFailure(
                f"the Backlog bar's Primary buttons are {_primary}, not Activate alone"
            )
        ok.append("the Backlog bar carries one Primary button, Activate")

        # A launch opens on the active work, and the tab row keeps its order.
        if win.pages.currentIndex() != win._board_tab_index:
            raise SmokeFailure("the window did not open on the Board view")
        selected = [b.accessibleName() for b in win._tab_buttons if b.isChecked()]
        if selected != ["Board"]:
            raise SmokeFailure(f"the Board tab is not the selected one: {selected}")
        if [b.accessibleName() for b in win._tab_buttons][0] != "Search":
            raise SmokeFailure("the tab row order changed to put Board first")
        ok.append("a launch opens on Board, with the tab row order unchanged")

        # Search and Archive are tables that sort by header, and the search
        # field follows the typing.
        if [
            win.search_results.horizontalHeaderItem(c).text()
            for c in range(win.search_results.columnCount())
        ] != ["Type", "#", "Title", "Status", "Closed"]:
            raise SmokeFailure("the Search results do not carry their headers")
        if not win.search_results.isSortingEnabled() or not win.archive_results.isSortingEnabled():
            raise SmokeFailure("a results table does not sort by its headers")
        win.search_input.setText("zz-no-card-says-this")
        win._search_settle.timeout.emit()
        if win.search_results.count() != 0:
            raise SmokeFailure("typing in the search field did not search")
        win.search_input.clear()
        win._execute_global_search()
        ok.append("Search and Archive are sortable tables, and Search follows the typing")

        # An assistive tool presses a tab by toggling it, which emits no click.
        archive_tab = win._tab_buttons[win._archive_tab_index]
        archive_tab.toggle()
        if win.pages.currentIndex() != win._archive_tab_index:
            raise SmokeFailure(
                "toggling a tab, as an accessibility press does, did not open its view"
            )
        archive_tab.toggle()
        if not archive_tab.isChecked() or sum(1 for b in win._tab_buttons if b.isChecked()) != 1:
            raise SmokeFailure("a second press switched the open tab off")
        win._show_page(win._board_tab_index)
        ok.append("a tab opens its view when toggled, and a second press leaves it open")

        # Kanban stage model: tabs populate from task.stage.
        win._refresh_board()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("Board To Do should show the one active/todo task")
        if win.backlog_column.list_widget.count() != 2:
            raise SmokeFailure("Backlog should show two backlog tasks")
        if win.archive_results.count() != 1:
            raise SmokeFailure("Archive should show one archived task")
        ok.append("Board/Backlog/Archive populate by stage")

        # A card another session closes leaves To Do without a Refresh.
        with tempfile.TemporaryDirectory() as watched_dir:
            watched_path = Path(watched_dir) / "watched.db"
            fconn = sqlite3.connect(watched_path)
            mconn.backup(fconn)
            watched = MainWindow(fconn)
            before = watched.columns["todo"].list_widget.count()
            other = sqlite3.connect(watched_path)
            other.execute("UPDATE task SET status='done' WHERE stage='active' AND status='todo'")
            other.commit()
            other.close()
            watched._reload_if_changed()
            after = watched.columns["todo"].list_widget.count()
            watched._board_watch.stop()
            watched.close()
            fconn.close()
        if (before, after) != (1, 0):
            raise SmokeFailure(
                f"a card closed by another connection stayed in To Do "
                f"({before} before, {after} after the poll)"
            )
        ok.append("a write from another connection reaches the Board on the next poll")

        # Where a control sits says what it reaches. The top bar is one band:
        # the views as a segmented control, then Create, the same on every
        # view, Refresh and Create at its right, and on the Mac it shares the title bar's
        # band at the title bar's height. The board's own control row narrows
        # the board and offers nothing else, since each kind of card leaves the
        # board on its own event; a column header carries no control at all,
        # which is what keeps the three names and counts on one line.
        import ui.theme as _theme
        from PySide6.QtCore import Qt as _Qt
        from PySide6.QtWidgets import QPushButton, QToolBar, QWidget

        if win.findChildren(QToolBar):
            raise SmokeFailure("a toolbar stands beside the top bar")
        header = win.centralWidget().layout().itemAt(0).widget()
        if header is None or header.objectName() != "appHeader":
            raise SmokeFailure("the top bar is not the window's first row")
        if (
            sys.platform == "darwin"
            and not win._header_in_title_bar
            and hasattr(_Qt.WindowType, "ExpandedClientAreaHint")
        ):
            raise SmokeFailure("the top bar is not in the title bar's band")
        from ui import mac_window as _mac_window

        if header.maximumHeight() > _mac_window.TALL_TITLE_BAR:
            raise SmokeFailure("the top bar is taller than a Mac's tall title bar")
        header_buttons = [b.text() or b.accessibleName() for b in header.findChildren(QPushButton)]
        views_named = {b.accessibleName() for b in win._tab_buttons}
        centre = header.findChild(QWidget, "viewTabs")
        at_centre = {b.accessibleName() for b in centre.findChildren(QPushButton)}
        if set(header_buttons) != views_named | {
            "Refresh",
            "Create",
            "Settings",
        } or at_centre != views_named - {"Search"}:
            raise SmokeFailure(
                f"the top bar should be the named views, then Search, Refresh, "
                f"Create and Settings, got "
                f"{header_buttons}"
            )
        if any(b.parent() is None or not header.isAncestorOf(b) for b in win._tab_buttons):
            raise SmokeFailure("a view segment sits outside the top bar")
        if views_named != {"Search", "Backlog", "Board", "Archive"}:
            raise SmokeFailure(
                f"the top bar's views should be Search, Backlog, "
                f"Board and Archive, got {sorted(views_named)}"
            )
        if header.findChild(QWidget, "headerDivider") is not None:
            raise SmokeFailure("a hairline still divides the top bar's views")
        # The top bar's Agent picker offers what Settings' Agent picker offers
        # and stands on the same agent.
        if not header.isAncestorOf(win.agent_picker):
            raise SmokeFailure("the Agent picker is not in the top bar")
        top_agents = [win.agent_picker.itemData(i) for i in range(win.agent_picker.count())]
        settings_picker = win.settings_tab.next_agent
        settings_agents = [settings_picker.itemData(i) for i in range(settings_picker.count())]
        if (
            top_agents != settings_agents
            or win.agent_picker.currentData() != settings_picker.currentData()
        ):
            raise SmokeFailure("the top bar's Agent picker and Settings' disagree")
        for b in win._tab_buttons + [win.refresh_btn, win.global_create_btn, win.settings_btn]:
            if b.text() and not b.icon().isNull():
                raise SmokeFailure(f"{b.accessibleName()} carries an icon beside its name")
            if not b.text() and b.icon().isNull():
                raise SmokeFailure(
                    f"{b.accessibleName() or 'a button'} in the "
                    f"top bar has neither a name nor an icon"
                )
            if not b.text() and b.toolTip():
                raise SmokeFailure(
                    f"{b.accessibleName()} carries hover text; "
                    f"the top bar's icons explain themselves"
                )
        filter_row = win.pages.widget(win._board_tab_index).layout().itemAt(0).widget()
        if filter_row is not win.filter_row:
            raise SmokeFailure("the board does not open on its filter row")
        board_buttons = [b.text() for b in filter_row.findChildren(QPushButton)]
        if any("Done" in text for text in board_buttons):
            raise SmokeFailure(f"the board offers a sweep button: {board_buttons}")
        if board_buttons != ["Clear"]:
            raise SmokeFailure(
                f"an unfiltered board's filter row is its Clear alone, got {board_buttons}"
            )
        if not filter_row.isHidden():
            raise SmokeFailure("an unfiltered board shows an empty filter row")
        last_column = list(win.columns)[-1]
        for key, column in win.columns.items():
            controls = column.findChildren(QPushButton)
            expected = [win.filter_btn] if key == last_column else []
            if controls != expected:
                raise SmokeFailure(
                    f"the {key} column header should carry "
                    f"{'Filter alone' if expected else 'no control'}"
                )
        for page_index in range(win.pages.count()):
            win._show_page(page_index)
            if (
                win.global_create_btn.isHidden()
                or win.refresh_btn.isHidden()
                or not header.isAncestorOf(win.global_create_btn)
            ):
                raise SmokeFailure("Refresh or Create left the top bar on a view")
            if not win.global_create_btn.isEnabled():
                raise SmokeFailure("Create is greyed on a view of cards")
        win._show_page(win._board_tab_index)
        ok.append(
            "one top bar: Search, Backlog, Board and Archive as "
            "segments with no divider, then Refresh, Create and Settings; "
            "Filter on the last column's header line and no control on "
            "any other; the filter row hidden while nothing is set"
        )

        # ---- What the board is showing ------------------------------------
        # One filter state narrows the board, the Backlog and the Archive and
        # leaves Search alone; the control row says what it contains.
        import ui.filter_menu as fm

        mconn.execute("INSERT INTO epic (name, status) VALUES ('An epic', 'in progress')")
        live_epic = mconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        mconn.execute("INSERT INTO epic (name, status) VALUES ('A closed epic', 'completed')")
        theirs = _seed("theirs", "active", "todo", 1)
        mconn.execute(
            "UPDATE task SET assignee='librarian', epic_id=? WHERE id=?", (live_epic, theirs)
        )
        mconn.commit()
        win._refresh_board()
        if win.columns["todo"].list_widget.count() != 2:
            raise SmokeFailure("an unfiltered board should contain every active card")

        owners = [value for value, _caption in fm.assignee_options(mconn, win.filters)]
        if owners[0] != "user" or "librarian" not in owners:
            raise SmokeFailure("the assignee facet does not offer the board's owners")
        offered = [value for value, _caption in fm.epic_options(mconn, win.filters)]
        if live_epic not in offered or None not in offered:
            raise SmokeFailure("the epic facet offers neither the epic nor the cards without one")
        if len(offered) != 2:
            raise SmokeFailure("the epic facet offers a finished epic")

        win.filters.toggle(fm.ASSIGNEE, "librarian")
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("an assignee filter did not narrow the board")
        if win.backlog_column.list_widget.count() != 0:
            raise SmokeFailure("an assignee filter did not reach the Backlog")
        if win.archive_results.count() != 0:
            raise SmokeFailure("an assignee filter did not reach the Archive")
        if win.search_results.count() == 0:
            raise SmokeFailure("a filter reached Search, which must find anything")
        if win.filter_btn.text() != "Filter · 1" or win.filter_btn.property("active") != "true":
            raise SmokeFailure("the Filter button does not carry what is set")
        if win.filter_clear_btn.isHidden() or win.filter_row.isHidden():
            raise SmokeFailure("no Clear stands beside a filter that is set")
        if win.chip_row.count() != 1:
            raise SmokeFailure("a set filter is not on the control row as a chip")
        if win.backlog_filter_note.isHidden() or win.archive_filter_note.isHidden():
            raise SmokeFailure("a view leaving cards out does not say so")

        win.filters.toggle(fm.ASSIGNEE, "user")
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 2:
            raise SmokeFailure("two options in one section should unite, not intersect")

        win.filters.toggle(fm.EPIC, live_epic)
        win._on_filters_changed()
        if win.columns["todo"].list_widget.count() != 1:
            raise SmokeFailure("two sections should intersect")
        if win.filters.sole_epic() != live_epic:
            raise SmokeFailure("one epic filter does not name a new card's epic")
        if (
            fm.option_count(mconn, win.filters, fm.ASSIGNEE, "user") != 0
            or fm.option_count(mconn, win.filters, fm.ASSIGNEE, "librarian") != 1
        ):
            raise SmokeFailure("a count ignores what the other section holds")
        win.filters.toggle(fm.EPIC, None)
        if win.filters.sole_epic() is not None:
            raise SmokeFailure("two epic options still named a default epic")
        win.filters.toggle(fm.EPIC, None)

        if len(fm.applied(mconn, win.filters)) != 3:
            raise SmokeFailure("the chips do not stand for every filter set")
        win._remove_filter(fm.EPIC, live_epic)
        if win.filters.holds(fm.EPIC, live_epic):
            raise SmokeFailure("removing a chip did not remove its filter")
        win._clear_filters()
        if win.filters.any_set() or win.chip_row.count():
            raise SmokeFailure("Clear left a filter behind")
        if not win.filter_row.isHidden():
            raise SmokeFailure("the filter row stays after Clear")
        if win.filter_btn.text() != "Filter" or win.filter_btn.property("active") != "false":
            raise SmokeFailure("the Filter button still reads as set")
        if not win.backlog_filter_note.isHidden() or not win.archive_filter_note.isHidden():
            raise SmokeFailure("a view still says it is leaving cards out")

        # The panel builds a row per option, and a click anywhere on a row is a
        # click on its box.
        panel = fm.FilterMenu(win, mconn, win.filters)
        panel._build()
        rows = {(kind, value) for kind, value, _row in panel._rows}
        if (fm.ASSIGNEE, "librarian") not in rows or (fm.EPIC, live_epic) not in rows:
            raise SmokeFailure("the filter panel does not build a row per option")
        moved: list[int] = []
        panel.changed.connect(lambda: moved.append(1))
        row = next(r for k, v, r in panel._rows if (k, v) == (fm.ASSIGNEE, "librarian"))
        row.mousePressEvent(None)
        if not win.filters.holds(fm.ASSIGNEE, "librarian") or not moved:
            raise SmokeFailure("a click on a row did not set the filter and report it")
        panel._clear()
        if win.filters.any_set():
            raise SmokeFailure("Clear all left a filter behind")

        win._on_filters_changed()
        mconn.execute("DELETE FROM task WHERE id=?", (theirs,))
        mconn.commit()
        win._refresh_board()
        ok.append(
            "Filter: facets, conditional counts, union within a section, "
            "intersection across them, chips and Clear"
        )

        win.backlog_column._reorder_within([b2], 0)
        first = mconn.execute(
            "SELECT id FROM task WHERE stage='backlog' ORDER BY sort_order"
        ).fetchone()[0]
        if first != b2:
            raise SmokeFailure("backlog drag-reorder did not persist sort_order")
        ok.append("Backlog drag-reorder persists")

        lw = win.backlog_column.list_widget
        for i in range(lw.count()):
            if lw.item(i).data(Qt.ItemDataRole.UserRole) == b1:
                lw.item(i).setData(Qt.ItemDataRole.CheckStateRole, Qt.CheckState.Checked)
        win._bulk_activate_backlog()
        st = mconn.execute("SELECT stage, status FROM task WHERE id=?", (b1,)).fetchone()
        if tuple(st) != ("active", "todo"):
            raise SmokeFailure("Backlog Activate did not move the card to the active board")
        ok.append("Backlog Activate → Board")

        # Finishing a standing card archives it there and then, and a project
        # card stays in Done until its epic closes. The report is an epic's, so
        # nothing here writes one; what is guarded is which card leaves the
        # board on being finished and which one waits.
        import finishing

        mconn.execute(
            "INSERT INTO epic (name, type, status) "
            "VALUES ('Standing work','standing','in progress')"
        )
        standing_epic = mconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        mconn.execute("UPDATE task SET epic_id=?, status='done' WHERE id=?", (standing_epic, b1))
        finishing.finish(mconn, b1)
        project_card = _seed("a project card", "active", "todo", 2)
        mconn.execute(
            "UPDATE task SET epic_id=?, status='done' WHERE id=?", (live_epic, project_card)
        )
        finishing.finish(mconn, project_card)
        loose = _seed("nobody's card", "active", "todo", 3)
        mconn.execute("UPDATE task SET status='done' WHERE id=?", (loose,))
        finishing.finish(mconn, loose)
        mconn.commit()

        if mconn.execute("SELECT stage FROM task WHERE id=?", (b1,)).fetchone()[0] != "archive":
            raise SmokeFailure("a finished standing card stayed on the board")
        if (
            mconn.execute("SELECT stage FROM task WHERE id=?", (project_card,)).fetchone()[0]
            != "active"
        ):
            raise SmokeFailure("a finished project card left before its epic closed")
        where, whose = mconn.execute(
            "SELECT stage, epic_id FROM task WHERE id=?", (loose,)
        ).fetchone()
        if whose != standing_epic or where != "archive":
            raise SmokeFailure(
                "a card finished under no epic should be attributed to the "
                "standing workstream and archived with it"
            )
        ok.append(
            "finishing archives a standing card, attributes one with no "
            "epic, and leaves a project card for its epic to close"
        )

        # Taken back out of done, an archived card returns to the board: the
        # archive is where finishing put it, so unfinishing has to undo it.
        mconn.execute("UPDATE task SET status='doing' WHERE id=?", (b1,))
        finishing.reopen(mconn, b1)
        mconn.commit()
        if mconn.execute("SELECT stage FROM task WHERE id=?", (b1,)).fetchone()[0] != "active":
            raise SmokeFailure("a reopened card did not come back to the board")
        ok.append("a card taken out of done returns to the active board")

        # A card nobody has placed carries a mark the others do not, in both
        # places a card is drawn. Standing work is a decision, so a card in the
        # standing workstream carries nothing.
        from ui.theme import CARD_ROLE as _CARD_ROLE

        triaged = _seed("in an epic", "active", "todo", 4)
        mconn.execute("UPDATE task SET epic_id=? WHERE id=?", (live_epic, triaged))
        upkeep = _seed("standing upkeep", "active", "todo", 5)
        mconn.execute("UPDATE task SET epic_id=? WHERE id=?", (standing_epic, upkeep))
        untriaged = _seed("nobody placed this", "active", "todo", 6)
        backlog_untriaged = _seed("nor this", "backlog", "todo", 7)
        mconn.commit()
        win._refresh_board()

        def _card_payload(column, task_id):
            lw = column.list_widget
            for i in range(lw.count()):
                if lw.item(i).data(Qt.ItemDataRole.UserRole) == task_id:
                    return lw.item(i)
            raise SmokeFailure(f"card #{task_id} is not in the column drawn")

        for column, task_id, expected in (
            (win.columns["todo"], triaged, False),
            (win.columns["todo"], upkeep, False),
            (win.columns["todo"], untriaged, True),
            (win.backlog_column, backlog_untriaged, True),
        ):
            item = _card_payload(column, task_id)
            if bool(item.data(_CARD_ROLE).get("untriaged")) != expected:
                raise SmokeFailure(
                    f"card #{task_id} should {'' if expected else 'not '}be "
                    "marked as having no epic"
                )
            says_so = "no epic yet" in (item.toolTip() or "")
            if says_so != expected:
                raise SmokeFailure(
                    f"card #{task_id}'s tooltip should {'' if expected else 'not '}name the choice"
                )
        ok.append(
            "a card with no epic is marked on the board and in the "
            "backlog, and standing work is not"
        )

        # The transition log must capture the moves the UI just made, since
        # cycle time and work-item age are computed from nothing else. Backlog
        # Activate and an archive on finishing are both *stage* transitions —
        # neither touches status — so `field='stage'` is the invariant to assert
        # here. Asserting `field='status'` was checking for events these paths
        # never produce.
        events = mconn.execute("SELECT COUNT(*) FROM task_event WHERE field='stage'").fetchone()[0]
        if not events:
            raise SmokeFailure("no task_event rows written by UI board moves")
        archived = mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE field='stage' AND to_value='archive'"
        ).fetchone()[0]
        if not archived:
            raise SmokeFailure("a card was archived without logging the transition")
        ok.append(f"transition log records stage moves ({events} events)")

        # Create-modal Stage follows the active view, and lands on the board
        # from anywhere that is neither the Backlog nor the Archive — the same
        # default ticket_write.py add-task carries.
        win._show_page(win._board_tab_index)
        if win._stage_for_current_tab() != "active":
            raise SmokeFailure("Create from Board should default Stage=active")
        win._show_page(win._archive_tab_index)
        if win._stage_for_current_tab() != "archive":
            raise SmokeFailure("Create from Archive should default Stage=archive")
        win._show_page(win._backlog_tab_index)
        if win._stage_for_current_tab() != "backlog":
            raise SmokeFailure("Create from Backlog should default Stage=backlog")
        win._show_page(0)  # Search
        if win._stage_for_current_tab() != "active":
            raise SmokeFailure(
                "Create away from the Backlog and Archive tabs should default Stage=active"
            )
        from ui.record_dialog import UnifiedRecordDialog as _RecordDialog

        if _RecordDialog(win, mconn, mode="task").stage_combo.currentData() != "active":
            raise SmokeFailure(
                "the Create dialog defaults a card to somewhere other than the board"
            )
        win._sync_backlog_bar()  # must not raise with nothing checked
        ok.append("Create-modal Stage follows active tab, and defaults to the board")

        # The detail pane edits in place: a status flipped from the pane takes
        # the same write path as a drag or a dialog save — the row moves and
        # the change-log triggers record it. Collapse must round-trip without
        # touching the configuration (save=False).
        pane = win.detail_pane
        pane.show_task(b2)
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("doing"))
        moved_status = mconn.execute("SELECT status FROM task WHERE id=?", (b2,)).fetchone()[0]
        if moved_status != "doing":
            raise SmokeFailure("a pane status edit did not reach the database")
        logged = mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE task_id=? AND field='status' "
            "AND to_value='doing'",
            (b2,),
        ).fetchone()[0]
        if not logged:
            raise SmokeFailure("a pane edit was not recorded by the change-log triggers")
        pane.tier_combo.setCurrentIndex(pane.tier_combo.findData("max"))
        if mconn.execute("SELECT tier FROM task WHERE id=?", (b2,)).fetchone()[0] != "max":
            raise SmokeFailure("a pane tier edit did not reach the database")
        if not mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE task_id=? AND field='tier' AND to_value='max'",
            (b2,),
        ).fetchone()[0]:
            raise SmokeFailure("a tier edit was not recorded by the change log")
        pane.show_task(b1)
        if pane.tier_combo.currentData() != "standard":
            raise SmokeFailure("the pane did not show the card's stored tier")
        ok.append("the pane shows a card's tier and writes it through the change log")

        # A board written before the tier existed opens without losing a card:
        # pressure is retired, tier arrives unrated, and every other value of
        # every card is where it was.
        from ui.schema_guard import ensure_schema_up_to_date

        legacy = sqlite3.connect(":memory:")
        legacy.executescript(
            "CREATE TABLE epic (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);"
            "CREATE TABLE task (id INTEGER PRIMARY KEY AUTOINCREMENT, epic_id "
            "INTEGER, scope_id INTEGER, title TEXT NOT NULL, description TEXT, "
            "status TEXT NOT NULL DEFAULT 'todo', pressure INTEGER NOT NULL "
            "DEFAULT 0, estimate TEXT, created_at TEXT, updated_at TEXT, "
            "closed_at TEXT);"
            "INSERT INTO task (title, description, status, pressure, estimate) "
            "VALUES ('kept', 'body', 'doing', 70, 'M'), ('also kept', NULL, "
            "'todo', 0, NULL);"
        )
        before = legacy.execute(
            "SELECT id, title, description, status, estimate FROM task ORDER BY id"
        ).fetchall()
        ensure_schema_up_to_date(legacy)
        ensure_schema_up_to_date(legacy)  # idempotent
        cols = [r[1] for r in legacy.execute("PRAGMA table_info(task)")]
        if "pressure" in cols or "tier" not in cols:
            raise SmokeFailure(f"a legacy board migrated to the wrong columns: {cols}")
        after = legacy.execute(
            "SELECT id, title, description, status, estimate FROM task ORDER BY id"
        ).fetchall()
        if after != before:
            raise SmokeFailure("migrating a legacy board changed a card")
        if legacy.execute("SELECT COUNT(*) FROM task WHERE tier IS NOT NULL").fetchone()[0]:
            raise SmokeFailure("a legacy card arrived with a tier nobody chose")
        legacy.close()
        ok.append("a board carrying pressure opens with every card intact and pressure retired")
        win._set_pane_collapsed(True, save=False)
        if not win.detail_pane.isHidden():
            raise SmokeFailure("collapsing did not hide the detail pane")
        if win.pane_reveal.isHidden():
            raise SmokeFailure("the reveal strip did not appear for a collapsed pane")
        win._set_pane_collapsed(False, save=False)
        if win.detail_pane.isHidden():
            raise SmokeFailure("expanding did not bring the detail pane back")
        ok.append("Detail pane edits write through the shared path; collapse round-trips")

        # A typed block reason: what KIND of thing stopped the card, never which
        # card. It writes from the pane like any other field, the change log
        # records it, and Done clears it — a finished card is not blocked.
        pane.show_task(b2)
        pane.block_combo.setCurrentIndex(pane.block_combo.findData("capability"))
        if (
            mconn.execute("SELECT block_reason FROM task WHERE id=?", (b2,)).fetchone()[0]
            != "capability"
        ):
            raise SmokeFailure("a pane block-reason edit did not reach the database")
        if not mconn.execute(
            "SELECT COUNT(*) FROM task_event WHERE task_id=? AND "
            "field='block_reason' AND to_value='capability'",
            (b2,),
        ).fetchone()[0]:
            raise SmokeFailure("a block reason was not recorded by the change-log triggers")
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("done"))
        if (
            mconn.execute("SELECT block_reason FROM task WHERE id=?", (b2,)).fetchone()[0]
            is not None
        ):
            raise SmokeFailure("a card moved to done kept its block reason")
        pane.status_combo.setCurrentIndex(pane.status_combo.findData("doing"))
        # The two vocabularies are separate copies on purpose — the viewer
        # depends on no package outside itself — so they are checked against
        # each other rather than trusted to stay in step.
        import importlib.util as _ilu

        _spec = _ilu.spec_from_file_location("_ct", TOOLS / "ticket_tools" / "create_tickets.py")
        _ct = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_ct)
        from ui.theme import BLOCK_REASON_CHOICES

        viewer_set = tuple(v for v, _ in BLOCK_REASON_CHOICES if v is not None)
        if viewer_set != tuple(_ct.BLOCK_REASONS):
            raise SmokeFailure(
                f"block-reason vocabularies drifted: viewer {viewer_set} vs "
                f"CLI {tuple(_ct.BLOCK_REASONS)}"
            )
        if not _ct.BLOCK_REASONS_NEEDING_USER <= set(_ct.BLOCK_REASONS):
            raise SmokeFailure("a reason the status scripts surface is not in the vocabulary")
        ok.append(
            "Blocked: a typed reason writes from the pane, logs, clears on "
            "done, and both vocabularies agree"
        )

        # Unsaved-changes guard: clean dialog is not dirty and closes
        # freely; a field edit flips it dirty.
        from ui.record_dialog import UnifiedRecordDialog

        guard_dlg = UnifiedRecordDialog(win, mconn, mode="task", record_id=b1)
        if guard_dlg._is_dirty():
            raise SmokeFailure("freshly-loaded record dialog should not be dirty")
        if not guard_dlg._confirm_discard():
            raise SmokeFailure("clean dialog should close without prompting")
        guard_dlg.title_edit.setText(guard_dlg.title_edit.text() + " edited")
        if not guard_dlg._is_dirty():
            raise SmokeFailure("edited record dialog should read dirty")
        ok.append("Record dialog unsaved-changes guard detects edits")

        # Overflow guard: a tall ticket must not push the save button off the
        # screen. The body scrolls; the button row is pinned outside the scroll
        # area; and every field is a formCaption above its control in a
        # sectioned grid — the design system's vocabulary, never a QFormLayout.
        from PySide6.QtWidgets import QFormLayout, QLabel, QScrollArea

        if not isinstance(getattr(guard_dlg, "_scroll", None), QScrollArea):
            raise SmokeFailure("record dialog body is not inside a scroll area")
        scrolled = guard_dlg._scroll.widget()
        btn_parent = guard_dlg.button_box.parentWidget()
        if btn_parent is scrolled or (
            btn_parent and btn_parent.isAncestorOf(scrolled) and btn_parent is not guard_dlg
        ):
            raise SmokeFailure("button row is inside the scroll area — it can scroll away")
        if guard_dlg.findChildren(QFormLayout):
            raise SmokeFailure("record dialog lays out fields in a QFormLayout")
        for w in (
            guard_dlg.stage_combo,
            guard_dlg.status_combo,
            guard_dlg.owner_edit,
            guard_dlg.epic_combo,
            guard_dlg.tier_combo,
            guard_dlg.estimate_combo,
            guard_dlg.originator_edit,
            guard_dlg.title_edit,
            guard_dlg.desc_edit,
        ):
            cell = w.parentWidget()
            if not any(lbl.objectName() == "formCaption" for lbl in cell.findChildren(QLabel)):
                raise SmokeFailure(f"{w!r} has no formCaption above it")
        headers = {
            lbl.text()
            for lbl in guard_dlg.findChildren(QLabel)
            if lbl.objectName() == "sectionHeader"
        }
        for name in ("Record", "Placement", "Links", "Log", "Attachments"):
            if name not in headers:
                raise SmokeFailure(f"record dialog is missing the {name} section header")
        guard_dlg._update_visible_fields()  # must not raise
        ok.append("Record dialog scrolls, pins its buttons, captions fields in sections")

        # Required-field guard. A titleless save used to close the dialog and
        # write nothing, silently destroying whatever Description had been typed
        # — so the assertions that matter are that accept() refuses and keeps
        # the typing, that the empty field carries no mark before a save is
        # tried and carries one after, and that the default button names its
        # action.
        from PySide6.QtWidgets import QDialog

        req_dlg = UnifiedRecordDialog(win, mconn, mode="task")
        if req_dlg.ok_button.text() != "Create":
            raise SmokeFailure(
                f"a new record's default button reads {req_dlg.ok_button.text()!r}, not 'Create'"
            )
        if req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("empty required title is marked before any save was tried")
        req_dlg.desc_edit.setPlainText("a description the user would hate to lose")
        req_dlg.accept()
        if req_dlg.result() == QDialog.DialogCode.Accepted:
            raise SmokeFailure("accept() closed the dialog with a missing title")
        if req_dlg.desc_edit.toPlainText() != "a description the user would hate to lose":
            raise SmokeFailure("the refused accept discarded the Description")
        if not req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("empty required title is not marked after a tried save")
        req_dlg.title_edit.setText("Now it has a title")
        if req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("fieldMissing did not clear once the title was filled in")
        req_dlg.title_edit.setText("   ")
        if not req_dlg.title_edit.property("fieldMissing"):
            raise SmokeFailure("whitespace-only title counted as a title")
        req_dlg.type_combo.setCurrentText("Epic")  # required label changes with kind
        if not req_dlg.title_label.property("fieldMissing"):
            raise SmokeFailure("switching kind cleared the mark on an empty name")
        ok.append("Record dialog refuses a save with a required field empty, marking it only then")

        # One field, everywhere a person types more than a word. A one-line
        # field scrolls sideways and hides what came before, so the shared one
        # wraps, grows to its ceiling and then scrolls vertically.
        from PySide6.QtGui import QFontMetrics
        from PySide6.QtTest import QTest
        from ui.growing_edit import GrowingTextEdit
        from ui.links import AddLinkDialog

        link_dlg = AddLinkDialog(win)
        for name, field in (
            ("record title", req_dlg.title_edit),
            ("record log composer", req_dlg.log_post_input),
            ("detail-pane composer", win.detail_pane.comment_input),
            ("link address", link_dlg.uri_input),
            ("link caption", link_dlg.label_input),
        ):
            if not isinstance(field, GrowingTextEdit):
                raise SmokeFailure(f"the {name} field is not the shared growing field")

        # Hide Closed Items is a switch, and turning it over searches again.
        from ui.links import LINK_KINDS as _KINDS
        from ui.switch import Switch as _Switch

        if not isinstance(win.hide_closed_switch, _Switch):
            raise SmokeFailure("Hide Closed Items is not a switch")
        _searched = []
        _real_search = win._execute_global_search
        win._execute_global_search = lambda: _searched.append(True)
        try:
            win.hide_closed_switch.click()
            if not _searched or win.hide_closed_switch.isChecked():
                raise SmokeFailure("turning Hide Closed Items off did not search again")
            win.hide_closed_switch.click()
        finally:
            win._execute_global_search = _real_search
        if link_dlg.kind.value() != "issue" or link_dlg.uri_fields.isVisibleTo(link_dlg):
            raise SmokeFailure("Add Link does not open on a ticket link alone")
        link_dlg.kind.button(_KINDS[1][0]).click()
        if not link_dlg.uri_fields.isVisibleTo(link_dlg) or link_dlg.issue_fields.isVisibleTo(
            link_dlg
        ):
            raise SmokeFailure("choosing An Address does not show only its fields")
        ok.append(
            "Hide Closed Items is a switch that searches again, and Add Link "
            "shows one kind's fields at a time"
        )

        field = GrowingTextEdit(max_lines=4)
        field.setFixedWidth(180)
        field.show()
        shut = field.height()
        field.setText("a sentence long enough to wrap several times over " * 4)
        grown = field.height()
        line = QFontMetrics(field.font()).lineSpacing()
        if grown <= shut:
            raise SmokeFailure("the shared field did not grow with its text")
        if grown > shut + line * 4:
            raise SmokeFailure("the shared field grew past its ceiling")
        if field.horizontalScrollBarPolicy() != Qt.ScrollBarPolicy.ScrollBarAlwaysOff:
            raise SmokeFailure("the shared field can still scroll sideways")
        posted = []
        field.submitted.connect(lambda: posted.append(True))
        QTest.keyClick(field, Qt.Key.Key_Return)
        if not posted:
            raise SmokeFailure("Return did not post from the shared field")
        before = field.toPlainText()
        QTest.keyClick(field, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
        if field.toPlainText() == before:
            raise SmokeFailure("Shift+Return did not open a line")
        ok.append("every typing surface is one field that grows, wraps and posts on Return")

        # Links. The property worth guarding is that an issue link is ONE
        # symmetric row: it must read from both ends, refuse a duplicate offered
        # in either direction, and vanish from both tickets on a single delete.
        # That is the whole reason two mirrored rows were rejected, so a
        # regression here is the regression that matters.
        from ui.links import (
            LinkBar,
            add_issue_link,
            add_uri_link,
            list_links,
            remove_link,
            remove_links_for_task,
        )

        lc = sqlite3.connect(":memory:")
        lc.executescript(schema.read_text())

        def _seed_link_task(title):
            lc.execute(
                "INSERT INTO task (title, status, stage, record_type) "
                "VALUES (?, 'todo', 'active', 'build')",
                (title,),
            )
            return lc.execute("SELECT last_insert_rowid()").fetchone()[0]

        la, lb, ld = (_seed_link_task("Alpha"), _seed_link_task("Beta"), _seed_link_task("Delta"))
        lc.commit()

        def issue_ends(t):
            return [x["other_id"] for x in list_links(lc, t) if x["kind"] == "issue"]

        if add_issue_link(lc, la, lb) is not None:
            raise SmokeFailure("add_issue_link refused a valid pair")
        if issue_ends(la) != [lb] or issue_ends(lb) != [la]:
            raise SmokeFailure("issue link is not visible from both tickets")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("issue link wrote more than one row — it must be symmetric")
        if lc.execute("SELECT task_id, other_id FROM task_link").fetchone() != (
            min(la, lb),
            max(la, lb),
        ):
            raise SmokeFailure("issue link row is not normalized low->high")
        if not (add_issue_link(lc, la, lb) and add_issue_link(lc, lb, la)):
            raise SmokeFailure("duplicate issue link was accepted")
        if not (add_issue_link(lc, la, la) and add_issue_link(lc, la, 9999)):
            raise SmokeFailure("self-link or missing-ticket link was accepted")

        # A dependency is the same single row carrying a direction: it must
        # still be one row, read as 'blocks' from one end and 'blocked-by' from
        # the other, and retype in place rather than spawning a second row.
        if add_issue_link(lc, la, lb, relation="blocks") is not None:
            raise SmokeFailure("retyping an existing link to 'blocks' was refused")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("retyping a link wrote a second row")

        def rel(t):
            return [x["relation"] for x in list_links(lc, t) if x["kind"] == "issue"]

        if rel(la) != ["blocks"] or rel(lb) != ["blocked-by"]:
            raise SmokeFailure("a 'blocks' link does not read from both ends")
        if lc.execute("SELECT task_id, other_id FROM task_link").fetchone() != (la, lb):
            raise SmokeFailure("a 'blocks' row lost its direction to normalization")
        # The same dependency restated from the far end is the same one row: it
        # reports the pair as already linked and changes nothing. What must not
        # happen is a second row or a flipped direction.
        add_issue_link(lc, lb, la, relation="blocked-by")
        if lc.execute("SELECT COUNT(*) FROM task_link").fetchone()[0] != 1:
            raise SmokeFailure("'blocked-by' from the far end wrote a second row")
        if rel(la) != ["blocks"]:
            raise SmokeFailure("'blocked-by' did not store the same directed row")
        if add_issue_link(lc, la, lb, relation="related") is not None:
            raise SmokeFailure("retyping back to 'related' was refused")
        if rel(la) != ["related"]:
            raise SmokeFailure("retyping back to 'related' did not take")

        if add_uri_link(lc, la, "obsidian://open?vault=V&file=n.md", "note") is not None:
            raise SmokeFailure("add_uri_link refused a valid address")
        if not add_uri_link(lc, la, "   "):
            raise SmokeFailure("blank address was accepted")
        rendered = list_links(lc, la)
        if [x["kind"] for x in rendered] != ["issue", "uri"]:
            raise SmokeFailure("list_links should return issue links before uri links")
        if rendered[0]["other_title"] != "Beta" or rendered[1]["label"] != "note":
            raise SmokeFailure("list_links did not resolve the far title / label")

        remove_link(lc, rendered[0]["id"])
        if issue_ends(lb) or len(list_links(lc, la)) != 1:
            raise SmokeFailure("one delete must clear an issue link from both tickets")
        add_issue_link(lc, la, ld)
        remove_links_for_task(lc, ld)
        lc.commit()
        if list_links(lc, ld) or len(list_links(lc, la)) != 1:
            raise SmokeFailure("deleting a task left links pointing at it")

        # Links entered while a ticket is still being created buffer in the
        # widget and are written once the INSERT yields an id.
        bar = LinkBar(lc, allow_pending=True)
        bar.set_task(None)
        bar._pending += [
            ("issue", lb, "", "", "blocked-by"),
            ("uri", None, "https://x.test", "X", "related"),
        ]
        if not bar.has_pending():
            raise SmokeFailure("LinkBar did not buffer links for an unsaved ticket")
        le = _seed_link_task("Echo")
        bar.flush_pending(le)
        if bar.has_pending() or sorted(x["kind"] for x in list_links(lc, le)) != ["issue", "uri"]:
            raise SmokeFailure("flush_pending did not write the buffered links")
        if rel(le) != ["blocked-by"]:
            raise SmokeFailure("flush_pending dropped a buffered link's relation")
        ok.append("Links: one directed edge, related/blocks types, uri links, pending buffer")

        # A link row is as tall as its text in a pane squeezed to its minimum:
        # its button and its remove mark carry no minimum height of their own.
        from PySide6.QtWidgets import QSizePolicy as _QSizePolicy

        fa, fb = _seed_link_task("Follow from"), _seed_link_task("Follow to")
        add_issue_link(lc, fa, fb)
        lc.commit()
        rows_bar = LinkBar(lc)
        rows_bar.set_task(fa)
        first_row = rows_bar.rows.row(0)
        if (
            first_row.sizePolicy().verticalPolicy() != _QSizePolicy.Policy.Fixed
            or rows_bar.minimumSizeHint().height() < first_row.sizeHint().height()
        ):
            raise SmokeFailure("a link row can be squeezed below its own height")

        # The record window follows a card link in place, and asks before it
        # leaves edits behind.
        import ui.record_dialog as _rd

        follow = _rd.UnifiedRecordDialog(None, lc, mode="task", record_id=fa)
        target, target_title = fb, "Follow to"
        follow._open_linked_card(target)
        if (
            follow.record_id != target
            or follow.title_edit.text() != target_title
            or follow._is_dirty()
        ):
            raise SmokeFailure("the record window did not show a linked card in place")
        follow._show_record(fa)
        follow.title_edit.setText("Follow from, renamed")
        asked = []
        _real_choose = _rd.choose
        _rd.choose = lambda *a, **k: (asked.append(True), "save")[1]
        try:
            follow._open_linked_card(target)
        finally:
            _rd.choose = _real_choose
        if not asked or follow.record_id != target:
            raise SmokeFailure(
                "the record window switched cards without asking about unsaved changes"
            )
        if (
            lc.execute("SELECT title FROM task WHERE id=?", (fa,)).fetchone()[0]
            != "Follow from, renamed"
        ):
            raise SmokeFailure("Save before following a link did not save the card")
        follow.deleteLater()
        ok.append(
            "Links: a row keeps its height, and the record window follows a "
            "card link in place, saving first when asked"
        )

        # A bare-path link is stored repository-relative for a file inside the
        # repository, so the row outlives the machine that wrote it. Opening one
        # therefore has to resolve it against the project root, and leave a path
        # anywhere else on the disk as written.
        import config_file as _cf
        from ui.links import resolve_uri_path

        root = _cf.project_root()
        if root is None:
            raise SmokeFailure("no project root, so a relative link cannot resolve")
        if resolve_uri_path("src/app.md") != root / "src/app.md":
            raise SmokeFailure(
                "a repository-relative link did not resolve against the project root"
            )
        if not resolve_uri_path("src/app.md").is_file():
            raise SmokeFailure("a repository-relative link resolved to no file")
        outside = Path("/tmp/somewhere/else.md")
        if resolve_uri_path(str(outside)) != outside:
            raise SmokeFailure("an absolute link was not passed through as written")
        ok.append(
            "Links: a repository-relative uri resolves against the project "
            "root and an absolute one is passed through"
        )

        # A finished blocker's closing comment reaches the ticket it blocked.
        # The properties that matter are that it is a read of two live rows —
        # so editing the blocker's last comment changes what the blocked ticket
        # shows and nothing is written onto it — that only finished blockers
        # that said something contribute, that several arrive in the order they
        # closed, and that the viewer and the CLI read the same thing.
        from ui.links import carried_summaries

        def _close(task_id, at):
            lc.execute("UPDATE task SET status='done', closed_at=? WHERE id=?", (at, task_id))

        def _say(task_id, body):
            lc.execute(
                "INSERT INTO issue_log (task_id, author, body, created_at) "
                "VALUES (?,'chief_of_staff',?,?)",
                (task_id, body, "2026-02-01"),
            )

        # The three that finish close in an order matching neither their ids
        # ascending nor descending, so an id-ordered read cannot pass by luck.
        hb = _seed_link_task("Blocked one")
        hp1, hp2, hp3, hp4, hp5 = (
            _seed_link_task("Parent one"),
            _seed_link_task("Parent two"),
            _seed_link_task("Parent three"),
            _seed_link_task("Parent four"),
            _seed_link_task("Parent five"),
        )
        for parent in (hp1, hp2, hp3, hp4, hp5):
            if add_issue_link(lc, parent, hb, relation="blocks") is not None:
                raise SmokeFailure("a blocks link between fresh tickets was refused")
        _say(hp1, "an earlier note")
        _say(hp1, "one closing")
        _close(hp1, "2026-01-03")
        _say(hp2, "two closing")
        _close(hp2, "2026-01-01")
        _say(hp3, "three closing")
        _close(hp3, "2026-01-02")
        _close(hp4, "2026-01-04")  # done having said nothing
        _say(hp5, "five is still open")  # not done — carries nothing
        lc.commit()

        got = carried_summaries(lc, hb)
        if [e["id"] for e in got] != [hp2, hp3, hp1]:
            raise SmokeFailure(
                "carried summaries are not the finished blockers in the order they closed"
            )
        if [e["body"] for e in got] != ["two closing", "three closing", "one closing"]:
            raise SmokeFailure("a carried summary is not the blocker's own last comment")
        if lc.execute("SELECT COUNT(*) FROM issue_log WHERE task_id=?", (hb,)).fetchone()[0]:
            raise SmokeFailure("a carried summary was copied onto the blocked ticket")
        _say(hp1, "one closing, corrected")
        lc.commit()
        if carried_summaries(lc, hb)[2]["body"] != "one closing, corrected":
            raise SmokeFailure(
                "editing the blocker's last comment did not reach "
                "the blocked ticket — the summary is a copy, not a join"
            )
        if carried_summaries(lc, hp5):
            raise SmokeFailure("a ticket blocking nothing carried a summary")

        # The viewer shows it without the reader opening those tickets, and
        # shows no empty section on a ticket nothing finished ahead of.
        from ui.detail_pane import DetailPane

        hpane = DetailPane(lc)
        hpane.show_task(hb)
        if not hpane.handoff_view.isVisibleTo(hpane) or not hpane._handoff_header.isVisibleTo(
            hpane
        ):
            raise SmokeFailure(
                "the detail pane hid the carried summaries of a ticket that has them"
            )
        shown = hpane.handoff_view.toPlainText()
        if "one closing, corrected" not in shown or "two closing" not in shown:
            raise SmokeFailure("the detail pane did not render both carried summaries")
        if "five is still open" in shown:
            raise SmokeFailure("the detail pane carried an unfinished blocker's comment")
        # Sized to what it contains, like the description above it: a section left
        # at a widget's default height shows a heading and clips the handoff.
        one = _seed_link_task("Blocked two")
        add_issue_link(lc, hp2, one, relation="blocks")
        lc.commit()
        tall = hpane.handoff_view.height()
        hpane.show_task(one)
        if not hpane.handoff_view.height() < tall:
            raise SmokeFailure(
                "the carried-summaries section is not sized to its "
                "content — three summaries take the height of one"
            )
        hpane.show_task(hp5)
        if hpane.handoff_view.isVisibleTo(hpane) or hpane._handoff_header.isVisibleTo(hpane):
            raise SmokeFailure("the detail pane showed an empty carried-summaries section")

        # The status scripts read this through status_common, which is the one
        # copy both front ends call, so the two readers are compared rather than
        # trusted to stay in step.
        _spec_cs = _ilu.spec_from_file_location("_cs", TOOLS / "ticket_tools" / "status_common.py")
        _cs = _ilu.module_from_spec(_spec_cs)
        _spec_cs.loader.exec_module(_cs)
        cli = [(row[0], row[4]) for row in _cs.carried_summaries(lc, hb)]
        if cli != [(e["id"], e["body"]) for e in carried_summaries(lc, hb)]:
            raise SmokeFailure(f"carried-summary readers drifted: CLI {cli} vs viewer")
        ok.append(
            "Carried summaries: finished blockers only, in closing order, "
            "joined live, shown in the pane, and both readers agree"
        )

        # First-run setup. The properties worth guarding are that a cancelled
        # wizard writes nothing, that a finished one produces a board, a
        # config with no placeholders left in it and a pointer, and that the
        # window offers the menu route back to it.
        import ui.setup_wizard as wiz

        root = TOOLS.parent.parent
        menu_actions = [
            a.text() for m in win.menuBar().actions() if m.menu() for a in m.menu().actions()
        ]
        if "Setup…" not in menu_actions:
            raise SmokeFailure("no menu route back to first-run setup")
        ok.append("File → Setup… is on the menu bar")

        from PySide6.QtGui import QAction as _QAction

        menus = [m.text() for m in win.menuBar().actions() if m.menu()]
        if menus != ["File", "Edit", "View", "Window", "Help"]:
            raise SmokeFailure(f"the menu bar reads {menus}")
        roles = {
            a.text(): a.menuRole()
            for m in win.menuBar().actions()
            if m.menu()
            for a in m.menu().actions()
        }
        if (
            roles.get("Settings…") != _QAction.MenuRole.PreferencesRole
            or roles.get("About Bristol Tickets") != _QAction.MenuRole.AboutRole
            or roles.get("Quit Bristol Tickets") != _QAction.MenuRole.QuitRole
        ):
            raise SmokeFailure(
                "About, Settings… or Quit is not filed in the application menu by its role"
            )
        views = [
            a.text()
            for m in win.menuBar().actions()
            if m.menu() and m.text() == "View"
            for a in m.menu().actions()
        ]
        if views[: len(win._tab_buttons)] != [b.accessibleName() for b in win._tab_buttons]:
            raise SmokeFailure("the View menu does not list every tab")
        ok.append(
            "the menu bar carries File, Edit, View, Window and Help, and "
            "the application menu's About, Settings… and Quit"
        )

        if wiz.project_root() != root:
            raise SmokeFailure("setup wizard cannot find the clone it lives in")
        if not wiz.needs_setup(None) and not (root / "config" / "config.local.json").exists():
            raise SmokeFailure("a clone with no config and no board should need setup")
        if wiz.needs_setup(schema):  # any existing file stands in for a board
            raise SmokeFailure("an existing board should not trigger setup")

        with tempfile.TemporaryDirectory() as scratch:
            scratch_root = Path(scratch) / "clone"
            (scratch_root / "config").mkdir(parents=True)
            (scratch_root / "src").mkdir()
            (scratch_root / "src" / "app.md").write_text("marker\n")
            (scratch_root / "config" / "config.example.json").write_text(
                (root / "config" / "config.example.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            cfg = wiz.build_config(
                root=scratch_root,
                instance_dir=scratch_root / "data" / "tester",
                slug="tester",
                agents=["chief_of_staff", "librarian"],
                notebook="",
                zotero="",
            )
            if set(cfg["agents"]) - {"_notes", "chief_of_staff", "librarian"}:
                raise SmokeFailure("unchosen agents survived into the config")
            if cfg["active_agent"] != "chief_of_staff":
                raise SmokeFailure("active_agent was not set from the chosen agents")
            if "zotero" in cfg:
                raise SmokeFailure("a skipped integration was written into the config")
            # No notebook chosen: Bristol keeps its own inside the instance,
            # with its three folders attached and created at setup.
            own = cfg.get("markdown_notebook") or {}
            if own.get("notes_dir") != str(
                scratch_root / "data" / "tester" / "notebook"
            ) or own.get("folders") != ["inbox", "ai_workspace", "archive"]:
                raise SmokeFailure(f"a skipped notebook did not become Bristol's own: {own}")
            made = wiz._declared_dirs(scratch_root, cfg, scratch_root / "data" / "tester")
            if scratch_root / "data" / "tester" / "notebook" / "inbox" not in made:
                raise SmokeFailure("Bristol's own notebook folders are not created at setup")
            chosen_nb = wiz.build_config(
                root=scratch_root,
                instance_dir=scratch_root / "data" / "tester",
                slug="tester",
                agents=["chief_of_staff"],
                notebook=str(scratch_root / "elsewhere"),
                zotero="",
            )
            if chosen_nb["markdown_notebook"].get("folders") != []:
                raise SmokeFailure("a chosen notebook arrives with folders attached")
            blob = json.dumps(cfg)
            for token in (
                "<your-instance>",
                "/path/to/project",
                "/path/to/notebook",
                "/path/to/Zotero",
            ):
                if token in blob:
                    raise SmokeFailure(f"placeholder {token!r} survived into the config")
            if cfg["important_paths"]["tickets_db"] != "data/tester/tickets/tickets.db":
                raise SmokeFailure("tickets_db does not point at the new instance")
            ok.append("build_config fills every placeholder and drops what was skipped")

            # The whole flow, driven through the wizard's own pages: a scratch
            # clone with no pointer and no config is exactly the fresh-install
            # state, and Finish is the only thing that writes.
            import config_file

            pointer = Path(scratch) / "instance.json"
            written_config = scratch_root / "config" / "config.local.json"
            _orig_pointer = wiz.instance.pointer_path
            _orig_config_path = config_file.path
            wiz.instance.pointer_path = lambda: pointer
            config_file.path = lambda: written_config
            try:
                wizard = wiz.SetupWizard(scratch_root)
                from PySide6.QtWidgets import QWizard

                for role, word in (
                    (QWizard.WizardButton.CancelButton, "Cancel"),
                    (QWizard.WizardButton.BackButton, "Go Back"),
                    (QWizard.WizardButton.NextButton, "Continue"),
                ):
                    if wizard.buttonText(role) != word:
                        raise SmokeFailure(
                            f"the setup assistant's button reads "
                            f"{wizard.buttonText(role)!r}, not {word!r}"
                        )
                # A machine with no configuration and no pointer opens on the
                # operating system's user name, which is the first-run default.
                if wizard.instance_page.slug_edit.text() != wiz.default_slug():
                    raise SmokeFailure("a first run did not open on the default name")
                if wizard.instance_page.folder.value() != str(
                    scratch_root / "data" / wiz.default_slug()
                ):
                    raise SmokeFailure("a first run did not open on the clone's own data folder")
                wizard.instance_page.slug_edit.setText("tester")
                if wizard.instance_page.instance_dir() != scratch_root / "data" / "tester":
                    raise SmokeFailure("the data folder did not follow the instance name")
                offered = wizard.agents_page.agents
                if not offered.count():
                    raise SmokeFailure("the agents page offers no agents")
                for row in range(offered.count()):
                    slug_name = offered.key(offered.item(row))
                    offered.set_chosen(slug_name, slug_name in ("chief_of_staff", "librarian"))
                wizard.summary_page.initializePage()
                if "tester" not in wizard.summary_page.body.text():
                    raise SmokeFailure("the summary does not name what will be written")
                if pointer.exists() or (scratch_root / "data").exists():
                    raise SmokeFailure("the wizard wrote something before Finish")
                wizard.accept()
                db = wizard.db_path
            finally:
                wiz.instance.pointer_path = _orig_pointer
                config_file.path = _orig_config_path
            if db is None or not db.exists():
                raise SmokeFailure("setup did not provision a board")
            fresh = sqlite3.connect(db)
            if not fresh.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='task'"
            ).fetchone():
                raise SmokeFailure("the provisioned board has no task table")
            if fresh.execute("SELECT COUNT(*) FROM task").fetchone()[0]:
                raise SmokeFailure("setup seeded rows; an empty board is the first state")
            fresh.close()
            if not (scratch_root / "config" / "config.local.json").exists():
                raise SmokeFailure("setup did not write config.local.json")
            if not (scratch_root / "data" / "tester" / "personal").is_dir():
                raise SmokeFailure("setup did not create a chosen agent's data folder")
            if (scratch_root / "data" / "tester" / "clients").exists():
                raise SmokeFailure("setup created a folder for an agent that was not chosen")
            written = json.loads(pointer.read_text())
            if (
                written["instance_slug"] != "tester"
                or Path(written["data_root"]) != scratch_root / "data"
            ):
                raise SmokeFailure("the instance pointer does not name the new instance")
            ok.append(
                "Setup wizard writes nothing until Finish, then folders, "
                "an empty board, config and pointer"
            )

            # Adoption. The installation the run above created is now an
            # existing one, which is exactly the state a second run meets. The
            # properties worth guarding are that the wizard sees it, asks
            # nothing it does not need, leaves the board and the config alone,
            # and treats the pointer as the one thing Finish decides.
            adopted_db = scratch_root / "data" / "tester" / "tickets" / "tickets.db"
            seeded = sqlite3.connect(adopted_db)
            seeded.execute("INSERT INTO task (title, status) VALUES ('adopted', 'todo')")
            seeded.commit()
            seeded.close()
            config_before = (scratch_root / "config" / "config.local.json").read_bytes()
            pointer_before = pointer.read_text()
            pointer.write_text(
                json.dumps(
                    {
                        "repo_root": str(scratch_root),
                        "data_root": str(Path(scratch) / "elsewhere"),
                        "instance_slug": "other",
                        "config_path": str(scratch_root / "config" / "config.local.json"),
                    }
                )
                + "\n"
            )

            wiz.instance.pointer_path = lambda: pointer
            config_file.path = lambda: written_config
            try:
                second = wiz.SetupWizard(scratch_root)
                # Setup opens on the installation the configuration declares,
                # not on the operating system's user name and not on the
                # installation the pointer happens to be aimed at.
                if second.instance_page.slug_edit.text() != "tester":
                    raise SmokeFailure("setup did not open on the configured installation")
                if second.instance_page.folder.value() != str(scratch_root / "data" / "tester"):
                    raise SmokeFailure("setup did not open on the configured installation's folder")
                if "other" not in second.instance_page.disagreement.text():
                    raise SmokeFailure(
                        "a configuration and a pointer naming "
                        "different installations were reconciled "
                        "silently"
                    )
                second.instance_page.slug_edit.setText("tester")
                second.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                if not second.instance_page.adopting():
                    raise SmokeFailure(
                        "a folder containing a board was not seen as an installation"
                    )
                if second.instance_page.nextId() != wiz.PAGE_SUMMARY:
                    raise SmokeFailure("adoption still asks the pages only creation needs")
                second.summary_page.initializePage()
                summary = second.summary_page.body.text() + second.summary_page.pointer_note.text()
                if "other" not in summary or "tester" not in summary:
                    raise SmokeFailure(
                        "the summary does not name both the old and the new installation"
                    )
                # Both sides are named as an installation folder, so the reader
                # compares two paths of one kind rather than a data root
                # against a folder beneath one.
                if str(Path(scratch) / "elsewhere" / "other") not in summary:
                    raise SmokeFailure(
                        "the summary names the old installation by "
                        "its data root, not by its own folder"
                    )

                # Adopting the installation the app already opens must not say
                # it stops opening it.
                third_pointer = json.loads(pointer.read_text())
                pointer.write_text(
                    json.dumps(
                        {
                            **third_pointer,
                            "data_root": str(scratch_root / "data"),
                            "instance_slug": "tester",
                        }
                    )
                    + "\n"
                )
                same = wiz.SetupWizard(scratch_root)
                same.instance_page.slug_edit.setText("tester")
                same.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                same.summary_page.initializePage()
                if "stops opening" in same.summary_page.pointer_note.text():
                    raise SmokeFailure(
                        "the summary says it stops opening the installation it is about to open"
                    )
                pointer.write_text(json.dumps(third_pointer) + "\n")

                # Leaving the pointer alone writes nothing at all.
                second.summary_page.take_over.setChecked(False)
                second.accept()
                if pointer.read_text() == pointer_before:
                    raise SmokeFailure("an unchecked pointer option still rewrote the pointer")
                if second.db_path != adopted_db:
                    raise SmokeFailure("adoption did not return the board it adopted")

                # Taking it over writes the pointer, and only the pointer.
                third = wiz.SetupWizard(scratch_root)
                third.instance_page.slug_edit.setText("tester")
                third.instance_page.folder.set_value(str(scratch_root / "data" / "tester"))
                third.summary_page.initializePage()
                third.accept()
            finally:
                wiz.instance.pointer_path = _orig_pointer
                config_file.path = _orig_config_path

            adopted = json.loads(pointer.read_text())
            if (
                adopted["instance_slug"] != "tester"
                or Path(adopted["data_root"]) != scratch_root / "data"
            ):
                raise SmokeFailure("adoption did not point the app at the installation")
            if (scratch_root / "config" / "config.local.json").read_bytes() != config_before:
                raise SmokeFailure("adoption rewrote the configuration it was told to leave")
            kept = sqlite3.connect(adopted_db)
            titles = [r[0] for r in kept.execute("SELECT title FROM task")]
            kept.close()
            if titles != ["adopted"]:
                raise SmokeFailure("adoption ran the schema against the board it adopted")
            ok.append(
                "Adoption leaves the board and the config alone, and writes "
                "only the pointer the summary offers"
            )

            # Settings and the active agent, against the config the wizard just
            # wrote. The property that matters is that both read and write that
            # one file, and that a key this build does not offer survives a save.
            from ui.settings_tab import SettingsTab

            _orig_path = config_file.path
            config_file.path = lambda: written_config
            try:
                config_file.update({"a_key_from_a_newer_build": {"kept": True}})
                tab = SettingsTab()
                from PySide6.QtWidgets import QFormLayout as _QFormLayout

                for _form in tab.findChildren(_QFormLayout):
                    if not _form.labelAlignment() & Qt.AlignmentFlag.AlignRight or (
                        _form.horizontalSpacing(),
                        _form.verticalSpacing(),
                    ) != (_theme.space("lg"), _theme.space("lg")):
                        raise SmokeFailure(
                            "a Settings form does not right-align its labels SPACE lg "
                            "from their controls and SPACE lg row to row"
                        )
                if tab.new_ticket.currentData() != "active":
                    raise SmokeFailure("Settings did not load the stored board setting")
                tab.new_ticket.setCurrentIndex(tab.new_ticket.findData("backlog"))
                if config_file.get(config_file.NEW_TICKET_STAGE) != "backlog":
                    raise SmokeFailure("Settings did not write the board setting")
                if config_file.get("a_key_from_a_newer_build.kept") is not True:
                    raise SmokeFailure("a Settings write dropped an unrecognised key")
                # Work Scope: the whole queue by default, and One Ticket — the
                # position that changes anything — reaches the file.
                if tab.work_scope.currentData() is not True:
                    raise SmokeFailure("Work Scope did not default to the whole queue")
                tab.work_scope.setCurrentIndex(tab.work_scope.findData(False))
                if config_file.get(config_file.WORK_WHOLE_QUEUE) is not False:
                    raise SmokeFailure("Settings did not write the work scope")
                # Theme and Light & Dark are two rows writing two keys, and the
                # older single key is what an installation predating them has.
                import ui.theme as theme
                from PySide6.QtCore import Qt
                from ui.theme import DARK_MODE, LIGHT_MODE, SYSTEM_MODE

                if (tab.theme.currentData(), tab.mode.currentData()) != ("warm", SYSTEM_MODE):
                    raise SmokeFailure("Settings did not load the stored appearance")
                previewed: list[tuple[str, str]] = []
                tab._on_appearance_changed = lambda theme, mode: previewed.append((theme, mode))
                tab.theme.setCurrentIndex(tab.theme.findData("cool"))
                if previewed[-1:] != [("cool", SYSTEM_MODE)]:
                    raise SmokeFailure("picking a theme did not apply it live")
                if config_file.get(config_file.APPEARANCE_THEME) != "cool":
                    raise SmokeFailure("picking a theme did not write it")
                tab.mode.setCurrentIndex(tab.mode.findData(DARK_MODE))
                if previewed[-1:] != [("cool", DARK_MODE)]:
                    raise SmokeFailure("picking a mode did not apply it live")
                if config_file.get(config_file.APPEARANCE_MODE) != DARK_MODE:
                    raise SmokeFailure("picking a mode did not write it")
                # The collection is what the picker offers, so a theme
                # stored in the configuration is one of its entries and no
                # Custom door stands among them.
                if not tab.manage.isEnabled():
                    raise SmokeFailure("Settings offers no way to manage themes")
                if tab.theme.findData(theme.LEGACY_CUSTOM_THEME) >= 0:
                    raise SmokeFailure("the Theme picker still offers Custom")
                config_file.update(
                    {
                        config_file.APPEARANCE_THEMES: {
                            "added": {
                                "light_only": {
                                    "name": "Light Only",
                                    "light": dict(theme.REFERENCE_PALETTE),
                                    "dark": None,
                                }
                            }
                        }
                    }
                )
                tab.reload()
                if tab.theme.findData("light_only") < 0:
                    raise SmokeFailure("a theme in the configuration is not offered")
                # A theme with no dark half: the two dark rows are unclickable,
                # they carry the reason, and the row sits on Light.
                tab.theme.setCurrentIndex(tab.theme.findData("light_only"))
                for index in range(tab.mode.count()):
                    value = tab.mode.itemData(index)
                    item = tab.mode.model().item(index)
                    if (value == LIGHT_MODE) is not item.isEnabled():
                        raise SmokeFailure(f"mode {value!r} is offered against its theme")
                    hover = tab.mode.itemData(index, Qt.ItemDataRole.ToolTipRole)
                    if item.isEnabled() != (not hover):
                        raise SmokeFailure(f"mode {value!r} does not say why on hover")
                if tab.mode.currentData() != LIGHT_MODE:
                    raise SmokeFailure("a theme with no dark half did not sit on Light")
                if config_file.get(config_file.APPEARANCE_MODE) != DARK_MODE:
                    raise SmokeFailure("seating Light over an unofferable mode overwrote it")
                tab.theme.setCurrentIndex(tab.theme.findData("cool"))
                if tab.mode.currentData() != DARK_MODE:
                    raise SmokeFailure("returning to a theme with both halves lost the mode")
                config_file.update({config_file.APPEARANCE_THEMES: {}})
                tab.reload()
                if tab.theme.findData("light_only") >= 0:
                    raise SmokeFailure("a theme taken out of the configuration is still offered")
                if hasattr(tab, "save_btn"):
                    raise SmokeFailure("a Save button still stands on Settings")
                # Where things are: one button opens the notebook and its
                # folders, one every other location, and both windows build.
                if tab.notebook_btn.text() != "Notebook" or tab.locations_btn.text() != "Locations":
                    raise SmokeFailure("Settings does not offer Notebook and Locations")
                from ui.folders import LocationsDialog, NotebookDialog

                NotebookDialog(tab).close()
                LocationsDialog(tab).close()
                was_git = config_file.get(config_file.SUGGESTED_COMMIT)
                for value in config_file.GIT_ON_CLOSE:
                    tab.suggested_commit.setCurrentIndex(tab.suggested_commit.findData(value))
                    if config_file.get(config_file.SUGGESTED_COMMIT) != value:
                        raise SmokeFailure(f"choosing git '{value}' did not write it")
                if [config_file.git_on_close(v) for v in (True, False, None)] != [
                    "block",
                    "off",
                    "block",
                ]:
                    raise SmokeFailure("an older true/false git setting reads wrong")
                config_file.update({config_file.SUGGESTED_COMMIT: was_git})
                # Seating a stored value is not a choice, so reload writes nothing.
                marker = config_file.get(config_file.APPEARANCE_THEME)
                config_file.update({config_file.APPEARANCE_THEME: "warm"})
                tab.reload()
                if config_file.get(config_file.APPEARANCE_THEME) != "warm":
                    raise SmokeFailure("reloading Settings wrote a value back")
                config_file.update({config_file.APPEARANCE_THEME: marker})
                # The next-session agent is a field on this page like every
                # other: it loads from the configuration, moves only on a
                # deliberate choice, and reaches the file on that choice.
                picker = tab.next_agent
                if picker.currentData() not in config_file.agent_slugs():
                    raise SmokeFailure("the agent picker does not show a configured agent")
                from ui.theme import agent_caption as _agent_caption

                if picker.currentText() != _agent_caption(picker.currentData()):
                    raise SmokeFailure("the agent picker shows a slug, not a name")
                if picker.currentData() != config_file.get("active_agent"):
                    raise SmokeFailure("the agent picker opens on an agent that is not active")
                if not picker.isEnabled():
                    raise SmokeFailure("the agent picker is not selectable")
                if picker.count() != len(config_file.agent_slugs()):
                    raise SmokeFailure(
                        "the agent picker lists agents this installation does not configure"
                    )

                # A wheel gesture and an arrow key while it has focus leave
                # the value and write nothing.
                from PySide6.QtCore import QEvent, QPoint, QPointF
                from PySide6.QtGui import QKeyEvent, QWheelEvent

                before = picker.currentText()
                chosen: list[str] = []
                picker.picked.connect(chosen.append)
                picker.wheelEvent(
                    QWheelEvent(
                        QPointF(0, 0),
                        QPointF(0, 0),
                        QPoint(0, 0),
                        QPoint(0, -120),
                        Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase,
                        False,
                    )
                )
                picker.keyPressEvent(
                    QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
                )
                if picker.currentText() != before or chosen:
                    raise SmokeFailure("a wheel gesture or an arrow key moved the agent picker")

                # Loading a value is not a choice; choosing one is.
                picker.setCurrentIndex(picker.findData("librarian"))
                if chosen:
                    raise SmokeFailure("loading a value into the agent picker wrote it")
                picker.activated.emit(picker.findData("librarian"))
                if chosen != ["librarian"]:
                    raise SmokeFailure("choosing an agent did not report the choice")
                if config_file.get("active_agent") != "librarian":
                    raise SmokeFailure("choosing an agent did not write it")

                agent_win = MainWindow(mconn)
                if hasattr(agent_win, "agent_combo"):
                    raise SmokeFailure("an agent control still stands in the header")
                if agent_win.settings_btn.accessibleName() != "Settings":
                    raise SmokeFailure("no Settings button in the top bar")
            finally:
                config_file.path = _orig_path
            ok.append("Settings writes each choice as it is made, and a load is not a choice")

            # Speed: on a board the size of the user's, the five things a
            # person waits on each answer inside its limit. The limits are the
            # times measured on 2026-11-19 after #1440, with room for a slower
            # machine; a reload that re-themes the app, as one did before that
            # fix, takes several times its limit.
            from PySide6.QtWidgets import QApplication as _QApp

            sconn = sqlite3.connect(":memory:")
            sconn.executescript(schema.read_text())
            for _i in range(SPEED_BOARD_CARDS):
                sconn.execute(
                    "INSERT INTO task (title, description, status, stage, sort_order, "
                    "estimate, tier, record_type, assignee, reporter, created_at, "
                    "updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,'2026-11-19','2026-11-19')",
                    (
                        f"Card {_i} with a title long enough to wrap onto a second line",
                        "d",
                        ("todo", "doing", "done")[_i % 3],
                        "active" if _i % 5 else "backlog",
                        _i,
                        ("S", "M", "L", "XL")[_i % 4],
                        ("max", "standard")[_i % 2],
                        ("build", "fix")[_i % 2],
                        ("user", "chief_of_staff", "librarian")[_i % 3],
                        "user",
                    ),
                )
            sconn.commit()

            def _timed(what, limit, act):
                started = time.perf_counter()
                act()
                _QApp.processEvents()
                took = time.perf_counter() - started
                if took > limit:
                    raise SmokeFailure(
                        f"{what} took {took:.2f} s on {SPEED_BOARD_CARDS} cards, "
                        f"over its {limit:g} s limit"
                    )
                return f"{what} {took:.2f} s"

            config_file.path = lambda: written_config
            try:
                timings = []
                speed_win = []
                timings.append(
                    _timed(
                        "opening the window",
                        SPEED_LIMITS["open"],
                        lambda: speed_win.append(MainWindow(sconn)),
                    )
                )
                swin = speed_win[0]
                timings.append(_timed("a Refresh", SPEED_LIMITS["refresh"], swin._refresh_board))
                picker = swin.settings_tab.theme
                other = next(i for i in range(picker.count()) if i != picker.currentIndex())
                timings.append(
                    _timed(
                        "a theme change in Settings",
                        SPEED_LIMITS["theme"],
                        lambda: picker.setCurrentIndex(other),
                    )
                )
                timings.append(
                    _timed(
                        "a top-bar agent choice",
                        SPEED_LIMITS["agent"],
                        lambda: swin._choose_agent("chief_of_staff"),
                    )
                )
                timings.append(
                    _timed(
                        "a full Settings reload",
                        SPEED_LIMITS["reload"],
                        swin.settings_tab.reload,
                    )
                )
            finally:
                config_file.path = _orig_path
            ok.append("each answers inside its limit: " + "; ".join(timings))

            # Skills: the page reads one listing and files the judgment as a
            # card. The loader is stubbed, so what is checked is the page —
            # what it groups, what it says a skill carries, and what it writes.
            import importlib.util as _ilu
            import json as _json

            from ui.skills_tab import SkillsTab

            # The row's words come from the loader, so the stub listing is
            # worded by the loader too and the two cannot drift apart.
            _spec = _ilu.spec_from_file_location(
                "smoke_skills", TOOLS / "skill_tools" / "skills.py"
            )
            _loader = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_loader)

            listing = {
                "skills": [
                    {
                        "name": "native-one",
                        "directory": "native-one",
                        "description": "A native skill.",
                        "origin": "native",
                        "root": "native",
                        "repo": "",
                        "commit": "",
                        "license": "MIT",
                        "license_source": "",
                        "files": 1,
                        "scripts": [],
                        "holders": [],
                        "file_list": ["SKILL.md"],
                        "path": "/nowhere/native-one",
                        "source_url": "",
                    },
                    {
                        "name": "with-code",
                        "directory": "with-code",
                        "description": "An installed skill carrying scripts.",
                        "origin": "someone/repo@abc1234",
                        "root": "installed",
                        "repo": "https://github.com/someone/repo",
                        "commit": "abc1234def",
                        "license": "Apache-2.0",
                        "license_source": "SKILL.md",
                        "files": 4,
                        "scripts": ["scripts/run.py"],
                        "holders": ["chief_of_staff"],
                        "file_list": [
                            "SKILL.md",
                            "references/a.md",
                            "assets/b.txt",
                            "scripts/run.py",
                        ],
                        "path": "/nowhere/with-code",
                        "source_url": "https://github.com/someone/repo/tree/abc1234def/skills/with-code",
                    },
                    {
                        "name": "scanned",
                        "directory": "scanned",
                        "description": "A skill whose scan found nothing.",
                        "origin": "someone/other@0000000",
                        "root": "installed",
                        "repo": "https://github.com/someone/other",
                        "commit": "0000000aaa",
                        "license": "MIT",
                        "license_source": "SKILL.md",
                        "files": 2,
                        "scripts": ["scripts/x.py"],
                        "scan": {
                            "scanners": ["bandit", "semgrep"],
                            "ran": True,
                            "missing": [],
                            "unread": [],
                            "findings": [],
                        },
                        "holders": [],
                        "file_list": ["SKILL.md", "scripts/x.py"],
                        "path": "/nowhere/scanned",
                        "source_url": "https://github.com/someone/other/tree/0000000aaa/scanned",
                    },
                ],
                "agents": {"chief_of_staff": ["with-code"], "librarian": []},
            }
            # What an import adds: a skill the listing did not contain before.
            fresh = dict(
                listing["skills"][2], name="fresh", directory="fresh", path="/nowhere/fresh"
            )

            def _phrase(record):
                record["said_origin"] = _loader.origin_phrase(record)
                record["said_contents"] = _loader.contents_phrase(record)
                record["said_scan"] = _loader.scan_phrase(record)
                record["said_holders"] = _loader.holders_phrase(record["holders"])

            for _record in listing["skills"] + [fresh]:
                _phrase(_record)
            calls: list[tuple] = []

            refused = (
                "Not imported: risky, because the scan found a risk. "
                "Nothing was added.\n  HIGH     B602 shell=True — scripts/x.py:7"
            )

            def _stub_run(self, *args):
                calls.append(args)
                if args[:2] == ("list", "--json"):
                    return 0, _json.dumps(listing), ""
                if args[:1] == ("install",):
                    if "risky" in args[1]:
                        return 1, "", refused
                    listing["skills"].append(fresh)
                return 0, f"stub ran {' '.join(args)}", ""

            _orig_run = SkillsTab._run
            SkillsTab._run = _stub_run
            import ui.skills_tab as _skills_mod
            from ui.theme import CARD_ROLE as _CARD_ROLE

            try:
                for _r in listing["skills"] + [fresh]:
                    _r["title"] = _loader.title_phrase(_r["name"])
                    _r["subtitle"] = _loader.subtitle_phrase(_r)
                stab = SkillsTab(mconn)

                def _cards():
                    return [
                        stab.list.item(i).data(_CARD_ROLE)
                        for i in range(stab.list.count())
                        if stab.list.item(i).data(Qt.ItemDataRole.UserRole)
                    ]

                def _named():
                    return [c["title"] for c in _cards()]

                # One list, every row a skill, ordered by the name a person
                # reads and shown in Title Case.
                if _named() != ["Native One", "Scanned", "With Code"]:
                    raise SmokeFailure(f"Skills lists something other than the skills: {_named()}")
                if (
                    _loader.title_phrase("checking-a-wiki-for-disagreements")
                    != "Checking a Wiki for Disagreements"
                ):
                    raise SmokeFailure("a skill's name is not put in Title Case")
                # The page explains nothing in sentences and reports nothing.
                for gone in ("import_note", "status", "address", "open_btn", "remove_btn"):
                    if hasattr(stab, gone):
                        raise SmokeFailure(f"the Skills page still carries {gone}")
                if stab.search.placeholderText() != "Filter":
                    raise SmokeFailure("the narrowing field is not labelled Filter")
                cards = {c["title"]: c for c in _cards()}
                if cards["Scanned"]["meta"].find("Scanned, nothing found") < 0:
                    raise SmokeFailure("a scanned skill's card does not say what the scan found")
                if cards["With Code"]["pills"] != ["Chief of Staff"]:
                    raise SmokeFailure("a card does not carry the agents attached to it")
                if "Downloaded from someone/repo@abc1234" not in cards["With Code"]["meta"]:
                    raise SmokeFailure("a card does not say where a skill was downloaded from")
                if "Came with Bristol" not in cards["Native One"]["meta"]:
                    raise SmokeFailure("a card still expects the reader to know 'native'")
                if cards["Native One"]["description"] != "A native skill":
                    raise SmokeFailure("a card does not carry the skill's subtitle")
                if (
                    _loader.scan_phrase(
                        dict(
                            listing["skills"][2],
                            scan={
                                "scanners": ["bandit"],
                                "ran": True,
                                "findings": [],
                                "unread": ["scripts/x.ps1"],
                            },
                        )
                    )
                    != "Code not fully scanned"
                ):
                    raise SmokeFailure("code no scanner read reads as scanned")
                if _loader.refusal({"ran": True, "findings": [], "unread": []}):
                    raise SmokeFailure("a whole, clean scan is refused")
                for partial in (
                    {"ran": False, "findings": [], "unread": []},
                    {"ran": True, "findings": [], "unread": ["a.ps1"]},
                    {"ran": True, "unread": [], "findings": [{"severity": "MEDIUM"}]},
                ):
                    if not _loader.refusal(partial):
                        raise SmokeFailure(f"an import goes ahead on {partial}")
                if _loader.scan_phrase(listing["skills"][0]):
                    raise SmokeFailure("a skill with no code carries a scan line")
                if _loader.contents_phrase({"files": 1, "scripts": []}) != "one file, no code":
                    raise SmokeFailure("a count and its noun disagree in number")
                if (
                    _loader.subtitle_phrase(
                        {"description": "Deepfake detection — and more. Use when"}
                    )
                    != "Deepfake detection"
                ):
                    raise SmokeFailure("a skill with no subtitle is not cut to its first phrase")

                from ui.skills_tab import (
                    ANY_AGENT,
                    ANY_SOURCE,
                    CAME_WITH,
                    NO_AGENT,
                    NewSkillDialog,
                    SkillDialog,
                )

                stab.search.setText("scripts")
                if _named() != ["With Code"]:
                    raise SmokeFailure(f"the text filter does not narrow: {_named()}")
                stab.search.clear()
                stab.source.setCurrentText(CAME_WITH)
                if _named() != ["Native One"]:
                    raise SmokeFailure(f"the source filter does not narrow: {_named()}")
                stab.source.setCurrentText(ANY_SOURCE)
                stab.holder.setCurrentText("Chief of Staff")
                if _named() != ["With Code"]:
                    raise SmokeFailure(f"the agent filter does not narrow: {_named()}")
                stab.holder.setCurrentText(NO_AGENT)
                if "With Code" in _named():
                    raise SmokeFailure("the no-agent filter keeps an attached skill")
                stab.holder.setCurrentText(ANY_AGENT)
                if len(_named()) != 3:
                    raise SmokeFailure("clearing the filters does not restore the list")

                # A skill opens, and that is where its agents are chosen and a
                # downloaded one is removed.
                writes: list[tuple] = []

                def _dialog_run(*args):
                    writes.append(args)
                    return 0, f"stub ran {' '.join(args)}", ""

                coded_record = [s for s in listing["skills"] if s["name"] == "with-code"][0]
                dlg = SkillDialog(
                    None,
                    coded_record,
                    ["chief_of_staff", "librarian"],
                    "---\nname: with-code\n---\nthe body",
                    _dialog_run,
                )
                if "the body" not in dlg.body.toPlainText() or not dlg.body.isReadOnly():
                    raise SmokeFailure("a skill's view does not show its SKILL.md read-only")
                if dlg.files.count() != len(coded_record["file_list"]):
                    raise SmokeFailure("a skill's view does not list its files")
                if (
                    dlg.source_btn is None
                    or coded_record["source_url"] not in dlg.source_btn.toolTip()
                ):
                    raise SmokeFailure("a downloaded skill's view has no link to its source")
                if not dlg.holders.is_chosen("chief_of_staff") or dlg.holders.is_chosen(
                    "librarian"
                ):
                    raise SmokeFailure("the toggle rows do not carry who has the skill")
                dlg.holders.set_chosen("librarian", True)
                dlg.holders.set_chosen("chief_of_staff", False)
                if ("attach", "with-code", "--agent", "librarian") not in writes:
                    raise SmokeFailure("ticking an agent did not attach through the loader")
                if ("detach", "with-code", "--agent", "chief_of_staff") not in writes:
                    raise SmokeFailure("unticking an agent did not detach through the loader")
                asked: list[str] = []
                _real_confirm = _skills_mod.dialogs.confirm
                _skills_mod.dialogs.confirm = lambda parent, title, body, label, *a, **k: (
                    asked.append(title) or False
                )
                try:
                    dlg._remove()
                finally:
                    _skills_mod.dialogs.confirm = _real_confirm
                if not asked or ("remove", "with-code") in writes or dlg.removed:
                    raise SmokeFailure("Remove deleted a skill without a confirmation")
                removes = [b for b in dlg.findChildren(QPushButton) if b.text() == "Remove"]
                if len(removes) != 1:
                    raise SmokeFailure("a downloaded skill's view does not offer Remove")

                native = SkillDialog(
                    None, listing["skills"][0], ["chief_of_staff"], "native text", _dialog_run
                )
                if not native.body.isReadOnly() or native.files.count() != 1:
                    raise SmokeFailure("a native skill's view does not read")
                if native.source_btn is not None:
                    raise SmokeFailure("a native skill's view offers a source it has none of")
                if any(b.text() == "Remove" for b in native.findChildren(QPushButton)):
                    raise SmokeFailure("a native skill can be removed from the app")

                # Import is one field in a window of its own, with a live
                # example under it, and a refused import keeps the window.
                filed: list[tuple] = []
                imp = NewSkillDialog(
                    None, lambda *a: _stub_run(stab, *a), lambda t, b: filed.append((t, b)) or ""
                )
                if imp.go_btn.isEnabled():
                    raise SmokeFailure("New Skill can be pressed with nothing chosen")
                if not (imp.request_fields.isHidden() and imp.import_fields.isHidden()):
                    raise SmokeFailure("New Skill opens with a section already open")
                imp.request_choice.setChecked(True)
                if imp.request_fields.isHidden() or not imp.import_fields.isHidden():
                    raise SmokeFailure("choosing Request does not open only its fields")
                imp.title.setText("Tide tables")
                if imp.go_btn.isEnabled():
                    raise SmokeFailure("a request can be sent without its body")
                imp.request.setPlainText("Read the local tide tables.")
                imp._go()
                if filed != [("Tide tables", "Read the local tide tables.")] or not imp.filed:
                    raise SmokeFailure(f"a request did not file as asked: {filed}")
                if stab._standing_epic() is not None and not isinstance(stab._standing_epic(), int):
                    raise SmokeFailure("the standing epic lookup returns something else")
                # What a request files: the card's title, column, owner and
                # body, through the board's own writer.
                ran: list[list] = []

                class _Done:
                    returncode, stdout, stderr = 0, "OK", ""

                _real_sp_run = _skills_mod.subprocess.run
                _skills_mod.subprocess.run = lambda args, **k: ran.append(args) or _Done()
                try:
                    problem = stab._file_request("Tide tables", "Read them.")
                finally:
                    _skills_mod.subprocess.run = _real_sp_run
                if problem or not ran:
                    raise SmokeFailure(f"a request did not reach the ticket writer: {problem!r}")
                filed_args = ran[0]
                for flag, value in (
                    ("--title", "New Skill: Tide tables"),
                    ("--description", "Read them."),
                    ("--stage", "active"),
                    ("--status", "todo"),
                    ("--assignee", "chief_of_staff"),
                    ("--reporter", "user"),
                ):
                    if filed_args[filed_args.index(flag) + 1] != value:
                        raise SmokeFailure(f"a request files {flag} wrong: {filed_args}")
                if filed_args[2] != "add-task" or "ticket_write.py" not in filed_args[1]:
                    raise SmokeFailure("a request is not filed through ticket_write add-task")
                imp = NewSkillDialog(None, lambda *a: _stub_run(stab, *a), lambda t, b: "")
                imp.import_choice.setChecked(True)
                if imp.go_btn.text() != "Import Skill" or imp.import_fields.isHidden():
                    raise SmokeFailure("choosing Import does not open the import")
                if not imp.example.text().startswith("Example: https://github.com/"):
                    raise SmokeFailure("the Import window carries no example address")
                refusals: list[str] = []
                _real_notify = _skills_mod.dialogs.notify
                _skills_mod.dialogs.notify = lambda parent, title, body, *a, **k: refusals.append(
                    body
                )
                try:
                    count = len(listing["skills"])
                    imp.address.setText("https://github.com/someone/risky/tree/main/risky")
                    imp._go()
                    if len(listing["skills"]) != count or imp.imported:
                        raise SmokeFailure("a skill the scan flagged was added")
                    if not any("scripts/x.py:7" in r for r in refusals):
                        raise SmokeFailure("a refused import does not show what the scan found")
                    imp.address.setText("https://github.com/someone/other/tree/main/fresh")
                    imp._go()
                    if not imp.imported or len(listing["skills"]) != count + 1:
                        raise SmokeFailure("a clean import did not land")
                finally:
                    _skills_mod.dialogs.notify = _real_notify
            finally:
                SkillsTab._run = _orig_run
            ok.append(
                "Skills shows cards in Title Case, filters from the top row, "
                "imports in a window of its own, and attaches and removes "
                "from a skill's own view"
            )

            skills_win = MainWindow(mconn)
            modal = skills_win.settings_modal
            nav = list(modal.tabs)
            if nav != ["Agents", "Skills", "Appearance", "Folders", "Sessions", "Reports"]:
                raise SmokeFailure(f"the Settings modal's side nav reads {nav}")
            ok.append(
                "the Settings modal's side nav is Agents, Skills, "
                "Appearance, Folders, Sessions and Reports"
            )

            # The Agents tab: where it sits, what it lists, and that its form
            # contains every property an agent has. The writes are the agent_tools
            # target's; what is checked here is that nothing an agent is goes
            # missing between the reader and the form.
            import config_file as _config
            from PySide6.QtCore import Qt as _Qt
            from ui.agents_tab import AgentDialog, _grant_option, folder_grant
            from ui.theme import LAYOUT as _LAYOUT

            agents_page = skills_win.agents_tab
            listed = [
                agents_page.list.item(i).data(_Qt.ItemDataRole.UserRole)
                for i in range(agents_page.list.count())
            ]
            configured = _config.agent_slugs()
            if listed != configured:
                raise SmokeFailure(f"the Agents tab lists {listed}, config has {configured}")
            ok.append("the Agents tab lists the configured agents")

            # Each tab opens its page under its name; a Settings section turns
            # the Settings stack to that section. isHidden rather than
            # isVisible: the window is never shown here.
            from ui.settings_tab import SECTIONS as _SECTIONS

            skills_win._open_settings("Agents")
            if modal.isHidden() or not skills_win.settings_btn.isChecked():
                raise SmokeFailure("Settings did not open its modal")
            pages_for = {"Agents": skills_win.agents_tab, "Skills": skills_win.skills_tab}
            for name in nav:
                if not modal.tabs[name].isChecked():
                    modal.tabs[name].toggle()
                if modal.heading.text() != name:
                    raise SmokeFailure(f"the {name} tab is headed {modal.heading.text()!r}")
                if modal.pages.currentWidget() is not pages_for.get(name, skills_win.settings_tab):
                    raise SmokeFailure(f"the {name} tab opened the wrong page")
                if (
                    name in _SECTIONS
                    and skills_win.settings_tab.stack.currentIndex() != _SECTIONS.index(name)
                ):
                    raise SmokeFailure(f"the {name} tab shows another section")
                if sum(b.isChecked() for b in modal.tabs.values()) != 1:
                    raise SmokeFailure("more than one Settings tab is open")
            # An edit window opened from a page takes the panel's place, and
            # the panel comes back on the same tab when it closes.
            from PySide6.QtWidgets import QDialog as _QDialog

            modal.tabs["Skills"].toggle()
            editing = _QDialog(skills_win.skills_tab)
            editing.show()
            if not modal.panel.isHidden():
                raise SmokeFailure(
                    "an edit window opened over the Settings panel rather than in its place"
                )
            editing.reject()
            if modal.panel.isHidden() or modal.current_tab() != "Skills":
                raise SmokeFailure(
                    "closing an edit window did not return to the Settings tab it was opened from"
                )
            modal.close_modal()
            if not modal.isHidden() or skills_win.settings_btn.isChecked():
                raise SmokeFailure("closing Settings left its modal or its button standing")
            # An assistive tool presses the Settings button by toggling it.
            skills_win.settings_btn.toggle()
            if modal.isHidden() or modal.current_tab() != "Skills":
                raise SmokeFailure(
                    "toggling the Settings button, as an "
                    "accessibility press does, did not open "
                    "the modal on its last tab"
                )
            skills_win.settings_btn.toggle()
            if not modal.isHidden():
                raise SmokeFailure("unchecking the Settings button left its modal open")
            ok.append(
                "each Settings tab opens its page under its name, an "
                "edit window takes the panel's place and returns to its "
                "tab, and closing clears the Settings button"
            )

            if not agents_page._agents:
                raise SmokeFailure(
                    "the Agents tab lists no agent, so the form contains nothing "
                    "to check: the configuration this ran against declares none"
                )
            record = agents_page._agents[0]
            filled = AgentDialog(None, record, agents_page._run, set(listed), agents_page._skills)
            values = filled.values()
            if filled.slug.text() != record["slug"] or filled.slug.isEnabled():
                raise SmokeFailure("an existing agent's name is wrong or retypable")
            if values["charter"] != record["charter"]:
                raise SmokeFailure("the form does not contain the charter verbatim")
            for key in (
                "description",
                "identity",
                "key_data_paths",
                "key_context_files",
                "notebook_access",
                "env",
            ):
                if values[key] != record[key]:
                    raise SmokeFailure(
                        f"the form does not contain {key}: {values[key]!r} against {record[key]!r}"
                    )
            if filled.dashboards.changed_from(record["dashboard_access"]):
                raise SmokeFailure("an untouched form would rewrite the agent's dashboard access")
            if sorted(values["skills"]) != sorted(record["skills"]):
                raise SmokeFailure(
                    f"the form does not contain the attached skills: "
                    f"{values['skills']} against {record['skills']}"
                )
            for field in (filled.charter, filled.description, filled.identity):
                if field.isReadOnly():
                    raise SmokeFailure("a field on the agent form is read-only")
            if (
                not filled.data_paths.add_btn.isEnabled()
                or not filled.context_files.add_btn.isEnabled()
                or not filled.env.add_btn.isEnabled()
                or not filled.identity_btn.isEnabled()
            ):
                raise SmokeFailure("a list on the agent form cannot be added to")
            if filled.missing():
                raise SmokeFailure(f"a pre-filled form reports empty fields: {filled.missing()}")
            with tempfile.TemporaryDirectory() as _tmp:
                blank_file = Path(_tmp) / "x"
                blank_file.write_text("{}")
                if filled._edit_args(values, filled.extra.values(), blank_file, blank_file) != [
                    record["slug"]
                ]:
                    raise SmokeFailure("an untouched form would still have written")
            # Notebook access is a mode and, under Per Folder, one row per
            # attached folder; a choice survives a trip through Read All.
            access = filled.notebook
            stored = record["notebook_access"]
            if access.mode() != stored.get("mode", "per_folder"):
                raise SmokeFailure("the notebook mode disagrees with the entry")
            if access.choices:
                first = next(iter(access.choices))
                access.choices[first].button("write").setChecked(True)
                access.mode_control.button("read_all").setChecked(True)
                if not access.rows.isHidden():
                    raise SmokeFailure("Read All still shows the folder rows")
                access.mode_control.button("per_folder").setChecked(True)
                if access.values()["folders"].get(first) != "write" or access.rows.isHidden():
                    raise SmokeFailure("a folder choice was lost going through Read All")
            # Every choice on the form is a segmented control or a toggle row:
            # no radio button and no checkbox is left in it.
            from PySide6.QtWidgets import QCheckBox as _QCheckBox
            from PySide6.QtWidgets import QRadioButton as _QRadioButton

            if filled.findChildren(_QRadioButton) or filled.findChildren(_QCheckBox):
                raise SmokeFailure("the agent form still draws a radio button or a checkbox")
            if filled.skills.count():
                turned = filled.skills.item(0)
                was = turned.checkState()
                from PySide6.QtCore import Qt as _QtK
                from PySide6.QtTest import QTest as _QTest

                filled.skills.resize(400, 300)
                filled.skills.show()
                _QTest.mouseClick(
                    filled.skills.viewport(),
                    _QtK.MouseButton.LeftButton,
                    _QtK.KeyboardModifier.NoModifier,
                    filled.skills.visualItemRect(turned).center(),
                )
                if turned.checkState() == was:
                    raise SmokeFailure("a click on a skill's row does not turn it over")
                turned.setCheckState(was)
                filled.skills.hide()
            if filled.extra.isVisibleTo(filled) != bool(record["extra"]):
                raise SmokeFailure(
                    "the Other Keys section shows for an agent with no such keys"
                    if not record["extra"]
                    else "an agent with an unknown key gets no field for it"
                )
            if (
                _grant_option({"path": "x", "access": "read"}) != "--read-path"
                or _grant_option({"path": "x", "access": "write"}) != "--data-path"
            ):
                raise SmokeFailure(
                    "the form does not hand each access to the option that grants it"
                )
            ok.append(
                "opening an agent shows its charter, every key of its "
                "entry and its skills, all of them editable"
            )

            blank = AgentDialog(None, None, agents_page._run, set(listed), agents_page._skills)
            if not blank.creating or blank.slug.text():
                raise SmokeFailure("New Agent did not open a blank form")
            if not blank.slug.isEnabled():
                raise SmokeFailure("a new agent cannot be named")
            if "Agent Charter" not in blank.charter.toPlainText():
                raise SmokeFailure("a new agent does not start from a charter")
            if sorted(blank.missing()) != sorted(["charter", "description", "slug"]):
                if blank.missing() != ["slug", "description"]:
                    raise SmokeFailure(f"a blank form requires the wrong fields: {blank.missing()}")
            blank.charter.setPlainText("")
            import ui.agents_tab as _agents_tab

            refused_with: list[str] = []
            _real_agent_notify = _agents_tab.notify
            _agents_tab.notify = lambda parent, title, body, *a, **k: refused_with.append(body)
            try:
                blank._save()
            finally:
                _agents_tab.notify = _real_agent_notify
            said_back = " ".join(refused_with)
            for field in ("Name", "Description", "Charter"):
                if field not in said_back:
                    raise SmokeFailure(f"a refused save does not name {field}: {said_back!r}")
            if blank.status:
                raise SmokeFailure("a refused save reported a write")
            ok.append(
                "New Agent opens on a starting charter and refuses a save naming every empty field"
            )

            if agents_page.import_btn.text() != "Import Agent":
                raise SmokeFailure("the Agents tab offers no Import Agent")
            reading = _agents_tab.ImportAgentDialog(None, "addon_smoke", "AGENT     addon_smoke")
            if (
                reading.report.toPlainText() != "AGENT     addon_smoke"
                or not reading.report.isReadOnly()
            ):
                raise SmokeFailure(
                    "the import window does not show the agent file's report, read-only"
                )
            ok.append(
                "Import Agent is on the Agents tab, and its window shows the report it is accepting"
            )

            # Cramping is a geometry fault, which is the one thing an offscreen
            # render settles honestly: every field tall enough for what it
            # contains, both columns wide enough to read, and the fields column
            # scrolling rather than squeezing.
            for agent in agents_page._agents:
                sized = AgentDialog(None, agent, agents_page._run, set(listed), agents_page._skills)
                # A stated size rather than whatever screen this runs on, so
                # the check means the same thing everywhere.
                sized.resize(1280, 980)
                sized.show()
                app.processEvents()
                needed = sized.description.document().size().height()
                if sized.description.height() + 1 < needed:
                    raise SmokeFailure(
                        f"{agent['slug']}: the Description field is "
                        f"{sized.description.height()}px for {needed:.0f}px of text"
                    )
                if not sized.fields_scroll.widgetResizable():
                    raise SmokeFailure("the agent form's fields do not scroll")
                fields = sized.fields_scroll.viewport().width()
                charter = sized.charter.width()
                if fields < _LAYOUT["agent_fields_min_w"] - 40:
                    raise SmokeFailure(f"the agent form's field column is {fields}px wide")
                if charter < _LAYOUT["charter_min_w"] - 40:
                    raise SmokeFailure(f"the charter column is {charter}px wide")
                if sized.charter.height() < 400:
                    raise SmokeFailure(f"the charter editor is {sized.charter.height()}px tall")
                # An agent with several folders and variables is taller than
                # any column, so what is guarded is that nothing is squeezed
                # away and the last field can be reached — at the size the form
                # opens at and at the smallest it allows.
                last = sized.extra if sized.extra.isVisibleTo(sized) else sized.skills
                for width, height in ((1280, 980), (sized.minimumWidth(), sized.minimumHeight())):
                    sized.resize(width, height)
                    app.processEvents()
                    inner = sized.fields_scroll.widget()
                    if inner.height() < inner.minimumSizeHint().height():
                        raise SmokeFailure(
                            f"{agent['slug']}: the form squeezes its fields at {width}x{height}"
                        )
                    reach = (
                        sized.fields_scroll.viewport().height()
                        + sized.fields_scroll.verticalScrollBar().maximum()
                    )
                    below = last.y() + last.height()
                    if below > reach:
                        raise SmokeFailure(
                            f"{agent['slug']}: the last field ends {below}px "
                            f"down but only {reach}px can be reached at "
                            f"{width}x{height}"
                        )
                # A path row is a widget inside a list item, and an item takes
                # the height its hint asks for rather than growing to what it
                # contains, so a row whose hint was read before the stylesheet
                # reached it clips the path, the access and the remove button.
                sized.resize(1280, 980)
                app.processEvents()
                for caption, paths in (
                    ("Folders", sized.data_paths),
                    ("Context Files", sized.context_files),
                ):
                    for index in range(paths.list.count()):
                        item = paths.list.item(index)
                        holder = paths.list.itemWidget(item)
                        wanted = holder.minimumSizeHint().height()
                        if item.sizeHint().height() < wanted:
                            raise SmokeFailure(
                                f"{agent['slug']}: a {caption} row is "
                                f"{item.sizeHint().height()}px for {wanted}px "
                                f"of content"
                            )
                        line = holder.layout()
                        for slot in range(line.count()):
                            child = line.itemAt(slot).widget()
                            if child is None:
                                continue
                            short = child.minimumSizeHint().height()
                            if child.height() + 1 < short:
                                raise SmokeFailure(
                                    f"{agent['slug']}: a {caption} row's "
                                    f"{type(child).__name__} is "
                                    f"{child.height()}px for {short}px"
                                )
                sized.hide()
            ok.append(
                "every field on the agent form is tall enough for what it "
                "contains, a path row for the path and the access it has, "
                "and the form scrolls rather than squeezing"
            )

            # The folder list's − and every variable's ✕ ask before they drop a
            # row, and the question names what would go. The question is a modal, so the answer is
            # supplied rather than clicked.
            import ui.agents_tab as _agents_tab
            from PySide6.QtWidgets import QPushButton as _Button

            stocked = next(
                (a for a in agents_page._agents if a.get("key_data_paths") and a.get("env")), None
            )
            if stocked is None:
                raise SmokeFailure("no configured agent has both a folder and a variable")
            guarded = AgentDialog(None, stocked, agents_page._run, set(listed), agents_page._skills)
            asked: list[str] = []
            said = [False]
            real_confirm = _agents_tab.confirm

            def answered(parent, title, body, *args, **kwargs):
                asked.append(f"{title} {body}")
                return said[0]

            def cross(widget, name):
                for button in widget.findChildren(_Button):
                    if button.accessibleName() == name:
                        return button
                raise SmokeFailure(f"a row on the agent form has no ✕ ({name})")

            _agents_tab.confirm = answered
            # Every editable list on the form ends each row in its ✕, adds by
            # one button saying what it adds, and has no + and − left.
            for listed, label in (
                (guarded.data_paths, "Add Folder"),
                (guarded.context_files, "Add File"),
                (guarded.env, "Add Variable"),
            ):
                if listed.add_btn.text() != label:
                    raise SmokeFailure(
                        f"a list's add button says {listed.add_btn.text()!r}, not {label!r}"
                    )
                if any(b.text() in ("+", "\u2212") for b in listed.findChildren(_Button)):
                    raise SmokeFailure("an editable list still carries + and −")
            first_folder = guarded.data_paths.list.itemWidget(guarded.data_paths.list.item(0))
            try:
                for caption, named, button, count in (
                    (
                        "Folders",
                        folder_grant(guarded.data_paths.values()[0])["path"],
                        cross(first_folder, "Remove this folder"),
                        lambda: len(guarded.data_paths.values()),
                    ),
                    (
                        "Environment Variables",
                        guarded.env._rows[0][1].text().strip(),
                        cross(guarded.env._rows[0][0], "Remove this variable"),
                        lambda: len(guarded.env.values()),
                    ),
                ):
                    said[0] = False
                    before = count()
                    button.click()
                    if not asked:
                        raise SmokeFailure(f"{caption}: the ✕ asked nothing")
                    if named not in asked[-1]:
                        raise SmokeFailure(
                            f"{caption}: the question does not name {named}: {asked[-1]!r}"
                        )
                    if count() != before:
                        raise SmokeFailure(f"{caption}: a declined question dropped the row")
                    said[0] = True
                    button.click()
                    if count() != before - 1:
                        raise SmokeFailure(f"{caption}: an accepted question left the row")
            finally:
                _agents_tab.confirm = real_confirm
            ok.append(
                "every editable list on the agent form adds by one named "
                "button, and each folder's and variable's ✕ asks by name "
                "and drops a row only on an accept"
            )

        # ---- closed_at is the finish; the Archive orders by the archival ----
        # A card finished on one day and archived on another separates the two
        # moments, which is the whole of what is guarded here: archiving leaves
        # closed_at alone, and the Archive reads newest-archived first even
        # where that disagrees with newest-finished.
        aconn = sqlite3.connect(":memory:")
        aconn.executescript(schema.read_text())

        def _seed_closed(title, stage, closed_at):
            aconn.execute(
                "INSERT INTO task (title, status, stage, record_type, "
                "created_at, updated_at, closed_at) "
                "VALUES (?, 'done', ?, 'build', '2026-01-01T00:00:00+00:00', ?, ?)",
                (title, stage, closed_at, closed_at),
            )
            return aconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def _logged(task_id, field, to_value, at):
            aconn.execute(
                "INSERT INTO task_event (task_id, at, actor, field, to_value) "
                "VALUES (?,?,'user',?,?)",
                (task_id, at, field, to_value),
            )

        # Seeded before the window is built, so the change log carries these
        # moments rather than the moment the test seeded them.
        finished = "2026-03-03T09:00:00+00:00"
        swept = _seed_closed("Finished in March", "active", finished)
        _logged(swept, "status", "done", finished)
        older = _seed_closed("Finished in May", "archive", "2026-05-05T09:00:00+00:00")
        _logged(older, "status", "done", "2026-05-05T09:00:00+00:00")
        _logged(older, "stage", "archive", "2026-02-02T09:00:00+00:00")
        aconn.commit()

        awin = MainWindow(aconn)
        awin._move_tasks_to_stage([swept], "archive")
        stage, closed = aconn.execute(
            "SELECT stage, closed_at FROM task WHERE id=?", (swept,)
        ).fetchone()
        if stage != "archive":
            raise SmokeFailure("the card was not archived")
        if closed != finished:
            raise SmokeFailure(
                f"archiving rewrote closed_at to {closed!r}; it is the finish, {finished!r}"
            )
        awin._refresh_board()
        order = [awin.archive_results.row_text(i) for i in range(awin.archive_results.count())]
        if len(order) != 2 or f"#{swept}" not in order[0]:
            raise SmokeFailure(f"the Archive is not ordered newest-archived first: {order}")
        ok.append(
            "archiving a card leaves closed_at at the finish, and the "
            "Archive orders by the archival moment"
        )

        # ---- what a re-stamped closed_at can be recovered from --------------
        # The correction reads the change log alone: a card the log has a finish
        # for is set back to it, a card it says nothing about is left as it is
        # rather than guessed at, and a second pass writes nothing.
        from ui.schema_guard import _recover_closed_at_from_the_log

        rconn = sqlite3.connect(":memory:")
        rconn.executescript(schema.read_text())

        def _seed_restamped(title, closed_at, finish=None):
            rconn.execute(
                "INSERT INTO task (title, status, stage, record_type, "
                "created_at, updated_at, closed_at) VALUES "
                "(?, 'done', 'archive', 'build', '2026-01-01T00:00:00+00:00', ?, ?)",
                (title, closed_at, closed_at),
            )
            task_id = rconn.execute("SELECT last_insert_rowid()").fetchone()[0]
            if finish:
                rconn.execute(
                    "INSERT INTO task_event (task_id, at, actor, field, to_value) "
                    "VALUES (?,?,'user','status','done')",
                    (task_id, finish),
                )
            rconn.execute(
                "INSERT INTO task_event (task_id, at, actor, field, to_value) "
                "VALUES (?,?,'user','stage','archive')",
                (task_id, closed_at),
            )
            return task_id

        sweep_stamp = "2026-06-30T12:00:00+00:00"
        true_finish = "2026-06-03T12:00:00+00:00"
        restamped = _seed_restamped("Swept weeks later", sweep_stamp, true_finish)
        unrecorded = _seed_restamped("Finished before the log", sweep_stamp)
        rconn.commit()

        _recover_closed_at_from_the_log(rconn)
        rconn.commit()
        recovered = rconn.execute("SELECT closed_at FROM task WHERE id=?", (restamped,)).fetchone()[
            0
        ]
        if recovered != true_finish:
            raise SmokeFailure(
                f"the correction left closed_at at {recovered!r} rather than the "
                f"finish the log records, {true_finish!r}"
            )
        left = rconn.execute("SELECT closed_at FROM task WHERE id=?", (unrecorded,)).fetchone()[0]
        if left != sweep_stamp:
            raise SmokeFailure(
                f"a card the log contains no finish for was given one anyway: {left!r}"
            )
        settled = dict(rconn.execute("SELECT id, closed_at FROM task"))
        _recover_closed_at_from_the_log(rconn)
        rconn.commit()
        if dict(rconn.execute("SELECT id, closed_at FROM task")) != settled:
            raise SmokeFailure("a second correction pass rewrote a closed_at")
        ok.append(
            "a re-stamped closed_at is recovered from the log, one the "
            "log cannot account for is left alone, and a second pass "
            "writes nothing"
        )

        # ---- closing an epic is what ends a period --------------------------
        # The effort is the boundary: its finished cards leave the board in one
        # act and the report covers exactly them. What is guarded here is the
        # boundary rather than the metrics — that an open card stays, that the
        # standing workstream is refused, that an unreachable notebook costs the
        # report alone, and that a second closure leaves the first report as it
        # was.
        import epic_closure
        from PySide6.QtCore import QDate as _QDate

        econn = sqlite3.connect(":memory:")
        econn.executescript(schema.read_text())
        reports_home = Path(tempfile.mkdtemp(prefix="smoke_reports_"))

        def _epic_row(name, kind=None):
            econn.execute(
                "INSERT INTO epic (name, type, status) VALUES (?,?,'in progress')", (name, kind)
            )
            return econn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def _epic_card(epic_id, title, status):
            econn.execute(
                "INSERT INTO task (epic_id, title, status, stage, record_type, "
                "created_at, updated_at, closed_at) VALUES "
                "(?,?,?,'active','build','2026-02-01T00:00:00+00:00',"
                "'2026-02-10T00:00:00+00:00',?)",
                (epic_id, title, status, "2026-02-10T00:00:00+00:00" if status == "done" else None),
            )
            return econn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def _stage_of(task_id):
            return econn.execute("SELECT stage FROM task WHERE id=?", (task_id,)).fetchone()[0]

        effort = _epic_row("An effort")
        delivered = _epic_card(effort, "Delivered in the effort", "done")
        unfinished = _epic_card(effort, "Never finished", "todo")
        standing = _epic_row("Standing work", epic_closure.STANDING_KIND)
        upkeep = _epic_card(standing, "Upkeep", "done")
        econn.commit()

        closed = epic_closure.close_epic(econn, effort, out_dir=reports_home)
        if not closed.ok:
            raise SmokeFailure(f"closing an epic was refused: {closed.refused}")
        if closed.archived != [delivered]:
            raise SmokeFailure(f"the closure archived {closed.archived}, not the finished card")
        if _stage_of(delivered) != "archive" or _stage_of(unfinished) != "active":
            raise SmokeFailure(
                "closing an epic should archive what it finished and leave an "
                "open card on the board"
            )
        if closed.report is None or not closed.report.ok:
            raise SmokeFailure(f"no report on closure: {closed.report}")
        written = closed.report.written.read_text(encoding="utf-8")
        if "Delivered in the effort" not in written:
            raise SmokeFailure("the report does not cover the epic's own card")
        if "Never finished" in written:
            raise SmokeFailure("the report counts a card the effort never finished")
        ok.append("closing an epic archives its finished cards and reports on exactly them")

        refused = epic_closure.close_epic(econn, standing, out_dir=reports_home)
        if refused.ok:
            raise SmokeFailure("the standing workstream was allowed to close")
        if _stage_of(upkeep) != "active":
            raise SmokeFailure("a refused closure archived a card anyway")
        ok.append("the standing workstream is refused, and a refusal moves nothing")

        # An unreachable notebook: the parent of the folder does not exist, so
        # nothing is written and nothing is materialised in its place.
        elsewhere = _epic_row("Another effort")
        also = _epic_card(elsewhere, "Delivered elsewhere", "done")
        econn.commit()
        unreachable = Path(tempfile.gettempdir()) / "smoke_absent_notebook" / "r"
        lost = epic_closure.close_epic(econn, elsewhere, out_dir=unreachable)
        if _stage_of(also) != "archive":
            raise SmokeFailure("an unreachable notebook folder cost the closure itself")
        if lost.report is None or lost.report.ok:
            raise SmokeFailure("a report was written into a folder that is not there")
        if unreachable.exists():
            raise SmokeFailure("an absent notebook was materialised on disk")
        ok.append("an unreachable notebook costs the report alone")

        # Reopened, finished again, closed again: a second report over what it
        # closed with the second time, and the first left as it was.
        first_report = closed.report.written
        first_text = first_report.read_text(encoding="utf-8")
        econn.execute("UPDATE epic SET status='in progress', closed_at=NULL WHERE id=?", (effort,))
        after = _epic_card(effort, "Delivered after reopening", "done")
        econn.commit()
        again = epic_closure.close_epic(econn, effort, out_dir=reports_home)
        if again.archived != [after]:
            raise SmokeFailure(
                f"the second closure archived {again.archived}, not the card "
                "finished since the first"
            )
        if again.report is None or not again.report.ok:
            raise SmokeFailure(f"no second report: {again.report}")
        if again.report.written == first_report:
            raise SmokeFailure("the second closure overwrote the first report")
        if first_report.read_text(encoding="utf-8") != first_text:
            raise SmokeFailure("the first report was rewritten")
        if "Delivered after reopening" not in again.report.written.read_text(encoding="utf-8"):
            raise SmokeFailure("the second report misses what it closed with")
        ok.append(
            "a reopened epic closing again writes a second report and leaves the first as it was"
        )

        # The epic dialog is the other front end, and closes through the same
        # act. Its report resolves through the environment, since the dialog
        # passes no folder of its own.
        import ui.record_dialog as _record_dialog
        from ui.record_dialog import UnifiedRecordDialog

        dialog_effort = _epic_row("An effort closed from the dialog")
        by_dialog = _epic_card(dialog_effort, "Delivered for the dialog", "done")
        econn.commit()
        edlg = UnifiedRecordDialog(None, econn, mode="epic", record_id=dialog_effort)
        edlg.epic_status_combo.setCurrentIndex(edlg.epic_status_combo.findData("completed"))
        was_env = os.environ.get("BRISTOL_REPORTS_DIR")
        os.environ["BRISTOL_REPORTS_DIR"] = str(reports_home)
        try:
            edlg.save_data()
        finally:
            if was_env is None:
                os.environ.pop("BRISTOL_REPORTS_DIR", None)
            else:
                os.environ["BRISTOL_REPORTS_DIR"] = was_env
        if _stage_of(by_dialog) != "archive":
            raise SmokeFailure("closing an epic from its dialog did not archive its cards")
        if not econn.execute("SELECT closed_at FROM epic WHERE id=?", (dialog_effort,)).fetchone()[
            0
        ]:
            raise SmokeFailure("the dialog closed an epic without stamping it")
        ok.append("the epic dialog closes an epic through the same act as the command line")

        # ---- Clear Done is the second period boundary -----------------------
        # Every card in Done leaves whatever its epic's state, each keeps its
        # own closed_at, one report covers them from the earliest creation to
        # now, and an epic closed afterwards still reports what it finished.
        import clear_done

        cconn = sqlite3.connect(":memory:")
        cconn.executescript(schema.read_text())
        cconn.execute(
            "INSERT INTO epic (name, type, status) VALUES ('A long effort', NULL, 'in progress')"
        )
        long_effort = cconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def _long_card(title, status, created):
            cconn.execute(
                "INSERT INTO task (epic_id, title, status, stage, record_type, "
                "created_at, updated_at, closed_at) VALUES "
                "(?,?,?,'active','build',?,?,?)",
                (
                    long_effort,
                    title,
                    status,
                    created,
                    created,
                    "2026-03-01T00:00:00+00:00" if status == "done" else None,
                ),
            )
            return cconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        swept_a = _long_card("Swept early", "done", "2026-01-05T00:00:00+00:00")
        swept_b = _long_card("Swept late", "done", "2026-02-05T00:00:00+00:00")
        still_open = _long_card("Still open", "todo", "2026-01-01T00:00:00+00:00")
        cconn.commit()
        sweep_now = "2026-04-01T00:00:00+00:00"
        cleared = clear_done.clear_done(cconn, now=sweep_now, out_dir=reports_home)
        stages = dict(cconn.execute("SELECT id, stage FROM task"))
        if sorted(cleared.archived) != [swept_a, swept_b]:
            raise SmokeFailure(f"Clear Done archived {cleared.archived}, not the Done column")
        if stages[still_open] != "active":
            raise SmokeFailure("Clear Done moved a card that is not done")
        if {
            r[0]
            for r in cconn.execute(
                "SELECT closed_at FROM task WHERE id IN (?,?)", (swept_a, swept_b)
            )
        } != {"2026-03-01T00:00:00+00:00"}:
            raise SmokeFailure("Clear Done rewrote a card's closed_at")
        if cleared.report is None or not cleared.report.ok:
            raise SmokeFailure(f"no report on Clear Done: {cleared.report}")
        facts = cleared.report.facts
        if facts["period_start"] != "2026-01-05T00:00:00+00:00" or facts["period_end"] != sweep_now:
            raise SmokeFailure(
                "the Clear Done report should run from the earliest swept "
                f"card's creation to now, not {facts['period_start']} to "
                f"{facts['period_end']}"
            )
        if clear_done.clear_done(cconn, out_dir=reports_home).archived:
            raise SmokeFailure("a second Clear Done found cards to move")
        closed_later = epic_closure.close_epic(cconn, long_effort, out_dir=reports_home)
        if sorted(closed_later.reported) != [swept_a, swept_b]:
            raise SmokeFailure(
                "an epic closed after Clear Done should still report the cards "
                f"Clear Done archived, not {closed_later.reported}"
            )
        ok.append(
            "Clear Done archives the Done column alone, keeps each "
            "closed_at, reports from the first creation to now, and an "
            "epic closed later still reports what it finished"
        )

        # ---- what the projects cost, and upkeep beside them -----------------
        # The window is asked for rather than generated, so what is guarded is
        # the split, the sizing arithmetic and the two answers a window can
        # have: a note, or nothing finished.
        from reports import standing as standing_report_mod

        sconn = sqlite3.connect(":memory:")
        sconn.executescript(schema.read_text())
        sconn.execute(
            "INSERT INTO epic (name, type, status) VALUES ('An effort','development','in progress')"
        )
        an_effort = sconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        sconn.execute(
            "INSERT INTO epic (name, type, status) "
            "VALUES ('Standing work','standing','in progress')"
        )
        upkeep_epic = sconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        def _closed(epic_id, title, estimate, closed_at):
            sconn.execute(
                "INSERT INTO task (epic_id, title, status, stage, record_type, "
                "estimate, created_at, updated_at, closed_at) VALUES "
                "(?,?, 'done','archive','build', ?, '2026-01-01T00:00:00+00:00',"
                " ?, ?)",
                (epic_id, title, estimate, closed_at, closed_at),
            )

        _closed(an_effort, "Big piece of the effort", "L", "2026-05-10T12:00:00+00:00")
        _closed(an_effort, "Small piece of the effort", "S", "2026-05-12T12:00:00+00:00")
        _closed(upkeep_epic, "Upkeep, sized", "M", "2026-05-11T12:00:00+00:00")
        _closed(upkeep_epic, "Upkeep, unsized", None, "2026-05-11T13:00:00+00:00")
        _closed(None, "Finished under no epic", "S", "2026-05-13T12:00:00+00:00")
        _closed(an_effort, "Finished long after the window", "L", "2026-08-01T12:00:00+00:00")
        sconn.commit()

        facts = standing_report_mod.collect(sconn, "2026-05-01", "2026-05-31")
        if facts["total_cards"] != 5:
            raise SmokeFailure(
                f"the window covered {facts['total_cards']} cards, not the 5 "
                "that finished inside it"
            )
        if facts["project"]["cards"] != 2 or facts["standing"]["cards"] != 3:
            raise SmokeFailure(
                "a card finished under no epic belongs to the standing side: "
                f"{facts['project']['cards']} project, "
                f"{facts['standing']['cards']} standing"
            )
        if facts["standing"]["unsized"] != 1:
            raise SmokeFailure("an unsized card should be counted as unsized, not as zero")
        expected = round(standing_report_mod.SPEND["L"] + standing_report_mod.SPEND["S"], 2)
        if facts["project"]["spend"] != expected:
            raise SmokeFailure(
                f"the project side summed to {facts['project']['spend']}, not {expected}"
            )
        if not 0 < facts["standing"]["share"] < 1:
            raise SmokeFailure("each side should carry its share of the window")
        ok.append(
            "a window splits project work from upkeep, sums each as a "
            "share of budget, and counts what is unsized"
        )

        window_home = Path(tempfile.mkdtemp(prefix="smoke_standing_"))
        wrote = standing_report_mod.standing_report(
            sconn, "2026-05-01", "2026-05-31", out_dir=window_home
        )
        if not wrote.ok:
            raise SmokeFailure(f"no standing report written: {wrote}")
        note = wrote.written.read_text(encoding="utf-8")
        for required in (
            "# Standing Work",
            "#### What it cost",
            "| Projects |",
            "| Standing |",
            "#### The projects",
            "#### The upkeep",
        ):
            if required not in note:
                raise SmokeFailure(f"the report is missing {required!r}")
        if "Finished long after the window" in note:
            raise SmokeFailure("the report reached outside its own window")
        empty = standing_report_mod.standing_report(
            sconn, "2026-06-01", "2026-06-30", out_dir=window_home
        )
        if empty.ok or not empty.skipped:
            raise SmokeFailure("a window nothing finished in should write no file and say so")
        if len(list(window_home.glob("bristol_standing_*.md"))) != 1:
            raise SmokeFailure("an empty window left a note behind")
        ok.append(
            "a window with work writes one note, and a window with none writes nothing and says so"
        )

        # The Settings page is where it is asked for, and it opens on a window
        # rather than on nothing.
        import ui.settings_tab as _settings_tab
        from ui.settings_tab import SettingsTab

        page = SettingsTab(conn=sconn)
        if page.report_from.date() >= page.report_to.date():
            raise SmokeFailure("the report row does not open on a period that has any days in it")
        page.report_from.setDate(_QDate.fromString("2026-05-01", "yyyy-MM-dd"))
        page.report_to.setDate(_QDate.fromString("2026-05-31", "yyyy-MM-dd"))
        said = []
        _real_notify = _settings_tab.notify
        _settings_tab.notify = lambda parent, title, body, *a, **k: said.append(title)
        was_env = os.environ.get("BRISTOL_REPORTS_DIR")
        os.environ["BRISTOL_REPORTS_DIR"] = str(window_home)
        try:
            page.report_btn.click()
        finally:
            _settings_tab.notify = _real_notify
            if was_env is None:
                os.environ.pop("BRISTOL_REPORTS_DIR", None)
            else:
                os.environ["BRISTOL_REPORTS_DIR"] = was_env
        if said != ["Report written"]:
            raise SmokeFailure(f"the Settings button said {said}")
        if len(list(window_home.glob("bristol_standing_*.md"))) != 2:
            raise SmokeFailure("the Settings button wrote no second note")
        ok.append("Settings asks for the report over a window it opens already filled in")

        # ---- an epic's kind is chosen, not typed ----------------------------
        # One value means standing and a board has one standing workstream, so
        # what is guarded is that the field cannot be typed into, that an older
        # board's prose survives until someone chooses over it, and that a
        # second standing epic is refused with the reason.
        kconn = sqlite3.connect(":memory:")
        kconn.executescript(schema.read_text())
        kconn.execute(
            "INSERT INTO epic (name, type, status) "
            "VALUES ('Standing work','standing','in progress')"
        )
        the_standing = kconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        kconn.execute(
            "INSERT INTO epic (name, type, status) VALUES "
            "('An older epic','Epic (bounded — archived when the "
            "subsystem lands)','in progress')"
        )
        legacy = kconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        kconn.commit()

        legacy_dialog = UnifiedRecordDialog(None, kconn, mode="epic", record_id=legacy)
        if legacy_dialog.epic_type_combo.currentData() != "project":
            raise SmokeFailure(
                "an epic carrying legacy text should read as a project, not "
                f"{legacy_dialog.epic_type_combo.currentData()!r}"
            )
        if legacy_dialog.epic_type_combo.isEditable():
            raise SmokeFailure("the kind can still be typed into")
        if sorted(
            legacy_dialog.epic_type_combo.itemData(i)
            for i in range(legacy_dialog.epic_type_combo.count())
        ) != ["project", "standing"]:
            raise SmokeFailure("the kind is not the two kinds")
        legacy_dialog.save_data()
        kept = kconn.execute("SELECT type FROM epic WHERE id=?", (legacy,)).fetchone()[0]
        if "Epic (bounded" not in (kept or ""):
            raise SmokeFailure(f"saving without touching the kind rewrote it to {kept!r}")
        ok.append(
            "an epic's kind is one of two choices, and legacy text reads "
            "as project and survives a save that did not touch it"
        )

        said = []
        _real_notify = _record_dialog.notify
        _record_dialog.notify = lambda parent, title, body, *a, **k: said.append(body)
        try:
            legacy_dialog.epic_type_combo.setCurrentIndex(
                legacy_dialog.epic_type_combo.findData("standing")
            )
            legacy_dialog.save_data()
        finally:
            _record_dialog.notify = _real_notify
        if not said or "standing workstream" not in said[-1]:
            raise SmokeFailure(f"a second standing epic was not refused: {said}")
        after = kconn.execute("SELECT type FROM epic WHERE id=?", (legacy,)).fetchone()[0]
        if (after or "").lower() == "standing":
            raise SmokeFailure("a second epic was made standing anyway")
        if (
            kconn.execute(
                "SELECT COUNT(*) FROM epic WHERE LOWER(COALESCE(type,''))='standing'"
            ).fetchone()[0]
            != 1
        ):
            raise SmokeFailure("the board contains more than one standing epic")
        if finishing.standing_epic(kconn) != the_standing:
            raise SmokeFailure("the board's standing workstream moved")
        ok.append(
            "a second standing workstream is refused with the reason, "
            "and the epic keeps the kind it had"
        )

        # ---- a due date, on the few cards that have one --------------------
        # What is guarded: a date can be set, read back and cleared; it is drawn
        # where the card is drawn; a date that has gone by on an unfinished card
        # reads as overdue; and none of it touches the order of a column.
        from datetime import date as _date
        from datetime import timedelta as _timedelta

        dconn = sqlite3.connect(":memory:")
        dconn.executescript(schema.read_text())

        def _dated_card(title, order):
            dconn.execute(
                "INSERT INTO task (title, status, stage, sort_order, "
                "record_type, created_at, updated_at) VALUES "
                "(?, 'todo','active', ?, 'build','2026-01-01','2026-01-01')",
                (title, order),
            )
            return dconn.execute("SELECT last_insert_rowid()").fetchone()[0]

        first = _dated_card("first in the column", 0)
        second = _dated_card("second in the column", 1)
        dconn.commit()

        dwin = MainWindow(dconn)
        dialog = UnifiedRecordDialog(None, dconn, mode="task", record_id=second)
        if dialog.due_edit.date() != _record_dialog.NO_DUE_DATE:
            raise SmokeFailure("a card with no date did not open on 'no date'")
        gone_by = (_date.today() - _timedelta(days=3)).isoformat()
        dialog.due_edit.setDate(_QDate.fromString(gone_by, "yyyy-MM-dd"))
        dialog.save_data()
        stored = dconn.execute("SELECT due_date FROM task WHERE id=?", (second,)).fetchone()[0]
        if stored != gone_by:
            raise SmokeFailure(f"the date saved as {stored!r}, not {gone_by!r}")
        reopened = UnifiedRecordDialog(None, dconn, mode="task", record_id=second)
        if reopened.due_edit.date().toString("yyyy-MM-dd") != gone_by:
            raise SmokeFailure("the saved date did not read back into the field")

        dwin._refresh_board()
        column = dwin.columns["todo"]
        order = [
            column.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(column.list_widget.count())
        ]
        if order != [first, second]:
            raise SmokeFailure(
                f"a due date reordered the column: {order} rather than {[first, second]}"
            )
        payload = None
        for i in range(column.list_widget.count()):
            if column.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == second:
                payload = column.list_widget.item(i).data(_CARD_ROLE)
        if (payload or {}).get("due_date") != gone_by:
            raise SmokeFailure("the card is not carrying its date to be drawn")
        if not (payload or {}).get("overdue"):
            raise SmokeFailure(
                "a date that has gone by on an unfinished card should read as overdue"
            )
        dconn.execute("UPDATE task SET status='done' WHERE id=?", (second,))
        dconn.commit()
        dwin._refresh_board()
        done_column = dwin.columns["done"]
        finished = done_column.list_widget.item(0).data(_CARD_ROLE)
        if finished.get("overdue"):
            raise SmokeFailure("a finished card is not overdue, whatever its date")

        # Cleared by winding the field back past the date it starts on.
        clearing = UnifiedRecordDialog(None, dconn, mode="task", record_id=second)
        clearing.due_edit.setDate(_record_dialog.NO_DUE_DATE)
        clearing.save_data()
        if (
            dconn.execute("SELECT due_date FROM task WHERE id=?", (second,)).fetchone()[0]
            is not None
        ):
            raise SmokeFailure("the date could not be cleared")
        ok.append(
            "a due date is set, read back, drawn, marked overdue once it "
            "has gone by, cleared again, and orders nothing"
        )

        # Editing a finished card leaves its finish alone. Only the transition
        # into done writes closed_at; a save that changes a title is not one.
        finished_long_ago = "2026-04-04T10:00:00+00:00"
        dconn.execute(
            "INSERT INTO task (title, status, stage, sort_order, record_type, "
            "created_at, updated_at, closed_at) VALUES "
            "('finished in April','done','active', 9, 'build','2026-01-01',"
            " '2026-04-04', ?)",
            (finished_long_ago,),
        )
        old_card = dconn.execute("SELECT last_insert_rowid()").fetchone()[0]
        dconn.commit()
        editing = UnifiedRecordDialog(None, dconn, mode="task", record_id=old_card)
        editing.title_edit.setText("finished in April, retitled")
        editing.save_data()
        kept_finish = dconn.execute(
            "SELECT closed_at FROM task WHERE id=?", (old_card,)
        ).fetchone()[0]
        if kept_finish != finished_long_ago:
            raise SmokeFailure(f"editing a finished card moved its finish to {kept_finish!r}")

        # The transition itself still writes it, and leaving done still clears it.
        moving = UnifiedRecordDialog(None, dconn, mode="task", record_id=first)
        moving.status_combo.setCurrentIndex(moving.status_combo.findData("done"))
        moving.save_data()
        stamped = dconn.execute("SELECT closed_at FROM task WHERE id=?", (first,)).fetchone()[0]
        if not stamped:
            raise SmokeFailure("taking a card to done in the dialog stamped nothing")
        reopening = UnifiedRecordDialog(None, dconn, mode="task", record_id=first)
        reopening.status_combo.setCurrentIndex(reopening.status_combo.findData("doing"))
        reopening.save_data()
        if (
            dconn.execute("SELECT closed_at FROM task WHERE id=?", (first,)).fetchone()[0]
            is not None
        ):
            raise SmokeFailure("taking a card out of done left its finish behind")
        ok.append(
            "only the move into done writes a finish: an edit to a "
            "finished card leaves it, and leaving done clears it"
        )
    else:
        ok.append("(skipped MainWindow build — schema.sql not found)")
    return ok
