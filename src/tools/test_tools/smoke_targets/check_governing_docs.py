"""smoke_targets/check_governing_docs.py — the `governing_docs` smoke target, run by smoke.py."""

from __future__ import annotations

from qt_headless import PROJECT_ROOT, tool_on_path
from smoke_targets.failure import SmokeFailure

RESIDENT_CORE_CAP = 1500


def check_governing_docs() -> list[str]:
    ok: list[str] = []
    root = PROJECT_ROOT

    # The line a host is told to type names the entry point, and nothing in the
    # application reads it back. Composed here and resolved against the tree, a
    # renamed entry point fails a check rather than shipping an instruction
    # that points at nothing.
    tool_on_path("bristol")
    import payload

    typed = payload.connect_instructions(root)
    named = typed.splitlines()[0].strip().rstrip(".").split(maxsplit=1)[-1]
    relative = named.split("/", 1)[1] if "/" in named else named
    if not (root / relative).is_file():
        raise SmokeFailure(
            "the typed project instructions name a file that is not there:\n"
            f"    {typed}\n"
            f"  {relative!r} resolves to nothing under {root}. "
            "payload.connect_instructions composes that text."
        )
    ok.append(f"the typed project instructions name {relative}, which is there")

    core = root / "src" / "app.md"
    words = len(core.read_text().split())
    if words > RESIDENT_CORE_CAP:
        raise SmokeFailure(
            f"src/app.md is {words} words, over the {RESIDENT_CORE_CAP}-word cap by "
            f"{words - RESIDENT_CORE_CAP}. Move a rule to the file that owns it "
            f"(src/templates/identity_template.md, the style contract)."
        )
    ok.append(f"resident core is {words} words, within the {RESIDENT_CORE_CAP} cap")

    # The entry files are one text under two names, because two hosts read two
    # different names. Two copies of a rule are two rules the moment one is
    # edited, and nothing else would catch the edit that reached only one.
    entries = {
        name: (root / name).read_text(encoding="utf-8") for name in ("AGENTS.md", "CLAUDE.md")
    }
    if len(set(entries.values())) != 1:
        raise SmokeFailure(
            "AGENTS.md and CLAUDE.md have drifted apart — they are one text "
            "under the two names different hosts read."
        )
    ok.append("the entry files AGENTS.md and CLAUDE.md are one text")
    return ok
