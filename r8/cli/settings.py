import json

import click

import r8
from r8 import util


@click.group("settings")
def cli():
    """View and modify settings."""
    pass


@cli.command()
@util.with_database()
def view():
    """Print all settings"""
    util.run_sql(f"SELECT * FROM settings", rows=100)


@cli.command()
@click.argument("key")
@click.argument("value", nargs=-1)
@util.with_database()
def set(key, value):
    """Update a setting"""
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
    """Update a setting"""
    with r8.db:
        r8.db.execute("DELETE FROM settings WHERE key = ?", (key,))
    util.run_sql(f"SELECT * FROM settings", rows=100)

