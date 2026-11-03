"""
What the verifier takes the (16, 2, 6) game and its atlas to be, written down here on
its own. This package imports nothing from the generator, the atlas or `booker.core`,
so that a mistake there cannot also be a mistake here; a test checks that these
numbers agree with `booker.core`.
"""

NUM_TEAMS = 16
ELIMINATION_LOSSES = 2
CHAMPION_WINS = 6
MAX_MATCHES = 31

SCHEMA_VERSION = "5"
GAME = "unrestricted-16-2-6"
