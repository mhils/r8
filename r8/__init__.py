"""
The public API of r8 that is exposed to challenges.
"""
import sqlite3

from r8 import util
from r8.challenge import Challenge, challenges
from r8.util import log, echo

db: sqlite3.Connection

__all__ = ["Challenge", "challenges", "db", "util", "log", "echo"]

__version__ = "1.0.0"
"""
The current version of r8. This value is read from `setup.py`.
"""
