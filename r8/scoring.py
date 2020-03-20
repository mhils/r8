import math

import r8


def first_solve_bonus(existing_solves: int) -> int:
    return math.floor(r8.settings.get("scoring_first_blood", 0) / 2 ** existing_solves)


def challenge_score(solves: int) -> int:
    if solves == 0:
        return 500

    alpha = r8.settings.get("alpha", 0.25)
    beta = r8.settings.get("beta", 2.0)
    return round(470 / (1 + (alpha * (solves - 1)) ** beta)) + 30
