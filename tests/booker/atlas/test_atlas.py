import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.atlas.schema import SCHEMA_VERSION
from booker.atlas.state_id import StateId
from booker.core.model.state import State


def test_a_state_is_stored_once_and_comes_back_equal(
    path: Path, final_pair: Callable[[bool], State]
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            first = tx.add_state(final_pair(True))
            again = tx.add_state(final_pair(True))
            other = tx.add_state(final_pair(False))

        assert first == again
        assert first != other
        assert atlas.state(first) == final_pair(True)
        assert atlas.num_states() == 2


def test_lists_every_stored_state(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(final_pair(True))
            tx.add_state(champion_state)

        assert set(atlas.states()) == {final_pair(True), champion_state}


def test_an_unknown_state_is_an_error(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(KeyError):
        atlas.state(StateId(value=1))


def test_committed_writes_outlive_the_atlas(path: Path, champion_state: State) -> None:
    with Atlas.open(path) as atlas, atlas.transaction() as tx:
        stored = tx.add_state(champion_state)

    with Atlas.open(path) as reopened:
        assert reopened.state(stored) == champion_state


def test_unexpanded_states_are_listed_by_depth_until_marked(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    depth = final_pair(True).matches_played
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            parent = tx.add_state(final_pair(True))
            tx.add_state(champion_state)

        listed = atlas.unexpanded(depth)
        assert [stored.id for stored in listed] == [parent]
        assert listed[0].state == final_pair(True)
        assert atlas.num_unexpanded() == 2

        with atlas.transaction() as tx:
            tx.mark_expanded(parent)
            tx.mark_decided_expanded()

        assert atlas.num_unexpanded() == 0
        assert len(atlas.unexpanded(depth)) == 0


def test_refuses_a_database_of_another_schema_version(path: Path) -> None:
    with Atlas.open(path):
        pass
    con = sqlite3.connect(path)
    with con:
        con.execute("UPDATE meta SET value='0' WHERE key='schema_version'")
    con.close()

    with pytest.raises(ValueError, match=f"schema v0.*v{SCHEMA_VERSION}"):
        Atlas.open(path)
