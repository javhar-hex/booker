"""
Command line: `python -m booker.cli generate|solve|stats|verify|equilibrium ...`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from javhar_util.immutables import ZMap

from booker.atlas.storage import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.symmetry.kinds import SymmetryKind
from booker.equilibrium.flags import build, summary
from booker.generate.backend import BLISS, Backend
from booker.generate.generator import generate
from booker.solve import solve
from booker.verify.audit import audit
from booker.verify.plan import AuditPlan, IdRange
from booker.verify.symmetry_sample import compare_symmetries


def main(argv: Sequence[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "generate":
        _generate(args, parser)
    elif args.command == "solve":
        solve(args.db)
    elif args.command == "verify":
        _verify(args)
    elif args.command == "equilibrium":
        _equilibrium(args)
    elif args.command == "compare-symmetry":
        _compare_symmetry(args)
    else:
        _print_stats(args.db)


def _generate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    backend = Backend(args.backend)
    if args.max_depth is None and backend is not BLISS:
        parser.error(
            f"--backend {backend.value} gets slower with every state it meets; "
            "say how far to go with --max-depth"
        )
    max_depth = MAX_MATCHES if args.max_depth is None else args.max_depth
    generate(args.db, max_depth, backend)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unrestricted (16,2,6) Scheduler-Collider atlas"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    generating = sub.add_parser("generate")
    generating.add_argument("db")
    generating.add_argument(
        "--max-depth",
        type=int,
        help=f"matches to expand to (default {MAX_MATCHES}, the whole game, for bliss)",
    )
    generating.add_argument(
        "--backend", choices=[b.value for b in Backend], default=BLISS.value
    )
    sub.add_parser("solve").add_argument("db")
    sub.add_parser("stats").add_argument("db")
    _add_verify(sub)
    comparing = sub.add_parser(
        "compare-symmetry",
        help="do the symmetry implementations agree on states sampled from an atlas?",
    )
    comparing.add_argument("db")
    comparing.add_argument("--samples", type=int, default=300)
    comparing.add_argument("--seed", type=int, default=0)
    equilibrium = sub.add_parser(
        "equilibrium", help="flag the positions reachable under optimal play"
    )
    equilibrium.add_argument("atlas", type=Path)
    equilibrium.add_argument("flags", type=Path)
    equilibrium.add_argument("--summary-only", action="store_true")
    return parser


def _add_verify(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    verifying = sub.add_parser(
        "verify", help="independent position/transition/minimax verifier"
    )
    verifying.add_argument("db")
    verifying.add_argument(
        "--strict",
        choices=[k.value for k in SymmetryKind],
        help="also compare every child and orbit, using this implementation (slow)",
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
        strict=None if args.strict is None else SymmetryKind(args.strict),
        ids=IdRange(start=args.from_id, stop=args.to_id),
        limit=args.limit or None,
        expect_root=args.expect_root,
        require_complete=args.require_complete,
        checkpoint=args.checkpoint,
    )
    print(audit(plan, lambda message: print(message, flush=True)))


def _compare_symmetry(args: argparse.Namespace) -> None:
    implementations = ZMap({kind.value: kind.symmetry for kind in SymmetryKind})
    print(compare_symmetries(args.db, implementations, args.samples, args.seed))


def _equilibrium(args: argparse.Namespace) -> None:
    if not args.summary_only:
        build(args.atlas, args.flags)
    print("depth  scheduler  sched-eq  balanced-off  collider  coll-eq  critical")
    for layer in summary(args.atlas, args.flags):
        print(
            f"{layer.depth:>5} {layer.scheduler:>10,} {layer.scheduler_equilibrium:>9,} "
            f"{layer.scheduler_balanced_off_equilibrium:>13,} {layer.collider:>9,} "
            f"{layer.collider_equilibrium:>8,} {layer.collider_critical:>9,}"
        )


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
