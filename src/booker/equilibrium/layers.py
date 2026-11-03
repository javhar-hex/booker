import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class LayerSummary:
    "What the equilibrium pass found at one depth, in the atlas's own counts."

    depth: int
    scheduler: int
    scheduler_equilibrium: int
    scheduler_balanced_off_equilibrium: int
    collider: int
    collider_equilibrium: int
    collider_critical: int
