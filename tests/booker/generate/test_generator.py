import sqlite3
from pathlib import Path

import pytest

from booker.core.model.invariants import MAX_MATCHES
from booker.generate.backend import BLISS, VF2
from booker.generate.generator import generate

DEPTH = 5


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "atlas.db"


def _contents(path: Path) -> list[tuple[object, ...]]:
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT 's', id, key, depth, active, expanded FROM states "
        "UNION ALL SELECT 'a', parent, a, b, repeat_cost, class_size || ',' || a_wins "
        "|| ',' || b_wins FROM actions ORDER BY 1, 2, 3, 4"
    ).fetchall()
    con.close()
    return rows


@pytest.mark.parametrize("depth", [-1, MAX_MATCHES + 1])
def test_rejects_a_depth_outside_the_game(path: Path, depth: int) -> None:
    with pytest.raises(ValueError, match="at most"):
        generate(str(path), depth, BLISS)


def test_rejects_a_depth_the_vf2_backend_cannot_manage(path: Path) -> None:
    with pytest.raises(ValueError, match="vf2 generates to depth"):
        generate(str(path), VF2.max_depth + 1, VF2)


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


def test_an_atlas_is_not_resumed_with_another_backend(path: Path) -> None:
    generate(str(path), 2, BLISS)

    with pytest.raises(ValueError, match="Cannot resume bliss atlas using vf2"):
        generate(str(path), 2, VF2)
