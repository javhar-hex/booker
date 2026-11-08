import pytest
from javhar_util.immutables import ZMap, ZSet

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.team import Team

team_a, team_b, team_c, team_d = (Team(index=idx) for idx in range(4))
pairing_ab, pairing_cd = Pairing.of(team_a, team_b), Pairing.of(team_c, team_d)
TWO_MATCHES = ZSet([pairing_ab, pairing_cd])


def test_knows_winner_and_loser_of_each_pairing() -> None:
    outcome = Outcome(winners=ZMap({pairing_ab: team_b, pairing_cd: team_c}))

    assert (outcome.winner(pairing_ab), outcome.loser(pairing_ab)) == (team_b, team_a)
    assert (outcome.winner(pairing_cd), outcome.loser(pairing_cd)) == (team_c, team_d)
    assert outcome.pairings == TWO_MATCHES


def test_rejects_a_winner_outside_the_pairing() -> None:
    with pytest.raises(ValueError, match="cannot win"):
        Outcome(winners=ZMap({pairing_ab: team_c}))


def test_a_single_match_has_one_winner() -> None:
    outcome = Outcome.single(pairing_ab, team_b)

    assert outcome.pairings == ZSet([pairing_ab])
    assert (outcome.winner(pairing_ab), outcome.loser(pairing_ab)) == (team_b, team_a)


def test_every_outcome_of_k_pairings_is_one_of_2_to_the_k() -> None:
    outcomes = set(Outcome.every(TWO_MATCHES))

    assert len(outcomes) == 4
    assert all(outcome.pairings == TWO_MATCHES for outcome in outcomes)


def test_every_outcome_decides_each_pairing_both_ways() -> None:
    winners = {
        (outcome.winner(pairing_ab), outcome.winner(pairing_cd))
        for outcome in Outcome.every(TWO_MATCHES)
    }

    assert winners == {
        (team_a, team_c),
        (team_a, team_d),
        (team_b, team_c),
        (team_b, team_d),
    }
