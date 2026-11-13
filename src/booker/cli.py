"""
Command line: `python -m booker.cli expand|solve|stats|verify|equilibrium ...`.
"""

from __future__ import annotations

import argparse
import functools
from collections.abc import Sequence
from pathlib import Path

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.symmetry.state_symmetries import BLISS, STATE_SYMMETRIES
from booker.equilibrium.equilibrium_analysis import analyze_equilibrium, layer_summaries
from booker.expand.atlas_expander import expand_atlas
from booker.solve import solve
from booker.verify.audit.audit import audit
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

_LOG = functools.partial(print, flush=True)


def main(argv: Sequence[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "expand":
        _expand(args, parser)
    elif args.command == "solve":
        print(f"root GTV: {solve(args.db)}")
    elif args.command == "verify":
        _verify(args)
    elif args.command == "equilibrium":
        _equilibrium(args)
    else:
        _print_stats(args.db)


def _expand(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    symmetry = STATE_SYMMETRIES[args.state_symmetry]
    if args.max_depth is None and symmetry != BLISS:
        parser.error(
            f"--state-symmetry {symmetry.name} gets slower with every state it meets; "
            "say how far to go with --max-depth"
        )
    max_depth = MAX_MATCHES if args.max_depth is None else args.max_depth
    expanded = expand_atlas(args.db, max_depth, symmetry, log=_LOG)
    print("states:", expanded.num_states, "actions:", expanded.num_actions)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unrestricted (16,2,6) Scheduler-Collider atlas"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    expanding = sub.add_parser("expand")
    expanding.add_argument("db", type=Path)
    expanding.add_argument(
        "--max-depth",
        type=int,
        help=f"matches to expand to (default {MAX_MATCHES}, the whole game, for bliss)",
    )
    expanding.add_argument(
        "--state-symmetry", choices=sorted(STATE_SYMMETRIES), default=BLISS.name
    )
    sub.add_parser("solve").add_argument("db", type=Path)
    sub.add_parser("stats").add_argument("db", type=Path)
    _add_verify(sub)
    equilibrium = sub.add_parser(
        "equilibrium", help="analyze which positions optimal play can reach"
    )
    equilibrium.add_argument("atlas", type=Path)
    equilibrium.add_argument("analysis", type=Path)
    equilibrium.add_argument("--summary-only", action="store_true")
    return parser


def _state_id(text: str) -> StateId:
    return StateId(int(text))


def _add_verify(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    verifying = sub.add_parser(
        "verify", help="independent position/transition/minimax verifier"
    )
    verifying.add_argument("db", type=Path)
    verifying.add_argument(
        "--strict",
        choices=sorted(STATE_SYMMETRIES),
        help="also compare every child and orbit, using this implementation (slow)",
    )
    verifying.add_argument(
        "--limit", type=int, default=0, help="Number of states to check (0=all)"
    )
    verifying.add_argument("--require-complete", action="store_true")
    verifying.add_argument("--expect-root", type=int)
    verifying.add_argument(
        "--from-id",
        type=_state_id,
        help="First state id to check (inclusive); "
        "whole-database checks run only when omitted",
    )
    verifying.add_argument(
        "--to-id", type=_state_id, help="State id to stop before (exclusive)"
    )
    verifying.add_argument(
        "--checkpoint",
        type=Path,
        help="Progress file: saved periodically, resumed from if present",
    )


def _verify(args: argparse.Namespace) -> None:
    plan = AuditPlan(
        db=args.db,
        strict=None if args.strict is None else STATE_SYMMETRIES[args.strict],
        ids=StateIdRange(start=args.from_id, stop=args.to_id),
        limit=args.limit or None,
        expect_root=args.expect_root,
        require_complete=args.require_complete,
        checkpoint=args.checkpoint,
    )
    print(audit(plan, _LOG))


def _equilibrium(args: argparse.Namespace) -> None:
    if not args.summary_only:
        analyze_equilibrium(args.atlas, args.analysis)
    print("depth  scheduler  sched-eq  balanced-off  collider  coll-eq  critical")
    for layer in layer_summaries(args.atlas, args.analysis):
        print(
            f"{layer.depth:>5} {layer.scheduler:>10,} {layer.scheduler_equilibrium:>9,} "
            f"{layer.scheduler_balanced_off_equilibrium:>13,} {layer.collider:>9,} "
            f"{layer.collider_equilibrium:>8,} {layer.collider_critical:>9,}"
        )


def _print_stats(path: Path) -> None:
    print("depth  states  collider  pairings  min-gtv  max-gtv")
    with Atlas.open(path) as atlas:
        for row in atlas.depth_summaries():
            print(
                f"{row.depth:>5} {row.num_states:>7,} {row.num_colliders:>9,} "
                f"{row.num_pairings:>9,} {row.min_gtv!s:>8} {row.max_gtv!s:>8}"
            )


if __name__ == "__main__":
    main()
