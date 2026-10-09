"""History storage against a real PostgreSQL (skipped when it is not available)."""

import uuid

import pytest

from src import db, history


@pytest.fixture(autouse=True)
def database_available():
    try:
        db.run_query("SELECT 1")
        history.ensure_table()
    except Exception:
        pytest.skip("PostgreSQL is not available")


@pytest.fixture
def user():
    name = f"pytest-{uuid.uuid4().hex[:8]}"
    yield name
    history.clear_history(name)


def add(user, question):
    history.log_query(user, "thread", question, "SELECT 1", 1, "ok", 10)


def test_entries_are_listed_newest_first(user):
    add(user, "first")
    add(user, "second")

    assert [row["question"] for row in history.list_history(user)] == ["second", "first"]


def test_delete_removes_only_that_entry(user):
    add(user, "keep")
    add(user, "remove")
    remove_id = history.list_history(user)[0]["id"]

    assert history.delete_entry(user, remove_id) is True

    assert [row["question"] for row in history.list_history(user)] == ["keep"]


def test_a_user_cannot_delete_someone_elses_entry(user):
    add(user, "mine")
    entry_id = history.list_history(user)[0]["id"]

    assert history.delete_entry("someone-else", entry_id) is False
    assert len(history.list_history(user)) == 1


def test_deleting_twice_reports_not_found(user):
    add(user, "once")
    entry_id = history.list_history(user)[0]["id"]

    assert history.delete_entry(user, entry_id) is True
    assert history.delete_entry(user, entry_id) is False


def test_clear_removes_everything_of_that_user_only(user):
    other = f"{user}-other"
    add(user, "a")
    add(user, "b")
    add(other, "c")

    assert history.clear_history(user) == 2
    assert history.list_history(user) == []
    assert len(history.list_history(other)) == 1
    history.clear_history(other)