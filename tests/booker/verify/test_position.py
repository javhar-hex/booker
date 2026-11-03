import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.verify.failure import AuditFailure
from booker.verify.position import MAX_CODE, Pair, Position, Standing
from booker.verify.spec import NUM_TEAMS


def test_the_opening_is_sixteen_fresh_teams_that_have_not_met() -> None:
    opening = Position.opening()

    assert opening.size == NUM_TEAMS
    assert set(opening.standings) == {Standing(wins=0, losses=0)}
    assert len(opening.meetings) == 0
    assert opening.depth == 0
    assert opening.num_unbeaten == NUM_TEAMS


def test_parses_the_opening_key() -> None:
    pairs = NUM_TEAMS * (NUM_TEAMS - 1) // 2

    assert Position.parse(bytes([NUM_TEAMS]) + bytes(NUM_TEAMS) + bytes(15)) == (
        Position.opening()
    )
    assert pairs == 120


def test_parses_records_and_meetings_from_a_key() -> None:
    position = Position.parse(bytes([3, 3, 1, 4, 0b101]))

    assert list(position.standings) == [
        Standing(wins=1, losses=1),
        Standing(wins=0, losses=1),
        Standing(wins=2, losses=0),
    ]
    assert position.meetings == ZSet([Pair(low=0, high=1), Pair(low=1, high=2)])


def test_counts_the_matches_played() -> None:
    position = Position.parse(bytes([3, 3, 1, 4, 0]))

    assert position.depth == (NUM_TEAMS - 3) * 2 + 2
    assert position.num_unbeaten == 1
    assert not position.is_decided
    assert Position.parse(bytes([1, MAX_CODE])).is_decided


@pytest.mark.parametrize(
    "key",
    [
        pytest.param(b"", id="empty"),
        pytest.param(bytes([0]), id="no teams"),
        pytest.param(bytes([NUM_TEAMS + 1]) + bytes(200), id="too many teams"),
        pytest.param(bytes([2, 0, 0]), id="missing adjacency"),
        pytest.param(bytes([2, 0, 0, 0, 0]), id="surplus adjacency"),
        pytest.param(bytes([1, MAX_CODE + 1]), id="record beyond a champion"),
        pytest.param(bytes([2, 0, 0, 0b10]), id="bit beyond the last pair"),
    ],
)
def test_rejects_a_key_that_encodes_no_position(key: bytes) -> None:
    with pytest.raises(AuditFailure):
        Position.parse(key)


def test_a_standing_stays_within_the_game() -> None:
    with pytest.raises(ValueError, match="wins"):
        Standing(wins=7, losses=0)
    with pytest.raises(ValueError, match="losses"):
        Standing(wins=0, losses=3)


def test_standings_have_distinct_colours() -> None:
    colours = {
        Standing(wins=w, losses=loss).colour for w in range(7) for loss in range(2)
    }

    assert len(colours) == 14


def test_a_pair_is_two_distinct_teams_lowest_first() -> None:
    assert Pair(low=0, high=1).involves(1)
    assert not Pair(low=0, high=1).involves(2)
    with pytest.raises(ValueError, match="low < high"):
        Pair(low=1, high=1)


def test_a_position_needs_teams_and_meetings_between_them() -> None:
    with pytest.raises(ValueError, match="1 to"):
        Position(standings=ZVec([]), meetings=ZSet([]))
    with pytest.raises(ValueError, match="beyond"):
        Position(
            standings=ZVec([Standing(wins=0, losses=1)] * 2),
            meetings=ZSet([Pair(low=0, high=2)]),
        )
