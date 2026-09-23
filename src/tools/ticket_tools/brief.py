#!/usr/bin/env python3
"""
brief.py — the whole board, for a reader carrying none of it.

The two status scripts answer "what do I work next": the milestone, the
in-flight epic names on one line, the calling agent's own queue, and its
backlog only when that queue is empty. This answers what is on the board at
all. The user owns every epic whichever agent is in the chair, so this reads
fleet-wide and marks what the caller owns rather than filtering to it.

    python3 brief.py <your slug>

Ownership, the next-action precedence and the queue sort are `status_common.py`
and are called rather than restated. The groupings below — the epics, the cards
under none, the backlog — are this front end's own, as the fleet section is
`cos_status.py`'s.

An epic's next step is its own top open card in board order. `epic.next_action`
is not read here: a next step derived from the cards cannot disagree with them.

The procedure that reads this out to a person is
`src/skills/briefing-the-board/SKILL.md`.
"""

from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_tickets  # noqa: E402  (owns the schema and the status vocabularies)
import status_common as sc  # noqa: E402

# An epic's own description, cut to the length that still says what the epic is
# for. The whole of it is on the epic.
ABOUT_CHARS = 260

# How many just-closed cards say what has been happening. Bounded, because the
# briefing's subject is open work and the archive is a tab.
RECENT_CARDS = 8


def all_tasks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Every task on the board, every tab, with its epic joined."""
    return conn.execute(
        "SELECT t.id, t.title, t.status, t.stage, t.tier, t.sort_order, "
        "       t.estimate, t.assignee, t.block_reason, t.epic_id, "
        "       COALESCE(e.name, '(no epic)') AS epic, e.owner AS epic_owner "
        "FROM task t LEFT JOIN epic e ON t.epic_id = e.id"
    ).fetchall()


def in_flight_epics(cur: sqlite3.Cursor) -> list[sqlite3.Row]:
    """The epics the board counts as live, in the vocabulary create_tickets
    owns."""
    ph = ",".join("?" * len(create_tickets.EPIC_STATUS_IN_FLIGHT))
    return cur.execute(
        f"SELECT id, name, owner, status, type, description FROM epic "
        f"WHERE status IN ({ph}) ORDER BY id",
        tuple(create_tickets.EPIC_STATUS_IN_FLIGHT),
    ).fetchall()


def is_open(row: sqlite3.Row) -> bool:
    return row["stage"] == "active" and row["status"] in sc.STATUS_RANK


def line(row: sqlite3.Row, blockers: dict) -> str:
    """One card, carrying its id, because a briefing is answered by naming
    one."""
    held = blockers.get(row["id"]) or []
    flag = " [blocked by " + ", ".join(f"#{b}" for b in held) + "]" if held else ""
    reason = (row["block_reason"] or "").strip()
    if reason and reason != "dependency":
        flag += f" [blocked: {reason}]"
    who = (row["assignee"] or "").strip() or f"(epic:{row['epic_owner']})"
    return (f"     #{row['id']:<4} {row['status']:5} {row['estimate'] or '-':>3} "
            f"{sc.tier_word(row['tier']):8}  {row['title']}  <{who}>{flag}")


def about(text: str | None) -> list[str]:
    """The epic's own description, cut to ABOUT_CHARS."""
    if not text:
        return []
    flat = " ".join(text.split())
    if len(flat) > ABOUT_CHARS:
        flat = flat[:ABOUT_CHARS].rsplit(" ", 1)[0] + " …"
    return ["     about " + flat]


def print_group(rows: list[sqlite3.Row], blockers: dict) -> None:
    """A set of cards in queue order — `status_common.queue_sort` owns it."""
    for r in sc.queue_sort(rows):
        print(line(r, blockers))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: brief.py <your agent slug>")
    me = sys.argv[1]

    db_path, conn, cur = sc.open_board()
    print(f"=== BOARD BRIEFING ({db_path}) ===\n")
    print(f"MILESTONE: {sc.milestone_name(cur)}")

    rows = all_tasks(conn)
    board = [r for r in rows if r["stage"] == "active"]
    blockers = sc.unmet_blockers(conn, rows)

    by_epic: dict = {}
    for r in rows:
        by_epic.setdefault(r["epic_id"], []).append(r)

    epics = in_flight_epics(cur)
    standing = [e for e in epics
                if (e["type"] or "") == create_tickets.EPIC_KIND_STANDING]
    projects = [e for e in epics if e not in standing]
    live = [e for e in projects
            if any(is_open(r) for r in by_epic.get(e["id"], []))]
    idle = [e for e in projects if e not in live]

    print(f"\n{'=' * 72}\nEPICS IN FLIGHT, WITH CARDS OPEN ({len(live)})\n{'=' * 72}")
    for e in live:
        held = by_epic.get(e["id"], [])
        opens = [r for r in held if is_open(r)]
        doing = [r for r in opens if r["status"] == "doing"]
        done = [r for r in held if r["status"] == "done"]
        back = [r for r in held if r["stage"] == "backlog"]
        yours = " [yours]" if me in (e["owner"] or "") else ""
        print(f"\n  #{e['id']} {e['name']}{yours}")
        print(f"     owner {e['owner'] or '(none)'} · {e['status']} · "
              f"{len(opens)} open ({len(doing)} doing) · {len(done)} done · "
              f"{len(back)} in backlog")
        for extra in about(e["description"]):
            print(extra)
        print("     open cards, the first one its next step")
        print_group(opens, blockers)

    print(f"\n{'=' * 72}\nEPICS IN FLIGHT WITH NOTHING ON THE BOARD ({len(idle)})"
          f"\n{'=' * 72}\n")
    if idle:
        for e in idle:
            held = by_epic.get(e["id"], [])
            done = [r for r in held if r["status"] == "done"]
            back = [r for r in held if r["stage"] == "backlog"]
            yours = " [yours]" if me in (e["owner"] or "") else ""
            print(f"  #{e['id']} {e['name']}{yours}")
            print(f"     owner {e['owner'] or '(none)'} · {len(done)} done · "
                  f"{len(back)} in backlog · nothing open")
    else:
        print("     (none)")

    live = {e["id"] for e in epics}
    stranded = sorted({r["epic_id"] for r in board if is_open(r)
                       and r["epic_id"] is not None and r["epic_id"] not in live})
    if stranded:
        print(f"\n{'=' * 72}\nOPEN CARDS UNDER AN EPIC THAT IS NOT IN FLIGHT "
              f"({len(stranded)})\n{'=' * 72}")
        for eid in stranded:
            group = [r for r in by_epic.get(eid, []) if is_open(r)]
            print(f"\n  #{eid} {group[0]['epic']}")
            print_group(group, blockers)

    for e in standing:
        held = by_epic.get(e["id"], [])
        opens = [r for r in held if is_open(r)]
        done = [r for r in held if r["status"] == "done"]
        back = [r for r in held if r["stage"] == "backlog"]
        print(f"\n{'=' * 72}\nSTANDING WORK — #{e['id']} {e['name']} "
              f"({len(opens)} open)\n{'=' * 72}")
        print(f"\n     never closes · {len(done)} done · {len(back)} in backlog")
        if opens:
            print_group(opens, blockers)

    loose = [r for r in rows if r["epic_id"] is None
             and (is_open(r) or r["stage"] == "backlog")]
    print(f"\n{'=' * 72}\nUNTRIAGED — NO EPIC, NOT STANDING ({len(loose)})"
          f"\n{'=' * 72}\n")
    if loose:
        print("     each of these needs an epic or the standing workstream")
        print_group(loose, blockers)
    else:
        print("     (none)")

    backlog = [r for r in rows if r["stage"] == "backlog"]
    print(f"\n{'=' * 72}\nBACKLOG ({len(backlog)})\n{'=' * 72}")
    if backlog:
        seen: set = set()
        for r in sorted(backlog, key=lambda r: (r["epic"], r["sort_order"], r["id"])):
            if r["epic"] not in seen:
                seen.add(r["epic"])
                print(f"\n  under {r['epic']}")
            print(line(r, blockers))
    else:
        print("\n     (none)")

    recent = conn.execute(
        "SELECT t.id, t.title, t.assignee, t.closed_at, "
        "       COALESCE(e.name, '(no epic)') AS epic "
        "FROM task t LEFT JOIN epic e ON t.epic_id = e.id "
        "WHERE t.status = 'done' AND t.closed_at IS NOT NULL "
        "ORDER BY t.closed_at DESC LIMIT ?", (RECENT_CARDS,)).fetchall()
    print(f"\n{'=' * 72}\nFINISHED MOST RECENTLY ({len(recent)})\n{'=' * 72}\n")
    for r in recent:
        who = (r["assignee"] or "").strip() or "(unassigned)"
        print(f"     #{r['id']:<4} {(r['closed_at'] or '')[:10]}  {r['title']}  "
              f"<{who}>  [{r['epic']}]")

    mine_q = sc.queue_sort([r for r in board if sc.owned_by(r, me)
                            and r["status"] in sc.STATUS_RANK])
    print(f"\n{'=' * 72}\nWHERE THE QUEUE WOULD START ({me})\n{'=' * 72}\n")
    if mine_q:
        nxt, _, waiting = sc.next_action(conn, board, mine_q)
        if nxt is not None:
            print(f"  #{nxt['id']} {nxt['title']}  [{nxt['epic']}]")
            print(f"  {len(mine_q)} card(s) in this agent's queue, this one first.")
        else:
            print("  none — every card in this agent's queue is waiting on "
                  + ", ".join(f"#{b}" for b in waiting) + ".")
    else:
        print(f"  nothing on the active board for {me}.")

    conn.close()


if __name__ == "__main__":
    main()
