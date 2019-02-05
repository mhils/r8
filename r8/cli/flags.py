import click

import r8
from r8 import util


@click.group("flags")
def cli():
    """Flag-related commands."""
    pass


@cli.command("create")
@util.with_database
@click.argument("challenge")
@click.argument("name", required=False)
@click.option("--max", type=int, default=999999, help="Maximum number of submissions.")
def create_flag(challenge, name, max):
    """Manually create a new flag."""
    flag = util.create_flag(challenge, max, name)
    print(f"Created: {flag} (valid for {max} submissions)")


@cli.command("limit")
@util.with_database
@click.argument("flag")
@click.argument("max", type=int, required=False)
def limit_flag(flag, max):
    """
    Set maximum number of submissions for a flag.

    If no additional argument is provided, the maximium number of submissions is set the the number of
    current submissions, essentially locking the flag.
    """
    with r8.db:
        exists = r8.db.execute("SELECT COUNT(*) FROM flags WHERE fid = ?", (flag,)).fetchone()[0]
        if not exists:
            return r8.echo("r8","Error: Flag does not exist.", err=True)
        if max is None:
            max = r8.db.execute("SELECT COUNT(*) FROM submissions WHERE fid = ?", (flag,)).fetchone()[0]
        r8.db.execute("UPDATE flags SET max_submissions = ? WHERE fid = ?", (max, flag))
    print(f"{flag} restricted to {max} submissions")


@cli.command("list")
@util.with_database
@util.database_rows
@click.argument("challenge", required=False)
def list_flags(rows, challenge):
    """Print all flags [for a given challenge]."""
    with r8.db:
        if challenge:
            where = "WHERE cid = ?"
            parameters = (challenge,)
        else:
            where = ""
            parameters = None

        util.run_sql(f"""
        SELECT cid, fid, COUNT(uid) AS submissions, max_submissions FROM flags
        LEFT JOIN submissions USING(fid)
        {where}
        GROUP BY fid
        ORDER BY cid, submissions DESC
        """, parameters, rows=rows)


@cli.command("submit")
@util.with_database
@click.argument("user")
@click.argument("flag")
@click.option("--force", "-f", is_flag=True)
def list_flags(user, flag, force):
    """Submit a flag for a user."""
    try:
        cid = r8.util.submit_flag(flag, user, "127.0.0.1", force)
    except ValueError as e:
        r8.echo("r8", str(e), err=True)
    else:
        r8.echo("r8", f"Solved {cid}.")
