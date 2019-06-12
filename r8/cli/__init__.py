import click

from r8.cli.challenges import cli as challenges_cli
from r8.cli.events import cli as events_cli
from r8.cli.flags import cli as flags_cli
from r8.cli.password import cli as password_cli
from r8.cli.run import cli as run_cli
from r8.cli.settings import cli as settings_cli
from r8.cli.sql import cli as sql_cli
from r8.cli.teams import cli as teams_cli
from r8.cli.users import cli as users_cli


@click.group("r8")
def main():
    """r8 - /ɹeɪt/ - ctf autograding system"""
    pass


main.add_command(challenges_cli)
main.add_command(events_cli)
main.add_command(flags_cli)
main.add_command(password_cli)
main.add_command(run_cli)
main.add_command(settings_cli)
main.add_command(sql_cli)
main.add_command(teams_cli)
main.add_command(users_cli)
