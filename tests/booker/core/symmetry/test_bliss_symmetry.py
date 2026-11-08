"""Pairing orbits by BLISS on schedules small or symmetric enough to count by hand."""

import dataclasses as dc

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.bliss_symmetry import BlissSymmetry, orbits_of_schedule
from booker.core.symmetry.orbits import PairingOrbits


def _pairing(index_lhs: int, index_rhs: int) -> Pairing:
    return Pairing.of(Team(index=index_lhs), Team(index=index_rhs))


@dc.dataclass(frozen=True)
class OrbitShape:
    representative: Pairing
    size: int


def _orbit(index_lhs: int, index_rhs: int, size: int) -> OrbitShape:
    return OrbitShape(representative=_pairing(index_lhs, index_rhs), size=size)


def _shapes(orbits: PairingOrbits) -> list[OrbitShape]:
    return [OrbitShape(representative=o.representative, size=o.size) for o in orbits]


ONE_BOOKED = Schedule(state=State.start(), pairings=ZSet([_pairing(0, 1)]))


def _same_record_pairings(state: State) -> ZSet[Pairing]:
    return ZSet(
        Pairing.of(team_lhs, team_rhs)
        for team_lhs in state.teams
        for team_rhs in state.teams
        if team_lhs < team_rhs and state.record(team_lhs) == state.record(team_rhs)
    )


def _state(*records: Record, met: tuple[Pairing, ...]) -> State:
    return State(records=ZVec(records), met=ZSet(met))


def test_every_first_round_pairing_is_alike() -> None:
    start = State.start()

    orbits = orbits_of_schedule(Schedule.empty(start), _same_record_pairings(start))

    assert _shapes(orbits) == [_orbit(0, 1, 120)]


def test_two_played_matches_leave_three_orbits() -> None:
    won, lost = Record(wins=1, losses=0), Record(wins=0, losses=1)
    state = _state(
        *[Record.fresh()] * 12,
        won,
        lost,
        won,
        lost,
        met=(_pairing(12, 13), _pairing(14, 15)),
    )

    orbits = orbits_of_schedule(Schedule.empty(state), _same_record_pairings(state))

    assert _shapes(orbits) == [_orbit(0, 1, 66), _orbit(12, 14, 1), _orbit(13, 15, 1)]


def test_a_rematch_is_an_orbit_of_its_own() -> None:
    state = _state(*[Record(wins=1, losses=1)] * 4, met=(_pairing(0, 1),))

    orbits = orbits_of_schedule(Schedule.empty(state), _same_record_pairings(state))

    assert _shapes(orbits) == [_orbit(0, 1, 1), _orbit(0, 2, 4), _orbit(2, 3, 1)]


def test_scheduled_pairings_break_the_symmetry() -> None:
    unbooked = ZSet(
        p for p in _same_record_pairings(State.start()) if p not in ONE_BOOKED.pairings
    )

    orbits = orbits_of_schedule(ONE_BOOKED, unbooked)

    assert _shapes(orbits) == [_orbit(0, 2, 2 * 14), _orbit(2, 3, 14 * 13 // 2)]


def test_orbits_partition_the_additions() -> None:
    additions = ZSet(
        p for p in _same_record_pairings(State.start()) if p not in ONE_BOOKED.pairings
    )

    orbits = orbits_of_schedule(ONE_BOOKED, additions)

    assert orbits.pairings == additions
    assert len(orbits) == 2


def test_no_additions_no_orbits() -> None:
    assert len(orbits_of_schedule(Schedule.empty(State.start()), ZSet([]))) == 0


def test_rejects_additions_not_closed_under_symmetry() -> None:
    with pytest.raises(ValueError, match="not closed"):
        orbits_of_schedule(Schedule.empty(State.start()), ZSet([_pairing(0, 1)]))


def test_rejects_additions_already_booked() -> None:
    with pytest.raises(ValueError, match="already booked"):
        orbits_of_schedule(ONE_BOOKED, _same_record_pairings(State.start()))


def test_the_symmetry_of_a_state_is_that_of_the_schedule_with_nothing_booked() -> None:
    state = _state(*[Record(wins=1, losses=1)] * 4, met=(_pairing(0, 1),))
    legal = _same_record_pairings(state)

    assert BlissSymmetry().orbits(state, legal) == orbits_of_schedule(
        Schedule.empty(state), legal
    )
