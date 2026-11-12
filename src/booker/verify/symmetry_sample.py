"""
Do the implementations of `StateSymmetry` agree, on states picked at random from an atlas?

The atlas holds every state the game can reach, so a sample from it is a sample from the
whole graph, to every depth. Each sampled state is put to every implementation in the
same questions; wherever the right answer is known the implementations must give it,
and wherever it is not they must at least give the same one. This checks the
implementations, not the atlas, and is evidence in proportion to the sample: after n
states with no disagreement, a fault in a fraction p of the states is missed with
probability (1 - p) ** n, so 3 / n is a 95% upper bound on p.
"""

from __future__ import annotations

import dataclasses as dc
import random

from javhar_util.immutables import ZMap

from booker.core.model.outcome import Outcome
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.symmetry.relabelling import Relabelling
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.game.rules import legal_pairings
from booker.verify.audit_failure import AuditFailure
from booker.verify.database import Database
from booker.verify.sample_report import SampleReport
from booker.verify.state_id import StateId


def compare_symmetries(
    path: str, implementations: ZMap[str, StateSymmetry], samples: int, seed: int
) -> SampleReport:
    "Raises `AuditFailure` at the first question that the implementations answer wrongly."
    rng = random.Random(seed)
    with Database.open(path) as db:
        ids = list(db.state_ids(0, None))
        chosen = rng.sample(ids, min(samples, len(ids)))
        asked = [
            _Questions(db, implementations, rng).about(state_id) for state_id in chosen
        ]
    return SampleReport(
        states=len(chosen),
        orbit_questions=sum(a[0] for a in asked),
        isomorphism_questions=sum(a[1] for a in asked),
    )


@dc.dataclass(frozen=True, slots=True)
class _Questions:
    db: Database
    implementations: ZMap[str, StateSymmetry]
    rng: random.Random

    def about(self, state_id: StateId) -> tuple[int, int]:
        "How many orbit and isomorphism questions were asked of each implementation."
        state = self.db.stored(state_id).state
        where = f"state {state_id.value}"
        self._same_orbits(state, where)
        isomorphisms = self._relabelled_copy(state, where)
        for row in self.db.actions(state_id):
            children = (
                self.db.stored(row.lhs_wins).state,
                self.db.stored(row.rhs_wins).state,
            )
            for winner, child in zip((row.pairing.lhs, row.pairing.rhs), children):
                expected = successor(state, Outcome.single(row.pairing, winner))
                self._all_say(True, expected, child, f"{where}, winner {winner.index}")
            self._same_answer(
                children[0], children[1], f"{where}, the children of {row.pairing}"
            )
            isomorphisms += 3
        return 1, isomorphisms

    def _same_orbits(self, state: State, where: str) -> None:
        pairings = legal_pairings(state)
        orbits = {
            name: s.orbits(state, pairings) for name, s in self.implementations.items()
        }
        first_name, first = next(iter(orbits.items()))
        for name, found in orbits.items():
            if found != first:
                raise AuditFailure(
                    f"{where}: {name} and {first_name} find different orbits"
                )

    def _relabelled_copy(self, state: State, where: str) -> int:
        indices = list(range(state.size))
        self.rng.shuffle(indices)
        self._all_say(
            True, state, Relabelling.of(indices).state(state), f"{where}, relabelled"
        )
        return 1

    def _all_say(self, truth: bool, first: State, second: State, where: str) -> None:
        for name, symmetry in self.implementations.items():
            if symmetry.are_isomorphic(first, second) is not truth:
                raise AuditFailure(f"{where}: {name} says isomorphic is not {truth}")

    def _same_answer(self, first: State, second: State, where: str) -> None:
        answers = {
            n: s.are_isomorphic(first, second) for n, s in self.implementations.items()
        }
        if len(set(answers.values())) != 1:
            raise AuditFailure(f"{where}: the implementations disagree: {answers}")
