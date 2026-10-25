import pytest

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.model.team import Team
from util.dtypes.immutables.z_map import ZMap
from util.dtypes.immutables.z_set import ZSet
from util.dtypes.immutables.z_vec import ZVec

A, B, C, D = (Team(index=i) for i in range(4))


def _state(*records: Record, met: tuple[Pairing, ...] = ()) -> State:
    return State(records=ZVec(records), met=ZSet(met))


def _outcome(winners: dict[Pairing, Team]) -> Outcome:
    return Outcome(winners=ZMap(winners))


def _record(wins: int, losses: int) -> Record:
    return Record(wins=wins, losses=losses)


def test_updates_records_and_meetings() -> None:
    state = _state(_record(1, 0), _record(1, 0))

    after = successor(state, _outcome({Pairing.of(A, B): B}))

    assert after == _state(_record(1, 1), _record(2, 0), met=(Pairing.of(A, B),))


def test_drops_eliminated_teams_and_renumbers_survivors() -> None:
    state = _state(_record(1, 1), _record(1, 1), _record(2, 0), met=(Pairing.of(A, C),))

    after = successor(state, _outcome({Pairing.of(A, B): B}))

    assert after == _state(_record(2, 1), _record(2, 0))


def test_meetings_among_survivors_are_renumbered() -> None:
    state = _state(_record(0, 1), _record(0, 1), _record(1, 0), _record(1, 0))

    after = successor(state, _outcome({Pairing.of(A, B): B, Pairing.of(C, D): D}))

    assert after == _state(
        _record(1, 1), _record(1, 1), _record(2, 0), met=(Pairing.of(B, C),)
    )


def test_a_team_in_two_pairings_gets_both_results() -> None:
    semifinal = _state(_record(4, 0), _record(4, 1), _record(4, 1))

    after = successor(semifinal, _outcome({Pairing.of(A, B): A, Pairing.of(A, C): C}))

    assert after == _state(_record(5, 1), _record(5, 1), met=(Pairing.of(A, B),))


def test_champion_alone_remains() -> None:
    final = _state(_record(5, 1), _record(5, 1), met=(Pairing.of(A, B),))

    after = successor(final, _outcome({Pairing.of(A, B): B}))

    assert after == _state(_record(6, 1))
    assert after.is_decided


def test_rejects_results_for_teams_not_in_the_state() -> None:
    with pytest.raises(ValueError, match="not one of"):
        successor(_state(_record(0, 0), _record(0, 0)), _outcome({Pairing.of(A, C): C}))
