from functools import wraps
from typing import Any
from typing import Callable

import argon2
import itsdangerous
from aiohttp import web

import r8


def authenticated(f: Callable[[str, web.Request], Any]) -> Callable[[web.Request], Any]:
    """decorator that injects an authenticated user argument into the request handler"""

    @wraps(f)
    async def wrapper(request):
        token = request.query.get("token", "") or request.cookies.get("token", "")
        try:
            user = r8.util.auth_sign.unsign(token).decode()
        except itsdangerous.BadData:
            return web.HTTPUnauthorized()
        else:
            return await f(user, request)

    return wrapper


routes = web.RouteTableDef()


@routes.post("/register")
async def register(request: web.Request):
    """very very simply self-registration functionality that abuses teams for nicknames."""
    if not r8.settings.get("register", False):
        return web.HTTPForbidden()

    logindata = await request.json()
    try:
        user = logindata["username"]
        password = logindata["password"]
        nickname = logindata["nickname"]
    except KeyError:
        r8.log(request, "register-invalid", "incomplete request")
        return web.HTTPBadRequest(reason="All fields are required.")
    with r8.db:
        user_exists = r8.db.execute(
            "SELECT 1 FROM users WHERE uid = ?", (user,)
        ).fetchone()
        team_exists = r8.db.execute(
            "SELECT 1 FROM teams WHERE tid = ?", (nickname,)
        ).fetchone()
    if user_exists:
        r8.log(request, "register-invalid", "username exists")
        return web.HTTPBadRequest(
            reason="There already exists an account with this email."
        )
    if team_exists:
        r8.log(request, "register-invalid", "team exists")
        return web.HTTPBadRequest(reason="There already exists a team with that name.")
    with r8.db:
        r8.db.execute(
            "INSERT INTO users(uid, password) VALUES (?,?)",
            (user, r8.util.hash_password(password)),
        )
        r8.db.execute("INSERT INTO teams(uid, tid) VALUES (?,?)", (user, nickname))
    r8.log(request, "register-success", uid=user)
    return await login(request)


@routes.post("/login")
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
            "SELECT password FROM users WHERE uid = ?", (user,)
        ).fetchone()
    try:
        if not ok:
            raise ValueError()
        hash: str = ok[0]
        if hash.startswith("$plain$"):
            if hash.removeprefix("$plain$") != password:
                raise ValueError()
        else:
            r8.util.verify_hash(hash, password)
        r8.log(request, "login-success", uid=user)
        token = r8.util.auth_sign.sign(user.encode()).decode()
        is_secure = not r8.settings["origin"].startswith("http://")
        resp = web.json_response({})
        resp.set_cookie(
            "token",
            token,
            path="/",
            max_age=31536000,
            samesite="strict",
            httponly=True,
            secure=is_secure,
        )
        return resp
    except (argon2.exceptions.VerificationError, ValueError):
        r8.log(request, "login-fail", user, uid=user if ok else None)
        return web.HTTPUnauthorized(reason="Invalid credentials.")


@routes.post("/logout")
async def logout(request: web.Request):
    resp = web.json_response({})
    resp.del_cookie("token")
    return resp


app = web.Application()
app.add_routes(routes)
