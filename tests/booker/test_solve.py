from pathlib import Path

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
from booker.solve import solve_atlas

RECORD_5_1 = Record(wins=5, losses=1)
FINAL_PAIRING = Pairing.of(Team(index=0), Team(index=1))


def _last_match_atlas(directory: Path, have_met: bool) -> Path:
    path = directory / "atlas.db"
    final = State(
        records=ZVec([RECORD_5_1, RECORD_5_1]),
        past_pairings=ZSet([FINAL_PAIRING] if have_met else []),
    )
    with Atlas.open(path) as atlas:
        AtlasExpander.of(atlas=atlas, symmetry=BLISS, log=discard).expand(
            final, MAX_MATCHES
        )
    return path


@pytest.mark.parametrize("have_met", [False, True])
def test_logs_the_root_gtv_of_the_last_match(tmp_path: Path, have_met: bool) -> None:
    messages: list[str] = []

    solve_atlas(_last_match_atlas(tmp_path, have_met), log=messages.append)

    assert messages[-1] == f"root GTV: {int(have_met)}"


def test_logs_each_depth_from_the_last_match_back_to_the_start(tmp_path: Path) -> None:
    messages: list[str] = []

    solve_atlas(_last_match_atlas(tmp_path, have_met=False), log=messages.append)

    assert messages[:-1] == [
        f"backing up depth {depth:02d}" for depth in range(MAX_MATCHES, -1, -1)
    ]
