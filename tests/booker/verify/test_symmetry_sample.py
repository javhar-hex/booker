"""
The sample comparison of the symmetry implementations passes for correct implementations,
and fails for each way that an implementation can be wrong.
"""

from pathlib import Path

import pytest
from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.state_symmetries import STATE_SYMMETRIES
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.failure import AuditFailure
from booker.verify.symmetry_sample import compare_symmetries

ALL = STATE_SYMMETRIES


class NeverIsomorphic(StateSymmetry):
    "Wrong about isomorphism, right about orbits."

    @property
    def name(self) -> str:
        return "never-isomorphic"

    def are_isomorphic(self, first: State, second: State) -> bool:
        return False

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return BlissSymmetry().orbits(state, pairings)


class AlwaysIsomorphic(StateSymmetry):
    "Wrong about isomorphism, right about orbits."

    @property
    def name(self) -> str:
        return "always-isomorphic"

    def are_isomorphic(self, first: State, second: State) -> bool:
        return True

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return BlissSymmetry().orbits(state, pairings)


class NoSymmetry(StateSymmetry):
    "Right about isomorphism, but finds every pairing alone in its orbit."

    @property
    def name(self) -> str:
        return "no-symmetry"

    def are_isomorphic(self, first: State, second: State) -> bool:
        return BlissSymmetry().are_isomorphic(first, second)

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return PairingOrbits(
            orbits=ZVec(
                PairingOrbit(members=ZSet([pairing])) for pairing in sorted(pairings)
            )
        )


def test_correct_implementations_agree_on_a_sample(endgame: Path) -> None:
    report = compare_symmetries(str(endgame), ALL, samples=10, seed=0)

    assert report.states == 10
    assert report.orbit_questions == 10
    assert report.isomorphism_questions > report.states
    assert str(report).startswith("AGREE: 10 states, 10 orbit questions, ")


def test_a_sample_is_decided_by_its_seed(endgame: Path) -> None:
    assert compare_symmetries(
        str(endgame), ALL, samples=10, seed=4
    ) == compare_symmetries(str(endgame), ALL, samples=10, seed=4)


def test_a_sample_cannot_be_larger_than_the_atlas(endgame: Path) -> None:
    assert compare_symmetries(str(endgame), ALL, samples=10_000, seed=0).states == 29


def _with(wrong: StateSymmetry) -> ZMap[str, StateSymmetry]:
    return ZMap({"bliss": BlissSymmetry(), "wrong": wrong})


def test_an_implementation_that_denies_what_is_true_is_caught(endgame: Path) -> None:
    with pytest.raises(AuditFailure, match="wrong says isomorphic is not True"):
        compare_symmetries(
            str(endgame), _with(NeverIsomorphic()), samples=10_000, seed=0
        )


def test_an_implementation_that_confuses_different_states_is_caught(
    endgame: Path,
) -> None:
    with pytest.raises(AuditFailure, match="the implementations disagree"):
        compare_symmetries(
            str(endgame), _with(AlwaysIsomorphic()), samples=10_000, seed=0
        )


def test_an_implementation_that_finds_other_orbits_is_caught(endgame: Path) -> None:
    with pytest.raises(AuditFailure, match="find different orbits"):
        compare_symmetries(str(endgame), _with(NoSymmetry()), samples=10_000, seed=0)
