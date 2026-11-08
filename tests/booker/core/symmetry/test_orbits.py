"""The data classes of pairing orbits: what an orbit is, and what makes a partition."""

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.relabelling import Relabelling


def _pairing(index_lhs: int, index_rhs: int) -> Pairing:
    return Pairing.of(Team(index=index_lhs), Team(index=index_rhs))


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


def _single(index_lhs: int, index_rhs: int) -> PairingOrbit:
    return PairingOrbit(members=ZSet([_pairing(index_lhs, index_rhs)]))


def test_rejects_overlapping_orbits() -> None:
    overlapping = PairingOrbit(members=ZSet([_pairing(0, 1), _pairing(2, 3)]))

    with pytest.raises(ValueError, match="cannot overlap"):
        PairingOrbits(orbits=ZVec([overlapping, _single(2, 3)]))


def test_rejects_orbits_out_of_order() -> None:
    with pytest.raises(ValueError, match="in order"):
        PairingOrbits(orbits=ZVec([_single(2, 3), _single(0, 1)]))
