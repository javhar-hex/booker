"""Small atlases built by hand for the tests of the verifier, and a way to break them."""

import shutil
import sqlite3
from pathlib import Path

from javhar_util.immutables import ZSet, ZVec

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

PAIRING = Pairing.of(Team(index=0), Team(index=1))
RECORD_4_1 = Record(wins=4, losses=1)
RECORD_5_1 = Record(wins=5, losses=1)
RECORD_6_1 = Record(wins=6, losses=1)


def hand_built_state(*records: Record, met: bool = False) -> State:
    "A state of these records, in which the teams of `PAIRING` have met if `met`."
    return State(records=ZVec(records), past_pairings=ZSet([PAIRING] if met else []))


def hand_built_atlas(
    path: Path,
    parent: State,
    children: tuple[State, State],
    pairing: Pairing | None,
    is_rematch: bool = False,
) -> Path:
    "An atlas of `parent` and its `children`, solved, with one action for `pairing`."
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        parent_id = writer.add_state(parent)
        lhs_wins, rhs_wins = (writer.add_state(child) for child in children)
        writer.record_root(parent_id)
        if pairing is not None:
            writer.add_action(parent_id, pairing, is_rematch, 1, lhs_wins, rhs_wins)
        writer.mark_expanded(parent_id)
        writer.mark_decided_expanded()
        atlas.retrograde_solver().reset_gtvs()
        for depth in range(MAX_MATCHES, -1, -1):
            atlas.retrograde_solver().back_up(depth)
    return path


def final_pair_atlas(path: Path, met: bool = False) -> Path:
    "Two teams a loss from elimination: whoever wins the match is the champion."
    champion = hand_built_state(RECORD_6_1)
    return hand_built_atlas(
        path,
        hand_built_state(RECORD_5_1, RECORD_5_1, met=met),
        (champion, champion),
        PAIRING,
        met,
    )


def tampered_copy(atlas: Path, sql: str) -> Path:
    "A copy of `atlas` in which `sql` has been run."
    tampered = atlas.with_name("tampered.db")
    shutil.copy(atlas, tampered)
    connection = sqlite3.connect(tampered)
    with connection:
        connection.execute(sql)
    connection.close()
    return tampered


_NOT_THE_START = f"X'10{'02' + '00' * 15}{'00' * 15}'"
ORPHAN_STATE = "INSERT INTO states(key,depth,active,expanded) VALUES (X'010D', 31, 1, 1)"
SECOND_ROOT_STATE = (
    f"INSERT INTO states(key,depth,active,expanded) VALUES ({_NOT_THE_START}, 0, 16, 0)"
)
WRONG_ROOT_STATE = f"UPDATE states SET key={_NOT_THE_START} WHERE id=1"
