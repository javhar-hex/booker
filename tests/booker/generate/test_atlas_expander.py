import sqlite3
from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.generate.atlas_expander import AtlasExpander, generate
from booker.generate.state_canonicalizer import StateCanonicalizer

DEPTH = 5


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "atlas.db"


def _contents(path: Path) -> list[tuple[object, ...]]:
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT 's', id, key, depth, active, expanded FROM states "
        "UNION ALL SELECT 'a', parent, lhs, rhs, repeat_cost, class_size || ',' || lhs_wins "
        "|| ',' || rhs_wins FROM actions ORDER BY 1, 2, 3, 4"
    ).fetchall()
    con.close()
    return rows


@pytest.mark.parametrize("depth", [-1, MAX_MATCHES + 1])
def test_rejects_a_depth_outside_the_game(path: Path, depth: int) -> None:
    with pytest.raises(ValueError, match="between 0 and"):
        generate(str(path), depth, BLISS)


def test_resumed_generation_matches_generation_in_one_go(
    path: Path, tmp_path: Path
) -> None:
    generate(str(path), 2, BLISS)
    generate(str(path), DEPTH, BLISS)
    generate(str(tmp_path / "direct.db"), DEPTH, BLISS)

    assert _contents(path) == _contents(tmp_path / "direct.db")


def test_generating_again_changes_nothing(path: Path) -> None:
    generate(str(path), DEPTH, BLISS)
    before = _contents(path)
    generate(str(path), DEPTH, BLISS)

    assert _contents(path) == before


def test_an_atlas_is_not_resumed_with_another_symmetry(path: Path) -> None:
    generate(str(path), 2, BLISS)

    with pytest.raises(ValueError, match="Cannot resume bliss atlas using vf2"):
        generate(str(path), 2, VF2)


def test_expands_the_rest_of_a_game_from_a_late_state(path: Path) -> None:
    final = Record(wins=5, losses=1)
    last_match = State(
        records=ZVec([final, final]),
        past_pairings=ZSet([Pairing.of(Team(index=0), Team(index=1))]),
    )

    with Atlas.open(path) as atlas:
        AtlasExpander(
            atlas=atlas,
            symmetry=BLISS,
            state_canonicalizer=StateCanonicalizer(symmetry=BLISS, known=[]),
        ).expand(last_match, MAX_MATCHES)

        assert set(atlas.states()) == {
            last_match,
            State(records=ZVec([Record(wins=6, losses=1)]), past_pairings=ZSet([])),
        }
        assert atlas.num_actions() == 1
        assert atlas.num_unexpanded() == 0
