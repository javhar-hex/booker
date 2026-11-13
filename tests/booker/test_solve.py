import pytest
from javhar_util.immutables import ZSet, ZVec
from support.logs import discard

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.state_symmetries import BLISS
from booker.expand.atlas_expander import AtlasExpander
from booker.solve import solve

RECORD_5_1 = Record(wins=5, losses=1)
FINAL_PAIRING = Pairing.of(Team(index=0), Team(index=1))


@pytest.mark.parametrize("have_met", [False, True])
def test_returns_the_root_gtv_of_the_last_match(
    tmp_path_factory: pytest.TempPathFactory, have_met: bool
) -> None:
    path = tmp_path_factory.mktemp("last-match") / "atlas.db"
    final = State(
        records=ZVec([RECORD_5_1, RECORD_5_1]),
        past_pairings=ZSet([FINAL_PAIRING] if have_met else []),
    )
    with Atlas.open(path) as atlas:
        AtlasExpander.of(atlas=atlas, symmetry=BLISS, log=discard).expand(
            final, MAX_MATCHES
        )

    assert solve(path) == int(have_met)
