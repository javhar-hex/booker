import pytest

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team


def test_team_index_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        Team(index=-1)


def test_of_orders_the_teams() -> None:
    assert Pairing.of(Team(index=5), Team(index=2)) == Pairing(
        low=Team(index=2), high=Team(index=5)
    )


def test_order_given_does_not_matter() -> None:
    a, b = Team(index=3), Team(index=7)

    assert Pairing.of(a, b) == Pairing.of(b, a)


def test_rejects_a_team_paired_with_itself() -> None:
    with pytest.raises(ValueError):
        Pairing.of(Team(index=4), Team(index=4))


def test_constructor_rejects_unordered_teams() -> None:
    with pytest.raises(ValueError):
        Pairing(low=Team(index=5), high=Team(index=2))


def test_knows_which_teams_it_involves() -> None:
    pairing = Pairing.of(Team(index=2), Team(index=5))

    assert pairing.involves(Team(index=5))
    assert not pairing.involves(Team(index=3))


def test_opponent_is_the_other_team() -> None:
    a, b = Team(index=2), Team(index=5)
    pairing = Pairing.of(a, b)

    assert (pairing.opponent(a), pairing.opponent(b)) == (b, a)


def test_a_team_outside_the_pairing_has_no_opponent() -> None:
    with pytest.raises(ValueError, match="not in"):
        Pairing.of(Team(index=2), Team(index=5)).opponent(Team(index=3))
