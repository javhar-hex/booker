from pathlib import Path

import pytest

from booker.cli import main


@pytest.fixture
def path(tmp_path: Path) -> str:
    return str(tmp_path / "atlas.db")


def test_expands_and_reports_each_depth(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["expand", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["stats", path])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == [
        "depth",
        "states",
        "collider",
        "pairings",
        "min-gtv",
        "max-gtv",
    ]
    assert [line.split()[0] for line in lines[1:]] == ["0", "1", "2", "3"]
    assert lines[1].split()[1:4] == ["1", "1", "120"]


def test_expands_with_the_vf2_state_symmetry(path: str) -> None:
    main(["expand", path, "--max-depth", "3", "--state-symmetry", "vf2"])


def test_refuses_to_solve_a_truncated_atlas(path: str) -> None:
    main(["expand", path, "--max-depth", "3"])

    with pytest.raises(RuntimeError, match="truncated"):
        main(["solve", path])


def test_the_vf2_state_symmetry_must_be_told_how_far_to_go(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["expand", path, "--state-symmetry", "vf2"])

    assert "--max-depth" in capsys.readouterr().err
    assert not Path(path).exists()


def test_rejects_an_unknown_state_symmetry(path: str) -> None:
    with pytest.raises(SystemExit):
        main(["expand", path, "--state-symmetry", "bogus"])


def test_needs_a_mode() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_verifies_a_generated_atlas(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["expand", path, "--max-depth", "3"])
    capsys.readouterr()
    main(["verify", path])

    assert capsys.readouterr().out.startswith("PASS: ids [start, end): checked ")


@pytest.mark.parametrize("implementation", ["bliss", "vf2"])
def test_verifies_strictly_with_any_implementation_of_the_symmetries(
    path: str, implementation: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["expand", path, "--max-depth", "3"])
    capsys.readouterr()
    main(
        [
            "verify",
            path,
            "--reference-symmetry",
            implementation,
            "--start-state-id",
            "2",
            "--max-num-states",
            "4",
        ]
    )

    out = capsys.readouterr().out
    assert "checked 4 states" in out
    assert f"compared by {implementation}" in out


def test_verify_reports_a_failure_in_one_line_and_exits_with_status_1(
    path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["expand", path, "--max-depth", "3"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as exit_info:
        main(["verify", path, "--require-complete"])

    assert exit_info.value.code == 1
    assert capsys.readouterr().err.startswith("FAIL: not complete")


@pytest.mark.parametrize("command", ["solve", "stats", "verify"])
def test_a_command_on_a_missing_atlas_is_refused_and_creates_nothing(
    path: str, command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([command, path])

    assert exit_info.value.code == 2
    assert "no such file" in capsys.readouterr().err
    assert not Path(path).exists()
