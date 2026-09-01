#!/usr/bin/env python3
"""
propose_skill.py — file one skill proposal as a card.

    python3 propose_skill.py --skill <name> --reporter <slug> \
        --change "what changes" --body-file <path> \
        [--from-task N] [--attach-to <slug>|none] [--estimate S]

The proposal is a card, never a skill file: writing or patching a skill is a
behaviour change, and `src/app.md` §Content is yours; behavior is
chief_of_staff's assigns every one of them to chief_of_staff working an ordinary
card. This tool is the filing step of
`src/skills/session-review/SKILL.md` §Step 3, mechanised so it is not composed
by hand each time.

The card's description is the proposed text in full, so the card can be applied
without deriving it again. Whether the skill is attached to any agent stays the
user's; the proposal names the agent whose work produced the lesson and stops.
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "ticket_tools"))
sys.path.insert(0, str(HERE.parents[0]))
import skills  # noqa: E402
import create_tickets  # noqa: E402
from config_tools import data_paths  # noqa: E402

TICKET_WRITE = HERE.parents[0] / "ticket_tools" / "ticket_write.py"
OPEN_STAGES = ("active", "backlog")


def board() -> sqlite3.Connection:
    """A read connection to the shared board.

    // A mounted-folder bridge has wedged a database whose rollback journal was
    // written to disk, so every connection this system opens keeps the journal
    // out of the mount.
    """
    conn = sqlite3.connect(str(create_tickets.locate_or_provision()), timeout=10)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn


def existing_proposal(conn: sqlite3.Connection, title: str,
                      description: str) -> sqlite3.Row | None:
    """An open card already carrying this proposal.

    Two cards count as the same proposal: one with this title, and one whose
    description is the same text under a differently-worded title. A finished or
    archived card is not a duplicate — the same lesson learned again is a new
    proposal.
    """
    rows = conn.execute(
        "SELECT id, title, status, stage FROM task "
        "WHERE stage IN (?, ?) AND status != 'done'", OPEN_STAGES).fetchall()
    for row in rows:
        if row["title"] == title:
            return row
    for row in conn.execute(
            "SELECT id, title, status, stage FROM task "
            "WHERE stage IN (?, ?) AND status != 'done' AND description = ?",
            (*OPEN_STAGES, description)):
        return row
    return None


def ticket(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TICKET_WRITE), *args],
                          capture_output=True, text=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--skill", required=True,
                    help="the skill this proposes to add or patch")
    ap.add_argument("--reporter", required=True,
                    help="the agent whose session produced the lesson")
    ap.add_argument("--change", required=True,
                    help="what changes, in a few words, for the title")
    ap.add_argument("--body-file", required=True, type=Path,
                    help="the proposed text in full; - reads standard input")
    ap.add_argument("--from-task", type=int,
                    help="the card the lesson came from")
    ap.add_argument("--attach-to", default=None,
                    help="the agent the skill would serve, or 'none' "
                         "(default: the reporter)")
    ap.add_argument("--estimate", default="S", help="S|M|L|XL (default S)")
    args = ap.parse_args(argv)

    text = (sys.stdin.read() if str(args.body_file) == "-"
            else args.body_file.read_text(encoding="utf-8"))
    if not text.strip():
        print("propose_skill: the proposed text is empty.", file=sys.stderr)
        return 1

    found = skills.find_skill(args.skill, include_quarantine=True)
    verb = "Patch" if found else "Add"
    title = f"{verb} {args.skill} — {args.change}"

    conn = board()
    try:
        clash = existing_proposal(conn, title, text)
    finally:
        conn.close()
    if clash is not None:
        print(f"propose_skill: #{clash['id']} already carries this proposal "
              f"({clash['stage']}/{clash['status']}) — \"{clash['title']}\".")
        print("Add to that card rather than filing a second one.")
        return 1

    made = ticket("add-task", "--title", title, "--record-type", "build",
                  "--assignee", "chief_of_staff", "--reporter", args.reporter,
                  "--actor", args.reporter, "--estimate", args.estimate,
                  "--description", text)
    sys.stdout.write(made.stdout)
    if made.returncode != 0:
        sys.stderr.write(made.stderr)
        return made.returncode

    conn = board()
    try:
        new_id = conn.execute(
            "SELECT id FROM task WHERE title = ? ORDER BY id DESC LIMIT 1",
            (title,)).fetchone()["id"]
    finally:
        conn.close()

    if found:
        # The skill itself, so the card carries the body it patches one hop away.
        # Recorded repository-relative where it is inside the tree: an absolute
        # path is this machine's, and a board is read on more than one.
        skill_md = found[0] / "SKILL.md"
        try:
            skill_md = skill_md.relative_to(data_paths.project_root())
        except ValueError:
            pass
        out = ticket("link-add", "--task", str(new_id), "--uri", str(skill_md),
                     "--label", f"The skill this patches ({found[1]})",
                     "--type", "related", "--author", args.reporter)
        sys.stdout.write(out.stdout or out.stderr)

    if args.from_task:
        out = ticket("link-add", "--task", str(new_id),
                     "--to-task", str(args.from_task), "--type", "related",
                     "--author", args.reporter)
        sys.stdout.write(out.stdout or out.stderr)

    attach = args.reporter if args.attach_to is None else args.attach_to
    if attach and attach != "none":
        out = ticket("add-issue-log", "--task", str(new_id),
                     "--author", args.reporter,
                     "--body", f"Proposed attachment: {attach}, whose work "
                               f"produced this. Attaching is a decision, not "
                               f"part of the proposal.")
        sys.stdout.write(out.stdout or out.stderr)

    print(f"Filed #{new_id} — {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
