import random
from collections.abc import Callable, Iterator

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.packed_state import MAX_CODE, PackedState
from booker.core.model.invariants import NUM_PARTICIPANTS
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

TEAM_A, TEAM_B, TEAM_C = (Team(index=idx) for idx in range(3))
RECORD_1_1 = Record(wins=1, losses=1)
RECORD_0_1 = Record(wins=0, losses=1)
RECORD_2_0 = Record(wins=2, losses=0)


def _state(*records: Record, past_pairings: tuple[Pairing, ...] = ()) -> State:
    return State(records=ZVec(records), past_pairings=ZSet(past_pairings))


def test_packs_to_the_documented_layout() -> None:
    state = _state(
        RECORD_1_1, RECORD_0_1, RECORD_2_0, past_pairings=(Pairing.of(TEAM_A, TEAM_B),)
    )

    assert PackedState.of(state).data == bytes([3, 3, 1, 4, 0b001])


def test_packs_each_met_pair_into_its_own_bit() -> None:
    state = _state(
        RECORD_1_1,
        RECORD_0_1,
        RECORD_2_0,
        past_pairings=(Pairing.of(TEAM_A, TEAM_C), Pairing.of(TEAM_B, TEAM_C)),
    )

    assert PackedState.of(state).data[-1] == 0b110


def test_packs_the_start_without_any_meetings() -> None:
    pairs = NUM_PARTICIPANTS * (NUM_PARTICIPANTS - 1) // 2

    assert PackedState.of(State.start()).data == (
        bytes([NUM_PARTICIPANTS]) + bytes(NUM_PARTICIPANTS) + bytes((pairs + 7) // 8)
    )


def test_different_states_pack_differently() -> None:
    first = _state(RECORD_1_1, RECORD_0_1, past_pairings=(Pairing.of(TEAM_A, TEAM_B),))

    assert PackedState.of(first) != PackedState.of(_state(RECORD_1_1, RECORD_0_1))
    assert PackedState.of(first) != PackedState.of(
        _state(RECORD_0_1, RECORD_1_1, past_pairings=(Pairing.of(TEAM_A, TEAM_B),))
    )


def test_equal_states_pack_equally() -> None:
    assert PackedState.of(_state(RECORD_1_1, RECORD_0_1)) == PackedState.of(
        _state(RECORD_1_1, RECORD_0_1)
    )


def test_unpacks_what_it_packed_along_every_game(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(0)

    states = [state for _ in range(30) for state in play_game(rng)]

    assert all(PackedState.of(state).state == state for state in states)
    assert all(PackedState.of(state).size == state.size for state in states)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(bytes([0]), id="no teams"),
        pytest.param(bytes([NUM_PARTICIPANTS + 1]) + bytes(200), id="too many teams"),
        pytest.param(bytes([2, 0, 0]), id="missing adjacency"),
        pytest.param(bytes([2, 0, 0, 0, 0]), id="surplus adjacency"),
        pytest.param(bytes([1, MAX_CODE + 1]), id="record beyond a champion"),
        pytest.param(bytes([2, 0, 0, 0b10]), id="bit beyond the last pair"),
    ],
)
def test_rejects_bytes_that_encode_no_state(data: bytes) -> None:
    with pytest.raises(ValueError):
        PackedState(data=data)
