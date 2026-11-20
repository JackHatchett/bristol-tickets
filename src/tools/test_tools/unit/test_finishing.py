"""finishing.py: what a card reaching done, or leaving it, does to the board."""

from __future__ import annotations

import finishing
from conftest import add_card, add_epic, card


def test_standing_epic_is_none_on_a_board_without_one(conn):
    add_epic(conn, "Project")
    assert finishing.standing_epic(conn) is None


def test_standing_epic_finds_the_standing_workstream(conn):
    add_epic(conn, "Project")
    standing = add_epic(conn, "Upkeep", "Standing")
    assert finishing.standing_epic(conn) == standing


def test_standing_conflict_allows_the_first_and_the_same_epic(conn):
    project = add_epic(conn, "Project")
    assert finishing.standing_conflict(conn, project) is None
    standing = add_epic(conn, "Upkeep", "standing")
    assert finishing.standing_conflict(conn, standing) is None


def test_standing_conflict_refuses_a_second_standing_epic(conn):
    add_epic(conn, "Upkeep", "standing")
    other = add_epic(conn, "Other")
    reason = finishing.standing_conflict(conn, other)
    assert reason is not None and "Upkeep" in reason


def test_finish_archives_a_standing_card(conn):
    standing = add_epic(conn, "Upkeep", "standing")
    task = add_card(conn, "chore", standing, status="done")
    assert finishing.finish(conn, task) is True
    assert card(conn, task)["stage"] == "archive"


def test_finish_attributes_an_epicless_card_to_the_standing_epic(conn):
    standing = add_epic(conn, "Upkeep", "standing")
    task = add_card(conn, "loose", None, status="done")
    assert finishing.finish(conn, task) is True
    row = card(conn, task)
    assert (row["epic_id"], row["stage"]) == (standing, "archive")


def test_finish_leaves_a_project_card_in_done(conn):
    add_epic(conn, "Upkeep", "standing")
    project = add_epic(conn, "Project")
    task = add_card(conn, "feature", project, status="done")
    assert finishing.finish(conn, task) is False
    assert card(conn, task)["stage"] == "active"


def test_finish_leaves_an_epicless_card_where_the_board_has_no_standing_epic(conn):
    task = add_card(conn, "loose", None, status="done")
    assert finishing.finish(conn, task) is False
    row = card(conn, task)
    assert (row["epic_id"], row["stage"]) == (None, "active")


def test_finish_appends_to_the_bottom_of_the_archive(conn):
    standing = add_epic(conn, "Upkeep", "standing")
    add_card(conn, "old", standing, status="done", stage="archive", sort_order=7)
    task = add_card(conn, "chore", standing, status="done")
    finishing.finish(conn, task)
    assert card(conn, task)["sort_order"] == 8


def test_finish_of_a_missing_card_is_false(conn):
    add_epic(conn, "Upkeep", "standing")
    assert finishing.finish(conn, 999) is False


def test_reopen_returns_an_archived_card_to_the_bottom_of_its_column(conn):
    standing = add_epic(conn, "Upkeep", "standing")
    add_card(conn, "first", standing, status="todo", sort_order=4)
    task = add_card(conn, "chore", standing, status="todo", stage="archive")
    assert finishing.reopen(conn, task) is True
    row = card(conn, task)
    assert (row["stage"], row["sort_order"]) == ("active", 5)


def test_reopen_leaves_a_card_already_on_the_board(conn):
    task = add_card(conn, "on board", None, status="todo")
    assert finishing.reopen(conn, task) is False
    assert finishing.reopen(conn, 999) is False
