"""
The verifier shares the game's rules and the model with the generator, which unit tests
cover. What it must not share is the code it checks: how states are canonicalized,
how orbits are found, and how the atlas is written.
"""

import ast
from pathlib import Path

import booker.verify

ALLOWED_OUTSIDE_VERIFY = (
    "booker.core.model.",
    "booker.game.",
    "booker.atlas.codec",
    "booker.atlas.schema",
)


def _imports() -> set[str]:
    package = Path(booker.verify.__file__).parent
    imported: set[str] = set()
    for source in package.glob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
    return {name for name in imported if name.startswith("booker")}


def test_the_verifier_reads_the_atlas_with_its_own_code() -> None:
    assert "booker.verify.database" in _imports()


def test_the_verifier_imports_nothing_that_generates_the_atlas() -> None:
    outside = {name for name in _imports() if not name.startswith("booker.verify")}

    assert outside
    assert all(name.startswith(ALLOWED_OUTSIDE_VERIFY) for name in outside), outside
