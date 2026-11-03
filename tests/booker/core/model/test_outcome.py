import pytest
from javhar_util.immutables import ZMap, ZSet

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.team import Team

A, B, C, D = (Team(index=i) for i in range(4))
AB, CD = Pairing.of(A, B), Pairing.of(C, D)
TWO_MATCHES = ZSet([AB, CD])


def test_knows_winner_and_loser_of_each_pairing() -> None:
    outcome = Outcome(winners=ZMap({AB: B, CD: C}))

    assert (outcome.winner(AB), outcome.loser(AB)) == (B, A)
    assert (outcome.winner(CD), outcome.loser(CD)) == (C, D)
    assert outcome.pairings == TWO_MATCHES


def test_rejects_a_winner_outside_the_pairing() -> None:
    with pytest.raises(ValueError, match="cannot win"):
        Outcome(winners=ZMap({AB: C}))


def test_a_single_match_has_one_winner() -> None:
    outcome = Outcome.single(AB, B)

    assert outcome.pairings == ZSet([AB])
    assert (outcome.winner(AB), outcome.loser(AB)) == (B, A)


def test_every_outcome_of_k_pairings_is_one_of_2_to_the_k() -> None:
    outcomes = set(Outcome.every(TWO_MATCHES))

    assert len(outcomes) == 4
    assert all(outcome.pairings == TWO_MATCHES for outcome in outcomes)


def test_every_outcome_decides_each_pairing_both_ways() -> None:
    winners = {
        (outcome.winner(AB), outcome.winner(CD))
        for outcome in Outcome.every(TWO_MATCHES)
    }

    assert winners == {(A, C), (A, D), (B, C), (B, D)}
