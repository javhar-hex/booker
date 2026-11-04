from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.invariant import TeamSignature, signature, team_colour
from booker.core.symmetry.relabelling import Relabelling

ONE_ONE = Record(wins=1, losses=1)
ZERO_ONE = Record(wins=0, losses=1)


def _state(records: list[Record], *met: tuple[int, int]) -> State:
    return State(
        records=ZVec(records),
        met=ZSet(Pairing.of(Team(index=a), Team(index=b)) for a, b in met),
    )


def test_a_signature_is_each_teams_record_and_opponents_sorted() -> None:
    state = _state([ONE_ONE, ZERO_ONE, ONE_ONE], (0, 1), (1, 2))

    assert list(signature(state)) == [
        TeamSignature(wins=0, losses=1, degree=2),
        TeamSignature(wins=1, losses=1, degree=1),
        TeamSignature(wins=1, losses=1, degree=1),
    ]


def test_relabelled_states_have_the_same_signature() -> None:
    state = _state([ONE_ONE, ZERO_ONE, ONE_ONE], (0, 1), (1, 2))

    assert signature(Relabelling.of([2, 0, 1]).state(state)) == signature(state)


def test_states_that_differ_in_who_has_met_whom_can_differ() -> None:
    path = _state([ONE_ONE] * 3, (0, 1), (1, 2))
    triangle_free = _state([ONE_ONE] * 3, (0, 1))

    assert signature(path) != signature(triangle_free)


def test_every_live_record_has_a_colour_of_its_own() -> None:
    records = [Record(wins=w, losses=loss) for w in range(7) for loss in range(2)]

    assert len({team_colour(record) for record in records}) == len(records)
