import sqlite3
from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.schema import SCHEMA_VERSION
from booker.atlas.storage import Atlas
from booker.atlas.stored import StateId
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

PAIRING = Pairing.of(Team(index=0), Team(index=1))
TIED = Record(wins=5, losses=1)
CHAMPION = Record(wins=6, losses=1)
CHAMPION_STATE = State(records=ZVec([CHAMPION]), met=ZSet([]))


def _final_pair(met: bool) -> State:
    "Two teams one loss from elimination: whoever wins the match is the champion."
    return State(records=ZVec([TIED, TIED]), met=ZSet([PAIRING] if met else []))


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "atlas.db"


def test_state_ids_are_numbered_from_one() -> None:
    with pytest.raises(ValueError):
        StateId(value=0)


def test_a_state_is_stored_once_and_comes_back_equal(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            first = tx.add_state(_final_pair(met=True))
            again = tx.add_state(_final_pair(met=True))
            other = tx.add_state(_final_pair(met=False))

        assert first == again
        assert first != other
        assert atlas.state(first) == _final_pair(met=True)
        assert atlas.num_states() == 2


def test_lists_every_stored_state(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(_final_pair(met=True))
            tx.add_state(CHAMPION_STATE)

        assert set(atlas.states()) == {_final_pair(met=True), CHAMPION_STATE}


def test_an_unknown_state_is_an_error(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(KeyError):
        atlas.state(StateId(value=1))


def test_committed_writes_outlive_the_atlas(path: Path) -> None:
    with Atlas.open(path) as atlas, atlas.transaction() as tx:
        stored = tx.add_state(CHAMPION_STATE)

    with Atlas.open(path) as reopened:
        assert reopened.state(stored) == CHAMPION_STATE


def test_a_failed_transaction_writes_nothing(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with pytest.raises(RuntimeError), atlas.transaction() as tx:
            tx.add_state(CHAMPION_STATE)
            raise RuntimeError("interrupted")

        assert atlas.num_states() == 0


def test_the_canonicalization_backend_cannot_change(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.use_backend("bliss")
            tx.use_backend("bliss")
        with pytest.raises(ValueError), atlas.transaction() as tx:
            tx.use_backend("vf2")


def test_unexpanded_states_are_listed_by_depth_until_marked(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            parent = tx.add_state(_final_pair(met=True))
            tx.add_state(CHAMPION_STATE)

        listed = atlas.unexpanded(_final_pair(met=True).matches_played)
        assert [stored.id for stored in listed] == [parent]
        assert listed[0].state == _final_pair(met=True)
        assert atlas.num_unexpanded() == 2

        with atlas.transaction() as tx:
            tx.mark_expanded(parent)
            tx.mark_decided_expanded()

        assert atlas.num_unexpanded() == 0
        assert len(atlas.unexpanded(_final_pair(met=True).matches_played)) == 0


def test_refuses_a_database_of_another_schema_version(path: Path) -> None:
    with Atlas.open(path):
        pass
    con = sqlite3.connect(path)
    with con:
        con.execute("UPDATE meta SET value='0' WHERE key='schema_version'")
    con.close()

    with pytest.raises(ValueError, match=f"schema v0.*v{SCHEMA_VERSION}"):
        Atlas.open(path)


def _solved(path: Path, met: bool) -> Atlas:
    atlas = Atlas.open(path)
    with atlas.transaction() as tx:
        parent = tx.add_state(_final_pair(met))
        champion = tx.add_state(CHAMPION_STATE)
        tx.record_root(parent)
        tx.add_action(parent, PAIRING, met, 1, champion, champion)
        tx.mark_expanded(parent)
        tx.mark_decided_expanded()
    atlas.reset_values()
    for depth in range(31, -1, -1):
        atlas.back_up(depth)
        assert atlas.num_unvalued(depth) == 0
    atlas.mark_solved()
    return atlas


@pytest.mark.parametrize("met", [False, True])
def test_a_rematch_costs_the_scheduler_one(path: Path, met: bool) -> None:
    with _solved(path, met) as atlas:
        assert atlas.num_actions() == 1
        assert atlas.root_value() == int(met)


def test_an_unsolved_atlas_has_no_root_value(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(ValueError):
        atlas.root_value()


def test_summarizes_each_depth(path: Path) -> None:
    with _solved(path, met=True) as atlas:
        summaries = list(atlas.depth_summaries())

    parent_depth = _final_pair(met=True).matches_played
    assert [summary.depth for summary in summaries] == [parent_depth, parent_depth + 1]
    assert (summaries[0].num_states, summaries[0].num_colliders) == (1, 1)
    assert (summaries[0].num_pairings, summaries[0].min_value) == (1, 1)
    assert (summaries[1].num_states, summaries[1].max_value) == (1, 0)
