import abc
from typing import Tuple

from aiohttp import web

import r8


class WebServerChallenge(r8.Challenge):
    runner: web.AppRunner = None

    @property
    @abc.abstractmethod
    def address(self) -> Tuple[str, int]:
        """The web server address"""
        pass

    @abc.abstractmethod
    def make_app(self) -> web.Application:
        raise NotImplementedError()

    async def start(self):
        self.echo("Starting server...")
        app = self.make_app()
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, *self.address)
        await site.start()
        self.echo(f"Running at {r8.util.format_address(self.address)}.")
        await super().start()

    async def stop(self):
        await super().stop()
        self.echo("Stopping server...")
        await self.runner.cleanup()
        self.echo("Stopped.")
