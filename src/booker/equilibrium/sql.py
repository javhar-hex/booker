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
  a INTEGER NOT NULL,
  b INTEGER NOT NULL,
  equilibrium INTEGER NOT NULL CHECK(equilibrium IN (0, 1)),
  critical INTEGER NOT NULL CHECK(critical IN (0, 1) AND critical <= equilibrium),
  fewest_past_repeats INTEGER NOT NULL CHECK(fewest_past_repeats >= 0),
  PRIMARY KEY(parent, a, b)
);
"""

COLLIDER_LAYER = """
WITH layer AS (
  SELECT c.parent, c.a, c.b,
         f.equilibrium AND c.repeat_cost + c.value = p.value AS optimal_pairing,
         MIN(wa.value, wb.value) < c.value AS has_mistake,
         f.fewest_past_repeats + c.repeat_cost AS repeats
  FROM atlas.states p
  JOIN atlas.actions c ON c.parent = p.id
  JOIN scheduler_flags f ON f.id = p.id
  JOIN atlas.states wa ON wa.id = c.a_wins
  JOIN atlas.states wb ON wb.id = c.b_wins
  WHERE p.depth = ?
)
INSERT INTO collider_flags
SELECT parent, a, b, optimal_pairing, optimal_pairing AND has_mistake, repeats FROM layer
"""

SCHEDULER_LAYER = """
WITH edge AS (
  SELECT CASE w.side WHEN 0 THEN c.a_wins ELSE c.b_wins END AS child,
         f.equilibrium, c.value AS collider_value, f.fewest_past_repeats
  FROM atlas.states p
  JOIN atlas.actions c ON c.parent = p.id
  JOIN collider_flags f ON (f.parent, f.a, f.b) = (c.parent, c.a, c.b)
  CROSS JOIN (SELECT 0 AS side UNION ALL SELECT 1) w
  WHERE p.depth = ?
)
INSERT INTO scheduler_flags
SELECT e.child, MAX(e.equilibrium AND s.value = e.collider_value),
       MIN(e.fewest_past_repeats)
FROM edge e JOIN atlas.states s ON s.id = e.child
GROUP BY e.child
"""

SUMMARY = """
WITH s AS (
  SELECT st.depth, COUNT(*) AS n, SUM(f.equilibrium) AS eq,
         SUM(NOT f.equilibrium AND f.fewest_past_repeats + st.value = ?) AS balanced_off
  FROM atlas.states st JOIN scheduler_flags f ON f.id = st.id GROUP BY st.depth
), c AS (
  SELECT p.depth, COUNT(*) AS n, SUM(f.equilibrium) AS eq, SUM(f.critical) AS critical
  FROM collider_flags f JOIN atlas.states p ON p.id = f.parent GROUP BY p.depth
)
SELECT s.depth, s.n, s.eq, s.balanced_off,
       COALESCE(c.n, 0), COALESCE(c.eq, 0), COALESCE(c.critical, 0)
FROM s LEFT JOIN c ON c.depth = s.depth ORDER BY s.depth
"""
