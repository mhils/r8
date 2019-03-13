import click

import r8
from r8 import util


@click.group("flags")
def cli():
    """Flag-related commands."""
    pass


@cli.command("create")
@util.with_database()
@click.argument("challenge")
@click.argument("name", required=False)
@click.option("--max", type=int, default=999999, help="Maximum number of submissions.")
def create(challenge, name, max):
    """Manually create a new flag."""
    flag = util.create_flag(challenge, max, name)
    print(f"Created: {flag} (valid for {max} submissions)")


@cli.command("limit")
@util.with_database()
@click.argument("flag")
@click.argument("max", type=int, required=False)
def limit(flag, max):
    """
    Set maximum number of submissions for a flag.

    If no additional argument is provided, the maximium number of submissions is set the the number of
    current submissions, essentially locking the flag.
    """
    with r8.db:
        exists = r8.db.execute("SELECT COUNT(*) FROM flags WHERE fid = ?", (flag,)).fetchone()[0]
        if not exists:
            raise click.UsageError("Flag does not exist.")
        if max is None:
            max = r8.db.execute("SELECT COUNT(*) FROM submissions WHERE fid = ?", (flag,)).fetchone()[0]
        r8.db.execute("UPDATE flags SET max_submissions = ? WHERE fid = ?", (max, flag))
    print(f"{flag} restricted to {max} submissions")


@cli.command("list")
@util.with_database()
@util.database_rows
@click.argument("challenge", required=False)
def list(rows, challenge):
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


@cli.command()
@util.with_database()
@click.argument("flag")
@click.argument("user")
@click.option("--force", "-f", is_flag=True)
def submit(flag, user, force):
    """Submit a flag for a user."""
    try:
        cid = r8.util.submit_flag(flag, user, "127.0.0.1", force)
    except ValueError as e:
        raise click.UsageError(str(e))
    else:
        r8.echo("r8", f"Solved {cid} for {user}.")


@cli.command()
@util.with_database()
@util.backup_db
@click.argument("flag")
@click.argument("user", required=False)
def revoke(flag, user):
    """Revoke a flag submission [for a given user]."""
    with r8.db:
        submissions = [
            x[0] for x in
            r8.db.execute("SELECT uid FROM submissions WHERE fid=?", (flag,)).fetchall()
        ]
        if not submissions:
            raise click.UsageError(f"No submissions for {flag}.")
        if user:
            if user in submissions:
                r8.db.execute("DELETE FROM submissions WHERE fid = ? AND uid = ?", (flag, user))
                r8.echo("r8", f"Submission revoked.")
            else:
                raise click.UsageError(f"Error: {user} did not submit {flag}.")
        else:
            click.confirm(f"Deleting all {len(submissions)} submission for {flag}. Continue?", abort=True)
            r8.db.execute("DELETE FROM submissions WHERE fid = ?", (flag,))
            r8.echo("r8", f"Submissions have been revoked for the following users: {', '.join(submissions)}")


@cli.command()
@util.with_database()
@click.argument("flag")
def delete(flag):
    """Delete an unsubmitted flag."""
    with r8.db:
        exists = r8.db.execute("SELECT COUNT(*) FROM flags WHERE fid = ?", (flag,)).fetchone()[0]
        if not exists:
            raise click.UsageError("Flag does not exist.")
        submissions = r8.db.execute("SELECT COUNT(*) FROM submissions WHERE fid = ?", (flag,)).fetchone()[0]
        if submissions:
            raise click.UsageError("Cannot delete a flag that is in use. Revoke all submissions first.")
        r8.db.execute("DELETE FROM flags WHERE fid = ?", (flag,))
    r8.echo("r8", f"Successfully deleted {flag}.")
