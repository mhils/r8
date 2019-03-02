import json
from functools import wraps
from pathlib import Path
from typing import Callable, Any, Union

import argon2
import itsdangerous
from aiohttp import web

import r8


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
            raise ValueError()
        r8.util.verify_hash(ok[0], password)
        r8.log(request, "login-success", uid=user)
        token = r8.util.auth_sign.sign(user.encode()).decode()
        secure_flag = "; Secure"
        if r8.settings["origin"].startswith("http://"):
            secure_flag = ""
        return web.json_response(
            {},
            headers={
                # aiohttp doesn't support SameSite as of writing this.
                "Set-Cookie": f"token={token}; Path=/; Max-Age=31536000; SameSite=strict; HttpOnly{secure_flag}"
            }
        )
    except (argon2.exceptions.VerificationError, ValueError):
        r8.log(request, "login-fail", user, uid=user if ok else None)
        return web.HTTPUnauthorized(
            reason="Invalid credentials."
        )


async def logout(request: web.Request):
    resp = web.json_response({})
    resp.del_cookie("token")
    return resp


def authenticated(f: Callable[[str, web.Request], Any]) -> Callable[[web.Request], Any]:
    """decorator that injects an authenticated user argument into the request handler"""

    @wraps(f)
    def wrapper(request):
        token = request.query.get("token", "") or request.cookies.get("token", "")
        try:
            user = r8.util.auth_sign.unsign(token).decode()
        except itsdangerous.BadData:
            return web.HTTPUnauthorized()
        else:
            return f(user, request)

    return wrapper


@authenticated
async def get_challenges(user: str, request: web.Request):
    """Get the current challenge state."""
    r8.log(request, "get-challenges", request.headers.get("User-Agent"), uid=user)
    challenges = await r8.util.get_challenges(user)
    return web.json_response({
        "user": user,
        "challenges": challenges,
    })


@authenticated
async def submit_flag(user: str, request: web.Request):
    """Submit a flag."""
    flag = (await request.json()).get("flag", "")
    try:
        cid = r8.util.submit_flag(flag, user, request)
    except ValueError as e:
        return web.HTTPBadRequest(reason=str(e))
    else:
        return web.json_response({
            "challenges": await r8.util.get_challenges(user),
            "solved": r8.challenges[cid].title,
        })


@authenticated
async def handle_challenge_request(user: str, request: web.Request):
    try:
        inst = r8.challenges[request.match_info["cid"]]
    except KeyError:
        return web.HTTPBadRequest(reason="Unknown challenge.")

    if request.method == "GET":
        resp = await inst.handle_get_request(user, request)
    else:
        path = (request.match_info["path"] + " ").lstrip()
        data = path + await request.text()
        # We want this to appear before any challenge-specific logging...
        rowid = r8.log(request, "handle-request", data, uid=user, cid=inst.id)
        resp = await inst.handle_post_request(user, request)
        # ...yet we also want to include the response code.
        with r8.db:
            r8.db.execute("""
                UPDATE events SET data = ? WHERE ROWID = ?
            """, (f"{data} -> {resp.status} {resp.reason}", rowid))

    if isinstance(resp, str):
        resp = web.json_response({"message": resp})
    return resp


def make_app(static_dir: Union[Path, str]) -> web.Application:
    static_dir = Path(static_dir)

    async def index(_):
        return web.FileResponse(static_dir / 'index.html')

    app = web.Application()
    app.router.add_post('/api/login', login)
    app.router.add_post('/api/logout', logout)
    app.router.add_post('/api/submit', submit_flag)
    app.router.add_get('/api/challenges', get_challenges)
    app.router.add_get('/api/challenges/{cid}{path:(/.*)?}', handle_challenge_request)
    app.router.add_post('/api/challenges/{cid}{path:(/.*)?}', handle_challenge_request)
    app.router.add_get('/', index)
    app.router.add_static('/', path=static_dir)
    return app


runner: web.AppRunner = None


async def start():
    global runner
    r8.echo("r8", "Starting server...")
    app = make_app(r8.settings["static_dir"])
    runner = web.AppRunner(app)
    await runner.setup()
    address = json.loads(r8.settings["listen_address"])
    site = web.TCPSite(runner, *address)
    await site.start()
    r8.echo("r8", f"Running at {r8.util.format_address(address)}.")
    return runner


async def stop():
    r8.echo("r8", "Stopping server...")
    await runner.cleanup()
    r8.echo("r8", "Stopped.")
