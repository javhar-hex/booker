from pathlib import Path

import pytest

from booker.cli import main
from booker.verify.failure import AuditFailure


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


def test_verifies_a_generated_atlas(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["verify", path])

    assert capsys.readouterr().out.startswith("PASS: ids [start, end): checked ")


@pytest.mark.parametrize("mode", ["networkx", "igraph"])
def test_verifies_with_either_isomorphism_library(
    path: str, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["verify", path, "--mode", mode, "--from-id", "2", "--limit", "4"])

    out = capsys.readouterr().out
    assert "checked 4 states" in out
    assert f"with independent {mode.upper()} isomorphism" in out


def test_verify_fails_loudly_on_a_bad_atlas(path: str) -> None:
    main(["generate", path, "--max-depth", "3"])

    with pytest.raises(AuditFailure, match="not complete"):
        main(["verify", path, "--require-complete"])
