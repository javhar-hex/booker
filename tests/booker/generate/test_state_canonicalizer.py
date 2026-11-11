import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.state_symmetries import BLISS, STATE_SYMMETRIES, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.generate.state_canonicalizer import StateCanonicalizer

RECORD_1_1 = Record(wins=1, losses=1)
PATH = State(
    records=ZVec([RECORD_1_1] * 4),
    past_pairings=ZSet(
        Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
        for index_lhs, index_rhs in [(0, 1), (1, 2), (2, 3)]
    ),
)
SHUFFLED_PATH = Relabelling.of([2, 0, 3, 1]).state(PATH)


@pytest.mark.parametrize("symmetry", list(STATE_SYMMETRIES.values()))
def test_maps_isomorphic_states_to_one_state(symmetry: StateSymmetry) -> None:
    canonicalizer = StateCanonicalizer(symmetry=symmetry, known_states=[])

    assert SHUFFLED_PATH != PATH
    assert canonicalizer(SHUFFLED_PATH) == canonicalizer(PATH)


def test_bliss_ignores_the_known_states() -> None:
    with_known_states = StateCanonicalizer(symmetry=BLISS, known_states=[PATH])

    assert with_known_states(SHUFFLED_PATH) == StateCanonicalizer(
        symmetry=BLISS, known_states=[]
    )(PATH)


def test_vf2_stays_consistent_with_the_known_states() -> None:
    assert StateCanonicalizer(symmetry=VF2, known_states=[PATH])(SHUFFLED_PATH) == PATH
