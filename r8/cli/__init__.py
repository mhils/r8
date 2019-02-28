import click

from r8.cli.challenges import cli as challenges
from r8.cli.events import cli as events
from r8.cli.flags import cli as flags
from r8.cli.password import cli as password
from r8.cli.run import cli as run
from r8.cli.settings import cli as settings
from r8.cli.sql import cli as sql
from r8.cli.users import cli as users


@click.group()
def main():
    """r8 - /ɹeɪt/ - ctf autograding system"""
    pass


main.add_command(challenges)
main.add_command(events)
main.add_command(flags)
main.add_command(password)
main.add_command(run)
main.add_command(settings)
main.add_command(sql)
main.add_command(users)
