#!/usr/bin/env python3
"""
agent_status.py — the board snapshot every agent but chief_of_staff reads.

Everything about how the board is read — ownership, the next-action precedence,
the queue sort, the comments, links, carried summaries, attachments and role
history — is `status_common.py`, and this file calls it. What is here is what is
this front end's own: the slug it is given, and the wording of its headings. It
prints no fleet section: another agent's card is never this agent's next action,
and coordinating the fleet is chief_of_staff's job.

    python3 agent_status.py <agent_slug>

chief_of_staff runs `cos_status.py` — `src/app.md` Phase 3.1. That stays two
commands rather than one with a flag, because which agent a session is running
as is an identity rather than an option.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import status_common as sc  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2 or not sys.argv[1]:
        sys.exit(
            "agent_status: ERROR — agent_slug is required, e.g.\n"
            "  python3 agent_status.py career_coach\n"
            "(chief_of_staff should use cos_status.py instead)"
        )
    me = sys.argv[1]

    db_path, conn, cur = sc.open_board()

    print(f"=== Agent Ticket Status: {me} ({db_path}) ===\n")
    sc.warn_if_low_on_space()

    print(f"MILESTONE: {sc.milestone_name(cur)}")
    print(f"ACTIVE EPICS ({me}): {sc.active_epic_names(cur, owner=me)}")

    board = sc.board_tasks(conn)
    print(f"ACTIVE BOARD (stage=active): {len(board)} task(s)\n")

    mine_all = [r for r in board if sc.owned_by(r, me)]
    mine_q = sc.queue_sort([r for r in board
                            if sc.owned_by(r, me) and r["status"] in sc.STATUS_RANK])

    sc.print_queue(conn, board, mine_q, me,
                   label="NEXT ACTION", show_owner=False)

    sc.print_needs_you(mine_all)
    sc.print_body(conn, db_path, me, mine_all, mine_q)

    # No handoff section by design — a session's carry-forward is a `doing` card
    # on the active board, never a narrative note.
    conn.close()


if __name__ == "__main__":
    main()
