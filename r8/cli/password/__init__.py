import io
import random
import re
import smtplib
from contextlib import redirect_stdout
from dataclasses import dataclass
from email.mime.text import MIMEText
from pathlib import Path
from textwrap import dedent
from time import sleep

import click

import r8
from r8 import util


@click.group("password")
def cli():
    """Password-related commands."""


@cli.command()
@click.option("-n", default=1, help="Number of passwords")
@click.option("--length", default=3, help="Number of words per password.")
@click.option("--max-len", default=15, help="Max length of parts.")
@click.option("--hash/--no-hash", default=True, help="Include hash")
@click.pass_context
def generate(ctx: click.Context, n, length, max_len, hash):
    """Generate a memorable password."""
    here = Path(__file__).parent

    def clean(lst):
        return [x.strip() for x in lst if x.strip() and len(x.strip()) <= max_len]

    with open(here / "adjectives.txt") as f:
        adjectives = clean(f.readlines())
    with open(here / "animals.txt") as f:
        animals = clean(f.readlines())

    for _ in range(n):
        parts: list[str] = []
        for _ in range(1, length, 2):
            parts.append(random.choice(adjectives))
            parts.append(random.choice(animals))
        if length % 2:
            parts.insert(0, random.choice(adjectives))
        password = "".join(x.capitalize() for x in parts)
        print(password, end="; " if hash else "\n")
        if hash:
            ctx.invoke(hash_password, password=password)


@cli.command("hash")
@click.password_option()
def hash_password(password):
    """Hash a password."""
    print(util.hash_password(password))


@cli.command()
@util.with_database()
@click.argument("user")
@click.password_option()
def update_temporary(user, password):
    """Update a user's password in the live database.

    This change will be undone if you reset credentials in `config.sql`.
    """
    password = util.hash_password(password)
    with r8.db:
        exists = r8.db.execute(
            "SELECT COUNT(*) FROM users WHERE uid = ?", (user,)
        ).fetchone()[0]
        if not exists:
            raise click.UsageError("User does not exist.")
        r8.db.execute("UPDATE users SET password = ? WHERE uid = ?", (password, user))
    r8.echo(
        "r8",
        f"Password updated. "
        f"Note that this change may only be temporary if you reset credentials in `config.sql`.",
    )
