#!/usr/bin/env python3
"""
cos_status.py — the board snapshot chief_of_staff reads at session start.

Everything about how the board is read — ownership, the next-action precedence,
the queue sort, the comments, links, carried summaries, attachments and role
history — is `status_common.py`, and this file calls it. What is here is what is
this front end's own: the fixed slug, the wording of its headings, and the fleet
section, which is the one thing that stays fleet-wide in the chief of staff's
view because coordinating the fleet is that agent's job.

    python3 cos_status.py

Every other agent runs `agent_status.py <slug>` — `src/app.md` Phase 3.1. That
stays two commands rather than one with a flag, because which agent a session is
running as is an identity rather than an option.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import status_common as sc  # noqa: E402

ME = "chief_of_staff"


def main() -> None:
    db_path, conn, cur = sc.open_board()

    print(f"=== CoS Ticket status ({db_path}) ===\n")
    sc.warn_if_low_on_space()

    print(f"DIRECTION — current milestone: {sc.milestone_name(cur)}")
    print(f"ACTIVE EPICS: {sc.active_epic_names(cur)}")

    board = sc.board_tasks(conn)
    print(f"ACTIVE BOARD (stage=active): {len(board)} task(s)\n")

    mine_all = [r for r in board if sc.owned_by(r, ME)]
    mine_q = sc.queue_sort([r for r in board
                            if sc.owned_by(r, ME) and r["status"] in sc.STATUS_RANK])
    others_q = sc.queue_sort([r for r in board
                              if not sc.owned_by(r, ME) and r["status"] in sc.STATUS_RANK])

    sc.print_queue(conn, board, mine_q, ME,
                   label="YOUR NEXT ACTION", show_owner=True)

    # Fleet-wide, unlike every other section: a card any agent left waiting on
    # the user is the user's to clear whoever owns it.
    sc.print_needs_you(board)
    sc.print_body(conn, db_path, ME, mine_all, mine_q)

    print("\n--- FLEET (active-board items owned by OTHER agents — context only, not yours) ---")
    if others_q:
        blockers = sc.unmet_blockers(conn, board)
        for r in others_q:
            print(sc.fmt(r, blockers, show_owner=True))
    else:
        print("  (none)")

    # No handoff section by design. A session's carry-forward IS its cards: work
    # left mid-flight is a `doing` card on the active board with a real owner and
    # pressure. There is no per-agent narrative block, because a note saying
    # "where things stand" is work state living somewhere other than a ticket.
    conn.close()


if __name__ == "__main__":
    main()
