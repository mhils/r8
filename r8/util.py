import asyncio
import datetime
import functools
import os
import secrets
import sqlite3
import textwrap
from functools import wraps
from pathlib import Path
from typing import Optional, Union, Tuple

import argon2
import click
import itsdangerous
import texttable
from aiohttp import web

import r8

_colors = [
    "black",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "white"
]


def echo(namespace: str, message: str, err: bool = False) -> None:
    """
    Print to console with a namespace added in front.
    """
    if err:
        color = "red"
    else:
        color = _colors[hash(str) % len(_colors)]
    click.echo(click.style(f"[{namespace}] ", fg=color) + message)


auth_sign = itsdangerous.Signer(
    os.getenv("R8_SECRET", secrets.token_bytes(32)),
    salt="auth"
)

database_path = click.option(
    "--database",
    type=click.Path(exists=True),
    envvar="R8_DATABASE",
    default="r8.db"
)

database_rows = click.option(
    '--rows',
    type=int,
    default=100,
    help='Number of rows'
)


def with_database(f):
    @database_path
    @wraps(f)
    def wrapper(database, **kwds):
        r8.db = sqlite3_connect(database)
        return f(**kwds)

    return wrapper


def backup_db(f):
    @click.option("--backup/--no-backup", default=True,
                  help="Backup database to ~/.r8 before execution")
    @wraps(f)
    def wrapper(backup, **kwds):
        if backup:
            backup_dir = Path.home() / ".r8"
            backup_dir.mkdir(exist_ok=True)
            time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            with open(backup_dir / f"backup-{time}.sql", 'w') as out:
                for line in r8.db.iterdump():
                    out.write('%s\n' % line)
        return f(**kwds)

    return wrapper


def sqlite3_connect(filename):
    """
    Wrapper around sqlite3.connect that enables convenience features.
    """
    db = sqlite3.connect(filename)
    db.execute("PRAGMA foreign_keys = ON")
    return db


def run_sql(query: str, parameters=None, *, rows: int = 10) -> None:
    """
    Run SQL query against the database and pretty-print the result.
    """
    with r8.db:
        try:
            cursor = r8.db.execute(query, parameters or ())
        except Exception as e:
            return click.secho(str(e), fg="red")
        data = cursor.fetchmany(rows)
    table = texttable.Texttable(click.get_terminal_size()[0])
    if data:
        table.set_cols_align(["r" if isinstance(x, int) else "l" for x in data[0]])
    if cursor.description:
        table.set_deco(table.BORDER | table.HEADER | table.VLINES)
        header = [x[0] for x in cursor.description]
        table.add_rows([header] + data)
        print(table.draw())
    else:
        print("Statement did not return data.")


def media(src, desc, visible: bool = True):
    """
    HTML for bootstrap media element
    https://getbootstrap.com/docs/4.0/layout/media-object/
    """
    return textwrap.dedent(f"""
        <div class="media">
            <img class="mr-3" style="max-width: 128px; max-height: 128px;" src="{src if visible else "/challenge.png"}">
            <div class="align-self-center media-body">{desc}</div>
        </div>
        """)


def spoiler(help_text: str, button_text="🕵️ Show Hint") -> str:
    """
    HTML for spoiler element in challenge descriptions
    """
    div_id = secrets.token_hex(5)
    return f"""<div id="{div_id}-help" class="d-none">
                <hr/>
                {help_text}
            </div>
            <div id="{div_id}-button" class="btn btn-outline-info btn-sm">{button_text}</div>
            <script>
            document.getElementById("{div_id}-button").addEventListener("click", function(){{
                document.getElementById("{div_id}-button").classList.add("d-none");
                document.getElementById("{div_id}-help").classList.remove("d-none");
            }});
            </script>"""


def api_url(user: str, path: str) -> str:
    """
    URL to the CTF System API
    """
    origin = os.getenv("R8_ORIGIN", "").rstrip("/")
    token = r8.util.auth_sign.sign(user.encode()).decode()
    path = path.lstrip("/")
    if "?" in path:
        path += f"&token={token}"
    else:
        path += f"?token={token}"
    return f"{origin}/{path}"


def create_flag(
    challenge: str,
    max_submissions: int = 1,
    flag: str = None
) -> str:
    """
    Create a new flag for an existing challenge.
    """
    if flag is None:
        flag = "__flag__{" + secrets.token_hex(16) + "}"
    with r8.db:
        r8.db.execute(
            "INSERT OR REPLACE INTO flags (fid, cid, max_submissions) VALUES (?,?,?)",
            (flag, challenge, max_submissions)
        )
    return flag


def get_team(user: str) -> Optional[str]:
    with r8.db:
        row = r8.db.execute("""SELECT tid FROM teams WHERE uid = ?""", (user,)).fetchone()
        if row:
            return row[0]
        return None


def has_solved(user: str, challenge: str) -> bool:
    with r8.db:
        return r8.db.execute("""
            SELECT COUNT(*)
            FROM challenges
            NATURAL JOIN flags
            INNER JOIN submissions ON (
                flags.fid = submissions.fid
                AND (
                    submissions.uid = ? OR
                    team = 1 AND submissions.uid IN (SELECT uid FROM teams WHERE tid = (SELECT tid FROM teams WHERE uid = ?))
                )
            )
            WHERE challenges.cid = ?
        """, (user, user, challenge)).fetchone()[0]


THasIP = Union[str, tuple, asyncio.StreamWriter, asyncio.BaseTransport, web.Request]


def log(
    ip: THasIP,
    type: str,
    data: Optional[str] = None,
    *,
    cid: Optional[str] = None,
    uid: Optional[str] = None,
) -> None:
    """
    Create a log entry.

    For convenience reasons, ip can also be an address tuple or an asyncio.StreamWriter.
    """
    if isinstance(ip, web.Request):
        ip = ip.headers.get("X-Forwarded-For", ip.transport)
    if isinstance(ip, (asyncio.StreamWriter, asyncio.BaseTransport)):
        ip = ip.get_extra_info("peername")
    if isinstance(ip, tuple):
        ip = ip[0]
    with r8.db:
        r8.db.execute(
            "INSERT INTO events (ip, type, data, cid, uid) VALUES (?, ?, ?, ?, ?)",
            (ip, type, data, cid, uid)
        )


ph = argon2.PasswordHasher()


def hash_password(s: str) -> str:
    return ph.hash(s)


def verify_hash(hash: str, password: str) -> bool:
    return ph.verify(hash, password)


def format_address(address: Tuple[str, int]) -> str:
    host, port = address
    if not host:
        host = "0.0.0.0"
    return f"{host}:{port}"


def connection_timeout(f):
    """Timeout a connection after 60 seconds."""

    @functools.wraps(f)
    async def wrapper(*args, **kwds):
        try:
            await asyncio.wait_for(f(*args, **kwds), 60)
        except asyncio.TimeoutError:
            writer = args[-1]
            writer.write("\nconnection timed out.\n".encode())
            await writer.drain()
            writer.close()

    return wrapper


def tolerate_connection_error(f):
    """Silently catch all ConnectionErrors."""

    @functools.wraps(f)
    async def wrapper(*args, **kwds):
        try:
            return await f(*args, **kwds)
        except ConnectionError:
            pass

    return wrapper


def challenge_form_js(cid: str) -> str:
    return """
        <script>{ // make sure to add a block here so that `let` is scoped.
        let form = document.currentScript.previousElementSibling;
        let resp = form.querySelector(".response")
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            let post = {};
            (new FormData(form)).forEach(function(v,k){
                post[k] = v;
            });
            fetchApi(
                "/api/challenges/%s",
                {method: "POST", body: JSON.stringify(post)}
            ).then(json => {
                resp.textContent = json['message'];
            }).catch(e => {
                resp.textContent = "Error: " + e;
            })
        });
        }</script>
    """ % cid
