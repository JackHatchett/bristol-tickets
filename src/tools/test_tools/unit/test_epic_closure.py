"""epic_closure.py: closing an epic archives its finished cards and reports them."""

from __future__ import annotations

import epic_closure
from conftest import add_card, add_epic, card


def test_refusal_refuses_the_standing_workstream(conn):
    standing = add_epic(conn, "Upkeep", "Standing")
    assert "standing workstream" in (epic_closure.refusal(conn, standing) or "")


def test_refusal_refuses_a_missing_epic(conn):
    assert "no epic" in (epic_closure.refusal(conn, 42) or "")


def test_refusal_allows_a_project(conn):
    assert epic_closure.refusal(conn, add_epic(conn, "Project")) is None


def test_close_epic_archives_finished_cards_and_leaves_open_ones(conn, tmp_path):
    project = add_epic(conn, "Project")
    done = add_card(conn, "done", project, status="done")
    open_card = add_card(conn, "open", project, status="doing")
    result = epic_closure.close_epic(conn, project, out_dir=tmp_path / "reports")
    assert result.ok
    assert result.archived == [done]
    assert result.reported == [done]
    assert card(conn, done)["stage"] == "archive"
    assert card(conn, open_card)["stage"] == "active"


def test_close_epic_reports_but_does_not_move_a_card_already_archived(conn, tmp_path):
    project = add_epic(conn, "Project")
    archived = add_card(conn, "swept", project, status="done", stage="archive")
    result = epic_closure.close_epic(conn, project, out_dir=tmp_path / "reports")
    assert result.archived == []
    assert result.reported == [archived]


def test_close_epic_refuses_the_standing_workstream_and_moves_nothing(conn, tmp_path):
    standing = add_epic(conn, "Upkeep", "standing")
    task = add_card(conn, "chore", standing, status="done")
    result = epic_closure.close_epic(conn, standing, out_dir=tmp_path / "reports")
    assert not result.ok
    assert str(result).startswith("refused:")
    assert card(conn, task)["stage"] == "active"


def test_close_epic_appends_each_card_below_the_archive(conn, tmp_path):
    project = add_epic(conn, "Project")
    add_card(conn, "old", None, status="done", stage="archive", sort_order=3)
    first = add_card(conn, "a", project, status="done")
    second = add_card(conn, "b", project, status="done")
    epic_closure.close_epic(conn, project, out_dir=tmp_path / "reports")
    assert (card(conn, first)["sort_order"], card(conn, second)["sort_order"]) == (4, 5)
