"""
The verifier shares the game's rules and the model with the generator, which unit tests
cover, and the implementations of the symmetries of states, which tests compare with one
another. What it must not share is the code that generates and writes the atlas.
"""

import ast
from pathlib import Path

import booker.verify

ALLOWED_OUTSIDE_VERIFY = (
    "booker.core.model.",
    "booker.core.symmetry.",
    "booker.game.",
    "booker.atlas.packed_state",
    "booker.atlas.schema",
)


def _imports(subpackage: str = "") -> set[str]:
    package = Path(booker.verify.__file__).parent / subpackage
    imported: set[str] = set()
    for source in package.rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
    return {name for name in imported if name.startswith("booker")}


def test_the_verifier_reads_the_atlas_with_its_own_code() -> None:
    assert "booker.verify.spot_check.database" in _imports()


def test_the_verifier_imports_nothing_that_generates_the_atlas() -> None:
    outside = {name for name in _imports() if not name.startswith("booker.verify")}

    assert outside
    assert all(name.startswith(ALLOWED_OUTSIDE_VERIFY) for name in outside), outside


def test_the_spot_check_knows_nothing_of_the_audit_that_runs_it() -> None:
    inside = {
        name for name in _imports("spot_check") if name.startswith("booker.verify")
    }

    assert inside
    assert all(name.startswith("booker.verify.spot_check") for name in inside), inside
