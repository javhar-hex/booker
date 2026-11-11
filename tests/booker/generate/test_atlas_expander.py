import sqlite3
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
from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.generate.atlas_expander import AtlasExpander, expand_atlas
from booker.generate.expansion_summary import ExpansionSummary

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
        expand_atlas(str(path), depth, BLISS, log=discard)


def test_resumed_generation_matches_generation_in_one_go(
    path: Path, tmp_path: Path
) -> None:
    expand_atlas(str(path), 2, BLISS, log=discard)
    expand_atlas(str(path), DEPTH, BLISS, log=discard)
    expand_atlas(str(tmp_path / "direct.db"), DEPTH, BLISS, log=discard)

    assert _contents(path) == _contents(tmp_path / "direct.db")


def test_generating_again_changes_nothing(path: Path) -> None:
    expand_atlas(str(path), DEPTH, BLISS, log=discard)
    before = _contents(path)
    expand_atlas(str(path), DEPTH, BLISS, log=discard)

    assert _contents(path) == before


def test_an_atlas_is_not_resumed_with_another_symmetry(path: Path) -> None:
    expand_atlas(str(path), 2, BLISS, log=discard)

    with pytest.raises(ValueError, match="Cannot resume bliss atlas using vf2"):
        expand_atlas(str(path), 2, VF2, log=discard)


def test_expands_the_rest_of_a_game_from_a_late_state(path: Path) -> None:
    final = Record(wins=5, losses=1)
    last_match = State(
        records=ZVec([final, final]),
        past_pairings=ZSet([Pairing.of(Team(index=0), Team(index=1))]),
    )

    with Atlas.open(path) as atlas:
        AtlasExpander.of(atlas=atlas, symmetry=BLISS, log=discard).expand(
            last_match, MAX_MATCHES
        )

        assert set(atlas.states()) == {
            last_match,
            State(records=ZVec([Record(wins=6, losses=1)]), past_pairings=ZSet([])),
        }
        assert atlas.num_actions() == 1
        assert atlas.num_unexpanded() == 0


def test_logs_each_depth_that_it_expands(path: Path) -> None:
    messages: list[str] = []

    expand_atlas(str(path), 2, BLISS, log=messages.append)

    assert messages == [
        "expanding depth 00: 1 states",
        "expanding depth 01: 1 states",
    ]


def test_logs_nothing_for_depths_that_are_expanded_already(path: Path) -> None:
    expand_atlas(str(path), 2, BLISS, log=discard)
    messages: list[str] = []

    expand_atlas(str(path), 2, BLISS, log=messages.append)

    assert messages == []


def test_returns_how_much_the_atlas_holds(path: Path) -> None:
    summary = expand_atlas(str(path), DEPTH, BLISS, log=discard)

    with Atlas.open(path) as atlas:
        assert summary == ExpansionSummary(
            num_states=atlas.num_states(), num_actions=atlas.num_actions()
        )
    assert summary.num_states > 0 and summary.num_actions > 0


def test_a_resumed_vf2_expansion_knows_the_states_already_stored(
    path: Path, tmp_path: Path
) -> None:
    expand_atlas(str(path), 2, VF2, log=discard)
    expand_atlas(str(path), 3, VF2, log=discard)
    expand_atlas(str(tmp_path / "direct.db"), 3, VF2, log=discard)

    assert _contents(path) == _contents(tmp_path / "direct.db")
