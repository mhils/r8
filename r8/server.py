import time

import aiohttp_jinja2
import jinja2
from aiohttp import web

import r8
from . import rest_api


async def render_template(request):
    return aiohttp_jinja2.render_template(
        request.match_info["filename"] or "index.html",
        request,
        {"r8": r8, "time": time}
    )


async def serve_static(request: web.Request):
    return r8.util.serve_static(r8.settings["static_dir"], request.match_info["path"])


def make_app() -> web.Application:
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(r8.settings["static_dir"]))
    app.add_subapp("/api/", rest_api.make_app())
    app.router.add_get('/{filename:(\\w+\\.html)?}', render_template)
    app.router.add_get('/{path:.+}', serve_static)
    return app


runner: web.AppRunner


async def start():
    global runner
    r8.echo("r8", "Starting server...")
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, r8.settings["host"], r8.settings["port"])
    await site.start()
    address = r8.util.format_address((r8.settings["host"], r8.settings["port"]))
    r8.echo("r8", f"Running at {address}.")
    return runner


async def stop():
    r8.echo("r8", "Stopping server...")
    await runner.cleanup()
    r8.echo("r8", "Stopped.")
