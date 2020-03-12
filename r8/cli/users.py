import collections

import click
import texttable

import r8
from r8 import util


@click.command("users")
@util.with_database()
@click.option("--user", multiple=True,
              help="Only display users/teams that start with the given string. Can be passed multiple times.")
@click.option("--challenge", multiple=True,
              help="Only display challenges that start with the given string. Can be passed multiple times.")
@click.option("-T", is_flag=True, help="Transpose table.")
@click.option("--format", type=click.Choice(['table', 'csv']), default="table")
@click.option("--teams", is_flag=True, help="Group users by teams.")
@click.option("--no-team-solves", is_flag=True, help="Include team solves.")
def cli(user, challenge, t, format, teams, no_team_solves):
    """View users and their progress."""
    with r8.db:
        all_challenges = r8.db.execute(
            "SELECT cid, team FROM challenges WHERE t_start < datetime('now') ORDER BY ROWID ASC"
        ).fetchall()
        user_info = r8.db.execute(
            "SELECT uid, tid FROM users NATURAL LEFT JOIN teams ORDER BY users.ROWID ASC"
        ).fetchall()
        submissions = r8.db.execute(
            "SELECT uid, tid, cid FROM submissions NATURAL JOIN flags NATURAL LEFT JOIN teams"
        ).fetchall()

    entries = []
    team_users = collections.defaultdict(list)
    for uid, tid in user_info:
        if teams:
            entries.append(tid)
        else:
            entries.append(uid)
        team_users[tid].append(uid)
    if user:
        entries = [
            x for x in entries
            if any(x.startswith(u) for u in user)
        ]
    entry_index = {
        x: i for i, x in enumerate(entries)
    }

    challenges = {}
    for cid, team in all_challenges:
        if teams and not team:
            continue
        if challenge and not any(cid.startswith(c) for c in challenge):
            continue
        challenges[cid] = team

    if format == "table":
        SOLVED = "OK"
        NOT_SOLVED = "FAIL"
    else:
        SOLVED = "TRUE"
        NOT_SOLVED = "FALSE"

    solved = {
        cid: [NOT_SOLVED] * len(entries)
        for cid in challenges
    }
    if teams:
        for _, tid, cid in submissions:
            if cid in challenges and tid in entry_index:
                solved[cid][entry_index[tid]] = SOLVED
    elif no_team_solves:
        for uid, _, cid in submissions:
            if cid in challenges and uid in entry_index:
                solved[cid][entry_index[uid]] = SOLVED
    else:
        for uid, tid, cid in submissions:
            if cid in challenges:
                if challenges[cid]:
                    for uid in team_users[tid]:
                        if uid in entry_index:
                            solved[cid][entry_index[uid]] = SOLVED
                elif uid in entry_index:
                    solved[cid][entry_index[uid]] = SOLVED

    if not t and teams:
        header = "Team"
    elif not t and not teams:
        header = "User"
    else:
        header = "Challenge"

    table_contents = (
            [[header] + entries] +
            [[cid] + solved for cid, solved in solved.items()]
    )
    if format == "table":
        for row in table_contents:
            row[0] = row[0][:22]
    if not t:
        table_contents = list(zip(*table_contents))

    if format == "table":
        table = texttable.Texttable(click.get_terminal_size()[0])
        table.set_cols_align(["l"] + ["c"] * (len(table_contents[0]) - 1))
        table.set_deco(table.BORDER | table.HEADER | table.VLINES)
        table.add_rows(table_contents)

        try:
            table._compute_cols_width()
        except ValueError:
            table._max_width = False

        tbl = table.draw()
        print(
            tbl
                .replace(SOLVED, click.style(SOLVED, fg="green"))
                .replace(NOT_SOLVED, click.style(NOT_SOLVED, fg="red"))
        )
    else:
        for row in table_contents:
            print(", ".join(x.replace(",", ";") for x in row))
