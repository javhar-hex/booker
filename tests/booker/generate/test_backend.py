import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling
from booker.generate.backend import BLISS, VF2, Backend, BlissCanonicalizer
from booker.generate.canonicalizer import Canonicalizer

RECORD_1_1 = Record(wins=1, losses=1)
PATH = State(
    records=ZVec([RECORD_1_1] * 4),
    past_pairings=ZSet(
        Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
        for index_lhs, index_rhs in [(0, 1), (1, 2), (2, 3)]
    ),
)
SHUFFLED_PATH = Relabelling.of([2, 0, 3, 1]).state(PATH)


def test_backends_are_named_as_an_atlas_records_them() -> None:
    assert (Backend("bliss"), Backend("vf2")) == (BLISS, VF2)


@pytest.mark.parametrize("backend", list(Backend))
def test_every_canonicalizer_declares_that_it_implements_the_protocol(
    backend: Backend,
) -> None:
    assert Canonicalizer in type(backend.canonicalizer([])).__mro__


def test_bliss_maps_isomorphic_states_to_one_state() -> None:
    canon = BlissCanonicalizer()

    assert SHUFFLED_PATH != PATH
    assert canon(SHUFFLED_PATH) == canon(PATH)


def test_bliss_ignores_the_known_states() -> None:
    assert BLISS.canonicalizer([PATH])(SHUFFLED_PATH) == BlissCanonicalizer()(PATH)


def test_vf2_stays_consistent_with_the_known_states() -> None:
    assert VF2.canonicalizer([PATH])(SHUFFLED_PATH) == PATH
