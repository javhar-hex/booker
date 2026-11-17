# booker

A solver for a combinatorial game on tournaments, and an independent verifier of its
solution.

The tournament is a 16-team double-elimination bracket in which a team is eliminated
after 2 losses and the champion needs exactly 6 wins. In the *unrestricted* game there
are no rounds: any legal pairing may be booked at any time. Two players take turns:

- the **Scheduler** books a legal pairing, trying to avoid *repeats*, matches between
  teams that have already met;
- the **Collider** decides who wins that match, trying to force repeats.

The **game-theoretical value (GTV)** of a position is the number of further repeats that
occur under optimal play by both players: the Scheduler can keep it from exceeding that
value, and the Collider can keep it from falling below. `booker` builds
the whole game graph up to isomorphism (an *atlas*, stored in SQLite), solves it by
retrograde analysis, verifies the result with a separate implementation, and analyzes which
positions can be reached when both players play optimally.

## Result

The value of the game is **3**: with optimal play on both sides, a tournament has exactly
three repeats.

| | |
|---|---|
| Scheduler positions (canonical states, up to isomorphism) | 661,114 |
| Stored Collider positions (one per Scheduler action, up to symmetry) | 5,431,178 |
| Labelled pairings those actions stand for | 6,295,589 |
| Depths (matches played) | 0 to 31 |
| Scheduler positions reachable under optimal play | 481,272 |
| Collider positions reachable under optimal play | 3,494,664 |
| *Critical* Collider positions | 442,706 |

A Collider position is *critical* when it is reachable under optimal play and its two
possible winners lead to positions of different value, so that one of the two moves is a
mistake.

## Installation

Python 3.11 or newer. Tested on Linux, with Python 3.11 to 3.14.

```
pip install "booker @ git+https://github.com/javhar-hex/booker"
```

This installs `networkx`, `igraph` and [`javhar-util`](https://github.com/javhar-hex/util)
(immutable collections), and a `booker` command (`python -m booker.cli` works too).

## Usage

The commands work on one SQLite file, the atlas:

```
booker expand atlas.db                # build the atlas
booker solve atlas.db                 # back up the GTVs; logs the root GTV
booker stats atlas.db                 # states, Collider positions and GTVs by depth
booker verify atlas.db --require-complete --expected-root-gtv 3
booker equilibrium atlas.db analysis.db   # which positions optimal play reaches
```

Each command has `--help`. To try the pipeline in seconds, stop the expansion early:
`booker expand atlas.db --max-depth 6` gives a small atlas that `stats` and `verify` accept.

Reproducing the whole atlas takes about 1 hour 45 minutes for `expand`, under a minute for
`solve`, about an hour for `verify` and about a minute for `equilibrium`, on a 2-core cloud
VM. The atlas is 459 MB and the equilibrium analysis 202 MB.

## What the verifier checks

`booker.verify` reads the atlas with its own SQL, not through the code that wrote it. It
shares only the rules of the game, the model and the schema constants with the generator
(a test enforces what it may import).

- **Every position** (`verify`): the stored key decodes to a valid position; its depth and
  team count agree with its records; its pairings are legal; the sizes of its symmetry
  orbits add up; each child is exactly one match deeper; and its GTV is the minimax of its
  children's. Leaves are worth 0.
- **The atlas as a whole**: its metadata and schema version; the opening position; no
  orphan positions; SQLite's integrity and foreign-key checks; with `--require-complete`,
  that nothing is unexpanded or unsolved and that both possible endings are present; with
  `--expected-root-gtv`, the value of the root.
- **`--reference-symmetry`** (slow, hours for the whole atlas): additionally re-derives
  every child and every orbit with a second, independent implementation of the symmetries
  of positions (`bliss` through `igraph`, or `vf2` through `networkx`) and compares them.

A run can be split into ranges (`--start-state-id`, `--stop-state-id`), capped
(`--max-num-states`) and resumed from a progress file (`--checkpoint`). A failed audit prints
one `FAIL:` line and exits with status 1.

## Limitations

- Only the (16, 2, 6) tournament is built: its parameters are constants in
  `booker.core.model.invariants`, and the rules in `booker.game` are specific to it.
- Counts are up to isomorphism of the standings and of the meetings already played. They are
  not counts of labelled schedules.
- The default (`bliss`) symmetry implementation is the only one that can expand the whole
  game: `vf2` gets slower with every position it meets and needs `--max-depth`.
- The release was verified with the default checks over the whole atlas. The slow
  `--reference-symmetry` pass has not been run over the whole atlas; the tests run it on small
  atlases.
- The atlas is an SQLite file in WAL mode, written by one process at a time.

## Layout

```
booker.core.model       the tournament model: teams, records, positions, pairings
booker.core.symmetry    isomorphism, automorphisms and canonical forms of schedules
booker.game             the legal pairings of the unrestricted game
booker.atlas            the SQLite atlas: schema, writers, retrograde solver
booker.expand           expands the atlas from the opening position
booker.solve            solves it from the last match back to the first
booker.equilibrium      which positions optimal play can reach
booker.verify           spot_check: one position; audit: the atlas as a whole
booker.cli              the command line
```

The packages and the modules inside them depend on each other without cycles; see the
[dependency diagram](docs/dependencies.svg).

## Development

```
pip install -e ".[dev]"
ruff check && ruff format --check && mypy src tests && pytest
```

The code is strictly typed (`mypy --strict`) and immutable by default.

## License

Apache License 2.0.
