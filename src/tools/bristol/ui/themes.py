"""ui/themes.py — schemes, themes, modes, the collection and the live palette.

Themes and modes
--------------------------------
A scheme is one complete palette under a name. A **theme** is a pair of them, a
light member and a dark member, and a **mode** is which of the two is drawn:
``light``, ``dark``, or ``system`` to follow the OS. The two are separate
choices, so a picker offers themes rather than every combination of theme and
mode. ``resolve_scheme()`` turns a theme, a mode and the OS state into one
scheme name, and ``set_scheme(name)`` makes it live.

A theme with no dark member is a theme: ``theme_has_dark()`` says which, and
``resolve_scheme()`` draws its light palette whatever the mode and the OS say.
An older build stored the two choices collapsed into one value;
``appearance_choice()`` reads that value back as the theme and mode it gave.

The collection
--------------------------------
Which themes an installation offers is not this module's to decide. It ships
the ones under ``THEME_CHOICES``; the configuration carries the differences —
themes the user added, themes he deleted, a palette stored under a shipped
theme's id where he changed one — and ``resolve_collection()`` puts the two
together. ``install_collection()`` then rewrites ``SCHEMES`` and ``THEMES``
from the result, so a theme the user built is an ordinary theme from that point
and no resolver has a case for it. Storing differences rather than the whole
collection is what lets the themes a later release ships reach an installation
that has already been used.

``collection_differences()`` is the inverse, and what the manage-themes dialog
hands back to be stored.

The live palette
--------------------------------
Every consumer reads the current palette out of the single mutable dict ``C``
rather than binding colour names at import time, which could not be re-pointed
live. ``set_scheme()`` swaps ``C``'s contents in place, so a module that did
``from .themes import C`` or ``from .theme import C`` keeps seeing live values,
and a repaint after a scheme change is all it takes for QPainter-drawn widgets
to re-theme. ``SCHEMES`` and ``THEMES`` are rewritten in place for the same
reason.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Qt

from .palettes import (
    COOL_DARK,
    COOL_LIGHT,
    GITHUB_DARK,
    GITHUB_LIGHT,
    NORD_DARK,
    NORD_LIGHT,
    ROSE_PINE_DARK,
    ROSE_PINE_LIGHT,
    WARM_DARK,
    WARM_LIGHT,
)
from .tokens import SCRIM

# The registry. A name here is what config.local.json stores and what
# set_scheme() takes.
SCHEMES: dict[str, dict[str, str]] = {
    "warm_light": WARM_LIGHT,
    "warm_dark": WARM_DARK,
    "cool_light": COOL_LIGHT,
    "cool_dark": COOL_DARK,
    "github_light": GITHUB_LIGHT,
    "github_dark": GITHUB_DARK,
    "nord_light": NORD_LIGHT,
    "nord_dark": NORD_DARK,
    "rose_pine_light": ROSE_PINE_LIGHT,
    "rose_pine_dark": ROSE_PINE_DARK,
}

# A theme is a (light, dark) pair of scheme names. A theme whose dark member is
# None goes dark nowhere, and every resolver draws its light palette instead.
THEMES: dict[str, tuple[str, str | None]] = {
    "warm": ("warm_light", "warm_dark"),
    "cool": ("cool_light", "cool_dark"),
    "github": ("github_light", "github_dark"),
    "nord": ("nord_light", "nord_dark"),
    "rose_pine": ("rose_pine_light", "rose_pine_dark"),
}

# The scheme whose key set defines a complete palette, and the fallback for a
# name the config asks for and this build does not have.
REFERENCE_SCHEME = "warm_light"
DEFAULT_THEME = "warm"

# The palette every other one is completed against. It is a copy rather than a
# lookup into ``SCHEMES``, because deleting Pumpkin takes ``warm_light`` out of
# ``SCHEMES`` and every completion after that would have nothing to read.
REFERENCE_PALETTE: dict[str, str] = dict(WARM_LIGHT)

# The palette a dark half is seeded and completed against. A dark half filled
# from the light reference is the half-lit palette a dark half is turned on
# whole to avoid, so each half completes against its own kind.
REFERENCE_DARK_PALETTE: dict[str, str] = dict(WARM_DARK)

# Which half of a theme is drawn. SYSTEM_MODE follows the OS; the other two pin
# one half whatever the OS is set to.
LIGHT_MODE = "light"
DARK_MODE = "dark"
SYSTEM_MODE = "system"
DEFAULT_MODE = SYSTEM_MODE

# What this build calls each theme it ships. The value is the theme's id, which
# is what a stored choice names; the caption is the name on screen. The two are
# deliberately separate — a theme can be renamed without migrating a stored
# choice. What the Settings picker offers is the collection rather than this
# list: ``theme_choices()`` is what builds it.
THEME_CHOICES: list[tuple[str, str]] = [
    ("cool", "Frosty"),
    ("github", "GitHub"),
    ("nord", "Nord"),
    ("warm", "Pumpkin"),
    ("rose_pine", "Rosé Pine"),
]

# What this build ships, kept apart from the live SCHEMES and THEMES, which the
# collection rewrites. Restore Shipped Themes reads these, so an edit the user
# makes can always be undone against what the build actually defines.
_SHIPPED_SCHEMES: dict[str, dict[str, str]] = {
    name: dict(palette) for name, palette in SCHEMES.items()
}
_SHIPPED_THEMES: dict[str, tuple[str, str | None]] = dict(THEMES)

MODE_CHOICES: list[tuple[str, str]] = [
    (LIGHT_MODE, "Light"),
    (DARK_MODE, "Dark"),
    (SYSTEM_MODE, "Follow System"),
]

# What a mode the theme in force cannot offer says when the pointer rests on it.
NO_DARK_HALF = "This theme has no dark colors yet."

# What a build before the theme and the mode were separate controls stored in
# one key, and the theme and mode each of its values named. A configuration
# written by such a build comes up as the appearance it named.
LEGACY_APPEARANCE: dict[str, tuple[str, str]] = {
    "warm": ("warm", SYSTEM_MODE),
    "warm_light": ("warm", LIGHT_MODE),
    "warm_dark": ("warm", DARK_MODE),
    "cool": ("cool", SYSTEM_MODE),
    "cool_light": ("cool", LIGHT_MODE),
    "cool_dark": ("cool", DARK_MODE),
    "custom": ("custom", LIGHT_MODE),
}

# The id and the name a palette built when the picker offered one Custom option
# comes back as. Such a palette joins the collection as an ordinary theme, so
# nothing about it is a special case once it is there.
LEGACY_CUSTOM_THEME = "custom"
LEGACY_CUSTOM_NAME = "Custom"

# A palette form's rows, in the order it offers them: a heading, then the keys
# it groups. A key the reference scheme carries and no group names still gets a
# field, under the last heading — ``palette_rows()`` is what places it.
KEY_GROUPS: list[tuple[str, list[str]]] = [
    ("Text", ["INK", "INK_SOFT", "INK_FAINT"]),
    ("Surfaces", ["CANVAS", "SURFACE", "LIST_BG", "BORDER"]),
    ("Accent", ["ACCENT", "ACCENT_DK", "ON_ACCENT"]),
    ("Cards", ["SEL_BG", "HOVER_BG"]),
    ("Badges", ["BUILD_BG", "BUILD_TX", "FIX_BG", "FIX_TX", "NEUTRAL_BG", "NEUTRAL_TX"]),
    (
        "Buttons",
        [
            "BTN_BG",
            "BTN_BORDER",
            "BTN_HOVER",
            "BTN_PRESSED",
            "CREATE_HOVER",
            "DELETE_BG",
            "DELETE_HOVER",
            "DISABLED_BG",
            "DISABLED_TX",
            "MISSING",
        ],
    ),
]

# What each key is called on a palette form's rows. A caption names the thing
# the colour lands on, so a row can be read without the styling contract open.
KEY_CAPTIONS: dict[str, str] = {
    "INK": "Primary Text",
    "INK_SOFT": "Secondary Text",
    "INK_FAINT": "Tertiary Text",
    "CANVAS": "Window Background",
    "SURFACE": "Card Surface",
    "LIST_BG": "Recessed List",
    "BORDER": "Hairline Border",
    "ACCENT": "Accent",
    "ACCENT_DK": "Accent Text",
    "ON_ACCENT": "Text on Accent",
    "SEL_BG": "Selected Card",
    "HOVER_BG": "Hovered Card",
    "BUILD_BG": "Build Pill",
    "BUILD_TX": "Build Pill Text",
    "FIX_BG": "Fix Pill",
    "FIX_TX": "Fix Pill Text",
    "NEUTRAL_BG": "Quiet Pill",
    "NEUTRAL_TX": "Quiet Pill Text",
    "BTN_BG": "Button",
    "BTN_BORDER": "Interactive Edge",
    "BTN_HOVER": "Button Hovered",
    "BTN_PRESSED": "Button Pressed",
    "CREATE_HOVER": "Primary Button Hovered",
    "DELETE_BG": "Delete Button",
    "DELETE_HOVER": "Delete Button Hovered",
    "DISABLED_BG": "Unclickable Button",
    "DISABLED_TX": "Unclickable Button Text",
    "MISSING": "Empty Required Field",
}

# Text that has to be read, over the surface it is read on. Every shipped scheme
# clears CONTRAST_MIN on every pair here, so a palette that does not is one the
# builder names rather than one this product ships.
#
# The unclickable pair is deliberately absent: text a control greys out is meant
# to be hard to read, and every shipped scheme puts it near 2:1.
TEXT_PAIRS: list[tuple[str, str]] = [
    ("INK", "CANVAS"),
    ("INK", "SURFACE"),
    ("INK", "LIST_BG"),
    ("INK", "SEL_BG"),
    ("INK", "HOVER_BG"),
    ("INK", "BTN_BG"),
    ("INK", "BTN_HOVER"),
    ("INK", "BTN_PRESSED"),
    ("INK_SOFT", "CANVAS"),
    ("INK_SOFT", "SURFACE"),
    ("INK_SOFT", "LIST_BG"),
    ("INK_FAINT", "CANVAS"),
    ("INK_FAINT", "SURFACE"),
    ("INK_FAINT", "LIST_BG"),
    ("ACCENT_DK", "CANVAS"),
    ("ACCENT_DK", "SURFACE"),
    ("ACCENT_DK", "SEL_BG"),
    ("ON_ACCENT", "ACCENT"),
    ("ON_ACCENT", "CREATE_HOVER"),
    ("DELETE_BG", "BTN_BG"),
    ("DELETE_HOVER", "BTN_HOVER"),
    ("MISSING", "CANVAS"),
    ("MISSING", "SURFACE"),
    ("BUILD_TX", "BUILD_BG"),
    ("FIX_TX", "FIX_BG"),
    ("NEUTRAL_TX", "NEUTRAL_BG"),
]

# The ratio a pair above has to reach. WCAG AA for body text.
CONTRAST_MIN = 4.5

# A mark that carries a state, over what it sits on: the accent as focus, a
# checkbox's edge, a selected row's bar, and a chosen toggle row's edge and
# check on the list and on its own fill, and a switch's knob on its track; an
# empty required field's edge; and the edge of everything that can be clicked.
MARK_PAIRS: list[tuple[str, str]] = [
    ("ACCENT", "CANVAS"),
    ("ACCENT", "SURFACE"),
    ("MISSING", "SURFACE"),
    ("BTN_BORDER", "CANVAS"),
    ("BTN_BORDER", "SURFACE"),
    ("BTN_BORDER", "LIST_BG"),
    ("ACCENT", "LIST_BG"),
    ("ACCENT", "SEL_BG"),
    ("INK_SOFT", "BTN_BG"),
    ("ON_ACCENT", "ACCENT"),
]

# The ratio a mark above has to reach. WCAG AA for non-text contrast.
MARK_MIN = 3.0

# The single live palette every consumer reads from. Starts at the reference
# scheme; the app calls set_scheme() at startup, on every OS colour-scheme
# change, and whenever the choice is edited in Settings.
C: dict[str, str] = dict(REFERENCE_PALETTE)

_current_scheme = REFERENCE_SCHEME


def theme_has_dark(theme: str | None) -> bool:
    """True when this theme has a dark half to draw."""
    return bool(THEMES.get(theme or "", (None, None))[1])


def default_theme() -> str:
    """The theme a choice falls back to.

    This build's default where the collection still contains it, and the first
    theme in the collection where it does not: a user who deletes Pumpkin is
    left with a fallback rather than with none.
    """
    if DEFAULT_THEME in THEMES:
        return DEFAULT_THEME
    return next(iter(THEMES), DEFAULT_THEME)


def resolve_scheme(theme: str | None, mode: str | None, dark: bool) -> str:
    """The scheme name a theme and a mode mean right now.

    ``system`` resolves against the OS state and the other two modes pin one
    half. A theme with no dark half draws its light one whatever either says,
    which is what makes such a theme an ordinary choice rather than a broken
    one. An unknown theme falls back to the default.
    """
    fallback = THEMES.get(default_theme(), (REFERENCE_SCHEME, None))
    light, dark_member = THEMES.get(theme or "", fallback)
    if dark_member and (mode == DARK_MODE or (mode == SYSTEM_MODE and dark)):
        return dark_member
    return light


def appearance_choice(theme, mode, legacy) -> tuple[str, str]:
    """The theme and mode in force, from the three values config can contain.

    The two current keys win where they name a theme the collection holds.
    Where they do not, the one key an older build wrote is read for the theme
    and mode it named. Where neither answers, the default.
    """
    modes = {name for name, _caption in MODE_CHOICES}
    if isinstance(theme, str) and theme in THEMES:
        return theme, mode if isinstance(mode, str) and mode in modes else DEFAULT_MODE
    if isinstance(legacy, str) and legacy in LEGACY_APPEARANCE:
        named, named_mode = LEGACY_APPEARANCE[legacy]
        if named in THEMES:
            return named, named_mode
    return default_theme(), DEFAULT_MODE


def set_scheme(name: str) -> None:
    """Point the live palette ``C`` at a named scheme, in place, so existing
    ``from .theme import C`` references keep seeing current values.

    A key the named scheme is missing is filled from the reference palette, so
    an incomplete palette shows the wrong colour rather than raising mid-paint.
    ``check_schemes()`` is what names such a gap.
    """
    global _current_scheme
    scheme = SCHEMES.get(name)
    if scheme is None:
        name = resolve_scheme(default_theme(), LIGHT_MODE, False)
        scheme = SCHEMES.get(name, REFERENCE_PALETTE)
    _current_scheme = name
    C.clear()
    C.update(REFERENCE_PALETTE)
    C.update(scheme)


# ---------------------------------------------------------------------------
# The collection: which themes this installation offers
#
# A theme is a record — a name, a light palette, and a dark palette or None —
# under an id that never changes. The configuration carries only the
# differences from what the build ships: the themes the user added, the names
# he deleted, and a palette stored under a shipped theme's name where he
# changed one. An installation that has touched nothing stores nothing, which
# is what lets a later release's new themes reach it.
# ---------------------------------------------------------------------------


def _complete(palette: dict | None, dark: bool = False) -> dict[str, str]:
    """``palette`` with every key the reference palette defines, its own values
    winning. A value that is not a colour string is dropped, so nothing
    unpaintable reaches a scheme. A dark half is completed against the dark
    reference, so a key it does not carry comes back dark."""
    usable = {
        key: value
        for key, value in (palette or {}).items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }
    complete = dict(REFERENCE_DARK_PALETTE if dark else REFERENCE_PALETTE)
    complete.update({key: value for key, value in usable.items() if key in complete})
    return complete


def shipped_collection() -> dict[str, dict]:
    """Every theme this build ships, as records. Restore Shipped Themes puts
    exactly this back."""
    captions = dict(THEME_CHOICES)
    return {
        theme_id: {
            "name": captions.get(theme_id, theme_id.replace("_", " ").title()),
            "light": dict(_SHIPPED_SCHEMES[light]),
            "dark": dict(_SHIPPED_SCHEMES[dark]) if dark else None,
        }
        for theme_id, (light, dark) in _SHIPPED_THEMES.items()
    }


def _baseline(legacy_custom: dict | None = None) -> dict[str, dict]:
    """What the differences are measured against: the shipped themes, and the
    one palette an older build stored outside them."""
    collection = shipped_collection()
    if isinstance(legacy_custom, dict) and legacy_custom and LEGACY_CUSTOM_THEME not in collection:
        collection[LEGACY_CUSTOM_THEME] = {
            "name": LEGACY_CUSTOM_NAME,
            "light": _complete(legacy_custom),
            "dark": None,
        }
    return collection


def _stored_record(raw, fallback_name: str) -> dict | None:
    """One stored theme as a record, or None where it is not one."""
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    dark = raw.get("dark")
    return {
        "name": name.strip() if isinstance(name, str) and name.strip() else fallback_name,
        "light": _complete(raw.get("light")),
        "dark": (_complete(dark, dark=True) if isinstance(dark, dict) and dark else None),
    }


def resolve_collection(
    stored: dict | None = None, legacy_custom: dict | None = None
) -> dict[str, dict]:
    """The themes on offer: what this build ships, with the differences the
    configuration carries applied, ordered by name.

    A collection that came out empty is the shipped one, because an app with no
    theme has nothing to draw.
    """
    stored = stored if isinstance(stored, dict) else {}
    deleted = {name for name in stored.get("deleted", []) if isinstance(name, str)}
    edited = stored.get("edited")
    edited = edited if isinstance(edited, dict) else {}
    added = stored.get("added")
    added = added if isinstance(added, dict) else {}

    collection: dict[str, dict] = {}
    for theme_id, record in _baseline(legacy_custom).items():
        if theme_id in deleted:
            continue
        change = edited.get(theme_id)
        if isinstance(change, dict):
            name = change.get("name")
            if isinstance(name, str) and name.strip():
                record["name"] = name.strip()
            if isinstance(change.get("light"), dict):
                record["light"] = _complete(change["light"])
            if "dark" in change:
                half = change["dark"]
                record["dark"] = (
                    _complete(half, dark=True) if isinstance(half, dict) and half else None
                )
        collection[theme_id] = record

    for theme_id, raw in added.items():
        if not isinstance(theme_id, str) or theme_id in collection:
            continue
        record = _stored_record(raw, theme_id.replace("_", " ").title())
        if record is not None:
            collection[theme_id] = record

    # A change stored against a theme this build no longer ships is the user's
    # theme, kept as one he added: the halves he changed are his, and a half he
    # left alone completes against the reference.
    for theme_id, change in edited.items():
        if (
            not isinstance(theme_id, str)
            or theme_id in collection
            or theme_id in deleted
            or not isinstance(change, dict)
            or not (isinstance(change.get("light"), dict) or isinstance(change.get("dark"), dict))
        ):
            continue
        record = _stored_record(change, theme_id.replace("_", " ").title())
        if record is not None:
            collection[theme_id] = record

    if not collection:
        collection = _baseline(legacy_custom)
    return order_collection(collection)


def order_collection(collection: dict[str, dict]) -> dict[str, dict]:
    """The collection by name, which is the order a picker is read in: scan to
    the letter."""
    return {
        theme_id: collection[theme_id]
        for theme_id in sorted(
            collection, key=lambda key: (collection[key]["name"].casefold(), key)
        )
    }


def collection_differences(collection: dict[str, dict], legacy_custom: dict | None = None) -> dict:
    """What the configuration stores for ``collection``: the themes added, the
    changes to shipped ones, and the shipped names deleted. A theme nobody has
    touched appears in none of them."""
    baseline = _baseline(legacy_custom)
    added: dict[str, dict] = {}
    edited: dict[str, dict] = {}
    for theme_id, record in collection.items():
        base = baseline.get(theme_id)
        if base is None:
            added[theme_id] = {
                "name": record["name"],
                "light": dict(record["light"]),
                "dark": dict(record["dark"]) if record["dark"] else None,
            }
            continue
        change: dict = {}
        if record["name"] != base["name"]:
            change["name"] = record["name"]
        if record["light"] != base["light"]:
            change["light"] = dict(record["light"])
        if record["dark"] != base["dark"]:
            change["dark"] = dict(record["dark"]) if record["dark"] else None
        if change:
            edited[theme_id] = change
    deleted = sorted(theme_id for theme_id in baseline if theme_id not in collection)
    difference: dict = {}
    if added:
        difference["added"] = added
    if edited:
        difference["edited"] = edited
    if deleted:
        difference["deleted"] = deleted
    return difference


def install_collection(collection: dict[str, dict]) -> dict[str, dict]:
    """Make ``collection`` the themes this app draws from: one scheme per half,
    named for the theme it belongs to, and one ``THEMES`` pair per theme.

    Every resolver, the completeness check and the stylesheet read ``SCHEMES``
    and ``THEMES``, so a theme the user built is one of them from here on and
    no path has a case for it.
    """
    SCHEMES.clear()
    THEMES.clear()
    for theme_id, record in collection.items():
        light_name = f"{theme_id}_light"
        SCHEMES[light_name] = _complete(record["light"])
        dark_name = None
        if record.get("dark"):
            dark_name = f"{theme_id}_dark"
            SCHEMES[dark_name] = _complete(record["dark"], dark=True)
        THEMES[theme_id] = (light_name, dark_name)
    return collection


def register_collection(
    stored: dict | None = None, legacy_custom: dict | None = None
) -> dict[str, dict]:
    """Resolve the stored differences and install what they come to."""
    return install_collection(resolve_collection(stored, legacy_custom))


def theme_choices(collection: dict[str, dict]) -> list[tuple[str, str]]:
    """What the Theme picker offers: each theme's id and its name, in the
    collection's own order."""
    return [(theme_id, record["name"]) for theme_id, record in collection.items()]


def theme_id_for(name: str, taken) -> str:
    """A stable id for a theme just named, unused among ``taken``.

    The name changes afterwards and this does not: what the configuration
    stores as the theme in force is the id, so a rename never has to migrate a
    stored choice.
    """
    base = re.sub(r"[^a-z0-9]+", "_", name.strip().casefold()).strip("_")
    candidate = base or "theme"
    suffix = 2
    while candidate in taken:
        candidate = f"{base or 'theme'}_{suffix}"
        suffix += 1
    return candidate


def palette_rows() -> list[tuple[str, list[str]]]:
    """A palette form: a heading and the keys under it, covering every key the
    reference palette defines.

    A key no group names is appended to the last heading rather than left out,
    so a palette gaining a key gains a field with no edit here.
    """
    grouped = {key for _, keys in KEY_GROUPS for key in keys}
    rows = [
        (heading, [key for key in keys if key in REFERENCE_PALETTE]) for heading, keys in KEY_GROUPS
    ]
    loose = [key for key in REFERENCE_PALETTE if key not in grouped]
    if loose:
        rows[-1] = (rows[-1][0], rows[-1][1] + loose)
    return rows


def key_caption(key: str) -> str:
    """What a palette key is called on screen. A key with no caption reads as
    itself, so a palette gaining a key is still editable."""
    return KEY_CAPTIONS.get(key, key.replace("_", " ").title())


def _relative_luminance(colour: str) -> float:
    """The WCAG relative luminance of a ``#RRGGBB`` or ``#AARRGGBB`` colour.

    An alpha channel is ignored: what a translucent colour actually reads
    against depends on what is behind it, and the pairs checked here are opaque.
    """
    digits = colour.strip().lstrip("#")
    if len(digits) == 8:
        digits = digits[2:]
    if len(digits) != 6:
        raise ValueError(f"not a colour: {colour!r}")
    channels = []
    for start in (0, 2, 4):
        value = int(digits[start : start + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """How far apart two colours read, on the WCAG 1:1 to 21:1 scale."""
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def readable_on(background: str) -> str:
    """Black or white, whichever reads further from ``background``.

    The one colour in this product not taken from a scheme. A palette being
    edited is previewed live, so the line naming what is unreadable is drawn in
    the palette that broke it; this is what keeps that one line legible. Falls
    back to the live ink for a value that is not a colour.
    """
    try:
        light = contrast_ratio("#ffffff", background)
        dark = contrast_ratio("#000000", background)
    except ValueError:
        return C["INK"]
    return "#ffffff" if light > dark else "#000000"


def contrast_complaints(palette: dict) -> list[str]:
    """Every pair in ``TEXT_PAIRS`` that ``palette`` puts under ``CONTRAST_MIN``,
    then every mark in ``MARK_PAIRS`` it puts under ``MARK_MIN``, as readable
    lines naming both sides, the ratio and the minimum.

    Empty means every pair reads. A pair either side of which is missing or
    unparseable is skipped: an incomplete palette is ``check_schemes()``'s to
    name, and a field mid-edit is the form's.
    """
    complaints = []
    for pairs, minimum, what in (
        (TEXT_PAIRS, CONTRAST_MIN, "reads"),
        (MARK_PAIRS, MARK_MIN, "shows"),
    ):
        for foreground, background in pairs:
            try:
                ratio = contrast_ratio(palette[foreground], palette[background])
            except (KeyError, ValueError):
                continue
            if ratio < minimum:
                complaints.append(
                    f"{key_caption(foreground)} on {key_caption(background)} "
                    f"{what} at {ratio:.1f}:1, under {minimum:g}:1"
                )
    return complaints


def current_scheme() -> str:
    """The scheme name ``C`` currently contains."""
    return _current_scheme


def check_schemes() -> list[str]:
    """Every key one scheme carries and another does not, as readable lines.

    Empty means every scheme is complete against the union of all of them.
    """
    every_key = set()
    for palette in SCHEMES.values():
        every_key.update(palette)
    complaints = []
    for name in sorted(SCHEMES):
        missing = sorted(every_key - set(SCHEMES[name]))
        if missing:
            complaints.append(f"{name} is missing: {', '.join(missing)}")
    for name, pair in sorted(THEMES.items()):
        for member in pair:
            if member is not None and member not in SCHEMES:
                complaints.append(f"theme {name} names {member}, which is not a scheme")
    return complaints


def is_dark_scheme(app) -> bool:
    """True when the OS colour scheme is Dark, and False wherever that cannot
    be read."""
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


# The colour scheme the platform is held to, or None while it follows the OS.
# Kept here rather than read back from Qt, because Qt reports a held scheme as
# the OS's own.
_held_scheme = None


def scheme_is_dark(name: str) -> bool:
    """True when ``name`` is the dark half of a theme."""
    return any(dark == name for _light, dark in THEMES.values())


def scrim() -> str:
    """The SCRIM for the half of the theme currently drawn."""
    return SCRIM["dark" if scheme_is_dark(current_scheme()) else "light"]


def _hold_platform(app, scheme) -> None:
    """Hold the platform to ``scheme``, a ``Qt.ColorScheme``, or let it follow
    the OS where ``scheme`` is None.

    The hold is recorded before Qt is told, because telling Qt raises its
    colour-scheme signal, which re-enters the theme and must find the hold
    already in place. A Qt without the call leaves the platform following the
    OS."""
    global _held_scheme
    if scheme == _held_scheme:
        return
    previous, _held_scheme = _held_scheme, scheme
    hints = app.styleHints()
    try:
        if scheme is None:
            hints.unsetColorScheme()
        else:
            hints.setColorScheme(scheme)
    except AttributeError:
        _held_scheme = previous


def live_scheme(app, theme: str | None, mode: str | None) -> str:
    """The scheme a theme and a mode mean now, with the platform held to its
    light or dark.

    The platform draws the title bar, the window frame and every control a
    stylesheet leaves to Qt's palette, so it is held to the half Bristol draws:
    a pinned mode holds it, and Follow System lets the OS's own setting through
    before that setting is read.
    """
    if app is None:
        return resolve_scheme(theme, mode, False)
    if mode == SYSTEM_MODE:
        _hold_platform(app, None)
    name = resolve_scheme(theme, mode, is_dark_scheme(app))
    if mode != SYSTEM_MODE:
        _hold_platform(app, Qt.ColorScheme.Dark if scheme_is_dark(name) else Qt.ColorScheme.Light)
    return name
