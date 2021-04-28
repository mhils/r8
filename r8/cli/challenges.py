import click
import pkg_resources

import r8
from r8 import util


@click.group("challenges")
def cli():
    """Challenge-related commands."""
    pass


@cli.command()
@util.with_database()
@util.database_rows
@click.argument("query", nargs=-1)
def list(rows, query):
    """
    Print the state of all created challenges.

    Accepts an optional query argument to limit the selection,
    e.g. "WHERE cid LIKE 'Basic%'".
    """
    util.run_sql(f"""
    SELECT cid, COUNT(uid) AS solved, t_start, t_stop, team FROM challenges
    LEFT JOIN flags USING (cid)
    LEFT JOIN submissions USING (fid)
    {" ".join(query)}
    GROUP BY cid
    ORDER BY challenges.rowid
    """, rows=rows)


@cli.command("list-available")
def list_available_challenges():
    """
    List all available challenges.
    """
    for entry_point in pkg_resources.iter_entry_points('r8.challenges'):
        entry_point.load()

    challenges = {}
    for name, cls in r8.challenges._classes.items():
        mod = cls.__module__.split(".")[0]
        challenges.setdefault(mod, []).append(name)

    for mod, challenges in sorted(challenges.items()):
        print(f"{mod}:")
        for c in sorted(challenges):
            print(f" - {c}")
