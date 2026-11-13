"""
The SQL of the equilibrium analysis. It is written to a database of its own, with the
atlas attached read-only as `atlas`, and keyed by the atlas's state ids and Collider rows.
"""

SCHEMA = """
CREATE TABLE scheduler_equilibrium (
  id INTEGER PRIMARY KEY,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0)
);
CREATE TABLE collider_equilibrium (
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
         parent_equilibrium.equilibrium
           AND action.repeat_cost + action.gtv = parent_state.gtv AS optimal_pairing,
         MIN(lhs_child.gtv, rhs_child.gtv) < action.gtv AS has_mistake,
         parent_equilibrium.fewest_past_repeats + action.repeat_cost AS repeats
  FROM atlas.states parent_state
  JOIN atlas.actions action ON action.parent = parent_state.id
  JOIN scheduler_equilibrium parent_equilibrium ON parent_equilibrium.id = parent_state.id
  JOIN atlas.states lhs_child ON lhs_child.id = action.lhs_wins
  JOIN atlas.states rhs_child ON rhs_child.id = action.rhs_wins
  WHERE parent_state.depth = ?
)
INSERT INTO collider_equilibrium
SELECT parent, lhs, rhs, optimal_pairing, optimal_pairing AND has_mistake, repeats FROM layer
"""

SCHEDULER_LAYER = """
WITH edge AS (
  SELECT CASE winner.side WHEN 0 THEN action.lhs_wins ELSE action.rhs_wins END AS child,
         action_equilibrium.equilibrium, action.gtv AS collider_gtv,
         action_equilibrium.fewest_past_repeats
  FROM atlas.states parent_state
  JOIN atlas.actions action ON action.parent = parent_state.id
  JOIN collider_equilibrium action_equilibrium
    ON (action_equilibrium.parent, action_equilibrium.lhs, action_equilibrium.rhs)
     = (action.parent, action.lhs, action.rhs)
  CROSS JOIN (SELECT 0 AS side UNION ALL SELECT 1) winner
  WHERE parent_state.depth = ?
)
INSERT INTO scheduler_equilibrium
SELECT edge.child,
       MAX(edge.equilibrium AND child_state.gtv = edge.collider_gtv),
       MIN(edge.fewest_past_repeats)
FROM edge JOIN atlas.states child_state ON child_state.id = edge.child
GROUP BY edge.child
"""

SUMMARY = """
WITH scheduler AS (
  SELECT state.depth, COUNT(*) AS num_positions,
         SUM(scheduler_equilibrium.equilibrium) AS num_equilibrium,
         SUM(NOT scheduler_equilibrium.equilibrium
             AND scheduler_equilibrium.fewest_past_repeats + state.gtv = ?)
           AS num_balanced_off
  FROM atlas.states state
  JOIN scheduler_equilibrium ON scheduler_equilibrium.id = state.id
  GROUP BY state.depth
), collider AS (
  SELECT parent_state.depth, COUNT(*) AS num_positions,
         SUM(collider_equilibrium.equilibrium) AS num_equilibrium,
         SUM(collider_equilibrium.critical) AS num_critical
  FROM collider_equilibrium
  JOIN atlas.states parent_state ON parent_state.id = collider_equilibrium.parent
  GROUP BY parent_state.depth
)
SELECT scheduler.depth, scheduler.num_positions, scheduler.num_equilibrium,
       scheduler.num_balanced_off, COALESCE(collider.num_positions, 0),
       COALESCE(collider.num_equilibrium, 0), COALESCE(collider.num_critical, 0)
FROM scheduler LEFT JOIN collider ON collider.depth = scheduler.depth
ORDER BY scheduler.depth
"""
