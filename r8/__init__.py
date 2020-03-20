"""
The public API of r8 that is exposed to challenges.
"""
import sqlite3
import typing

from r8 import util
from r8.challenge import Challenge, challenges
from r8.util import echo, log

db: sqlite3.Connection
settings: typing.Dict[str, typing.Any] = {}

__all__ = ["Challenge", "challenges", "db", "util", "log", "echo"]

__version__ = "2.0.0"
"""
The current version of r8. This value is read from `setup.py`.
"""
