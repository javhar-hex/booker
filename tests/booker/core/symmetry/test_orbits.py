"""The data classes of pairing orbits: what an orbit is, and what makes a partition."""

import pytest
from javhar_util.immutables import ZSet, ZVec
from support.pairings import pairing_of_indices

from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.relabelling import Relabelling


def test_orbit_of_a_pairing_under_a_rotation_of_three_teams() -> None:
    rotation = ZVec([Relabelling.of([1, 2, 0])])

    orbit = PairingOrbit.of(pairing_of_indices(0, 1), rotation)

    assert orbit.members == ZSet(
        [pairing_of_indices(0, 1), pairing_of_indices(1, 2), pairing_of_indices(0, 2)]
    )
    assert (orbit.representative, orbit.size) == (pairing_of_indices(0, 1), 3)


def test_without_symmetries_an_orbit_is_a_single_pairing() -> None:
    assert PairingOrbit.of(pairing_of_indices(2, 5), ZVec([])).members == ZSet(
        [pairing_of_indices(2, 5)]
    )


def test_an_orbit_is_never_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PairingOrbit(members=ZSet([]))


def _single(index_lhs: int, index_rhs: int) -> PairingOrbit:
    return PairingOrbit(members=ZSet([pairing_of_indices(index_lhs, index_rhs)]))


def test_rejects_overlapping_orbits() -> None:
    overlapping = PairingOrbit(
        members=ZSet([pairing_of_indices(0, 1), pairing_of_indices(2, 3)])
    )

    with pytest.raises(ValueError, match="cannot overlap"):
        PairingOrbits(orbits=ZVec([overlapping, _single(2, 3)]))


def test_rejects_orbits_out_of_order() -> None:
    with pytest.raises(ValueError, match="in order"):
        PairingOrbits(orbits=ZVec([_single(2, 3), _single(0, 1)]))
