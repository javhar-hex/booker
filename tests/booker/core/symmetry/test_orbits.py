"""Pairing orbits on schedules small or symmetric enough to count by hand."""

import dataclasses as dc

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.relabelling import Relabelling


def _pairing(a: int, b: int) -> Pairing:
    return Pairing.of(Team(index=a), Team(index=b))


@dc.dataclass(frozen=True)
class OrbitShape:
    representative: Pairing
    size: int


def _orbit(a: int, b: int, size: int) -> OrbitShape:
    return OrbitShape(representative=_pairing(a, b), size=size)


def _shapes(orbits: PairingOrbits) -> list[OrbitShape]:
    return [OrbitShape(representative=o.representative, size=o.size) for o in orbits]


ONE_BOOKED = Schedule(state=State.start(), pairings=ZSet([_pairing(0, 1)]))


def _same_record_pairings(state: State) -> ZSet[Pairing]:
    return ZSet(
        Pairing.of(x, y)
        for x in state.teams
        for y in state.teams
        if x < y and state.record(x) == state.record(y)
    )


def _state(*records: Record, met: tuple[Pairing, ...]) -> State:
    return State(records=ZVec(records), met=ZSet(met))


def test_every_first_round_pairing_is_alike() -> None:
    start = State.start()

    orbits = PairingOrbits.of(Schedule.empty(start), _same_record_pairings(start))

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

    orbits = PairingOrbits.of(Schedule.empty(state), _same_record_pairings(state))

    assert _shapes(orbits) == [_orbit(0, 1, 66), _orbit(12, 14, 1), _orbit(13, 15, 1)]


def test_a_rematch_is_an_orbit_of_its_own() -> None:
    state = _state(*[Record(wins=1, losses=1)] * 4, met=(_pairing(0, 1),))

    orbits = PairingOrbits.of(Schedule.empty(state), _same_record_pairings(state))

    assert _shapes(orbits) == [_orbit(0, 1, 1), _orbit(0, 2, 4), _orbit(2, 3, 1)]


def test_scheduled_pairings_break_the_symmetry() -> None:
    unbooked = ZSet(
        p for p in _same_record_pairings(State.start()) if p not in ONE_BOOKED.pairings
    )

    orbits = PairingOrbits.of(ONE_BOOKED, unbooked)

    assert _shapes(orbits) == [_orbit(0, 2, 2 * 14), _orbit(2, 3, 14 * 13 // 2)]


def test_rejects_additions_not_closed_under_symmetry() -> None:
    with pytest.raises(ValueError, match="not closed"):
        PairingOrbits.of(Schedule.empty(State.start()), ZSet([_pairing(0, 1)]))


def test_rejects_additions_already_booked() -> None:
    with pytest.raises(ValueError, match="already booked"):
        PairingOrbits.of(ONE_BOOKED, _same_record_pairings(State.start()))


def test_orbit_of_a_pairing_under_a_rotation_of_three_teams() -> None:
    rotation = ZVec([Relabelling.of([1, 2, 0])])

    orbit = PairingOrbit.of(_pairing(0, 1), rotation)

    assert orbit.members == ZSet([_pairing(0, 1), _pairing(1, 2), _pairing(0, 2)])
    assert (orbit.representative, orbit.size) == (_pairing(0, 1), 3)


def test_without_symmetries_an_orbit_is_a_single_pairing() -> None:
    assert PairingOrbit.of(_pairing(2, 5), ZVec([])).members == ZSet([_pairing(2, 5)])


def test_an_orbit_is_never_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PairingOrbit(members=ZSet([]))


def test_orbits_partition_the_additions() -> None:
    start = State.start()
    additions = ZSet(
        p for p in _same_record_pairings(start) if p not in ONE_BOOKED.pairings
    )

    orbits = PairingOrbits.of(ONE_BOOKED, additions)

    assert orbits.pairings == additions
    assert len(orbits) == 2


def test_no_additions_no_orbits() -> None:
    assert len(PairingOrbits.of(Schedule.empty(State.start()), ZSet([]))) == 0


def _single(a: int, b: int) -> PairingOrbit:
    return PairingOrbit(members=ZSet([_pairing(a, b)]))


def test_rejects_overlapping_orbits() -> None:
    overlapping = PairingOrbit(members=ZSet([_pairing(0, 1), _pairing(2, 3)]))

    with pytest.raises(ValueError, match="cannot overlap"):
        PairingOrbits(orbits=ZVec([overlapping, _single(2, 3)]))


def test_rejects_orbits_out_of_order() -> None:
    with pytest.raises(ValueError, match="in order"):
        PairingOrbits(orbits=ZVec([_single(2, 3), _single(0, 1)]))
