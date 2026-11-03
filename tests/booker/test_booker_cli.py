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


def test_the_vf2_backend_must_be_told_how_far_to_go(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["generate", path, "--backend", "vf2"])

    assert "--max-depth" in capsys.readouterr().err
    assert not Path(path).exists()


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


@pytest.mark.parametrize("implementation", ["bliss", "vf2"])
def test_verifies_strictly_with_any_implementation_of_the_symmetries(
    path: str, implementation: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["verify", path, "--strict", implementation, "--from-id", "2", "--limit", "4"])

    out = capsys.readouterr().out
    assert "checked 4 states" in out
    assert f"compared by {implementation}" in out


def test_verify_fails_loudly_on_a_bad_atlas(path: str) -> None:
    main(["generate", path, "--max-depth", "3"])

    with pytest.raises(AuditFailure, match="not complete"):
        main(["verify", path, "--require-complete"])


def test_compares_the_symmetry_implementations_on_sampled_states(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "4"])
    capsys.readouterr()
    main(["compare-symmetry", path, "--samples", "5", "--seed", "3"])

    assert capsys.readouterr().out.startswith("AGREE: 5 states, 5 orbit questions, ")


def test_there_can_be_no_more_samples_than_states(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["generate", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["compare-symmetry", path, "--samples", "500"])

    assert capsys.readouterr().out.startswith("AGREE: 6 states, ")
