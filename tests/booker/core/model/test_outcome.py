import pytest
from javhar_util.immutables import ZMap, ZSet

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.team import Team

TEAM_A, TEAM_B, TEAM_C, TEAM_D = (Team(index=idx) for idx in range(4))
PAIRING_AB, PAIRING_CD = Pairing.of(TEAM_A, TEAM_B), Pairing.of(TEAM_C, TEAM_D)
TWO_MATCHES = ZSet([PAIRING_AB, PAIRING_CD])


def test_knows_winner_and_loser_of_each_pairing() -> None:
    outcome = Outcome(winners=ZMap({PAIRING_AB: TEAM_B, PAIRING_CD: TEAM_C}))

    assert (outcome.winner(PAIRING_AB), outcome.loser(PAIRING_AB)) == (TEAM_B, TEAM_A)
    assert (outcome.winner(PAIRING_CD), outcome.loser(PAIRING_CD)) == (TEAM_C, TEAM_D)
    assert outcome.pairings == TWO_MATCHES


def test_rejects_a_winner_outside_the_pairing() -> None:
    with pytest.raises(ValueError, match="cannot win"):
        Outcome(winners=ZMap({PAIRING_AB: TEAM_C}))


def test_a_single_match_has_one_winner() -> None:
    outcome = Outcome.single(PAIRING_AB, TEAM_B)

    assert outcome.pairings == ZSet([PAIRING_AB])
    assert (outcome.winner(PAIRING_AB), outcome.loser(PAIRING_AB)) == (TEAM_B, TEAM_A)


def test_every_outcome_of_k_pairings_is_one_of_2_to_the_k() -> None:
    outcomes = set(Outcome.every(TWO_MATCHES))

    assert len(outcomes) == 4
    assert all(outcome.pairings == TWO_MATCHES for outcome in outcomes)


def test_every_outcome_decides_each_pairing_both_ways() -> None:
    winners = {
        (outcome.winner(PAIRING_AB), outcome.winner(PAIRING_CD))
        for outcome in Outcome.every(TWO_MATCHES)
    }

    assert winners == {
        (TEAM_A, TEAM_C),
        (TEAM_A, TEAM_D),
        (TEAM_B, TEAM_C),
        (TEAM_B, TEAM_D),
    }
