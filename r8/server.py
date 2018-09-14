import html
import os
import re
import secrets
import traceback
from functools import wraps
from pathlib import Path
from typing import Callable, Any, Union

import argon2
import itsdangerous
from aiohttp import web

import r8

DEFAULT_STATIC_DIR = Path(__file__).parent / "static"

auth_sign = itsdangerous.Signer(
    os.getenv("R8_SECRET", secrets.token_bytes(32)),
    salt="auth"
)


async def login(request: web.Request):
    logindata = await request.json()
    try:
        user = logindata["username"]
        password = logindata["password"]
    except KeyError:
        r8.log(request, "login-invalid")
        return web.HTTPBadRequest(reason="username or password missing.")
    with r8.db:
        ok = r8.db.execute(
            "SELECT password FROM users WHERE uid = ?",
            (user,)
        ).fetchone()
    try:
        if not ok:
            raise RuntimeError()
        r8.util.verify_hash(ok[0], password)
        r8.log(request, "login-success", uid=user)
        token = auth_sign.sign(user.encode()).decode()
        return web.json_response({"token": token})
    except (argon2.exceptions.VerificationError, RuntimeError):
        r8.log(request, "login-fail", user, uid=user if ok else None)
        return web.HTTPUnauthorized(
            reason="Invalid credentials."
        )


def authenticated(f: Callable[[str, web.Request], Any]) -> Callable[[web.Request], Any]:
    """decorator that injects an authenticated user argument into the request handler"""

    @wraps(f)
    def wrapper(request):
        try:
            token = request.query["token"]
        except KeyError:
            return web.HTTPUnauthorized()
        try:
            user = auth_sign.unsign(token).decode()
        except itsdangerous.BadData:
            return web.HTTPUnauthorized()
        else:
            return f(user, request)

    return wrapper


@authenticated
async def get_challenges(user: str, request: web.Request):
    """Get the current status."""
    r8.log(request, "get-challenges", request.headers.get("User-Agent"), uid=user)
    challenges = await _get_challenges(user)
    return web.json_response(challenges)


async def _get_challenges(user: str):
    with r8.db:
        cursor = r8.db.execute("""
          SELECT 
            challenges.cid AS cid, 
            cast(strftime('%s',t_start) AS INTEGER) AS start, 
            cast(strftime('%s',t_stop) AS INTEGER) AS stop, 
            max(cast(strftime('%s',submissions.timestamp) AS INTEGER)) AS solved,
            team
            FROM challenges
          LEFT JOIN flags ON flags.cid = challenges.cid
          LEFT JOIN submissions ON (
            flags.fid = submissions.fid 
            AND (
            submissions.uid = ? OR
            team = 1 AND submissions.uid IN (SELECT uid FROM teams WHERE tid = (SELECT tid FROM teams WHERE uid = ?))
            )
          )
          WHERE t_start < datetime('now')  -- hide not yet active challenges
          GROUP BY challenges.cid
        """, (user, user))
        column_names = tuple(x[0] for x in cursor.description)
        results = [
            {
                key: value
                for key, value in zip(column_names, row)
            } for row in cursor.fetchall()
        ]
        results = [
            x for x in results
            if x["solved"] or await r8.challenges[x["cid"]].visible(user)
        ]
        for challenge in results:
            inst = r8.challenges[challenge["cid"]]
            try:
                challenge["title"] = str(inst.title)
            except Exception:
                challenge["title"] = "Title Error"
                challenge["description"] = f"<pre>{html.escape(traceback.format_exc())}</pre>"
                continue
            try:
                challenge["description"] = await inst.description(user, bool(challenge["solved"]))
            except Exception:
                challenge["description"] = f"<pre>{html.escape(traceback.format_exc())}</pre>"
        return results


def correct_flag(flag: str) -> str:
    filtered = flag.replace(" ", "").lower()
    match = re.search(r"[0-9a-f]{32}", filtered)
    if match:
        return "__flag__{" + match.group(0) + "}"
    return flag


@authenticated
async def submit_flag(user: str, request: web.Request):
    """Submit a flag."""
    flag = (await request.json()).get("flag", "")
    flag = correct_flag(flag)
    with r8.db:
        cid = (r8.db.execute("""
          SELECT cid FROM flags 
          NATURAL INNER JOIN challenges
          WHERE fid = ? 
        """, (flag,)).fetchone() or [None])[0]
        if not cid:
            r8.log(request, "flag-err-unknown", flag, uid=user)
            return web.HTTPBadRequest(reason="Unknown Flag ¯\\_(ツ)_/¯")

        is_active = r8.db.execute("""
          SELECT 1 FROM challenges
          WHERE cid = ? 
          AND datetime('now') BETWEEN t_start AND t_stop
        """, (cid,)).fetchone()
        if not is_active:
            r8.log(request, "flag-err-inactive", flag, uid=user, cid=cid)
            return web.HTTPBadRequest(reason="Challenge is not active.")

        is_already_submitted = r8.db.execute("""
          SELECT COUNT(*) FROM submissions 
          NATURAL INNER JOIN flags
          NATURAL INNER JOIN challenges
          WHERE cid = ? AND (
          uid = ? OR
          challenges.team = 1 AND submissions.uid IN (SELECT uid FROM teams WHERE tid = (SELECT tid FROM teams WHERE uid = ?))
          )
        """, (cid, user, user)).fetchone()[0]
        if is_already_submitted:
            r8.log(request, "flag-err-solved", flag, uid=user, cid=cid)
            return web.HTTPBadRequest(reason="Challenge already solved.")

        is_oversubscribed = r8.db.execute("""
          SELECT 1 FROM flags
          WHERE fid = ?
          AND (SELECT COUNT(*) FROM submissions WHERE flags.fid = submissions.fid) >= max_submissions
        """, (flag,)).fetchone()
        if is_oversubscribed:
            r8.log(request, "flag-err-used", flag, uid=user, cid=cid)
            return web.HTTPBadRequest(reason="Flag already used too often.")

        # print(f"{user} solved {challenge} with {flag}.")
        r8.log(request, "flag-submit", flag, uid=user, cid=cid)
        r8.db.execute("""
          INSERT INTO submissions (uid, fid) VALUES (?, ?)
        """, (user, flag))

    return web.json_response({
        "challenges": await _get_challenges(user),
        "solved": r8.challenges[cid].title
    })


@authenticated
async def handle_challenge_request(user: str, request: web.Request):
    cid = request.match_info["cid"]
    if cid not in r8.challenges:
        return web.HTTPBadRequest(reason="Unknown challenge.")
    r8.log(request, "handle-request", await request.text(), uid=user, cid=cid)
    inst = r8.challenges[cid]
    resp = await inst.handle_request(user, request)
    if isinstance(resp, str):
        resp = web.json_response({"message": resp})
    return resp


def make_app(static_dir: Union[Path,str]) -> web.Application:
    static_dir = Path(static_dir)
    async def index(_):
        return web.FileResponse(static_dir / 'index.html')

    app = web.Application()
    app.router.add_get('/api/challenges', get_challenges)
    app.router.add_post('/api/login', login)
    app.router.add_post('/api/submit', submit_flag)
    app.router.add_post('/api/challenges/{cid}', handle_challenge_request)
    app.router.add_get('/', index)
    app.router.add_static('/', path=static_dir)
    return app


runner: web.AppRunner = None


async def start(address=("", 8000), static_dir = DEFAULT_STATIC_DIR):
    global runner
    r8.echo("ctf", "Starting...")
    app = make_app(static_dir)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, *address)
    await site.start()
    r8.echo("ctf", f"Running at {r8.util.format_address(address)}.")
    return runner


async def stop():
    r8.echo("ctf", "Stopping...")
    await runner.cleanup()
    r8.echo("ctf", "Stopped.")
