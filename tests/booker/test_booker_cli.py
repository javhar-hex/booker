from pathlib import Path

import pytest

from booker.cli import main


@pytest.fixture
def path(tmp_path: Path) -> str:
    return str(tmp_path / "atlas.db")


def test_generates_and_reports_each_depth(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["stats", path])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == [
        "depth",
        "states",
        "collider",
        "pairings",
        "min-value",
        "max-value",
    ]
    assert [line.split()[0] for line in lines[1:]] == ["0", "1", "2", "3"]
    assert lines[1].split()[1:4] == ["1", "1", "120"]


def test_generates_with_the_vf2_backend(path: str) -> None:
    main(["generate", path, "--max-depth", "3", "--backend", "vf2"])


def test_refuses_to_solve_a_truncated_atlas(path: str) -> None:
    main(["generate", path, "--max-depth", "3"])

    with pytest.raises(RuntimeError, match="truncated"):
        main(["solve", path])


def test_rejects_an_unknown_backend(path: str) -> None:
    with pytest.raises(SystemExit):
        main(["generate", path, "--backend", "bogus"])


def test_needs_a_mode() -> None:
    with pytest.raises(SystemExit):
        main([])
