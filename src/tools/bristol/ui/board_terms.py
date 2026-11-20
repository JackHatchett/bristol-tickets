"""ui/board_terms.py — what the board is made of, and the words a reader sees for it.

The board's columns and the item-data role the card delegate paints from; the
fleet's agents and the caption each slug is read as; the caption each stored
value is shown under, with the hints for size, tier and block reason; and the
check-state test the board's lists use. Every vocabulary follows
``ui/README.md`` §Words on screen.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from PySide6.QtWidgets import QComboBox

# ---------------------------------------------------------------------------
# Board columns and the custom data role the card delegate paints from
# ---------------------------------------------------------------------------
COLUMNS = [
    ("todo", "To Do"),
    ("doing", "Doing"),
    ("done", "Done"),
]

CARD_ROLE = Qt.ItemDataRole.UserRole + 1  # structured payload the delegate paints from

# The fleet's agent slugs plus 'user' — the valid set of owners/originators for
# a task. Kept here as the single source for the record dialog's Owner picker
# . Order: 'user' first (the most common default), then agents
# alphabetically. Mirrors src/agent_identities/*.md.
FLEET_AGENTS = [
    "user",
    "chief_of_staff",
    "client_services",
    "game_designer",
    "librarian",
    "teaching_assistant",
    "writers_room",
]

# Words a caption leaves lowercase unless they open it, and words it capitalises
# whole. The same rule src/tools/skill_tools/skills.py title_phrase applies to a
# skill's name.
_CAPTION_SMALL = {
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "nor",
    "for",
    "so",
    "yet",
    "as",
    "at",
    "by",
    "in",
    "of",
    "on",
    "to",
    "per",
    "via",
    "vs",
    "with",
    "from",
    "into",
}
_CAPTION_UPPER = {"ai", "api", "csv", "html", "jd", "pdf", "qa", "ui", "url"}


def agent_caption(slug: str | None) -> str:
    """An agent's slug as a person reads it: chief_of_staff is Chief of Staff,
    qa_engineer is QA Engineer, user is User. The slug is what every control
    stores; this is only what it shows."""
    words = [w for w in (slug or "user").replace("-", "_").split("_") if w]
    out = []
    for i, word in enumerate(words):
        low = word.lower()
        if low in _CAPTION_UPPER:
            out.append(low.upper())
        elif i and low in _CAPTION_SMALL:
            out.append(low)
        else:
            out.append(low[:1].upper() + low[1:])
    return " ".join(out)


def fleet_agents() -> list[str]:
    """'user' and then every agent this installation configures, read from
    config at call time so a new agent is an owner the moment it exists.
    FLEET_AGENTS stands in where no configuration can be read."""
    try:
        import config_file  # bristol-local; absent in a bare import of theme

        slugs = sorted(config_file.agent_slugs())
    except Exception:
        slugs = []
    return ["user", *slugs] if slugs else list(FLEET_AGENTS)


def fill_agents(combo: QComboBox, slugs: Iterable[str]) -> None:
    """Load a picker with agents: the caption shown, the slug as item data."""
    for slug in slugs:
        combo.addItem(agent_caption(slug), slug)


def select_agent(combo: QComboBox, slug: str | None) -> None:
    """Seat a picker on an agent, adding it where a legacy record carries one
    the list does not, so editing never silently rewrites who owns a card."""
    slug = (slug or "user").strip() or "user"
    index = combo.findData(slug)
    if index < 0:
        combo.addItem(agent_caption(slug), slug)
        index = combo.findData(slug)
    combo.setCurrentIndex(index)


# What a stored value is called on screen. The database keeps the value and a
# reader sees the caption, so a vocabulary can be reworded without a migration —
# `src/tools/bristol/ui/README.md` §Words on screen states the rule and its one
# exception. Each list is ordered as the picker offers it.
STATUS_CHOICES: list[tuple[str, str]] = [
    ("todo", "To Do"),
    ("doing", "Doing"),
    ("done", "Done"),
]

# `active` is captioned Board, because that is the tab the card appears on.
STAGE_CHOICES: list[tuple[str, str]] = [
    ("backlog", "Backlog"),
    ("active", "Board"),
    ("archive", "Archive"),
]

# An epic is a project and ends, or it is the standing workstream and does not.
# `epic.type` carries the difference, and these are the two values written here:
# create_tickets.EPIC_KIND_STANDING is the one that means standing, and every
# other value, including the prose older versions wrote, means project.
EPIC_KIND_CHOICES: list[tuple[str, str]] = [
    ("project", "Project"),
    ("standing", "Standing"),
]

# The vocabulary create_tickets.EPIC_STATUS_CHOICES writes.
EPIC_STATUS_CHOICES: list[tuple[str, str]] = [
    ("not started", "Not Started"),
    ("in progress", "In Progress"),
    ("completed", "Completed"),
    ("on hold", "On Hold"),
]

# A size code as the word a reader who does not know the codes can read.
SIZE_WORDS = {"S": "Small", "M": "Medium", "L": "Large", "XL": "Extra Large"}
SIZE_CHOICES: list[tuple[str, str]] = [("", "Not Sized")] + [
    (code, word) for code, word in SIZE_WORDS.items()
]
SIZE_HINT = (
    "How much of a full usage budget this card would take.\n"
    "Small — under a tenth.    Medium — a tenth to about half.\n"
    "Large — half a budget or more.    Extra Large — more than one; split it."
)

# The depth of processing a card should be worked at. None is not yet rated.
# Mirrors ticket_tools/create_tickets.TIERS; the viewer carries its own copy so
# it depends on no package outside itself. What each tier runs on is config's
# `tiers` key, never this file.
TIER_WORDS = {"max": "Max", "standard": "Standard"}
TIER_CHOICES: list[tuple[str | None, str]] = [
    (None, "No Tier"),
    *((code, word) for code, word in TIER_WORDS.items()),
]
TIER_HINT = (
    "How much thinking this card needs, whatever its size.\n"
    "Max — the session must work out what right looks like,\n"
    "or a wrong answer would be built on unchecked.\n"
    "Standard — the card already says what right looks like."
)

# What kind of thing has stopped a card. None is not blocked. A dependency names
# no card here — that is a 'blocks' link, resolved live — and the prose goes in a
# comment. Mirrors ticket_tools/create_tickets.BLOCK_REASONS; the viewer carries
# its own copy so it depends on no package outside itself.
BLOCK_REASON_CHOICES: list[tuple[str | None, str]] = [
    (None, "Not Blocked"),
    ("dependency", "Dependency"),
    ("decision", "User Decision"),
    ("capability", "Missing Capability"),
    ("transient", "Transient Failure"),
]
BLOCK_REASON_HINT = (
    "What kind of thing has stopped this card. Which card is a Links entry.\n"
    "Dependency — another card.    User Decision — yours to make.\n"
    "Missing Capability — never granted.    Transient Failure — it failed once."
)


def _is_checked(state: object) -> bool:
    """True when a Qt.CheckStateRole value is checked, whether it arrives as a
    Qt.CheckState enum or as the raw int 2."""
    if state is None:
        return False
    val = getattr(state, "value", state)
    if not isinstance(val, int | str):
        return bool(state == Qt.CheckState.Checked)
    try:
        return int(val) == 2  # Qt.Checked == 2
    except (TypeError, ValueError):
        return bool(state == Qt.CheckState.Checked)


def size_label(code: str | None) -> str:
    """A size code as a word. An unrecognised or absent code returns the code
    itself, so a board carrying something else still says what it contains."""
    key = (code or "").strip().upper()
    if not key:
        return ""
    return SIZE_WORDS.get(key, key)


def tier_label(code: str | None) -> str:
    """A tier as a word. An unrecognised code returns itself, and an absent one
    returns nothing, so a card not yet rated draws no pill."""
    key = (code or "").strip().lower()
    if not key:
        return ""
    return TIER_WORDS.get(key, key)
