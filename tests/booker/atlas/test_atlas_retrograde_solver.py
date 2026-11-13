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
        assert atlas.retrograde_solver().root_gtv() == int(met)


def test_an_unsolved_atlas_has_no_root_gtv(path: Path) -> None:
    with Atlas.open(path) as atlas, pytest.raises(ValueError):
        atlas.retrograde_solver().root_gtv()


def test_every_position_is_unsolved_until_backed_up(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        writer.add_state(final_pair(False))
        writer.add_state(champion_state)
        solver = atlas.retrograde_solver()

        assert solver.num_unsolved(final_pair(False).matches_played) == 1
        solver.reset_gtvs()
        assert solver.num_unsolved(champion_state.matches_played) == 0
