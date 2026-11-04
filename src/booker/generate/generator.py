"""The generator of the atlas. No verifier code is imported."""

from __future__ import annotations

from booker.atlas.storage import Atlas
from booker.atlas.stored import StoredState
from booker.atlas.transaction import AtlasTransaction
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.outcome import Outcome
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.game.rules import legal_pairings
from booker.generate.backend import Backend, Canonicalizer


def generate(path: str, max_depth: int, backend: Backend) -> None:
    "Expands the atlas at `path`, resuming it if it exists, to `max_depth` matches."
    if not 0 <= max_depth <= MAX_MATCHES:
        raise ValueError(f"depth must be between 0 and {MAX_MATCHES}, not {max_depth}")
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.use_backend(backend.value)
        canon = backend.canonicalizer(atlas.states())
        expand(atlas, canon, State.start(), max_depth)
        print("states:", atlas.num_states(), "actions:", atlas.num_actions())


def expand(atlas: Atlas, canon: Canonicalizer, root: State, max_depth: int) -> None:
    """
    Expands `atlas` from `root` down to `max_depth` matches. The root is the start of the
    tournament for the whole atlas; any state that can arise in play gives the atlas of
    what remains of that game.
    """
    with atlas.transaction() as tx:
        tx.record_root(tx.add_state(canon(root)))
    for depth in range(max_depth):
        _expand_depth(atlas, canon, depth)
    # A decided state is never expanded, even when every depth is.
    with atlas.transaction() as tx:
        tx.mark_decided_expanded()


def _expand_depth(atlas: Atlas, canon: Canonicalizer, depth: int) -> None:
    unexpanded = atlas.unexpanded(depth)
    if not unexpanded:
        return
    print(f"expanding depth {depth:02d}: {len(unexpanded):,} states", flush=True)
    # One depth is atomic; interruption never leaves a half-expanded layer.
    with atlas.transaction() as tx:
        for parent in unexpanded:
            if not parent.state.is_decided:
                _expand(tx, canon, parent)
            tx.mark_expanded(parent.id)


def _expand(tx: AtlasTransaction, canon: Canonicalizer, parent: StoredState) -> None:
    "Book the Collider state of each pairing orbit of `parent` that can be scheduled."
    state = parent.state
    for orbit in BlissSymmetry().orbits(state, legal_pairings(state)):
        pairing = orbit.representative
        low_wins = successor(state, Outcome.single(pairing, pairing.low))
        high_wins = successor(state, Outcome.single(pairing, pairing.high))
        tx.add_action(
            parent=parent.id,
            pairing=pairing,
            is_rematch=state.has_met(pairing),
            class_size=orbit.size,
            low_wins=tx.add_state(canon(low_wins)),
            high_wins=tx.add_state(canon(high_wins)),
        )
