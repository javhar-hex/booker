from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.state_symmetry import TeamSignature, signature

RECORD_1_1 = Record(wins=1, losses=1)
RECORD_0_1 = Record(wins=0, losses=1)


def _state(records: list[Record], *past_pairings: tuple[int, int]) -> State:
    return State(
        records=ZVec(records),
        past_pairings=ZSet(
            Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
            for index_lhs, index_rhs in past_pairings
        ),
    )


def test_a_signature_is_each_teams_record_and_opponents_sorted() -> None:
    state = _state([RECORD_1_1, RECORD_0_1, RECORD_1_1], (0, 1), (1, 2))

    assert list(signature(state)) == [
        TeamSignature(wins=0, losses=1, degree=2),
        TeamSignature(wins=1, losses=1, degree=1),
        TeamSignature(wins=1, losses=1, degree=1),
    ]


def test_relabelled_states_have_the_same_signature() -> None:
    state = _state([RECORD_1_1, RECORD_0_1, RECORD_1_1], (0, 1), (1, 2))

    assert signature(Relabelling.of([2, 0, 1]).state(state)) == signature(state)


def test_states_that_differ_in_who_has_met_whom_can_differ() -> None:
    path = _state([RECORD_1_1] * 3, (0, 1), (1, 2))
    triangle_free = _state([RECORD_1_1] * 3, (0, 1))

    assert signature(path) != signature(triangle_free)
