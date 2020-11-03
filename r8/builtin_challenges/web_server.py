from aiohttp import web

import r8.challenge_mixins


class WebServer(r8.challenge_mixins.WebServerChallenge):
    title = "Embedded Web Application Example"
    address = ("", 8203)

    async def description(self, user: str, solved: bool):
        website_url = f"""http://{r8.util.get_host()}:{self.address[1]}/"""
        return r8.util.media(None, f"""
            <p>
            Hello World!
            </p>
            <a href="{website_url}">🌍 {website_url}</a>
            """)

    def make_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/", self.index)
        return app

    async def index(self, request: web.Request):
        return web.Response(text="Hello World.")
