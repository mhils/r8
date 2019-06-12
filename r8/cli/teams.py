import click

import r8
from r8 import util


@click.group("teams")
def cli():
    """Team-related commands."""
    pass


@cli.command("list")
@util.with_database()
@util.database_rows
def list(rows):
    """Print all teams."""
    util.run_sql(f"""
    SELECT tid, uid FROM teams
    ORDER BY tid, uid DESC
    """, rows=rows)


@cli.command()
@util.with_database()
@click.argument("old-name")
@click.argument("new-name")
def rename(old_name, new_name):
    """Change a team name."""
    with r8.db:
        old_exists = r8.db.execute("SELECT COUNT(*) FROM teams WHERE tid = ?", (old_name,)).fetchone()[0]
        if not old_exists:
            raise click.UsageError("Old team does not exist.")
        new_exists = r8.db.execute("SELECT COUNT(*) FROM teams WHERE tid = ?", (new_name,)).fetchone()[0]
        if new_exists:
            raise click.UsageError("New team name does already exist.")
        r8.db.execute("UPDATE teams SET tid = ? WHERE tid = ?", (new_name, old_name))
    r8.echo("r8", f"""Renamed "{old_name}" to "{new_name}".""")
