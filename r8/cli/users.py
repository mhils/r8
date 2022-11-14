from __future__ import annotations

import collections
import io
import re
import shutil
import smtplib
import time
from contextlib import redirect_stdout
from dataclasses import dataclass
from email.mime.text import MIMEText
from pathlib import Path

import click
import texttable

import r8
from r8 import util
from r8.cli.password import generate


@click.group("users")
def cli():
    """User-related commands."""


@cli.command()
@util.with_database()
@click.option(
    "--user",
    "entry_filter",
    multiple=True,
    help="Only display users/teams that start with the given string. Can be passed multiple times.",
)
@click.option(
    "--challenge",
    "challenge_filter",
    multiple=True,
    help="Only display challenges that start with the given string. Can be passed multiple times.",
)
@click.option("-T", "transpose", is_flag=True, help="Transpose table.")
@click.option("--format", type=click.Choice(["table", "csv"]), default="table")
@click.option("--teams", is_flag=True, help="Group users by teams.")
@click.option(
    "--team-solves/--no-team-solves",
    default=True,
    is_flag=True,
    help="Include team solves.",
)
def show(entry_filter, challenge_filter, transpose, format, teams, team_solves):
    """View users and their progress."""

    if teams and not team_solves:
        raise click.UsageError("--teams and --no-team-solves are mutually exclusive.")

    with r8.db:
        all_challenges = r8.db.execute(
            "SELECT cid, team FROM challenges WHERE t_start < datetime('now') ORDER BY ROWID"
        ).fetchall()
        user_info = r8.db.execute(
            "SELECT uid, tid FROM users NATURAL LEFT JOIN teams ORDER BY users.ROWID"
        ).fetchall()
        submissions = r8.db.execute(
            "SELECT uid, tid, cid FROM submissions NATURAL JOIN flags NATURAL LEFT JOIN teams"
        ).fetchall()

    entries = []  # either teams or users
    team_users = collections.defaultdict(list)
    for uid, tid in user_info:
        if teams:
            entries.append(tid)
        else:
            entries.append(uid)
        team_users[tid].append(uid)

    # remove duplicate teams
    entries = list(dict.fromkeys(entries))

    if entry_filter:
        entries = [
            entry for entry in entries if any(entry.startswith(x) for x in entry_filter)
        ]
    entry_index = {x: i for i, x in enumerate(entries)}

    challenges = {}
    for cid, is_team_challenge in all_challenges:
        if teams and not is_team_challenge:
            continue
        if challenge_filter and not any(cid.startswith(c) for c in challenge_filter):
            continue
        challenges[cid] = is_team_challenge

    if format == "table":
        SOLVED = "OK"
        NOT_SOLVED = "FAIL"
    else:
        SOLVED = "TRUE"
        NOT_SOLVED = "FALSE"

    solved = {cid: [NOT_SOLVED] * len(entries) for cid in challenges}
    if teams:
        for _, tid, cid in submissions:
            if cid in challenges and tid in entry_index:
                solved[cid][entry_index[tid]] = SOLVED
    else:
        for uid, tid, cid in submissions:
            if cid in challenges:
                if challenges[cid] and team_solves:
                    for uid in team_users[tid]:
                        if uid in entry_index:
                            solved[cid][entry_index[uid]] = SOLVED
                elif uid in entry_index:
                    solved[cid][entry_index[uid]] = SOLVED

    if not transpose and teams:
        header = "Team"
    elif not transpose and not teams:
        header = "User"
    else:
        header = "Challenge"

    table_contents = [[header] + entries] + [
        [cid] + solved for cid, solved in solved.items()
    ]
    if format == "table":
        for row in table_contents:
            row[0] = row[0][:22]
    if not transpose:
        table_contents = list(zip(*table_contents))

    if format == "table":
        table = texttable.Texttable(shutil.get_terminal_size((0, 0))[0])
        table.set_cols_align(["l"] + ["c"] * (len(table_contents[0]) - 1))
        table.set_deco(table.BORDER | table.HEADER | table.VLINES)
        table.add_rows(table_contents)

        try:
            table._compute_cols_width()
        except ValueError:
            table._max_width = False

        tbl = table.draw()
        print(
            tbl.replace(SOLVED, click.style(SOLVED, fg="green")).replace(
                NOT_SOLVED, click.style(NOT_SOLVED, fg="red")
            )
        )
    else:
        for row in table_contents:
            print(", ".join((x or "").replace(",", ";") for x in row))


@cli.command()
@click.argument("usernames", default="usernames.txt", type=click.File("r"))
@click.option("--teams", "teamnames", type=click.File("r"))
@click.pass_context
def make_sql(ctx: click.Context, usernames: io.StringIO, teamnames: io.StringIO):
    """Generate SQL code to provision users from usernames.txt."""
    users = usernames.read().strip().splitlines()

    if teamnames:
        teams = teamnames.read().strip().splitlines()
        if len(teams) < len(users):
            raise click.UsageError(f"There are {len(users)} users, but only {len(teams)} teams.")
    else:
        teams = None

    click.secho("DELETE FROM users;", fg="cyan")
    click.secho("INSERT INTO users (uid, password) VALUES", fg="cyan")
    for user in users:
        f = io.StringIO()
        with redirect_stdout(f):
            ctx.invoke(generate)
        plaintext, _, hash = f.getvalue().partition("; ")
        if user != users[-1]:
            print(f"  ('{user}', '{hash.strip()}'), -- {plaintext}")
        else:
            print(f"  ('{user}', '{hash.strip()}')  -- {plaintext}")
    click.secho(";", fg="cyan")

    if not teams:
        print("")
        click.secho("The --teams option was not passed, skipping SQL for teams.", fg="yellow")
        return

    click.secho("\nDELETE FROM teams;", fg="cyan")
    click.secho("INSERT INTO teams (uid, tid) VALUES", fg="cyan")
    for (user, team) in zip(users, teams):
        if user != users[-1]:
            print(f"  ('{user}', '{team}'),")
        else:
            print(f"  ('{user}', '{team}')")
    click.secho(";", fg="cyan")


@dataclass
class UserInfo:
    username: str
    password: str
    team: str | None


DEFAULT_MAIL = """
# User credentials email template. Delete ~/.r8/mail.txt to restore the default.
# Available variables:
#  - ctf_domain
#  - user.username
#  - user.password
#  - user.team

Hi,

Here are your credentials for the CTF system.

Website: https://{ctf_domain}
Username: {user.username}
Password: {user.password}

You should be able to login, but not see any challenges yet.

The CTF has a public scoreboard. To protect your privacy, you (and everyone else) 
will only appear under a randomly-chosen pseudonym. Your current alias is "{user.team}".

Best,
The CTF System
""".strip()
MAIL_FILE = Path("~/.r8/mail.txt").expanduser()


def _get_mail_template() -> str:
    if MAIL_FILE.exists():
        raw_template = MAIL_FILE.read_text("utf8").strip()
    else:
        raw_template = ""

    raw_template = click.edit(raw_template or DEFAULT_MAIL, require_save=False)

    template = re.sub(r"^(#.*\n?|\s+)+", "", raw_template)

    MAIL_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAIL_FILE.write_text(raw_template, "utf8")

    if not template:
        print("Empty template, aborting.")
        raise click.Abort()

    return template


@cli.command()
@click.option("--config", prompt="Configuration file", default="config.sql", type=click.File("r"),
              help="The configuration file which includes plaintext passwords.")
@click.option("--ctf-domain", prompt="CTF domain (e.g. ctf.example.com)",
              help="The domain the CTF system is running on, e.g. `ctf.example.com`.")
@click.option("--smtp-server", prompt="SMTP server", default="smtp.uibk.ac.at",
              help="Server name for outgoing mail, e.g. smtp.uibk.ac.at.")
@click.option("--smtp-username", prompt="SMTP username (e.g. noreply@uibk.ac.at)",
              help="The sender's username, e.g. noreply@uibk.ac.at.")
@click.password_option("--smtp-password", prompt="SMTP password", help="The sender's password.")
@click.option("--subject", prompt="Email subject", default="CTF Credentials", help="The email subject.")
@click.option("--sender", prompt="Email sender name", default="CTF System",
              help='The sender\'s name displayed in the "From" field, e.g. "CTF System".')
@click.option("--receiver-domain", prompt=True, default="uibk.ac.at",
              help="The receiver's domain. All emails will go to <ctf username>@<receiver domain>.")
def send_mails(
    config: io.StringIO,
    ctf_domain: str,
    smtp_server: str,
    smtp_username: str,
    smtp_password: str,
    subject: str,
    sender: str,
    receiver_domain: str,
):
    """
    Send emails with credentials to all users.

    This command has a few prerequisites:
      1. The configuration file must include plaintext passwords as comments (as generated by `r8 users make-sql`).
      2. Each user's email address is <username>@<same domain for all users>.
    """
    contents = config.read()
    passwords = re.findall(r"\('(.+?)',\s*'\$argon2.+?'\),?\s*--\s*(\S+)", contents)

    if not passwords:
        click.echo(
            "Error finding users. Your configuration files should have lines like this:\n\n"
            "('username', '$argon2id$...'), -- PlaintextPassword\n\n",
            err=True
        )
        return

    teams = {}
    team_sql = contents.partition("DELETE FROM teams;")[2]
    for (a, b) in re.findall(r"\('(.+?)',\s*'(.+?)'\)", team_sql):
        teams.setdefault(a, b)
        teams.setdefault(b, a)

    try:
        users = [
            UserInfo(name, password, teams.get(name))
            for (name, password) in passwords
        ]
    except KeyError:
        # We either have teams for all users or none at all.
        users = [
            UserInfo(name, password, None)
            for (name, password) in passwords
        ]

    for user in users:
        print(user)
    click.confirm(f"Found credentials for {len(users)} users. Is this correct?", abort=True)

    template = _get_mail_template()

    with click.progressbar(users, label="Sending emails...") as progress:
        for i, user in enumerate(progress):
            message = MIMEText(template.format(
                ctf_domain=ctf_domain,
                user=user,
            ))
            message['Subject'] = subject
            message['From'] = f"{sender} <{smtp_username}>"
            message['To'] = f"{user.username}@{receiver_domain}"

            to = [message['To']]
            if not smtp_username.startswith("noreply"):
                to.append(smtp_username)

            if i == 0:
                print("")
                click.secho("=" * 20 + " First Email to be sent " + "=" * 20, fg="cyan")
                print(str(message))
                click.secho("=" * 64, fg="cyan")
                click.confirm(f"Does the email above look good?", abort=True)

            s = smtplib.SMTP(smtp_server, 587)
            s.starttls()
            s.login(smtp_username, smtp_password)
            s.sendmail(
                message['From'],
                [message['To'], smtp_username],
                message.as_string()
            )
            s.quit()

            if i == 0:
                click.confirm(f"First email sent. Continue?", abort=True)
            # Don't run into rate limits.
            time.sleep(10)
