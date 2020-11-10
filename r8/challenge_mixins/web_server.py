import abc
from typing import Callable, Union

from aiohttp import web
from aiohttp.web import StaticResource, middleware

import r8


def log_nonstatic(request: web.Request) -> bool:
    return not isinstance(getattr(request.match_info.handler, "__self__", None), StaticResource)


def log_nonsafe(request: web.Request) -> bool:
    return request.method not in ("GET", "HEAD", "OPTIONS", "TRACE")


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

        req_str = f"{request.method} {request.path_qs}"
        # We want this to appear before any challenge-specific logging...
        rowid = r8.log(request, "handle-request", req_str, cid=challenge.id)

        resp_str: str = ""
        try:
            resp = await handler(request)
            resp_str = f"{resp.status} {resp.reason}"
        except Exception as e:
            resp_str = f"{e}"
            raise
        else:
            return resp
        finally:
            req_text: str = ""
            try:
                if request._post is not None or request.content_type in (
                        "application/x-www-form-urlencoded",
                        "multipart/form-data"
                ):
                    req_data = await request.post()
                    req_text = "&".join(f"{k}={v}" for k, v in req_data.items())
                else:
                    req_text = await request.text()
                req_text = req_text[:1024]
            except Exception as e:
                req_text = req_text or f"{e}"
            req_str = f"{req_str} {req_text}".rstrip()
            with r8.db:
                r8.db.execute("""UPDATE events SET data = ? WHERE ROWID = ?""",
                              (f"{req_str} -> {resp_str}", rowid))

    return log_request
