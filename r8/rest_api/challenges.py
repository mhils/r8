import urllib.parse

from aiohttp import web

import r8
from .auth import authenticated

routes = web.RouteTableDef()


@routes.get("/")
@authenticated
async def get_challenges(user: str, request: web.Request):
    """Get the current challenge state."""
    r8.log(request, "get-challenges", request.headers.get("User-Agent"), uid=user)
    challenges = await r8.util.get_challenges(user)
    return web.json_response({
        "user": user,
        "team": r8.util.get_team(user),
        "challenges": challenges,
    })


@routes.post("/submit")
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


@routes.get("/{cid}{path:(/.*)?}")
@routes.post("/{cid}{path:(/.*)?}")
@authenticated
async def handle_challenge_request(user: str, request: web.Request):
    try:
        inst = r8.challenges[request.match_info["cid"]]
    except KeyError:
        return web.HTTPBadRequest(reason="Unknown challenge.")

    if request.method == "GET":
        resp = await inst.handle_get_request(user, request)
        if isinstance(resp, str):
            resp = web.json_response({"message": resp})
    else:
        path = (request.match_info["path"] + " ").lstrip()
        text = await request.text()
        if request.content_type == 'application/x-www-form-urlencoded':
            text = urllib.parse.unquote(text)
        data = path + text
        # We want this to appear before any challenge-specific logging...
        rowid = r8.log(request, "handle-request", data, uid=user, cid=inst.id)
        try:
            resp = await inst.handle_post_request(user, request)
            if isinstance(resp, str):
                resp = web.json_response({"message": resp})
            with r8.db:
                r8.db.execute("""UPDATE events SET data = ? WHERE ROWID = ?""",
                              (f"{data} -> {resp.status} {resp.reason}", rowid))
        except Exception as e:
            with r8.db:
                r8.db.execute("""UPDATE events SET data = ? WHERE ROWID = ?""",
                              (f"{data} -> {e}", rowid))
            raise

    return resp


app = web.Application()
app.add_routes(routes)
