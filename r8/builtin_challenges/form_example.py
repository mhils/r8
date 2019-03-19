from aiohttp import web

import r8


class FormExample(r8.Challenge):
    title = "The Fabulous Form"

    async def description(self, user: str, solved: bool):
        return r8.util.media(
            None,
            """
            <h6>What's your favorite IP address?</h6>
            <form>
                <input class="form-control mb-1" name="ip" type="text" placeholder="0.0.0.0"/>
                <button class="btn btn-primary mb-1">Submit</button>
                <div class="response"></div>
            </form>
            """ + r8.util.challenge_form_js(self.id)
        )

    async def handle_post_request(self, user: str, request: web.Request):
        json = await request.json()
        if json.get("ip", "") == "127.0.0.1":
            return web.json_response({"message": self.log_and_create_flag(request, user)})
        else:
            return web.HTTPBadRequest(reason="There are better ones.")
