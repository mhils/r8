import abc
import urllib.parse
from typing import Union, Callable

from aiohttp import web
from aiohttp.web import StaticResource, middleware

import r8


def log_nonstatic(request: web.Request) -> bool:
    return not isinstance(request.match_info.handler.__self__, StaticResource)


class WebServerChallenge(r8.Challenge):
    runner: web.AppRunner = None
    log_web_requests: Union[bool, Callable[[web.Request], bool]] = lambda self, x: log_nonstatic(x)

    @property
    @abc.abstractmethod
    def address(self) -> tuple[str, int]:
        """The web server address"""
        pass

    @abc.abstractmethod
    def make_app(self) -> web.Application:
        raise NotImplementedError()

    async def start(self) -> None:
        self.echo("Starting server...")
        app = self.make_app()
        if self.log_web_requests:
            app.middlewares.append(make_logger(self))
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, *self.address)
        await site.start()
        self.echo(f"Running at {r8.util.format_address(self.address)}.")
        await super().start()

    async def stop(self) -> None:
        await super().stop()
        self.echo("Stopping server...")
        await self.runner.cleanup()
        self.echo("Stopped.")


def make_logger(challenge: WebServerChallenge):
    @middleware
    async def log_request(request: web.Request, handler):
        if isinstance(challenge.log_web_requests, bool):
            should_log = challenge.log_web_requests
        else:
            should_log = challenge.log_web_requests(request)
        if not should_log:
            return await handler(request)

        text = await request.text()
        if request.content_type == 'application/x-www-form-urlencoded':
            text = urllib.parse.unquote(text)
        data = f"{request.method} {request.path_qs} {text}".rstrip()
        # We want this to appear before any challenge-specific logging...
        rowid = r8.log(request, "handle-request", data, cid=challenge.id)
        try:
            resp = await handler(request)
            with r8.db:
                r8.db.execute("""UPDATE events SET data = ? WHERE ROWID = ?""",
                              (f"{data} -> {resp.status} {resp.reason}", rowid))
        except Exception as e:
            with r8.db:
                r8.db.execute("""UPDATE events SET data = ? WHERE ROWID = ?""",
                              (f"{data} -> {e}", rowid))
            raise
        else:
            return resp

    return log_request
