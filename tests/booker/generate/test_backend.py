from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling
from booker.generate.backend import BLISS, VF2, Backend, BlissCanonicalizer
from booker.generate.vf2 import MAX_DEPTH as VF2_MAX_DEPTH

ONE_ONE = Record(wins=1, losses=1)
PATH = State(
    records=ZVec([ONE_ONE] * 4),
    met=ZSet(
        Pairing.of(Team(index=a), Team(index=b)) for a, b in [(0, 1), (1, 2), (2, 3)]
    ),
)
SHUFFLED_PATH = Relabelling.of([2, 0, 3, 1]).state(PATH)


def test_backends_are_named_as_an_atlas_records_them() -> None:
    assert (Backend("bliss"), Backend("vf2")) == (BLISS, VF2)


def test_bliss_generates_the_whole_game_and_vf2_a_prefix() -> None:
    assert BLISS.max_depth == MAX_MATCHES
    assert VF2.max_depth == VF2_MAX_DEPTH < MAX_MATCHES


def test_bliss_maps_isomorphic_states_to_one_state() -> None:
    canon = BlissCanonicalizer()

    assert SHUFFLED_PATH != PATH
    assert canon(SHUFFLED_PATH) == canon(PATH)


def test_bliss_ignores_the_known_states() -> None:
    assert BLISS.canonicalizer([PATH])(SHUFFLED_PATH) == BlissCanonicalizer()(PATH)


def test_vf2_stays_consistent_with_the_known_states() -> None:
    assert VF2.canonicalizer([PATH])(SHUFFLED_PATH) == PATH
