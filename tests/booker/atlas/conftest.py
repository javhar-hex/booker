"""What the tests of the atlas build their positions from."""

from collections.abc import Callable
from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

PAIRING = Pairing.of(Team(index=0), Team(index=1))


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "atlas.db"


@pytest.fixture
def pairing() -> Pairing:
    return PAIRING


@pytest.fixture
def champion_state() -> State:
    return State(records=ZVec([Record(wins=6, losses=1)]), past_pairings=ZSet([]))


@pytest.fixture
def final_pair() -> Callable[[bool], State]:
    "Two teams a loss from elimination, who have met or not: the winner is the champion."

    def build(met: bool) -> State:
        tied = Record(wins=5, losses=1)
        return State(
            records=ZVec([tied, tied]), past_pairings=ZSet([PAIRING] if met else [])
        )

    return build


@pytest.fixture
def solved(
    path: Path,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> Callable[[bool], Atlas]:
    "An open atlas of the last match of a game, solved: whether the two have met or not."

    def build(met: bool) -> Atlas:
        atlas = Atlas.open(path)
        writer = atlas.expansion_writer()
        parent = writer.add_state(final_pair(met))
        champion = writer.add_state(champion_state)
        writer.record_root(parent)
        writer.add_action(parent, pairing, met, 1, champion, champion)
        writer.mark_expanded(parent)
        writer.mark_decided_expanded()
        solver = atlas.retrograde_solver()
        solver.reset_gtvs()
        for depth in range(MAX_MATCHES, -1, -1):
            solver.back_up(depth)
            assert solver.num_unsolved(depth) == 0
        solver.mark_solved()
        return atlas

    return build
