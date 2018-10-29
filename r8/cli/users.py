import click
import texttable

import r8
from r8 import util


@click.command("users")
@util.with_database
@click.option("--user", multiple=True, help="Only display users/teams that start with the given string. Can be passed multiple times.")
@click.option("--challenge", multiple=True, help="Only display challenges that start with the given string. Can be passed multiple times.")
@click.option("-T", is_flag=True, help="Transpose table.")
@click.option("--format", type=click.Choice(['table', 'csv']), default="table")
@click.option("--teams", is_flag=True, help="Group users by teams.")
def cli(user, challenge, t, format, teams):
    """View users and their progress."""
    if teams:
        challenges_stmt = "SELECT cid FROM challenges WHERE t_start < datetime('now') AND team = 1 ORDER BY ROWID ASC"
        users_stmt = "SELECT DISTINCT tid FROM teams ORDER BY ROWID ASC"
        submissions_stmt = "SELECT tid, cid FROM submissions NATURAL JOIN flags NATURAL JOIN teams"
    else:
        challenges_stmt = "SELECT cid FROM challenges WHERE t_start < datetime('now') ORDER BY ROWID ASC"
        users_stmt = "SELECT uid FROM users ORDER BY ROWID ASC"
        submissions_stmt = "SELECT uid, cid FROM submissions NATURAL JOIN flags"

    with r8.db:
        challenges = r8.db.execute(challenges_stmt).fetchall()
        challenges = [
            x[0] for x in challenges
            if not challenge or any(x[0].startswith(c) for c in challenge)
        ]

        users = r8.db.execute(users_stmt).fetchall()
        users = [
            x[0] for x in users
            if not user or any(x[0].startswith(u) for u in user)
        ]

        submissions = r8.db.execute(submissions_stmt).fetchall()

    user_index = {
        x: i for i, x in enumerate(users)
    }

    if format == "table":
        SOLVED = "OK"
        NOT_SOLVED = "FAIL"
    else:
        SOLVED = "TRUE"
        NOT_SOLVED = "FALSE"

    solved = {
        cid: [NOT_SOLVED] * len(users)
        for cid in challenges
    }
    for uid, cid in submissions:
        if cid in solved and uid in user_index:
            solved[cid][user_index[uid]] = SOLVED

    if t and teams:
        header = "Team"
    elif t and not teams:
        header = "User"
    else:
        header = "Challenge"

    table_contents = (
        [[header] + users] +
        [[cid] + solved for cid, solved in solved.items()]
    )
    if format == "table":
        for row in table_contents:
            row[0] = row[0][:22]
    if t:
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
