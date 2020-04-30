import asyncio
import time
import weakref
from typing import List

import aiohttp
from aiohttp import web

import r8
from .auth import authenticated
from ..scoring import Scoreboard

scoreboards: List[Scoreboard] = [Scoreboard()]
ws_connections = weakref.WeakSet()


async def on_startup(app):
    scoreboards[0].timestamp = r8.settings.get("start", time.time())
    with r8.db:
        submissions = r8.db.execute("""
            SELECT tid, cid, CAST(strftime('%s',timestamp) AS INTEGER) AS timestamp FROM submissions
            NATURAL INNER JOIN flags
            NATURAL INNER JOIN teams
            ORDER BY TIMESTAMP
        """)
        for team, cid, timestamp in submissions:
            if team.startswith("_"):
                continue
            scoreboards.append(scoreboards[-1].solve(team, r8.challenges[cid], timestamp))
    if len(scoreboards) > 1:
        scoreboards[0].timestamp = min(scoreboards[0].timestamp, scoreboards[1].timestamp)
    r8.echo(
        "scoreboard",
        f"Processed {len(scoreboards) - 1} submission(s): {scoreboards[-1]}"
    )
    r8.util.on_submit.connect(on_solve)


def on_solve(sender, user, cid):
    team = r8.util.get_team(user)
    if team.startswith("_"):
        return
    scoreboards.append(scoreboards[-1].solve(team, r8.challenges[cid], time.time()))
    for ws in ws_connections:
        try:
            asyncio.create_task(ws.send_json(scoreboards[-1].to_json()))
        except ConnectionError:
            pass


async def on_shutdown(app):
    for ws in ws_connections:
        await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')


routes = web.RouteTableDef()


@routes.get('/state')
@authenticated
async def get_state(user: str, request: web.Request):
    if not r8.settings.get("scoring", False):
        return web.HTTPForbidden()
    challenges = await r8.util.get_challenges(user)

    return web.json_response({
        "teams": [t for t in r8.util.get_teams() if not t.startswith("_")],  # only show active teams: list(scoreboards[-1].scores.keys()),
        "challenges": challenges,
        "solves": {
            challenge["cid"]: scoreboards[-1].solves[challenge["cid"]]
            for challenge in challenges
        },
        "scoreboards": [x.to_json() for x in scoreboards]
    })


@routes.get('/updates')
@authenticated
async def get_updates(user: str, request: web.Request):
    if not r8.settings.get("scoring", False):
        return web.HTTPForbidden()
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    ws_connections.add(ws)
    # r8.echo('scoreboard', 'websocket connection opened')
    try:
        async for msg in ws:
            assert isinstance(msg, aiohttp.WSMessage)
            # this is here for debugging.
            if msg.type == aiohttp.WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    await ws.send_str(msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                r8.echo("scoreboard", f'ws connection closed with exception {ws.exception()}')
    finally:
        ws_connections.discard(ws)
        # r8.echo('scoreboard', 'websocket connection closed')
    return ws


app = web.Application()
app.add_routes(routes)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
