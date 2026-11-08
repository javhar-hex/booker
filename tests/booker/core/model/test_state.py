import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import ELIMINATION_LOSSES, NUM_PARTICIPANTS
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

TEAM_A, TEAM_B, TEAM_C = (Team(index=idx) for idx in range(3))
ONE_ONE = Record(wins=1, losses=1)
TWO_ZERO = Record(wins=2, losses=0)


def _state(*records: Record, past_pairings: tuple[Pairing, ...] = ()) -> State:
    return State(records=ZVec(records), past_pairings=ZSet(past_pairings))


def test_start_has_every_team_fresh_and_no_meetings() -> None:
    start = State.start()

    assert start.size == NUM_PARTICIPANTS
    assert set(start.records) == {Record.fresh()}
    assert len(start.past_pairings) == 0
    assert start.matches_played == 0


def test_matches_played_counts_lives_lost_including_eliminated_teams() -> None:
    state = _state(TWO_ZERO, ONE_ONE, ONE_ONE)

    assert state.matches_played == (NUM_PARTICIPANTS - 3) * ELIMINATION_LOSSES + 2


def test_decided_when_one_team_is_left() -> None:
    assert _state(Record(wins=6, losses=1)).is_decided
    assert not _state(TWO_ZERO, ONE_ONE).is_decided


def test_knows_its_teams() -> None:
    state = _state(TWO_ZERO, ONE_ONE)

    assert state.teams == ZVec([TEAM_A, TEAM_B])
    assert TEAM_B in state and TEAM_C not in state
    assert state.record(TEAM_B) == ONE_ONE


def test_counts_rematches_among_pairings() -> None:
    state = _state(
        TWO_ZERO, ONE_ONE, ONE_ONE, past_pairings=(Pairing.of(TEAM_A, TEAM_B),)
    )

    assert state.has_met(Pairing.of(TEAM_A, TEAM_B))
    assert (
        state.rematches(ZSet([Pairing.of(TEAM_A, TEAM_B), Pairing.of(TEAM_B, TEAM_C)]))
        == 1
    )


@pytest.mark.parametrize("size", [0, NUM_PARTICIPANTS + 1])
def test_rejects_impossible_team_counts(size: int) -> None:
    with pytest.raises(ValueError, match="live teams"):
        State(records=ZVec([Record.fresh()] * size), past_pairings=ZSet([]))


def test_rejects_eliminated_teams() -> None:
    with pytest.raises(ValueError, match="eliminated"):
        _state(TWO_ZERO, Record(wins=1, losses=ELIMINATION_LOSSES))


def test_rejects_meetings_with_unknown_teams() -> None:
    with pytest.raises(ValueError, match="not one of"):
        _state(TWO_ZERO, ONE_ONE, past_pairings=(Pairing.of(TEAM_A, TEAM_C),))


def test_rejects_two_unbeaten_teams_having_met() -> None:
    with pytest.raises(ValueError, match="unbeaten"):
        _state(TWO_ZERO, TWO_ZERO, past_pairings=(Pairing.of(TEAM_A, TEAM_B),))


def test_record_of_unknown_team_is_an_error() -> None:
    with pytest.raises(ValueError, match="not one of"):
        _state(TWO_ZERO).record(TEAM_B)
