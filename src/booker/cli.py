"""
Command line: `python -m booker.cli --help` lists the commands.

The arguments are read off argparse's `Namespace`, whose attributes are untyped; each
handler hands them straight to a typed function of the library.
"""

from __future__ import annotations

import argparse
import functools
from collections.abc import Callable, Sequence
from pathlib import Path

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.symmetry.state_symmetries import BLISS, STATE_SYMMETRIES
from booker.equilibrium.equilibrium_analysis import analyze_equilibrium, layer_summaries
from booker.expand.atlas_expander import expand_atlas
from booker.solve import solve_atlas
from booker.verify.audit.atlas_auditor import AtlasAuditor
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

_LOG = functools.partial(print, flush=True)

MAX_DEPTH_OPTION = "--max-depth"
STATE_SYMMETRY_OPTION = "--state-symmetry"
STOP_STATE_ID_OPTION = "--stop-state-id"
SUMMARY_ONLY_OPTION = "--summary-only"


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    args.run(args)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unrestricted (16,2,6) Scheduler-Collider atlas"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    expanding = subparsers.add_parser("expand")
    _add_db_path(expanding, Path)
    _add_expand_options(expanding)
    expanding.set_defaults(run=functools.partial(_expand, parser=expanding))
    solving = subparsers.add_parser("solve")
    _add_db_path(solving, _existing_path)
    solving.set_defaults(run=_solve)
    statistics = subparsers.add_parser("stats")
    _add_db_path(statistics, _existing_path)
    statistics.set_defaults(run=_stats)
    verifying = subparsers.add_parser(
        "verify", help="independent position/transition/minimax verifier"
    )
    _add_db_path(verifying, _existing_path)
    _add_verify_options(verifying)
    verifying.set_defaults(run=functools.partial(_verify, parser=verifying))
    equilibrium = subparsers.add_parser(
        "equilibrium", help="analyze which positions optimal play can reach"
    )
    equilibrium.add_argument("atlas_path", type=_existing_path)
    equilibrium.add_argument("analysis_path", type=Path)
    equilibrium.add_argument(SUMMARY_ONLY_OPTION, action="store_true")
    equilibrium.set_defaults(run=functools.partial(_equilibrium, parser=equilibrium))
    return parser


def _existing_path(text: str) -> Path:
    path = Path(text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"no such file: {path}")
    return path


def _state_id(text: str) -> StateId:
    return StateId(int(text))


def _add_db_path(
    parser: argparse.ArgumentParser, path_type: Callable[[str], Path]
) -> None:
    parser.add_argument("db_path", type=path_type)


def _add_expand_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        MAX_DEPTH_OPTION,
        type=int,
        help=f"matches to expand to (default {MAX_MATCHES}, the whole game, for {BLISS.name})",
    )
    parser.add_argument(
        STATE_SYMMETRY_OPTION, choices=sorted(STATE_SYMMETRIES), default=BLISS.name
    )


def _add_verify_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--reference-symmetry",
        choices=sorted(STATE_SYMMETRIES),
        help="also compare every child and orbit, using this implementation (slow)",
    )
    parser.add_argument(
        "--max-num-states",
        type=int,
        help="Number of states to check (all, when omitted)",
    )
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--expected-root-gtv", type=int)
    parser.add_argument(
        "--start-state-id",
        type=_state_id,
        help="First state id to check (inclusive); whole-database checks run only "
        f"when this and {STOP_STATE_ID_OPTION} are omitted",
    )
    parser.add_argument(
        STOP_STATE_ID_OPTION,
        type=_state_id,
        help="State id to stop before (exclusive)",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Progress file: saved periodically, resumed from if present",
    )


def _expand(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    symmetry = STATE_SYMMETRIES[args.state_symmetry]
    if args.max_depth is None and symmetry != BLISS:
        parser.error(
            f"{STATE_SYMMETRY_OPTION} {symmetry.name} gets slower with every state it "
            f"meets; say how far to go with {MAX_DEPTH_OPTION}"
        )
    max_depth = MAX_MATCHES if args.max_depth is None else args.max_depth
    expanded = expand_atlas(args.db_path, max_depth, symmetry, log=_LOG)
    _LOG(f"states: {expanded.num_states} actions: {expanded.num_actions}")


def _solve(args: argparse.Namespace) -> None:
    solve_atlas(args.db_path, log=_LOG)


def _stats(args: argparse.Namespace) -> None:
    _LOG(
        f"{'depth':>5} {'states':>7} {'collider':>9} "
        f"{'pairings':>9} {'min-gtv':>8} {'max-gtv':>8}"
    )
    with Atlas.open(args.db_path) as atlas:
        for row in atlas.depth_summaries():
            _LOG(
                f"{row.depth:>5} {row.num_states:>7,} {row.num_colliders:>9,} "
                f"{row.num_pairings:>9,} {row.min_gtv!s:>8} {row.max_gtv!s:>8}"
            )


def _verify(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    db_path = args.db_path.resolve()
    state_id_range = StateIdRange(start=args.start_state_id, stop=args.stop_state_id)
    reference_symmetry = (
        None
        if args.reference_symmetry is None
        else STATE_SYMMETRIES[args.reference_symmetry]
    )
    try:
        plan = AuditPlan(
            db_path,
            state_id_range,
            reference_symmetry,
            args.max_num_states,
            args.expected_root_gtv,
            args.require_complete,
            args.checkpoint,
        )
    except ValueError as invalid:
        parser.error(str(invalid))
    try:
        report = AtlasAuditor(plan=plan, log=_LOG).audit()
    except AuditFailure as failure:
        parser.exit(status=1, message=f"FAIL: {failure}\n")
    _LOG(str(report))


def _equilibrium(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.summary_only:
        if not args.analysis_path.is_file():
            parser.error(
                f"{SUMMARY_ONLY_OPTION} needs an analysis to summarize: "
                f"no such file: {args.analysis_path}"
            )
    else:
        analyze_equilibrium(args.atlas_path, args.analysis_path)
    _LOG(
        f"{'depth':>5} {'scheduler':>10} {'sched-eq':>9} {'balanced-off':>13} "
        f"{'collider':>9} {'coll-eq':>8} {'critical':>9}"
    )
    for layer in layer_summaries(args.atlas_path, args.analysis_path):
        _LOG(
            f"{layer.depth:>5} {layer.scheduler:>10,} {layer.scheduler_equilibrium:>9,} "
            f"{layer.scheduler_balanced_off_equilibrium:>13,} {layer.collider:>9,} "
            f"{layer.collider_equilibrium:>8,} {layer.collider_critical:>9,}"
        )


if __name__ == "__main__":
    main()
