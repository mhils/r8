import collections
import copy
import functools
import math
from math import ceil
from typing import Counter, DefaultDict, List, Optional

import r8

TTeamId = str
TChallengeId = str
TUnixtime = float


def first_solve_bonus(existing_solves: int) -> int:
    if not r8.settings.get("scoring", False):
        return 0
    return math.floor(r8.settings.get("scoring_first_solve_bonus", 0) / 2 ** existing_solves)


def challenge_points(solves: int) -> int:
    if not r8.settings.get("scoring", False):
        return 0
    if solves == 0:
        return 500
    alpha = r8.settings.get("scoring_alpha", 0.25)
    beta = r8.settings.get("scoring_beta", 2.0)
    return round(470 / (1 + (alpha * (solves - 1)) ** beta)) + 30


class Scoreboard:
    """Immutable snapshot of scores at a given point in time."""
    timestamp: TUnixtime
    scores: Counter[TTeamId]
    solves: DefaultDict[TChallengeId, List[TTeamId]]

    def __init__(self, timestamp: Optional[TUnixtime] = None):
        self.timestamp = timestamp
        self.scores = collections.Counter()
        self.solves = collections.defaultdict(list)

    def solve(
            self,
            team: TTeamId,
            challenge: TChallengeId,
            timestamp: TUnixtime
    ) -> "Scoreboard":
        if team in self.solves[challenge]:
            raise ValueError(f"{challenge} already solved by {team}.")

        existing_solves = len(self.solves[challenge])
        old_score = challenge_points(existing_solves)
        new_score = challenge_points(existing_solves + 1)
        score_delta = old_score - new_score

        ret = copy.deepcopy(self)
        ret.timestamp = timestamp
        ret.scores[team] += new_score
        # on equal scores, the oldest team to reach that score wins.
        ret.scores[team] = ceil(ret.scores[team]) - (int(timestamp) / 100_000_000_000)
        if new_score:
            ret.scores[team] += first_solve_bonus(existing_solves)
        for t in ret.solves[challenge]:
            ret.scores[t] -= score_delta
        ret.solves[challenge].append(team)
        return ret

    def __repr__(self):
        leaders = ", ".join(
            f"#{i + 1} {name} ({ceil(score)})"
            for i, (name, score)
            in enumerate(self.scores.most_common(3))
        )
        return f"Scoreboard[{leaders}]"

    @functools.lru_cache(maxsize=None)
    def to_json(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "scores": dict(self.scores)
        }
