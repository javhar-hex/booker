from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.core.model.state import State


@pytest.mark.parametrize("met", [False, True])
def test_a_rematch_costs_the_scheduler_one(
    met: bool, solved: Callable[[bool], Atlas]
) -> None:
    with solved(met) as atlas:
        assert atlas.num_actions() == 1
        assert atlas.solver().root_value() == int(met)


def test_an_unsolved_atlas_has_no_root_value(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(ValueError):
        atlas.solver().root_value()


def test_every_position_is_unvalued_until_backed_up(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(final_pair(False))
            tx.add_state(champion_state)
        solver = atlas.solver()

        assert solver.num_unvalued(final_pair(False).matches_played) == 1
        solver.reset_values()
        assert solver.num_unvalued(champion_state.matches_played) == 0
