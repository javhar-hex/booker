import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.atlas.schema import SCHEMA_VERSION
from booker.atlas.state_id import StateId
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.model.team import Team


def test_a_state_is_stored_once_and_comes_back_equal(
    path: Path, final_pair: Callable[[bool], State]
) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        first = writer.add_state(final_pair(True))
        again = writer.add_state(final_pair(True))
        other = writer.add_state(final_pair(False))

        assert first == again
        assert first != other
        assert atlas.state(first) == final_pair(True)
        assert atlas.num_states() == 2


def test_lists_every_stored_state(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        writer.add_state(final_pair(True))
        writer.add_state(champion_state)

        assert set(atlas.states()) == {final_pair(True), champion_state}


def test_an_unknown_state_is_an_error(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(KeyError):
        atlas.state(StateId(value=1))


def test_unexpanded_states_are_listed_by_depth_until_marked(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    depth = final_pair(True).matches_played
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        parent = writer.add_state(final_pair(True))
        writer.add_state(champion_state)

        listed = atlas.unexpanded(depth)
        assert [stored.id for stored in listed] == [parent]
        assert listed[0].state == final_pair(True)
        assert atlas.num_unexpanded() == 2

        writer.mark_expanded(parent)
        writer.mark_decided_expanded()

        assert atlas.num_unexpanded() == 0
        assert len(atlas.unexpanded(depth)) == 0


def test_what_is_done_in_a_transaction_is_kept(
    path: Path, champion_state: State
) -> None:
    with Atlas.open(path) as atlas, atlas.transaction():
        stored = atlas.expansion_writer().add_state(champion_state)

    with Atlas.open(path) as reopened:
        assert reopened.state(stored) == champion_state


def test_what_is_done_in_a_transaction_that_raises_is_not_kept(
    path: Path, champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with pytest.raises(RuntimeError), atlas.transaction():
            atlas.expansion_writer().add_state(champion_state)
            raise RuntimeError("interrupted")

        assert atlas.num_states() == 0


def test_a_new_atlas_has_the_schema_version_that_sqlite_keeps(path: Path) -> None:
    with Atlas.open(path) as atlas:
        version = atlas.connection.execute("PRAGMA user_version").fetchone()[0]

    assert version == SCHEMA_VERSION


def test_refuses_a_database_of_another_schema_version(path: Path) -> None:
    with Atlas.open(path):
        pass
    con = sqlite3.connect(path)
    con.execute("PRAGMA user_version = 0")
    con.close()

    with pytest.raises(ValueError, match=f"schema v0.*v{SCHEMA_VERSION}"):
        Atlas.open(path)


def test_summarizes_each_depth(
    final_pair: Callable[[bool], State], solved: Callable[[bool], Atlas]
) -> None:
    with solved(True) as atlas:
        summaries = list(atlas.depth_summaries())

    parent_depth = final_pair(True).matches_played
    assert [summary.depth for summary in summaries] == [parent_depth, parent_depth + 1]
    assert (summaries[0].num_states, summaries[0].num_colliders) == (1, 1)
    assert (summaries[0].num_pairings, summaries[0].min_value) == (1, 1)
    assert (summaries[1].num_states, summaries[1].max_value) == (1, 0)


def test_the_values_of_an_unsolved_atlas_are_none(
    path: Path, final_pair: Callable[[bool], State]
) -> None:
    with Atlas.open(path) as atlas:
        atlas.expansion_writer().add_state(final_pair(False))

        (summary,) = atlas.depth_summaries()

    assert (summary.min_value, summary.max_value) == (None, None)


def test_summarizes_a_depth_of_several_positions(
    path: Path,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> None:
    "Two positions at one depth, worth 1 and 0, with one action and two."
    other = Pairing.of(Team(index=0), Team(index=2))
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        champion = writer.add_state(champion_state)
        for met, pairings in (
            (True, [(pairing, 1)]),
            (False, [(pairing, 3), (other, 2)]),
        ):
            parent = writer.add_state(final_pair(met))
            for chosen, class_size in pairings:
                writer.add_action(parent, chosen, met, class_size, champion, champion)
            writer.mark_expanded(parent)
        writer.mark_decided_expanded()
        solver = atlas.retrograde_solver()
        solver.reset_values()
        for depth in range(MAX_MATCHES, -1, -1):
            solver.back_up(depth)

        summary = {s.depth: s for s in atlas.depth_summaries()}

    parents = summary[final_pair(True).matches_played]
    assert (parents.num_states, parents.num_colliders, parents.num_pairings) == (2, 3, 6)
    assert (parents.min_value, parents.max_value) == (0, 1)

    decided = summary[champion_state.matches_played]
    assert (decided.num_states, decided.num_colliders, decided.num_pairings) == (1, 0, 0)
    assert (decided.min_value, decided.max_value) == (0, 0)
