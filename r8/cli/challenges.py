import click
import pkg_resources

import r8
from r8 import util


@click.group("challenges")
def cli():
    """Challenge-related commands."""
    pass


@cli.command("list")
@util.with_database()
@util.database_rows
@click.argument("query", nargs=-1)
def list_challenges(rows, query):
    """
    Print the state of all created challenges.

    Accepts an optional query argument to limit the selection,
    e.g. "WHERE cid LIKE 'Attendance%'".
    """
    with r8.db:
        util.run_sql(f"""
        SELECT cid, COUNT(uid) AS solved, t_start, t_stop, team FROM challenges
        LEFT JOIN flags USING (cid)
        LEFT JOIN submissions USING (fid)
        {" ".join(query)}
        GROUP BY cid
        ORDER BY t_start DESC
        """, rows=rows)


@cli.command("list-available")
def list_available_challenges():
    """
    List all available challenges.
    """
    assert not r8.challenges._classes
    for entry_point in pkg_resources.iter_entry_points('r8.challenges'):
        print(f"{entry_point.module_name}:")
        entry_point.load()
        for c in sorted(r8.challenges._classes):
            print(f" - {c}")
        r8.challenges._classes.clear()
