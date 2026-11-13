import pytest
from javhar_util.immutables import ZVec
from support.states import state_of_indices

from booker.core.model.record import Record
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.state_signature import StateSignature
from booker.core.symmetry.team_signature import TeamSignature

RECORD_1_1 = Record(wins=1, losses=1)
RECORD_0_1 = Record(wins=0, losses=1)


def test_a_signature_is_the_team_signatures_sorted() -> None:
    state = state_of_indices([RECORD_1_1, RECORD_0_1, RECORD_1_1], (0, 1), (1, 2))

    assert list(StateSignature.of(state).team_signatures) == [
        TeamSignature(wins=0, losses=1, degree=2),
        TeamSignature(wins=1, losses=1, degree=1),
        TeamSignature(wins=1, losses=1, degree=1),
    ]


def test_relabelled_states_have_the_same_signature() -> None:
    state = state_of_indices([RECORD_1_1, RECORD_0_1, RECORD_1_1], (0, 1), (1, 2))

    relabelled = Relabelling.of([2, 0, 1]).state(state)

    assert StateSignature.of(relabelled) == StateSignature.of(state)


def test_states_that_differ_in_who_has_met_whom_can_differ() -> None:
    path = state_of_indices([RECORD_1_1] * 3, (0, 1), (1, 2))
    shorter = state_of_indices([RECORD_1_1] * 3, (0, 1))

    assert StateSignature.of(path) != StateSignature.of(shorter)


def test_signatures_that_are_not_sorted_are_refused() -> None:
    with pytest.raises(ValueError, match="not sorted"):
        StateSignature(
            team_signatures=ZVec(
                [
                    TeamSignature(wins=1, losses=1, degree=1),
                    TeamSignature(wins=0, losses=1, degree=2),
                ]
            )
        )
