"""The expansion of an atlas, forward from a root. No verifier code is imported."""

from __future__ import annotations

import dataclasses as dc

from booker.atlas.atlas import Atlas
from booker.atlas.atlas_expansion_writer import AtlasExpansionWriter
from booker.atlas.stored_state import StoredState
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.outcome import Outcome
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.game.rules import legal_pairings
from booker.generate.state_canonicalizer import StateCanonicalizer


def expand_atlas(path: str, max_depth: int, symmetry: StateSymmetry) -> None:
    "Expands the atlas at `path`, resuming it if it exists, to `max_depth` matches."
    if not 0 <= max_depth <= MAX_MATCHES:
        raise ValueError(f"depth must be between 0 and {MAX_MATCHES}, not {max_depth}")
    with Atlas.open(path) as atlas:
        atlas.expansion_writer().use_state_symmetry(symmetry.name)
        expander = AtlasExpander(
            atlas=atlas,
            symmetry=symmetry,
            state_canonicalizer=StateCanonicalizer(
                symmetry=symmetry, known=atlas.states()
            ),
        )
        expander.expand(State.start(), max_depth)
        print("states:", atlas.num_states(), "actions:", atlas.num_actions())


@dc.dataclass(frozen=True, slots=True)
class AtlasExpander:
    """
    Expands an atlas. Its `symmetry` finds the orbits of the legal pairings, and its
    `state_canonicalizer` the representative of each position that results.
    """

    atlas: Atlas
    symmetry: StateSymmetry
    state_canonicalizer: StateCanonicalizer

    def expand(self, root: State, max_depth: int) -> None:
        """
        Expands the atlas from `root` down to `max_depth` matches. The root is the start
        of the tournament for the whole atlas; any state that can arise in play gives
        the atlas of what remains of that game.
        """
        writer = self.atlas.expansion_writer()
        writer.record_root(writer.add_state(self.state_canonicalizer(root)))
        for depth in range(max_depth):
            self._expand_depth(writer, depth)
        # A decided state is never expanded, even when every depth is.
        writer.mark_decided_expanded()

    def _expand_depth(self, writer: AtlasExpansionWriter, depth: int) -> None:
        unexpanded = self.atlas.unexpanded(depth)
        if not unexpanded:
            return
        print(f"expanding depth {depth:02d}: {len(unexpanded):,} states", flush=True)
        # One depth is atomic; interruption never leaves a half-expanded layer.
        with self.atlas.transaction():
            for parent in unexpanded:
                if not parent.state.is_decided:
                    self._expand_parent(writer, parent)
                writer.mark_expanded(parent.id)

    def _expand_parent(self, writer: AtlasExpansionWriter, parent: StoredState) -> None:
        "Book the Collider state of each pairing orbit of `parent` that can be scheduled."
        state = parent.state
        for orbit in self.symmetry.orbits(state, legal_pairings(state)):
            pairing = orbit.representative
            lhs_wins = successor(state, Outcome.single(pairing, pairing.lhs))
            rhs_wins = successor(state, Outcome.single(pairing, pairing.rhs))
            writer.add_action(
                parent=parent.id,
                pairing=pairing,
                is_rematch=state.has_met(pairing),
                class_size=orbit.size,
                lhs_wins=writer.add_state(self.state_canonicalizer(lhs_wins)),
                rhs_wins=writer.add_state(self.state_canonicalizer(rhs_wins)),
            )
