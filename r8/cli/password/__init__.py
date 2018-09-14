import random
from pathlib import Path
from typing import List

import click

from r8 import util


@click.group("password")
def cli():
    """Password-related commands."""
    pass


@cli.command("generate")
@click.option("-n", default=1, help="Number of passwords")
@click.option("--length", default=3, help="Number of words per password.")
@click.option("--max-len", default=15, help="Max length of parts.")
@click.option("--hash/--no-hash", default=True, help="Include hash")
@click.pass_context
def generate_password(ctx: click.Context, n, length, max_len, hash):
    """Generate a memorable password."""
    here = Path(__file__).parent

    def clean(lst):
        return [
            x.strip() for x in lst
            if x.strip() and len(x.strip()) <= max_len
        ]

    with open(here / "adjectives.txt") as f:
        adjectives = clean(f.readlines())
    with open(here / "animals.txt") as f:
        animals = clean(f.readlines())

    for _ in range(n):
        parts: List[str] = []
        for _ in range(1, length, 2):
            parts.append(random.choice(adjectives))
            parts.append(random.choice(animals))
        if length % 2:
            parts.insert(0, random.choice(adjectives))
        password = "".join(x.capitalize() for x in parts)
        print(password, end=", " if hash else "\n")
        if hash:
            ctx.invoke(hash_password, password=password)


@cli.command("hash")
@click.password_option()
def hash_password(password):
    """Hash a password."""
    print(util.hash_password(password))
