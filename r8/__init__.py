"""
The public API of r8 that is exposed to challenges.
"""
import sqlite3
import typing

from r8 import util
from r8.challenge import Challenge, challenges
from r8.builtin_challenges.basic import StaticChallenge
from r8.util import log, echo

db: sqlite3.Connection
settings: typing.Dict[str, str]

__all__ = ["Challenge", "StaticChallenge", "challenges", "db", "util", "log", "echo"]

__version__ = "2.0.0"
"""
The current version of r8. This value is read from `setup.py`.
"""
