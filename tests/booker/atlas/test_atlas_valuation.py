from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.state import State


def _solved(
    path: Path,
    met: bool,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> Atlas:
    atlas = Atlas.open(path)
    with atlas.transaction() as tx:
        parent = tx.add_state(final_pair(met))
        champion = tx.add_state(champion_state)
        tx.record_root(parent)
        tx.add_action(parent, pairing, met, 1, champion, champion)
        tx.mark_expanded(parent)
        tx.mark_decided_expanded()
    valuation = atlas.valuation()
    valuation.reset_values()
    for depth in range(MAX_MATCHES, -1, -1):
        valuation.back_up(depth)
        assert valuation.num_unvalued(depth) == 0
    valuation.mark_solved()
    return atlas


@pytest.mark.parametrize("met", [False, True])
def test_a_rematch_costs_the_scheduler_one(
    path: Path,
    met: bool,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> None:
    with _solved(path, met, final_pair, champion_state, pairing) as atlas:
        assert atlas.num_actions() == 1
        assert atlas.valuation().root_value() == int(met)


def test_an_unsolved_atlas_has_no_root_value(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(ValueError):
        atlas.valuation().root_value()


def test_every_position_is_unvalued_until_backed_up(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(final_pair(False))
            tx.add_state(champion_state)
        valuation = atlas.valuation()

        assert valuation.num_unvalued(final_pair(False).matches_played) == 1
        valuation.reset_values()
        assert valuation.num_unvalued(champion_state.matches_played) == 0


def test_summarizes_each_depth(
    path: Path,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> None:
    with _solved(path, True, final_pair, champion_state, pairing) as atlas:
        summaries = list(atlas.valuation().depth_summaries())

    parent_depth = final_pair(True).matches_played
    assert [summary.depth for summary in summaries] == [parent_depth, parent_depth + 1]
    assert (summaries[0].num_states, summaries[0].num_colliders) == (1, 1)
    assert (summaries[0].num_pairings, summaries[0].min_value) == (1, 1)
    assert (summaries[1].num_states, summaries[1].max_value) == (1, 0)


def test_the_values_of_an_unsolved_atlas_are_none(
    path: Path, final_pair: Callable[[bool], State]
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(final_pair(False))

        (summary,) = atlas.valuation().depth_summaries()

    assert (summary.min_value, summary.max_value) == (None, None)
