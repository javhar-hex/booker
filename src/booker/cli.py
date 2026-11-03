"""Command line: `python -m booker.cli generate|solve|stats|verify <atlas.db>`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from booker.atlas.storage import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.generate.backend import BLISS, Backend
from booker.generate.generator import generate
from booker.solve import solve
from booker.verify.audit import audit
from booker.verify.isomorphism import NETWORKX, Mode
from booker.verify.plan import AuditPlan, IdRange


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "generate":
        generate(args.db, args.max_depth, Backend(args.backend))
    elif args.command == "solve":
        solve(args.db)
    elif args.command == "verify":
        _verify(args)
    else:
        _print_stats(args.db)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unrestricted (16,2,6) Scheduler-Collider atlas"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    generating = sub.add_parser("generate")
    generating.add_argument("db")
    generating.add_argument("--max-depth", type=int, default=MAX_MATCHES)
    generating.add_argument(
        "--backend", choices=[b.value for b in Backend], default=BLISS.value
    )
    sub.add_parser("solve").add_argument("db")
    sub.add_parser("stats").add_argument("db")
    _add_verify(sub)
    return parser


def _add_verify(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    verifying = sub.add_parser(
        "verify", help="independent position/transition/minimax verifier"
    )
    verifying.add_argument("db")
    verifying.add_argument(
        "--mode", choices=[m.value for m in Mode], default=NETWORKX.value
    )
    verifying.add_argument(
        "--limit", type=int, default=0, help="Number of states to check (0=all)"
    )
    verifying.add_argument("--require-complete", action="store_true")
    verifying.add_argument("--expect-root", type=int)
    verifying.add_argument(
        "--from-id",
        type=int,
        help="First state id to check (inclusive); "
        "whole-database checks run only when omitted",
    )
    verifying.add_argument(
        "--to-id", type=int, help="State id to stop before (exclusive)"
    )
    verifying.add_argument(
        "--checkpoint", help="Progress file: saved periodically, resumed from if present"
    )


def _verify(args: argparse.Namespace) -> None:
    plan = AuditPlan(
        db=args.db,
        mode=Mode(args.mode),
        ids=IdRange(start=args.from_id, stop=args.to_id),
        limit=args.limit or None,
        expect_root=args.expect_root,
        require_complete=args.require_complete,
        checkpoint=args.checkpoint,
    )
    print(audit(plan, lambda message: print(message, flush=True)))


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
