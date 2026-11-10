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
from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.canonical_schedule import canonical_state
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.symmetries import BLISS, VF2
from booker.generate.generator import Generator, generate, state_canonicalizer_for

DEPTH = 5
RECORD_1_1 = Record(wins=1, losses=1)
PATH = State(
    records=ZVec([RECORD_1_1] * 4),
    past_pairings=ZSet(
        Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
        for index_lhs, index_rhs in [(0, 1), (1, 2), (2, 3)]
    ),
)
SHUFFLED_PATH = Relabelling.of([2, 0, 3, 1]).state(PATH)


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
        Generator(
            atlas=atlas, symmetry=BlissSymmetry(), state_canonicalizer=canonical_state
        ).expand(last_match, MAX_MATCHES)

        assert set(atlas.states()) == {
            last_match,
            State(records=ZVec([Record(wins=6, losses=1)]), past_pairings=ZSet([])),
        }
        assert atlas.num_actions() == 1
        assert atlas.num_unexpanded() == 0


def test_bliss_maps_isomorphic_states_to_one_state() -> None:
    canonicalizer = state_canonicalizer_for(BLISS, [])

    assert SHUFFLED_PATH != PATH
    assert canonicalizer(SHUFFLED_PATH) == canonicalizer(PATH)


def test_bliss_ignores_the_known_states() -> None:
    known = state_canonicalizer_for(BLISS, [PATH])
    assert known(SHUFFLED_PATH) == state_canonicalizer_for(BLISS, [])(PATH)


def test_vf2_stays_consistent_with_the_known_states() -> None:
    assert state_canonicalizer_for(VF2, [PATH])(SHUFFLED_PATH) == PATH
