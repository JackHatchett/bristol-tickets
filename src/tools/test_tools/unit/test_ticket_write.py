"""ticket_write.py: the write CLI every agent uses, run against a temporary board."""

from __future__ import annotations

import sqlite3

import pytest
import ticket_write
from conftest import add_card, add_epic, card


def rows(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_connect_builds_the_log_tables_and_the_change_log(db_path, monkeypatch):
    monkeypatch.setattr(ticket_write, "resolve_db_path", lambda: db_path)
    conn = ticket_write.connect("tester")
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
        assert {"issue_log", "task_event", "task_link"} <= tables
        task = add_card(conn, "logged", None)
        conn.execute("UPDATE task SET status='doing' WHERE id=?", (task,))
        conn.commit()
        assert conn.execute(
            "SELECT actor, from_value, to_value FROM task_event "
            "WHERE task_id=? AND field='status' ORDER BY id",
            (task,),
        ).fetchall() == [("tester", None, "todo"), ("tester", "todo", "doing")]
    finally:
        conn.close()


def test_install_change_log_records_a_redacted_description(db_path):
    conn = sqlite3.connect(db_path)
    try:
        ticket_write.install_change_log(conn, "tester")
        task = add_card(conn, "card", None)
        conn.execute("UPDATE task SET description='secret' WHERE id=?", (task,))
        conn.commit()
        assert conn.execute(
            "SELECT to_value FROM task_event WHERE task_id=? AND field='description'", (task,)
        ).fetchall() == [("(changed)",)]
    finally:
        conn.close()


def test_add_epic_refuses_a_second_standing_epic(cli, db_path):
    cli("add-epic", "--name", "Upkeep", "--owner", "chief_of_staff", "--type", "standing")
    with pytest.raises(SystemExit):
        cli("add-epic", "--name", "More", "--owner", "chief_of_staff", "--type", "standing")
    assert rows(db_path, "SELECT name FROM epic") == [("Upkeep",)]


def test_add_task_appends_to_the_bottom_of_its_column(cli, db_path):
    cli("add-task", "--title", "one", "--stage", "active", "--tier", "max", "--estimate", "S")
    cli("add-task", "--title", "two", "--stage", "active")
    assert rows(db_path, "SELECT title, status, sort_order, tier FROM task ORDER BY id") == [
        ("one", "todo", 0, "max"),
        ("two", "todo", 1, None),
    ]


def test_add_task_folds_a_backlog_status_into_the_backlog_stage(cli, db_path):
    cli("add-task", "--title", "later", "--status", "backlog")
    assert rows(db_path, "SELECT stage, status FROM task") == [("backlog", "todo")]


def test_add_task_refuses_an_unknown_record_type(cli, db_path):
    with pytest.raises(SystemExit):
        cli("add-task", "--title", "x", "--stage", "active", "--record-type", "chore")
    assert rows(db_path, "SELECT COUNT(*) FROM task") == [(0,)]


def test_update_task_changes_content_and_not_position(cli, conn):
    task = add_card(conn, "old", None, status="doing", sort_order=3)
    cli("update-task", "--id", str(task), "--title", "new", "--estimate", "M")
    row = card(conn, task)
    assert (row["title"], row["estimate"], row["status"], row["sort_order"]) == (
        "new",
        "M",
        "doing",
        3,
    )


def test_update_task_refuses_a_missing_epic(cli, conn):
    task = add_card(conn, "card", None)
    with pytest.raises(SystemExit):
        cli("update-task", "--id", str(task), "--epic-id", "77")


def test_update_task_status_done_archives_standing_work(cli, conn):
    standing = add_epic(conn, "Upkeep", "standing")
    task = add_card(conn, "chore", standing, status="doing")
    cli("update-task-status", "--id", str(task), "--status", "done")
    row = card(conn, task)
    assert (row["status"], row["stage"]) == ("done", "archive")
    assert row["closed_at"] is not None


def test_update_task_status_done_keeps_project_work_in_done(cli, conn):
    project = add_epic(conn, "Project")
    task = add_card(conn, "feature", project, status="doing")
    cli("update-task-status", "--id", str(task), "--status", "done")
    row = card(conn, task)
    assert (row["status"], row["stage"]) == ("done", "active")


def test_update_task_status_out_of_done_reopens_archived_work(cli, conn):
    standing = add_epic(conn, "Upkeep", "standing")
    task = add_card(conn, "chore", standing, status="done", stage="archive")
    cli("update-task-status", "--id", str(task), "--status", "todo")
    row = card(conn, task)
    assert (row["status"], row["stage"], row["closed_at"]) == ("todo", "active", None)


def test_update_task_status_done_clears_the_block_reason(cli, conn):
    task = add_card(conn, "card", None, status="doing")
    cli("update-task-status", "--id", str(task), "--status", "doing", "--block-reason", "decision")
    assert card(conn, task)["block_reason"] == "decision"
    cli("update-task-status", "--id", str(task), "--status", "done")
    assert card(conn, task)["block_reason"] is None


def test_update_task_status_refuses_a_block_reason_on_a_done_card(cli, conn):
    task = add_card(conn, "card", None, status="doing")
    with pytest.raises(SystemExit):
        cli(
            "update-task-status",
            "--id",
            str(task),
            "--status",
            "done",
            "--block-reason",
            "decision",
        )
    assert card(conn, task)["status"] == "doing"


def test_set_stage_moves_a_card_to_the_bottom_of_another_tab(cli, conn):
    add_card(conn, "parked", None, stage="backlog", sort_order=2)
    task = add_card(conn, "card", None)
    cli("set-stage", "--id", str(task), "--stage", "backlog")
    row = card(conn, task)
    assert (row["stage"], row["sort_order"]) == ("backlog", 3)


def test_set_order_moves_a_card_and_renumbers_its_column(cli, conn):
    first = add_card(conn, "a", None, sort_order=0)
    second = add_card(conn, "b", None, sort_order=5)
    third = add_card(conn, "c", None, sort_order=9)
    cli("set-order", "--id", str(third), "--position", "1")
    assert [card(conn, t)["sort_order"] for t in (third, first, second)] == [0, 1, 2]


def test_add_issue_log_records_a_comment_and_refuses_a_missing_card(cli, conn, db_path):
    task = add_card(conn, "card", None)
    cli("add-issue-log", "--task", str(task), "--author", "tester", "--body", "note")
    assert rows(db_path, "SELECT task_id, author, body FROM issue_log") == [
        (task, "tester", "note")
    ]
    with pytest.raises(SystemExit):
        cli("add-issue-log", "--task", "999", "--author", "tester", "--body", "note")


def test_link_add_stores_one_row_read_from_both_ends(cli, conn, db_path):
    low = add_card(conn, "low", None)
    high = add_card(conn, "high", None)
    cli("link-add", "--task", str(high), "--to-task", str(low))
    cli("link-add", "--task", str(low), "--to-task", str(high))
    assert rows(db_path, "SELECT task_id, other_id, dep_type FROM task_link") == [
        (low, high, "related")
    ]


def test_link_add_blocked_by_stores_the_blocker_first_and_retypes(cli, conn, db_path):
    waiting = add_card(conn, "waiting", None)
    blocker = add_card(conn, "blocker", None)
    cli("link-add", "--task", str(waiting), "--to-task", str(blocker), "--type", "blocked-by")
    assert rows(db_path, "SELECT task_id, other_id, dep_type FROM task_link") == [
        (blocker, waiting, "blocks")
    ]
    cli("link-add", "--task", str(waiting), "--to-task", str(blocker))
    assert rows(db_path, "SELECT COUNT(*), MAX(dep_type) FROM task_link") == [(1, "related")]


def test_link_add_refuses_a_self_link(cli, conn):
    task = add_card(conn, "card", None)
    with pytest.raises(SystemExit):
        cli("link-add", "--task", str(task), "--to-task", str(task))


def test_link_add_uri_link(cli, conn, db_path):
    task = add_card(conn, "card", None)
    cli("link-add", "--task", str(task), "--uri", "https://example.org", "--label", "Example")
    assert rows(db_path, "SELECT kind, task_id, uri, label FROM task_link") == [
        ("uri", task, "https://example.org", "Example")
    ]


def test_link_list_reads_a_dependency_from_each_end(cli, conn, capsys):
    blocker = add_card(conn, "blocker", None)
    waiting = add_card(conn, "waiting", None)
    cli("link-add", "--task", str(blocker), "--to-task", str(waiting), "--type", "blocks")
    capsys.readouterr()
    cli("link-list", "--task", str(blocker))
    assert f"blocks     -> #{waiting}" in capsys.readouterr().out
    cli("link-list", "--task", str(waiting))
    assert f"blocked by -> #{blocker}" in capsys.readouterr().out


def test_link_remove_clears_the_link_from_both_cards(cli, conn, db_path):
    first = add_card(conn, "a", None)
    second = add_card(conn, "b", None)
    cli("link-add", "--task", str(first), "--to-task", str(second))
    link_id = rows(db_path, "SELECT id FROM task_link")[0][0]
    cli("link-remove", "--id", str(link_id))
    assert rows(db_path, "SELECT COUNT(*) FROM task_link") == [(0,)]


def test_update_epic_closing_archives_finished_cards(cli, conn, monkeypatch, tmp_path):
    monkeypatch.setenv("BRISTOL_REPORTS_DIR", str(tmp_path / "reports"))
    project = add_epic(conn, "Project")
    done = add_card(conn, "done", project, status="done")
    cli("update-epic", "--id", str(project), "--status", "completed")
    assert card(conn, done)["stage"] == "archive"


def test_update_epic_refuses_to_close_the_standing_workstream(cli, conn):
    standing = add_epic(conn, "Upkeep", "standing")
    with pytest.raises(SystemExit):
        cli("update-epic", "--id", str(standing), "--status", "completed")
    status = conn.execute("SELECT status FROM epic WHERE id=?", (standing,)).fetchone()[0]
    assert status == "in progress"


def test_add_attachment_copies_the_image_beside_the_board(cli, conn, db_path, tmp_path):
    task = add_card(conn, "card", None)
    image = tmp_path / "shot.png"
    image.write_bytes(b"\x89PNG\r\n")
    cli("add-attachment", "--task", str(task), "--file", str(image), "--author", "tester")
    stored = rows(db_path, "SELECT task_id, filename FROM attachment")
    assert len(stored) == 1 and stored[0][0] == task
    assert (db_path.parent / "images" / stored[0][1]).is_file()
