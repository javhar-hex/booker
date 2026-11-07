"""The writes that record the expansion of an atlas, forward from its root."""

from __future__ import annotations

import dataclasses as dc
import sqlite3

from booker.atlas.packed_state import PackedState
from booker.atlas.state_id import StateId
from booker.core.model.pairing import Pairing
from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True)
class AtlasExpansionWriter:
    """
    What records the expansion of an atlas, which the generator carries out: its backend,
    root, positions and actions. Obtain one from `Atlas.expansion_writer`. Each write
    commits itself; writes that must stand or fall together are made inside
    `Atlas.transaction`.
    """

    connection: sqlite3.Connection

    def use_canonicalization(self, name: str) -> None:
        "Record how states are canonicalized; an atlas is never resumed with another."
        prior = self.connection.execute(
            "SELECT value FROM meta WHERE key='backend'"
        ).fetchone()
        if prior and prior[0] != name:
            raise ValueError(
                f"Cannot resume {prior[0]} atlas using {name} canonicalization"
            )
        self.connection.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES ('backend',?)", (name,)
        )

    def record_root(self, root: StateId) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES ('root_id',?)",
            (str(root.value),),
        )

    def add_state(self, state: State) -> StateId:
        "The id of `state`, which is stored if it was not already."
        key = PackedState.of(state).data
        self.connection.execute(
            "INSERT OR IGNORE INTO states(key,depth,active) VALUES (?,?,?)",
            (key, state.matches_played, state.size),
        )
        row = self.connection.execute(
            "SELECT id FROM states WHERE key=?", (key,)
        ).fetchone()
        return StateId(value=row[0])

    def add_action(
        self,
        parent: StateId,
        pairing: Pairing,
        is_rematch: bool,
        class_size: int,
        low_wins: StateId,
        high_wins: StateId,
    ) -> None:
        self.connection.execute(
            "INSERT INTO actions(parent,a,b,repeat_cost,class_size,a_wins,b_wins) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                parent.value,
                pairing.low.index,
                pairing.high.index,
                int(is_rematch),
                class_size,
                low_wins.value,
                high_wins.value,
            ),
        )

    def mark_expanded(self, state_id: StateId) -> None:
        self.connection.execute(
            "UPDATE states SET expanded=1 WHERE id=?", (state_id.value,)
        )

    def mark_decided_expanded(self) -> None:
        "A decided position has nothing to expand."
        self.connection.execute("UPDATE states SET expanded=1 WHERE active=1")
