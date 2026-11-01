# booker

A game-agnostic tournament model (`booker.core.model`), isomorphism and automorphism
of schedules (`booker.core.symmetry`), and a generator, retrograde minimax solver and
verifier for the unrestricted Scheduler/Collider game.

## Installation

```
pip install "booker @ git+https://github.com/javhar-hex/booker"
```

Depends on [`javhar-util`](https://github.com/javhar-hex/util) for its immutable
collections, plus `networkx` and `igraph`.

## Development

```
pip install -e ".[dev]"
ruff check && ruff format --check && mypy src tests && pytest
```
