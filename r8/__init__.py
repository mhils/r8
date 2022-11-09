"""
The public API of r8 that is exposed to challenges.
"""
import sqlite3
from typing import Any

from r8 import util
from r8.challenge import Challenge
from r8.challenge import challenges
from r8.util import echo
from r8.util import log

db: sqlite3.Connection
settings: dict[str, Any] = {}

__all__ = ["Challenge", "challenges", "db", "util", "log", "echo"]

__version__ = "2.0.0"
"""
The current version of r8. This value is read from `setup.py`.
"""
