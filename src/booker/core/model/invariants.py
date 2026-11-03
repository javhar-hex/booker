"""
The sporadic (16, 2, 6) tournament that Booker studies: a double-elimination tournament
for 16 teams, where it requires exactly 6 wins to be champion.
"""

NUM_PARTICIPANTS = 16
ELIMINATION_LOSSES = 2
CHAMPION_WINS = 6
MAX_MATCHES = NUM_PARTICIPANTS * ELIMINATION_LOSSES - 1
"Each match costs one loss: all but the champion lose twice, the champion at most once."
