from __future__ import annotations

import collections
import io
import re
import shutil
import smtplib
import time
from contextlib import redirect_stdout
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
@click.option(
    "--teams",
    "teamnames",
    type=click.File("r"),
    help="A text file with at least as many team names as there are users, for example r8/misc/teamnames.txt.",
)
@click.pass_context
def make_sql(ctx: click.Context, usernames: io.StringIO, teamnames: io.StringIO):
    """Generate SQL code to provision users from a list of usernames or email addresses."""
    users = usernames.read().strip().splitlines()

    if not users:
        raise click.UsageError("No users passed.")

    if teamnames:
        teams = teamnames.read().strip().splitlines()
        if len(teams) < len(users):
            raise click.UsageError(
                f"There are {len(users)} users, but only {len(teams)} teams."
            )
    else:
        teams = None

    click.secho("DELETE FROM users;", fg="cyan")
    click.secho("INSERT INTO users (uid, password) VALUES", fg="cyan")
    for user in users:
        f = io.StringIO()
        with redirect_stdout(f):
            ctx.invoke(generate, hash=False)
        password = f"$plain${f.getvalue().strip()}"
        if user != users[-1]:
            print(f"  ('{user}', '{password}'),")
        else:
            print(f"  ('{user}', '{password}')")
    click.secho(";", fg="cyan")

    if not teams:
        print("")
        click.secho(
            "The --teams option was not passed, skipping SQL for teams.", fg="yellow"
        )
        return

    click.secho("\nDELETE FROM teams;", fg="cyan")
    click.secho("INSERT INTO teams (uid, tid) VALUES", fg="cyan")
    for (user, team) in zip(users, teams):
        if user != users[-1]:
            print(f"  ('{user}', '{team}'),")
        else:
            print(f"  ('{user}', '{team}')")
    click.secho(";", fg="cyan")


DEFAULT_MAIL = """
# User credentials email template. Delete ~/.r8/mail.txt to restore the default.
# Available variables:
#  - origin
#  - username
#  - password
#  - team

Hi,

Here are your credentials for the CTF system.

Website: {origin}
Username: {username}
Password: {password}

You should be able to login, but not see any challenges yet.

The CTF has a public scoreboard. To protect your privacy, you (and everyone else) 
will only appear under a randomly-chosen pseudonym. Your current alias is "{team}".

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


def _validate_sender(ctx, param, value):
    if not re.fullmatch(".+ <.+@.+>", value):
        raise click.BadParameter(
            'Sender must be in format "John Doe <john@example.com>".'
        )
    return value


@cli.command()
@util.with_database()
@click.option(
    "--smtp-server",
    prompt="SMTP server",
    default="smtp.uibk.ac.at",
    help="Server name for outgoing mail, e.g. smtp.uibk.ac.at.",
)
@click.option(
    "--smtp-username", prompt="SMTP username", help="SMTP username for sending mail."
)
@click.password_option(
    "--smtp-password", prompt="SMTP password", help="SMTP password for sending mail."
)
@click.option(
    "--subject",
    prompt="Email subject",
    default="CTF Credentials",
    help="The email subject.",
)
@click.option(
    "--from",
    "from_",
    prompt="Email sender name",
    default="CTF System <noreply@uibk.ac.at>",
    callback=_validate_sender,
    help='The sender\'s name displayed in the "From" field, e.g. "CTF System <noreply@uibk.ac.at>".',
)
@click.option(
    "--recipient-domain",
    help="Domain for all users where the username is only the local part of the email address.",
)
def send_credentials(
    smtp_server: str,
    smtp_username: str,
    smtp_password: str,
    subject: str,
    from_: str,
    recipient_domain: str | None,
):
    """
    Send emails with credentials to all users in the database.

    This command has two prerequisites:
    First, passwords can only be sent out for users with plaintext passwords in the database.
    Second, usernames must be full email addresses or the local part (the part before "@") of an email address
    with all users sharing the same domain.

    This command will show explicit confirmation prompts before sending any emails.
    """

    with r8.db:
        all_users = r8.db.execute(
            "SELECT uid, uid, password, tid FROM users NATURAL LEFT JOIN teams ORDER BY users.ROWID"
        ).fetchall()

    users = [
        (user, email, password.removeprefix("$plain$"), team)
        for (user, email, password, team) in all_users
        if password.startswith("$plain$")
    ]
    print(f"Total users: {len(all_users)}")
    print(f"Users with plaintext password: {len(users)}")

    if not users:
        click.secho("No users to send emails to.", fg="red")
        raise click.Abort()
    del all_users

    has_team_count = sum(bool(team) for (_, _, _, team) in users)
    if has_team_count == 0:
        click.secho("No users with plaintext passwords have a team.", fg="yellow")
    elif has_team_count == len(users):
        click.secho("All users with plaintext passwords have a team.", fg="green")
    else:
        click.confirm(
            f"Only {has_team_count} of {len(users)} users have a team. Continue with setup?",
            abort=True,
        )

    usernames_without_email = sum("@" not in email for (_, email, _, _) in users)
    if usernames_without_email:
        if not recipient_domain:
            click.secho(
                f"Users without an email address as username: {usernames_without_email}",
                fg="yellow",
            )
            if usernames_without_email == len(users):
                print("Please specify the domain under which they receive emails.")
                recipient_domain = click.prompt(
                    "Recipient domain: ", prompt_suffix="username@"
                )
            else:
                print(
                    f"You may specify a common domain under which they receive emails, "
                    f"or press enter to skip these users."
                )
                recipient_domain = click.prompt(
                    "Recipient domain: ",
                    prompt_suffix="username@",
                    default="",
                    show_default=False,
                )
        if recipient_domain:
            users = [
                (
                    username,
                    email if "@" in email else f"{email}@{recipient_domain}",
                    password,
                    team,
                )
                for (username, email, password, team) in users
            ]
        else:
            users = [
                (username, email, password, team)
                for (username, email, password, team) in users
                if "@" in email
            ]

    click.confirm(
        f"The plan is to email {len(users)} users. Continue with editing the email template?",
        abort=True,
    )

    template = _get_mail_template()

    with click.progressbar(users, label="Sending emails...") as progress:
        for i, (username, email, password, team) in enumerate(progress):
            message = MIMEText(
                template.format(
                    origin=r8.settings["origin"],
                    username=username,
                    password=password,
                    team=team,
                )
            )
            message["Subject"] = subject
            message["From"] = from_
            message["To"] = email

            to = [message["To"]]
            if not smtp_username.startswith("noreply"):
                to.append(smtp_username)

            if i == 0:
                print("")
                click.secho("=" * 20 + " First Email to be sent " + "=" * 20, fg="cyan")
                print(str(message))
                click.secho("=" * 64, fg="cyan")
                click.confirm(
                    f"Does the draft above look good? If yes, the first email will be sent.",
                    abort=True,
                )

            s = smtplib.SMTP(smtp_server, 587)
            s.starttls()
            s.login(smtp_username, smtp_password)
            s.sendmail(
                message["From"], [message["To"], smtp_username], message.as_string()
            )
            s.quit()

            if i == 0:
                click.confirm(f"First email sent. Send all other emails?", abort=True)
            # Don't run into rate limits.
            time.sleep(10)
