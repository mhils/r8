import collections
import copy
import functools
import math
from math import ceil
from typing import Optional

import r8

TTeamId = str
TChallengeId = str
TUnixtime = float


def first_solve_bonus(challenge: "r8.Challenge", existing_solves: int) -> int:
    if not r8.settings.get("scoring", False):
        return 0
    if challenge.points == 0:
        return 0
    return math.floor(r8.settings.get("scoring_first_solve_bonus", 0) / 2 ** existing_solves)


def challenge_points(challenge: "r8.Challenge", solves: int) -> int:
    if not r8.settings.get("scoring", False):
        return 0
    if challenge.points is not None:
        return challenge.points
    if solves == 0:
        return 500
    alpha = r8.settings.get("scoring_alpha", 0.25)
    beta = r8.settings.get("scoring_beta", 2.0)
    return round(470 / (1 + (alpha * (solves - 1)) ** beta)) + 30


class Scoreboard:
    """Immutable snapshot of scores at a given point in time."""
    timestamp: TUnixtime
    scores: collections.Counter[TTeamId]
    solves: collections.defaultdict[TChallengeId, list[TTeamId]]

    def __init__(self, timestamp: Optional[TUnixtime] = None):
        self.timestamp = timestamp
        self.scores = collections.Counter()
        self.solves = collections.defaultdict(list)

    def solve(
            self,
            team: TTeamId,
            challenge: "r8.Challenge",
            timestamp: TUnixtime
    ) -> Optional["Scoreboard"]:
        if team.startswith("_"):
            return None
        if team in self.solves[challenge.id]:
            raise ValueError(f"{challenge.id} already solved by {team}.")

        existing_solves = len(self.solves[challenge.id])
        old_score = challenge_points(challenge, existing_solves)
        new_score = challenge_points(challenge, existing_solves + 1)
        score_delta = old_score - new_score

        if old_score == new_score == 0:
            return None

        ret = copy.deepcopy(self)
        ret.timestamp = timestamp
        ret.scores[team] += new_score
        # on equal scores, the oldest team to reach that score wins.
        ret.scores[team] = ceil(ret.scores[team]) - (int(timestamp) / 100_000_000_000)
        if new_score:
            ret.scores[team] += first_solve_bonus(challenge, existing_solves)
        for t in ret.solves[challenge.id]:
            ret.scores[t] -= score_delta
        ret.solves[challenge.id].append(team)
        return ret

    def __repr__(self):
        leaders = ", ".join(
            f"#{i + 1} {name} ({ceil(score)})"
            for i, (name, score)
            in enumerate(self.scores.most_common(3))
        )
        return f"Scoreboard[{leaders}]"

    @functools.cache
    def to_json(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "scores": dict(self.scores)
        }


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    N = 50
    dummy = r8.Challenge("test")

    r8.settings = {
        "scoring": True,
        "scoring_alpha": 0.1,
        "scoring_beta": 2,
    }
    plt.plot(range(1, N), [challenge_points(dummy, i) for i in range(1, N)])
    plt.ylabel("score")
    plt.xlabel("solves")
    plt.show()
