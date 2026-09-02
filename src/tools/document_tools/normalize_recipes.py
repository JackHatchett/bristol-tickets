#!/usr/bin/env python3
"""
normalize_recipes.py — Recipe Library Standardizer
chief_of_staff / librarian tool

Reads all .md files from the canonical recipe library (a folder in the user's
Markdown notebook — resolved from config markdown_notebook.recipes_dir),
validates them against the Recipe Formatting Standard,
repairs non-conforming files in-place, and writes recipe_audit_log.md.

The library's filename convention is recipe_<snake_case>.md. A file whose name
does not match its H1 title is FLAGGED, not renamed: every recipe is reached by
[[wikilink]] from the Recipe Box hub, so a rename breaks links unless they are
rewritten with it. Pass --rename to opt in; the wikilink rewrite across the
notebook then happens in the same run.

Hub/index notes (any file starting with '_', e.g. _recipe_box.md) are skipped —
they are not recipes and must never be renamed or given recipe frontmatter.

Run from terminal:
    python3 src/tools/document_tools/normalize_recipes.py

Dry-run by default. --write repairs files in place and --rename rewrites
wikilinks across the notebook; both are the user's own commands, because the
recipe folder and the notebook around it sit outside the notebook's writable
zones. An agent runs the dry run, reports what it would change, and hands over
the command.
"""

import re
import sys
import hashlib
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config_tools"))
import data_paths  # noqa: E402
import read_config  # noqa: E402

# ── Config ───────────────────────────────────────────────────────────────────────

def _notebook_path(key: str) -> Path:
    """Resolve a markdown_notebook.<key> folder from config.

    No personal path is hardcoded in /src; the concrete folder lives in the
    git-ignored config, and data_paths owns turning a declaration into a real
    path — a host that reaches the user's folders somewhere other than where
    config names them is that module's case, not this file's.
    """
    declared = read_config.get(f"markdown_notebook.{key}", None)
    if not declared:
        raise SystemExit(
            f"normalize_recipes: config has no markdown_notebook.{key}."
        )
    return data_paths.resolve(declared)

RECIPES_DIR = _notebook_path("recipes_dir")
NOTEBOOK_DIR = _notebook_path("notes_dir")
QUARANTINE  = RECIPES_DIR / "_quarantine"
AUDIT_LOG   = RECIPES_DIR / "recipe_audit_log.md"

VALID_SOURCES = {"personal", "family", "friend", "internet", "unknown", "onenote", "apple-notes"}

UNIT_MAP = {
    r"\btablespoons?\b": "tbsp",
    r"\bteaspoons?\b":   "tsp",
    r"\bcups?\b":        "cup",
    r"\bounces?\b":      "oz",
    r"\bpounds?\b":      "lb",
    r"\bgrams?\b":       "g",
    r"\bkilograms?\b":   "kg",
    r"\bmilliliters?\b": "ml",
    r"\bliters?\b":      "l",
    r"\bpinches?\b":     "pinch",
    r"\bdashes?\b":      "dash",
    # plurals already caught above; add British variants
    r"\btbsps?\b":       "tbsp",
    r"\btsps?\b":        "tsp",
    r"\bfl\s*oz\b":      "oz",
}

REQUIRED_SECTIONS = ["## Ingredients", "## Instructions"]

# Fields the export pipeline writes that we carry forward
PIPELINE_FIELDS   = {"title", "source", "notebook", "section", "tags", "created", "updated"}

# Fields required by the recipe standard
RECIPE_META_FIELDS = ["servings", "prep_time", "cook_time", "total_time", "tags", "source"]

# YAML fields that are migration artifacts — strip from final output.
# 'title' included: the note's title is its H1, and template_recipe.md has no
# title field. Writing one duplicates the H1 and drifts from the template.
STRIP_FIELDS = {"reorg_category", "notebook", "section", "title"}

# Frontmatter key order — matches 02_templates/template_recipe.md, with the
# 'source' field the library also carries slotted next to source_url.
FRONTMATTER_ORDER = [
    "aliases", "tags", "created", "status",
    "servings", "prep_time", "cook_time", "total_time",
    "source", "source_url",
]

# Keywords that suggest a file in the Recipes folder is NOT a recipe
NON_RECIPE_SIGNALS = [
    r"^PLACES",
    r"^SCHEDULE",
    r"^SUN RISES",
    r"^THAILAND",
    r"^The Cabin at",
    r"^Decoration Ideas",
    r"^Errors",
    r"^Chris &",
    r"^Produce$",
    r"^Untitled Note",
    r"Augury",
    r"It's going to rain",
    r"Pages \(On \d",     # export artifact filenames
    r"TheMovement",
    r"not enough butter",
    r"Spa at Taj",
    r"FL Address",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_slug(title: str) -> str:
    """Convert a recipe title to the library's snake_case filename slug.

    The library convention is recipe_<snake_case>.md (recipe_yukon_potato_soup.md),
    not kebab-case. Accented characters fold to ASCII so 'La Viña' → la_vina.
    """
    s = unicodedata.normalize("NFKD", title)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"['‘’ʼ]", "", s)  # drop apostrophes
    s = re.sub(r"[^a-z0-9]+", "_", s)            # everything else is a separator
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def parse_frontmatter(text: str):
    """
    Split a markdown file into (frontmatter_dict, body_text).
    Returns ({}, text) if no YAML frontmatter found.
    Handles the case where the export pipeline wrote frontmatter.
    """
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    yaml_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")

    meta = {}
    current_key = None
    current_list = None

    for line in yaml_block.splitlines():
        # List item continuation
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue

        # New key
        m = re.match(r'^(\w+):\s*(.*)', line)
        if m:
            if current_list is not None and current_key:
                meta[current_key] = current_list
                current_list = None
            current_key = m.group(1)
            val = m.group(2).strip()
            if val == "" or val == "|":
                # Bare key: either the head of a '  - ' list or an empty field.
                # Which one is only known once the following lines are read, so
                # collect into a list and collapse an empty one to None below —
                # otherwise 'source_url:' round-trips as 'source_url: []'.
                current_list = []
                meta[current_key] = current_list
            elif val.startswith("[") and val.endswith("]"):
                # Inline YAML list: [a, b, c]
                items = [i.strip().strip('"\'') for i in val[1:-1].split(",") if i.strip()]
                meta[current_key] = items
                current_key = None
            else:
                val = val.strip('"\'')
                meta[current_key] = val
                current_key = None

    # A bare key that collected no '  - ' items was an empty field, not a list.
    # 'aliases: []' came through the inline branch and stays a real empty list.
    for key, val in list(meta.items()):
        if isinstance(val, list) and not val and f"{key}:" in yaml_block and f"{key}: []" not in yaml_block:
            meta[key] = None

    return meta, body


def build_frontmatter(meta: dict) -> str:
    """Serialize a metadata dict back to a YAML frontmatter block."""
    lines = ["---"]
    seen = set()
    for key in FRONTMATTER_ORDER:
        if key in meta:
            _write_meta_field(lines, key, meta[key])
            seen.add(key)
    # Remaining keys not in order
    for key, val in meta.items():
        if key not in seen:
            _write_meta_field(lines, key, val)
    lines.append("---")
    return "\n".join(lines)


def _write_meta_field(lines, key, val):
    """Serialize one field the way template_recipe.md writes it: an empty list
    is 'key: []' and an unknown value is a bare 'key:', not the literal 'null'."""
    if isinstance(val, list):
        if not val:
            lines.append(f"{key}: []")
        else:
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
    elif val is None or str(val).strip() == "":
        lines.append(f"{key}:")
    else:
        lines.append(f"{key}: {val}")


def normalize_units(text: str) -> str:
    """Replace spelled-out units with standard abbreviations."""
    for pattern, replacement in UNIT_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def strip_export_trash(text: str) -> str:
    """Remove common OneNote/Joplin/Apple Notes export artifacts."""
    # Remove HTML entities
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    # Remove inline **Tags:** #TagName lines (export artifact from OneNote)
    text = re.sub(r"^\*\*Tags:\*\*\s*#.*$", "", text, flags=re.MULTILINE)
    # Remove consecutive blank lines (more than 2 → 1)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are just horizontal rules
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove exported metadata lines like "Created:", "Modified:", UUIDs
    text = re.sub(r"^(Created|Modified|Updated|UUID|ID):\s*.+$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove bare URL lines (export artifacts)
    text = re.sub(r"^\(https?://[^\)]+\)\s*$", "", text, flags=re.MULTILINE)
    # Collapse trailing whitespace on lines
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


def is_likely_not_recipe(path: Path, body: str, meta: dict | None = None) -> bool:
    """Return True if the file is almost certainly not a recipe.

    A note the user has tagged recipe/<something> is a recipe by declaration,
    however terse — the short-body heuristic below otherwise quarantines real
    but very short notes ("Corn on the Cob": one air-fryer line) and deliberate
    stubs pointing at a cookbook.
    """
    tags = ensure_tags_list((meta or {}).get("tags"))
    if any(t == "recipe" or t.startswith("recipe/") for t in tags):
        return False

    name = path.stem
    for pattern in NON_RECIPE_SIGNALS:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    # If body has no food-related words at all and is very short, flag it
    food_words = re.search(
        r"\b(cup|tbsp|tsp|oz|lb|g|ml|ingredient|cook|bake|roast|fry|grill|simmer|boil|"
        r"stir|whisk|chop|slice|serve|heat|oven|degrees|mix|add|pour|dough|sauce)\b",
        body, re.IGNORECASE)
    if not food_words and len(body.strip()) < 200:
        return True
    return False


def extract_servings_from_body(body: str) -> tuple[int | None, str]:
    """
    Find 'Serves N' or 'Makes N servings' in body text.
    Returns (servings_int_or_None, body_with_line_removed).
    """
    m = re.search(r"^Serves\s+(\d+).*$", body, re.MULTILINE | re.IGNORECASE)
    if not m:
        m = re.search(r"^Makes\s+(\d+)\s+serving", body, re.MULTILINE | re.IGNORECASE)
    if not m:
        # Also check for "(Serves 6)" pattern in title or inline
        m = re.search(r"\(Serves\s+(\d+)", body, re.IGNORECASE)
    if m:
        try:
            n = int(m.group(1))
            # Remove the "Serves N" line from body
            cleaned = re.sub(r"^Serves\s+\d+.*\n?", "", body, flags=re.MULTILINE | re.IGNORECASE)
            cleaned = re.sub(r"^Makes\s+\d+\s+serving.*\n?", "", cleaned, flags=re.MULTILINE | re.IGNORECASE)
            return n, cleaned
        except (ValueError, IndexError):
            pass
    return None, body


def normalize_ingredients_section(body: str) -> tuple[str, list]:
    """
    Find the ## Ingredients section and ensure each item is a bullet.
    Returns (updated_body, list_of_changes).
    """
    changes = []

    def fix_ingredients(m):
        heading = m.group(1)
        content = m.group(2)
        lines = content.splitlines()
        new_lines = []
        changed = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append("")
                continue
            # Already a bullet or numbered item
            if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.", stripped):
                new_lines.append(line)
                continue
            # Skip sub-headings
            if stripped.startswith("#"):
                new_lines.append(line)
                continue
            # Plain text ingredient line → add bullet
            new_lines.append(f"- {stripped}")
            changed = True
        if changed:
            changes.append("converted plain-text ingredients to bullet list")
        # Trailing newline keeps the blank line before the next ## heading;
        # without it Ingredients and Instructions run together.
        return heading + "\n".join(new_lines).rstrip() + "\n"

    updated = re.sub(
        r"(## Ingredients\s*\n)(.*?)(?=\n## |\Z)",
        fix_ingredients,
        body,
        flags=re.DOTALL,
    )
    return updated, changes


def normalize_steps_to_instructions(body: str) -> tuple[str, list]:
    """
    Rename ## Steps → ## Instructions and ensure numbered list format.
    Returns (updated_body, list_of_changes).
    """
    changes = []

    # Rename ## Steps to ## Instructions
    if re.search(r"^## Steps\s*$", body, re.MULTILINE):
        body = re.sub(r"^## Steps\s*$", "## Instructions", body, flags=re.MULTILINE)
        changes.append("renamed '## Steps' → '## Instructions'")

    def fix_instructions(m):
        heading = m.group(1)
        content = m.group(2)
        lines = [l for l in content.splitlines() if l.strip()]  # drop blanks first
        new_lines = []
        step_num = 1
        changed = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                # Sub-recipe heading ("### Triple Raspberry Sauce"): keep it
                # surrounded by blank lines and restart the numbering, so a
                # multi-part recipe still reads as separate procedures.
                if new_lines and new_lines[-1] != "":
                    new_lines.append("")
                new_lines.append(line)
                new_lines.append("")
                step_num = 1
                continue
            # Already numbered — drop any bullet the numbering swallowed
            # on an earlier run ("1. - Combine…" → "1. Combine…").
            if re.match(r"^\d+\.\s+", stripped):
                stripped = re.sub(r"^(\d+\.\s+)[-*+]\s+", r"\1", stripped)
                new_lines.append(stripped)
                step_num += 1
                continue
            # A bulleted step is still a step: strip the bullet, then number it,
            # so it becomes "1. Combine…" and never "1. - Combine…".
            stripped = re.sub(r"^[-*+]\s+", "", stripped)
            new_lines.append(f"{step_num}. {stripped}")
            step_num += 1
            changed = True
        if changed:
            changes.append("converted paragraph steps to numbered list")
        return heading + "\n".join(new_lines) + "\n"

    updated = re.sub(
        r"(## Instructions\s*\n)(.*?)(?=\n## |\Z)",
        fix_instructions,
        body,
        flags=re.DOTALL,
    )
    return updated, changes


def extract_h1_title(body: str) -> str | None:
    """Extract the first # Heading from body text."""
    m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return m.group(1).strip() if m else None


def section_present(body: str, heading: str) -> bool:
    return bool(re.search(r"^" + re.escape(heading) + r"\s*$", body, re.MULTILINE))


def ingredients_look_valid(body: str) -> bool:
    """Check if the ## Ingredients section has at least one bullet."""
    m = re.search(r"## Ingredients\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if not m:
        return False
    section = m.group(1)
    return bool(re.search(r"^[-*]\s+\S", section, re.MULTILINE))


def instructions_look_valid(body: str) -> bool:
    """Check if the ## Instructions section has at least one numbered step."""
    m = re.search(r"## Instructions\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    if not m:
        return False
    section = m.group(1)
    return bool(re.search(r"^\d+\.\s+\S", section, re.MULTILINE))


def normalize_time(val: str | None) -> str | None:
    """Normalize a time string to 'X minutes' / 'X hours Y minutes' format."""
    if val is None:
        return None
    s = str(val).strip()
    # If it's a word-form time string, normalize abbreviations first
    if re.search(r"\b(min|minute|hr|hour)", s, re.IGNORECASE):
        s = re.sub(r"\bmins?\b", "minutes", s, flags=re.IGNORECASE)
        s = re.sub(r"\bhrs?\b", "hours", s, flags=re.IGNORECASE)
        return s
    # Pure number → assume minutes
    try:
        n = int(s)
        return f"{n} minutes"
    except ValueError:
        return s


def ensure_tags_list(tags) -> list:
    """Ensure tags is a list of lowercase strings."""
    if tags is None:
        return []
    if isinstance(tags, str):
        # Might be a comma-separated string
        tags = [t.strip().strip('"\'') for t in tags.split(",")]
    return [t.lower() for t in tags if t]


def normalize_source(source) -> str:
    if source is None:
        return "unknown"
    s = str(source).lower().strip()
    return s if s in VALID_SOURCES else "unknown"


# ── Per-file normalization ────────────────────────────────────────────────────

def normalize_file(path: Path, dry_run: bool = True, allow_rename: bool = False) -> dict:
    """
    Normalize a single recipe file. Returns a change report dict.
    If dry_run=True, computes changes but does not write.
    """
    original_text = path.read_text(encoding="utf-8")
    report = {
        "original_path": str(path),
        "new_path": None,
        "changes": [],
        "flags": [],
        "ok": True,
    }

    meta, body = parse_frontmatter(original_text)

    # ── Step 0: Detect non-recipe files ───────────────────────────────────
    if is_likely_not_recipe(path, body, meta):
        report["flags"].append("FILE DOES NOT APPEAR TO BE A RECIPE — move to _quarantine manually")
        report["ok"] = False
        report["quarantine"] = True
        return report

    # ── Step 1: Strip export trash ─────────────────────────────────────────
    # Compare against body.strip(): strip_export_trash() also trims the
    # trailing newline every file has, and comparing to the raw body reported
    # "stripped export artifacts" on all 85 notes on every run, so nothing ever
    # counted as already clean.
    clean_body = strip_export_trash(body)
    if clean_body != body.strip():
        report["changes"].append("stripped export artifacts")
    body = clean_body

    # Remember any frontmatter title before stripping — it is the fallback
    # source of the H1 for notes that never had one.
    title_from_meta = str(meta.get("title", "") or "").strip()

    # Strip migration-only YAML fields
    for field in STRIP_FIELDS:
        if field in meta:
            del meta[field]
            report["changes"].append(f"removed migration field '{field}' from YAML")

    # ── Step 2: Extract / validate title ──────────────────────────────────
    title_from_body = extract_h1_title(body)

    # Prefer body H1 as the human-readable title
    if title_from_body:
        recipe_title = title_from_body
    elif title_from_meta:
        recipe_title = title_from_meta
        # Insert H1 at top of body
        body = f"# {recipe_title}\n\n{body}"
        report["changes"].append(f"inserted H1 heading from metadata title: {recipe_title}")
    else:
        recipe_title = path.stem
        report["flags"].append("could not determine recipe title; using filename as fallback")

    # The H1 IS the title. 'title' is in STRIP_FIELDS and is never written back
    # to frontmatter — template_recipe.md has no such field.

    # ── Step 2b: Extract servings from the title, then the body ───────────
    # Half the library states its yield in the H1 — "(Serves 4 to 6)",
    # "(Makes 12 large pieces)" — so read that before falling back to the body.
    if not meta.get("servings"):
        m = re.search(r"\((serves|makes|yields)\s+([^)]+)\)", recipe_title, re.IGNORECASE)
        if m:
            yield_text = m.group(2).strip()
            meta["servings"] = (int(yield_text) if yield_text.isdigit()
                                else f"{m.group(1).lower()} {yield_text}")
            report["changes"].append(f"extracted servings from title: {meta['servings']}")

    servings_from_body, body = extract_servings_from_body(body)
    if servings_from_body and not meta.get("servings"):
        meta["servings"] = servings_from_body
        report["changes"].append(f"extracted servings from body text: {servings_from_body}")

    # ── Step 3: Normalize metadata fields ─────────────────────────────────

    # servings — an integer where the recipe gives one, but yields are honestly
    # ranges ("4 to 6") or counts ("makes 5 to 7 pancakes"). Those are valid,
    # not defects; only an empty value is worth flagging.
    raw_servings = meta.get("servings")
    if isinstance(raw_servings, list):
        raw_servings = " ".join(str(x) for x in raw_servings)
    raw_servings = str(raw_servings).strip() if raw_servings is not None else ""
    servings_missing = False
    if raw_servings in ("", "None", "[]", "unknown"):
        meta["servings"] = None
        # Flagged after the section check below: a technique note has no yield
        # to state, so warning about it there would be noise.
        servings_missing = True
    else:
        try:
            meta["servings"] = int(raw_servings)
        except (ValueError, TypeError):
            meta["servings"] = raw_servings  # range or count — keep verbatim

    # times
    for field in ["prep_time", "cook_time", "total_time"]:
        raw = meta.get(field)
        normalized = normalize_time(raw) if raw else None
        if normalized is None:
            # Left blank on purpose: template_recipe.md ships prep_time,
            # cook_time and total_time empty, and most of the library never
            # fills them. Flagging all three on every note buried the real
            # defects under 80-odd warnings per run, so an empty time is
            # normalized to blank and left alone.
            meta[field] = None
        else:
            if str(raw) != normalized:
                report["changes"].append(f"normalized {field}: '{raw}' → '{normalized}'")
            meta[field] = normalized

    # Compute total_time if both prep and cook are known and total is missing
    if meta.get("total_time") is None:
        if meta.get("prep_time") and meta.get("cook_time"):
            def extract_minutes(s):
                if s is None:
                    return 0
                hours = re.search(r"(\d+)\s*hour", s, re.IGNORECASE)
                mins  = re.search(r"(\d+)\s*minute", s, re.IGNORECASE)
                total = (int(hours.group(1)) * 60 if hours else 0) + (int(mins.group(1)) if mins else 0)
                return total
            total_mins = extract_minutes(meta["prep_time"]) + extract_minutes(meta["cook_time"])
            if total_mins > 0:
                if total_mins >= 60:
                    h = total_mins // 60
                    m = total_mins % 60
                    meta["total_time"] = f"{h} hours {m} minutes" if m else f"{h} hours"
                else:
                    meta["total_time"] = f"{total_mins} minutes"
                report["changes"].append(f"computed total_time: {meta['total_time']}")

    # tags — the library tags by nested cuisine/course (recipe/italian,
    # recipe/dessert). A nested tag already marks the note as a recipe, so a
    # bare 'recipe' alongside it is redundant; only add one when nothing else
    # in the recipe namespace is present.
    tags = ensure_tags_list(meta.get("tags"))
    if not any(t == "recipe" or t.startswith("recipe/") for t in tags):
        tags.insert(0, "recipe")
        report["changes"].append("added 'recipe' tag")
        report["flags"].append("no recipe/<cuisine> tag — add one (e.g. recipe/italian)")
    meta["tags"] = tags

    # source
    normalized_source = normalize_source(meta.get("source"))
    if normalized_source != meta.get("source"):
        report["changes"].append(f"normalized source: '{meta.get('source')}' → '{normalized_source}'")
    meta["source"] = normalized_source

    # ── Step 4: Normalize units in body ───────────────────────────────────
    normalized_body = normalize_units(body)
    if normalized_body != body:
        report["changes"].append("normalized ingredient units")
    body = normalized_body

    # ── Step 4b: Normalize ## Steps → ## Instructions ─────────────────────
    body, step_changes = normalize_steps_to_instructions(body)
    report["changes"].extend(step_changes)

    # ── Step 4c: Bulletize ingredients ────────────────────────────────────
    body, ing_changes = normalize_ingredients_section(body)
    report["changes"].extend(ing_changes)

    # ── Step 5: Validate required sections ────────────────────────────────
    # A note carrying neither heading but organised under its own ## sections
    # is a technique note, not a prose dump — "Corn on the Cob" is one line
    # under ## Frozen, "Frozen Burgers" is two numbered methods. Those have
    # nothing to repair, so requiring Ingredients/Instructions of them only
    # produces standing noise. Prose with no headings at all, or a note with
    # one of the two headings and not the other, is a real defect.
    present = [s for s in REQUIRED_SECTIONS if section_present(body, s)]
    has_own_sections = bool(re.search(r"^##\s+\S", body, re.MULTILINE))
    technique_note = not present and has_own_sections

    if not technique_note:
        for section in REQUIRED_SECTIONS:
            if not section_present(body, section):
                report["flags"].append(f"missing required section: {section}")
                report["ok"] = False

    if servings_missing and not technique_note and section_present(body, "## Ingredients"):
        report["flags"].append("servings unknown — please fill in manually")

    if section_present(body, "## Ingredients") and not ingredients_look_valid(body):
        report["flags"].append("## Ingredients section has no bullet-list items — check formatting")
        report["ok"] = False

    if section_present(body, "## Instructions") and not instructions_look_valid(body):
        report["flags"].append("## Instructions section has no numbered steps — check formatting")
        report["ok"] = False

    # ── Step 6: Determine the conventional filename ───────────────────────
    # Renaming is opt-in. Every recipe is reached by [[wikilink]] from the
    # Recipe Box hub and from sibling recipes, so an unaccompanied rename
    # silently breaks those links. Default behaviour is to flag the mismatch.
    new_filename = f"recipe_{to_slug(recipe_title)}.md"
    conventional_path = path.parent / new_filename

    if conventional_path == path:
        new_path = path
    elif allow_rename:
        new_path = conventional_path
        report["changes"].append(f"renamed: {path.name} → {new_filename}")
        report["renamed_from"] = path.stem
        report["renamed_to"] = conventional_path.stem
    else:
        new_path = path
        report["flags"].append(
            f"filename does not match title — conventional name is {new_filename}; "
            "re-run with --rename to rename and rewrite wikilinks"
        )

    report["new_path"] = str(new_path)

    # ── Reassemble ─────────────────────────────────────────────────────────
    new_text = build_frontmatter(meta) + "\n\n" + body.strip() + "\n"

    if not dry_run:
        new_path.write_text(new_text, encoding="utf-8")
        if new_path != path:
            path.unlink()

    report["new_text_hash"] = hashlib.sha256(new_text.encode()).hexdigest()[:8]
    return report


# ── Wikilink rewriting ───────────────────────────────────────────────────────

def rewrite_wikilinks(root: Path, renames: dict, dry_run: bool = True) -> list[str]:
    """Repoint [[old]] / [[old|Alias]] / ![[old]] at the new note name.

    A rename without this is a broken Recipe Box, so the two always run
    together. Scans the whole notebook because a recipe can be linked from a
    journal entry or a menu note, not just from the hub.
    """
    if not renames:
        return []
    touched = []
    pattern = re.compile(r"(!?\[\[)([^\]|#^]+)([|#^][^\]]*)?(\]\])")

    def sub(m):
        target = m.group(2).strip()
        new = renames.get(target)
        return f"{m.group(1)}{new}{m.group(3) or ''}{m.group(4)}" if new else m.group(0)

    for md in sorted(root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = pattern.sub(sub, text)
        if updated != text:
            touched.append(str(md.relative_to(root)))
            if not dry_run:
                md.write_text(updated, encoding="utf-8")
    return touched


# ── Audit log ────────────────────────────────────────────────────────────────

def write_audit_log(reports: list[dict], dry_run: bool):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "DRY RUN" if dry_run else "LIVE"

    lines = [
        f"# Recipe Audit Log",
        f"",
        f"Generated: {now} | Mode: {mode}",
        f"",
        f"---",
        f"",
    ]

    total        = len(reports)
    clean        = sum(1 for r in reports if not r["changes"] and not r["flags"] and r.get("ok", True))
    changed      = sum(1 for r in reports if r["changes"])
    flagged      = sum(1 for r in reports if r["flags"])
    needs_review = sum(1 for r in reports if not r.get("ok", True))
    quarantine   = sum(1 for r in reports if r.get("quarantine"))

    lines += [
        f"## Summary",
        f"",
        f"- Total files scanned: {total}",
        f"- Already clean: {clean}",
        f"- Auto-repaired: {changed}",
        f"- Flagged for review: {flagged}",
        f"- Non-recipe files to quarantine: {quarantine}",
        f"- Needs manual fix (missing required sections): {needs_review - quarantine}",
        f"",
        f"---",
        f"",
        f"## Per-File Results",
        f"",
    ]

    for r in sorted(reports, key=lambda x: (not x["flags"], x["original_path"])):
        orig   = Path(r["original_path"]).name
        status = "⚠️ NEEDS REVIEW" if not r["ok"] else ("✅ OK" if not r["changes"] and not r["flags"] else "🔧 REPAIRED")
        lines.append(f"### {orig}")
        lines.append(f"Status: {status}")
        if r.get("new_path") and r["new_path"] != r["original_path"]:
            lines.append(f"Renamed to: `{Path(r['new_path']).name}`")
        if r["changes"]:
            lines.append(f"Changes:")
            for c in r["changes"]:
                lines.append(f"  - {c}")
        if r["flags"]:
            lines.append(f"Flags (manual action needed):")
            for f in r["flags"]:
                lines.append(f"  - ⚠️ {f}")
        lines.append("")

    log_text = "\n".join(lines)

    if not dry_run:
        AUDIT_LOG.write_text(log_text, encoding="utf-8")
        print(f"Audit log written to: {AUDIT_LOG}")
    else:
        print(log_text)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Normalize recipe markdown files.")
    parser.add_argument("--write", action="store_true",
                        help="Actually write changes (default is dry-run)")
    parser.add_argument("--dir", type=Path, default=RECIPES_DIR,
                        help=f"Recipes directory (default: {RECIPES_DIR})")
    parser.add_argument("--rename", action="store_true",
                        help="Also rename files to recipe_<snake_case>.md and rewrite "
                             "[[wikilinks]] across the notebook to match "
                             "(default: report the mismatch only)")
    parser.add_argument("--notebook", type=Path, default=NOTEBOOK_DIR,
                        help="Notebook root scanned for wikilinks when --rename is used")
    args = parser.parse_args()

    recipes_dir = args.dir
    dry_run = not args.write

    if dry_run:
        print(f"DRY RUN — no files will be modified.")
        print(f"Run with --write to commit changes.")
        print(f"Directory: {recipes_dir}")
        print()

    if not recipes_dir.exists():
        print(f"ERROR: Recipes directory not found: {recipes_dir}")
        print("Make sure OneDrive is synced and the path exists.")
        sys.exit(1)

    md_files = sorted(recipes_dir.glob("*.md"))
    # Skip the audit log, and skip hub/index notes (a leading underscore, e.g.
    # _recipe_box.md). A hub is not a recipe: it has no ingredients, must keep
    # its name because everything links TO it, and must not be given recipe
    # frontmatter.
    skipped = [f.name for f in md_files
               if f.name == "recipe_audit_log.md" or f.name.startswith("_")]
    md_files = [f for f in md_files
                if f.name != "recipe_audit_log.md" and not f.name.startswith("_")]

    if skipped:
        print(f"Skipping {len(skipped)} non-recipe file(s): {', '.join(skipped)}")
        print()

    if not md_files:
        print(f"No .md files found in {recipes_dir}")
        sys.exit(0)

    print(f"Found {len(md_files)} recipe files.")
    print()

    reports = []
    for path in md_files:
        print(f"  Processing: {path.name}", end=" ... ", flush=True)
        try:
            report = normalize_file(path, dry_run=dry_run, allow_rename=args.rename)
            reports.append(report)
            status = "⚠️" if not report["ok"] else ("✅" if not report["changes"] else "🔧")
            print(status)
        except Exception as e:
            print(f"❌ ERROR: {e}")
            reports.append({
                "original_path": str(path),
                "new_path": str(path),
                "changes": [],
                "flags": [f"SCRIPT ERROR: {e}"],
                "ok": False,
            })

    print()

    # Renames and their wikilinks move together, or the hub breaks.
    if args.rename:
        renames = {r["renamed_from"]: r["renamed_to"]
                   for r in reports if r.get("renamed_from")}
        if renames:
            touched = rewrite_wikilinks(args.notebook, renames, dry_run=dry_run)
            verb = "would repoint" if dry_run else "repointed"
            print(f"Wikilinks: {verb} {len(renames)} note name(s) "
                  f"across {len(touched)} file(s).")
            for name in touched:
                print(f"  - {name}")
            print()

    write_audit_log(reports, dry_run=dry_run)

    if dry_run:
        print()
        print("Re-run with --write to apply changes.")


if __name__ == "__main__":
    main()
