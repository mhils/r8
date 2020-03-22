from aiohttp import web

from . import auth, challenges, scoreboard

app = web.Application()
app.add_subapp("/auth/", auth.app)
app.add_subapp("/challenges/", challenges.app)
app.add_subapp("/scoreboard/", scoreboard.app)
