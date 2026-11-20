"""clear_done.py: clearing the Done column archives every finished card on the board."""

from __future__ import annotations

import clear_done
from conftest import add_card, add_epic, card


def test_done_cards_are_the_finished_cards_on_the_board(conn):
    project = add_epic(conn, "Project")
    done = add_card(conn, "done", project, status="done")
    add_card(conn, "doing", project, status="doing")
    add_card(conn, "archived", project, status="done", stage="archive")
    add_card(conn, "parked", project, status="done", stage="backlog")
    assert clear_done.done_cards(conn) == [done]


def test_clear_done_on_an_empty_column_moves_nothing(conn, tmp_path):
    add_card(conn, "todo", None)
    result = clear_done.clear_done(conn, out_dir=tmp_path / "reports")
    assert result.archived == []
    assert str(result) == "archived 0 card(s)"


def test_clear_done_archives_every_done_card(conn, tmp_path):
    project = add_epic(conn, "Project")
    first = add_card(conn, "a", project, status="done")
    second = add_card(conn, "b", None, status="done")
    open_card = add_card(conn, "c", project, status="todo")
    result = clear_done.clear_done(
        conn, now="2026-02-01T00:00:00+00:00", out_dir=tmp_path / "reports"
    )
    assert result.archived == [first, second]
    assert card(conn, first)["stage"] == "archive"
    assert card(conn, second)["stage"] == "archive"
    assert card(conn, open_card)["stage"] == "active"
