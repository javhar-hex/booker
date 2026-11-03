import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.verify.position import Pair, Position, Standing
from booker.verify.rules import LOWER_BRACKET_SURVIVOR, legal_pairs, play

UNBEATEN = Standing(wins=2, losses=0)
OTHER_UNBEATEN = Standing(wins=3, losses=0)
ONE_LOSS = Standing(wins=3, losses=1)
CHAMPION = Standing(wins=6, losses=1)


def _position(*standings: Standing, met: tuple[tuple[int, int], ...] = ()) -> Position:
    return Position(
        standings=ZVec(standings),
        meetings=ZSet(Pair(low=a, high=b) for a, b in met),
    )


def _pairs(*pairs: tuple[int, int]) -> ZSet[Pair]:
    return ZSet(Pair(low=a, high=b) for a, b in pairs)


def test_everyone_may_meet_everyone_at_the_start() -> None:
    assert len(legal_pairs(Position.opening())) == 120


def test_teams_of_equal_record_may_meet_and_others_may_not() -> None:
    position = _position(ONE_LOSS, ONE_LOSS, UNBEATEN, OTHER_UNBEATEN)

    assert legal_pairs(position) == _pairs((0, 1))


def test_survivors_may_not_meet_while_a_team_is_unbeaten() -> None:
    survivor = LOWER_BRACKET_SURVIVOR

    assert legal_pairs(_position(survivor, survivor, UNBEATEN)) == _pairs((0, 2), (1, 2))
    assert legal_pairs(_position(survivor, survivor, UNBEATEN, OTHER_UNBEATEN)) == (
        _pairs()
    )


def test_survivors_may_meet_once_no_team_is_unbeaten() -> None:
    assert legal_pairs(_position(LOWER_BRACKET_SURVIVOR, LOWER_BRACKET_SURVIVOR)) == (
        _pairs((0, 1))
    )


def test_the_sole_unbeaten_team_may_meet_only_a_survivor() -> None:
    position = _position(ONE_LOSS, LOWER_BRACKET_SURVIVOR, UNBEATEN)

    assert legal_pairs(position) == _pairs((1, 2))


def test_a_decided_position_has_no_pairings() -> None:
    assert legal_pairs(_position(CHAMPION)) == _pairs()


def test_a_match_adds_a_win_and_a_loss_and_a_meeting() -> None:
    played = play(_position(UNBEATEN, UNBEATEN), winner=0, loser=1)

    assert list(played.position.standings) == [
        Standing(wins=3, losses=0),
        Standing(wins=2, losses=1),
    ]
    assert played.position.meetings == _pairs((0, 1))
    assert not played.is_rematch


def test_a_meeting_again_is_a_rematch() -> None:
    position = _position(ONE_LOSS, ONE_LOSS, met=((0, 1),))

    assert play(position, winner=1, loser=0).is_rematch


def test_a_team_on_two_losses_is_eliminated_and_the_rest_renumbered() -> None:
    standings = (ONE_LOSS, Standing(wins=0, losses=1), ONE_LOSS)
    position = _position(*standings, met=((0, 1), (1, 2), (0, 2)))

    played = play(position, winner=0, loser=1)

    assert list(played.position.standings) == [Standing(wins=4, losses=1), ONE_LOSS]
    assert played.position.meetings == _pairs((0, 1))


@pytest.mark.parametrize("winner", [0, 1])
def test_the_last_match_leaves_one_team(winner: int) -> None:
    final = Standing(wins=5, losses=1)
    played = play(_position(final, final), winner=winner, loser=1 - winner)

    assert played.position.is_decided
    assert played.position.standings[0] == CHAMPION
