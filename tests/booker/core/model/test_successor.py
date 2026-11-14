import pytest
from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.model.team import Team

TEAM_A, TEAM_B, TEAM_C, TEAM_D = (Team(index=idx) for idx in range(4))


def _state(*records: Record, past_pairings: tuple[Pairing, ...] = ()) -> State:
    return State(records=ZVec(records), past_pairings=ZSet(past_pairings))


def _outcome(winners: dict[Pairing, Team]) -> Outcome:
    return Outcome(winners=ZMap(winners))


def _record(wins: int, losses: int) -> Record:
    return Record(wins=wins, losses=losses)


def test_updates_records_and_meetings() -> None:
    state = _state(_record(1, 0), _record(1, 0))

    after = successor(state, _outcome({Pairing.of(TEAM_A, TEAM_B): TEAM_B}))

    assert after == _state(
        _record(1, 1), _record(2, 0), past_pairings=(Pairing.of(TEAM_A, TEAM_B),)
    )


def test_drops_eliminated_teams_and_renumbers_survivors() -> None:
    state = _state(
        _record(1, 1),
        _record(1, 1),
        _record(2, 0),
        past_pairings=(Pairing.of(TEAM_A, TEAM_C),),
    )

    after = successor(state, _outcome({Pairing.of(TEAM_A, TEAM_B): TEAM_B}))

    assert after == _state(_record(2, 1), _record(2, 0))


def test_meetings_among_survivors_are_renumbered() -> None:
    state = _state(_record(0, 1), _record(0, 1), _record(1, 0), _record(1, 0))

    after = successor(
        state,
        _outcome(
            {Pairing.of(TEAM_A, TEAM_B): TEAM_B, Pairing.of(TEAM_C, TEAM_D): TEAM_D}
        ),
    )

    assert after == _state(
        _record(1, 1),
        _record(1, 1),
        _record(2, 0),
        past_pairings=(Pairing.of(TEAM_B, TEAM_C),),
    )


def test_a_team_in_two_pairings_gets_both_results() -> None:
    semifinal = _state(_record(4, 0), _record(4, 1), _record(4, 1))

    after = successor(
        semifinal,
        _outcome(
            {Pairing.of(TEAM_A, TEAM_B): TEAM_A, Pairing.of(TEAM_A, TEAM_C): TEAM_C}
        ),
    )

    assert after == _state(
        _record(5, 1), _record(5, 1), past_pairings=(Pairing.of(TEAM_A, TEAM_B),)
    )


def test_champion_alone_remains() -> None:
    final = _state(
        _record(5, 1), _record(5, 1), past_pairings=(Pairing.of(TEAM_A, TEAM_B),)
    )

    after = successor(final, _outcome({Pairing.of(TEAM_A, TEAM_B): TEAM_B}))

    assert after == _state(_record(6, 1))
    assert after.is_leaf


def test_rejects_results_for_teams_not_in_the_state() -> None:
    with pytest.raises(ValueError, match="not one of"):
        successor(
            _state(_record(0, 0), _record(0, 0)),
            _outcome({Pairing.of(TEAM_A, TEAM_C): TEAM_C}),
        )
