from support.states import state_of_indices

from booker.core.model.record import Record
from booker.core.model.team import Team
from booker.core.symmetry.team_signature import TeamSignature

RECORD_1_1 = Record(wins=1, losses=1)
RECORD_0_1 = Record(wins=0, losses=1)
STATE = state_of_indices([RECORD_1_1, RECORD_0_1, RECORD_1_1], (0, 1), (1, 2))


def test_a_team_signature_is_its_record_and_the_number_of_teams_it_has_met() -> None:
    assert TeamSignature.of(STATE, Team(index=1)) == TeamSignature(
        wins=0, losses=1, degree=2
    )
    assert TeamSignature.of(STATE, Team(index=0)) == TeamSignature(
        wins=1, losses=1, degree=1
    )


def test_a_team_that_has_met_nobody_has_degree_zero() -> None:
    state = state_of_indices([RECORD_1_1, RECORD_0_1])

    assert TeamSignature.of(state, Team(index=0)).degree == 0


def test_team_signatures_are_ordered_by_wins_then_losses_then_degree() -> None:
    assert TeamSignature(wins=0, losses=1, degree=2) < TeamSignature(
        wins=1, losses=0, degree=0
    )
    assert TeamSignature(wins=1, losses=0, degree=1) < TeamSignature(
        wins=1, losses=0, degree=2
    )
