"""Atlases shared by the tests of the verifier."""

from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.state_symmetries import BLISS
from booker.generate.generator import Generator
from booker.generate.state_canonicalizer import StateCanonicalizer
from booker.solve import solve

ENDGAME = State(
    records=ZVec([Record(wins=4, losses=0)] + [Record(wins=3, losses=1)] * 4),
    past_pairings=ZSet(Pairing.of(Team(index=a), Team(index=4)) for a in (0, 1, 2)),
)


@pytest.fixture(scope="module")
def endgame(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    The rest of a real game from five teams on, fully generated and solved: unlike the
    hand-built atlases, its Scheduler has actions worth different amounts, and its
    Collider positions have children worth different amounts, so that a value taken as
    a minimum where it should be a maximum, or the reverse, shows. It has 29 states,
    all of them late enough in the game to be quick to compare.
    """
    path = tmp_path_factory.mktemp("endgame") / "atlas.db"
    with Atlas.open(path) as atlas:
        Generator(
            atlas=atlas,
            symmetry=BLISS,
            state_canonicalizer=StateCanonicalizer(symmetry=BLISS, known=[]),
        ).expand(ENDGAME, MAX_MATCHES)
    solve(str(path))
    return path
