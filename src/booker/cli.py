"""Command line: `python -m booker.cli generate|solve|stats <atlas.db>`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from booker.atlas.storage import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.generate.backend import BLISS, Backend
from booker.generate.generator import generate
from booker.solve import solve


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.mode == "generate":
        generate(args.db, args.max_depth, Backend(args.backend))
    elif args.mode == "solve":
        solve(args.db)
    else:
        _print_stats(args.db)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unrestricted (16,2,6) Scheduler-Collider atlas"
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    generating = sub.add_parser("generate")
    generating.add_argument("db")
    generating.add_argument("--max-depth", type=int, default=MAX_MATCHES)
    generating.add_argument(
        "--backend", choices=[b.value for b in Backend], default=BLISS.value
    )
    sub.add_parser("solve").add_argument("db")
    sub.add_parser("stats").add_argument("db")
    return parser


def _print_stats(path: str) -> None:
    print("depth  states  collider  pairings  min-value  max-value")
    with Atlas.open(path) as atlas:
        for row in atlas.depth_summaries():
            print(
                f"{row.depth:>5} {row.num_states:>7,} {row.num_colliders:>9,} "
                f"{row.num_pairings:>9,} {row.min_value!s:>10} {row.max_value!s:>10}"
            )


if __name__ == "__main__":
    main()
