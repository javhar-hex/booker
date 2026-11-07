"""The writes that record the expansion of an atlas, forward from its root."""

from __future__ import annotations

import sqlite3

from booker.atlas.packed_state import PackedState
from booker.atlas.state_id import StateId
from booker.core.model.pairing import Pairing
from booker.core.model.state import State


class AtlasExpansionWriter:
    """
    What records the expansion of an atlas, which the generator carries out: its backend,
    root, positions and actions. Obtain one from `Atlas.transaction`, which commits what
    is written through it, or none of it, when the transaction ends. After that every
    write is an error, as it would be one that nothing commits.
    """

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con
        self._is_open = True

    def end(self) -> None:
        "The transaction is over, and every later write is an error."
        self._is_open = False

    def use_backend(self, backend: str) -> None:
        "Record how states are canonicalized; an atlas is never resumed with another."
        self._require_open()
        prior = self._con.execute(
            "SELECT value FROM meta WHERE key='backend'"
        ).fetchone()
        if prior and prior[0] != backend:
            raise ValueError(
                f"Cannot resume {prior[0]} atlas using {backend} canonicalization"
            )
        self._con.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES ('backend',?)", (backend,)
        )

    def record_root(self, root: StateId) -> None:
        self._require_open()
        self._con.execute(
            "INSERT OR IGNORE INTO meta(key,value) VALUES ('root_id',?)",
            (str(root.value),),
        )

    def add_state(self, state: State) -> StateId:
        "The id of `state`, which is stored if it was not already."
        self._require_open()
        key = PackedState.of(state).data
        self._con.execute(
            "INSERT OR IGNORE INTO states(key,depth,active) VALUES (?,?,?)",
            (key, state.matches_played, state.size),
        )
        row = self._con.execute("SELECT id FROM states WHERE key=?", (key,)).fetchone()
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
        self._require_open()
        self._con.execute(
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
        self._require_open()
        self._con.execute("UPDATE states SET expanded=1 WHERE id=?", (state_id.value,))

    def mark_decided_expanded(self) -> None:
        "A decided position has nothing to expand."
        self._require_open()
        self._con.execute("UPDATE states SET expanded=1 WHERE active=1")

    def _require_open(self) -> None:
        if not self._is_open:
            raise RuntimeError("the transaction is over; start another to write")
