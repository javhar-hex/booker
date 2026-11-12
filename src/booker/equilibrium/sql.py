"""
The SQL of the equilibrium pass. The flags are written to a database of their own, with
the atlas attached read-only as `atlas`; they are keyed by the atlas's state ids and
Collider rows.
"""

SCHEMA = """
CREATE TABLE scheduler_flags (
  id INTEGER PRIMARY KEY,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0)
);
CREATE TABLE collider_flags (
  parent INTEGER NOT NULL,
  lhs INTEGER NOT NULL,
  rhs INTEGER NOT NULL,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  critical INTEGER NOT NULL CHECK(critical IN (0, 1) AND critical <= equilibrium),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0),
  PRIMARY KEY(parent, lhs, rhs)
);
"""

COLLIDER_LAYER = """
WITH layer AS (
  SELECT action.parent, action.lhs, action.rhs,
         parent_flags.equilibrium
           AND action.repeat_cost + action.value = parent_state.value AS optimal_pairing,
         MIN(lhs_child.value, rhs_child.value) < action.value AS has_mistake,
         parent_flags.fewest_past_repeats + action.repeat_cost AS repeats
  FROM atlas.states parent_state
  JOIN atlas.actions action ON action.parent = parent_state.id
  JOIN scheduler_flags parent_flags ON parent_flags.id = parent_state.id
  JOIN atlas.states lhs_child ON lhs_child.id = action.lhs_wins
  JOIN atlas.states rhs_child ON rhs_child.id = action.rhs_wins
  WHERE parent_state.depth = ?
)
INSERT INTO collider_flags
SELECT parent, lhs, rhs, optimal_pairing, optimal_pairing AND has_mistake, repeats FROM layer
"""

SCHEDULER_LAYER = """
WITH edge AS (
  SELECT CASE winner.side WHEN 0 THEN action.lhs_wins ELSE action.rhs_wins END AS child,
         action_flags.equilibrium, action.value AS collider_value,
         action_flags.fewest_past_repeats
  FROM atlas.states parent_state
  JOIN atlas.actions action ON action.parent = parent_state.id
  JOIN collider_flags action_flags
    ON (action_flags.parent, action_flags.lhs, action_flags.rhs)
     = (action.parent, action.lhs, action.rhs)
  CROSS JOIN (SELECT 0 AS side UNION ALL SELECT 1) winner
  WHERE parent_state.depth = ?
)
INSERT INTO scheduler_flags
SELECT edge.child,
       MAX(edge.equilibrium AND child_state.value = edge.collider_value),
       MIN(edge.fewest_past_repeats)
FROM edge JOIN atlas.states child_state ON child_state.id = edge.child
GROUP BY edge.child
"""

SUMMARY = """
WITH scheduler AS (
  SELECT state.depth, COUNT(*) AS num_positions, SUM(flags.equilibrium) AS num_equilibrium,
         SUM(NOT flags.equilibrium AND flags.fewest_past_repeats + state.value = ?)
           AS num_balanced_off
  FROM atlas.states state JOIN scheduler_flags flags ON flags.id = state.id
  GROUP BY state.depth
), collider AS (
  SELECT parent_state.depth, COUNT(*) AS num_positions,
         SUM(flags.equilibrium) AS num_equilibrium, SUM(flags.critical) AS num_critical
  FROM collider_flags flags JOIN atlas.states parent_state ON parent_state.id = flags.parent
  GROUP BY parent_state.depth
)
SELECT scheduler.depth, scheduler.num_positions, scheduler.num_equilibrium,
       scheduler.num_balanced_off, COALESCE(collider.num_positions, 0),
       COALESCE(collider.num_equilibrium, 0), COALESCE(collider.num_critical, 0)
FROM scheduler LEFT JOIN collider ON collider.depth = scheduler.depth
ORDER BY scheduler.depth
"""
