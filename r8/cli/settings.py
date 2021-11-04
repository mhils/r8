import json

import click

import r8
from r8 import util


@click.group("settings")
def cli():
    """View and modify the r8 configuration

    r8's database has a `settings` table where keys as strings and values are
    JSON objects, e.g. numbers, strings, or list of strings. The subcommands
    available here can be used to view or modify the configuration.
    """
    pass


@cli.command()
@util.with_database()
def view():
    """Print the current configuration"""
    util.run_sql(f"SELECT * FROM settings", rows=100)


@cli.command()
@click.argument("key")
@click.argument("value", nargs=-1)
@util.with_database()
def set(key, value):
    """Set a configuration key to a specific value

    Set KEY to VALUE.
    If multiple values are passed, they are treated as a list of strings.
    If a single value is passed that is not valid JSON, it is treated as a string.

    \b
    Examples:
        - r8 settings set host localhost
        - r8 settings set port 8000
        - r8 settings set static_dir /first/directory /second/directory
    """
    if len(value) == 1:
        value = value[0]
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            try:
                value = int(value)
            except ValueError:
                pass  # if the value is neither valid JSON nor an integer, we just treat it as a string.
    else:
        value = list(value)
    value = json.dumps(value)
    with r8.db:
        r8.db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    util.run_sql(f"SELECT * FROM settings", rows=100)


@cli.command()
@click.argument("key")
@util.with_database()
def delete(key):
    """Delete a configuration key."""
    with r8.db:
        r8.db.execute("DELETE FROM settings WHERE key = ?", (key,))
    util.run_sql(f"SELECT * FROM settings", rows=100)
