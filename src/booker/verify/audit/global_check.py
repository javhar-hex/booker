"""The checks on the atlas as a whole, rather than on one position."""

from __future__ import annotations

from javhar_util.immutables import ZSet

from booker.atlas.schema import META, SCHEMA_VERSION
from booker.core.model.invariants import (
    CHAMPION_WINS,
    ELIMINATION_LOSSES,
    MAX_MATCHES,
)
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId

# The champion wins CHAMPION_WINS matches, and loses none or all but one life. How deep
# those states are follows from their records, and is checked with every position.
CHAMPION_RECORDS = ZSet(
    Record(wins=CHAMPION_WINS, losses=losses) for losses in (0, ELIMINATION_LOSSES - 1)
)


class GlobalCheck:
    "The checks of what no single position can show: which atlas this is, and what is missing."

    def __init__(self, atlas_reader: AtlasReader) -> None:
        self._atlas_reader = atlas_reader

    @property
    def root_state_id(self) -> StateId:
        root_id = self._atlas_reader.metadata().get("root_id")
        if root_id is None:
            raise AuditFailure("the atlas does not say which position is its root")
        return StateId(value=int(root_id))

    def check_metadata(self) -> None:
        "The atlas is of this game and schema, and names its root."
        metadata = self._atlas_reader.metadata()
        schema_version = self._atlas_reader.schema_version()
        if schema_version != SCHEMA_VERSION:
            raise AuditFailure(f"schema version {schema_version}, not {SCHEMA_VERSION}")
        if metadata.get("game") != META["game"]:
            raise AuditFailure(f"game {metadata.get('game')}, not {META['game']}")
        # Even an audit of a range, which never needs the root, wants it to be named.
        _ = self.root_state_id

    def check_whole_database(self, plan: AuditPlan) -> None:
        if plan.require_complete:
            self._check_complete()
        self._check_opening()
        # A depth-increasing DAG whose only source is the root is rooted wholly there,
        # which rules out extra, disconnected positions. Cut short, the walk is partial.
        if plan.max_num_states is None:
            self._check_no_orphan()

    def check_root_gtv(self, expected_gtv: int) -> None:
        gtv = self._atlas_reader.state_row(self.root_state_id).gtv
        if gtv != expected_gtv:
            raise AuditFailure(f"root GTV is {gtv}, expected {expected_gtv}")

    def _check_complete(self) -> None:
        num_unexpanded_states = self._atlas_reader.num_unexpanded()
        num_unsolved = self._atlas_reader.num_unsolved()
        if num_unexpanded_states or num_unsolved:
            raise AuditFailure(
                f"not complete: {num_unexpanded_states:,} unexpanded states, "
                f"{num_unsolved:,} without a GTV"
            )
        max_depth = self._atlas_reader.max_depth()
        if max_depth != MAX_MATCHES:
            raise AuditFailure(f"last match is missing: depth {max_depth}")
        self._check_leaf_states()

    def _check_leaf_states(self) -> None:
        leaf_ids = self._atlas_reader.leaf_ids()
        champion_records = ZSet(
            self._atlas_reader.state_row(state_id).state.records[0]
            for state_id in leaf_ids
        )
        if (
            len(leaf_ids) != len(CHAMPION_RECORDS)
            or champion_records != CHAMPION_RECORDS
        ):
            raise AuditFailure(
                f"incorrect leaf states: {sorted(map(str, champion_records))}"
            )

    def _check_opening(self) -> None:
        root_state_id = self.root_state_id
        if self._atlas_reader.state_row(root_state_id).state != State.start():
            raise AuditFailure("wrong initial position")
        num_at_depth_0 = self._atlas_reader.num_at_depth(0)
        if num_at_depth_0 != 1:
            raise AuditFailure(f"{num_at_depth_0} positions at depth 0, expected 1")
        if not self._atlas_reader.is_intact():
            raise AuditFailure("SQLite integrity or foreign key check failed")

    def _check_no_orphan(self) -> None:
        orphan = self._atlas_reader.first_orphan(self.root_state_id)
        if orphan is not None:
            raise AuditFailure(f"orphan state {orphan.value}: no action leads to it")
