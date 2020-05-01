from aiohttp import web

import r8
from . import auth, challenges, scoreboard


def make_app() -> web.Application:
    app = web.Application()
    app.add_subapp("/auth/", auth.app)
    app.add_subapp("/challenges/", challenges.app)
    if r8.settings.get("scoring", False):
        app.add_subapp("/scoreboard/", scoreboard.app)
    return app
