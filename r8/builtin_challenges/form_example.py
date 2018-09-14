from aiohttp import web

import r8


class FormExample(r8.Challenge):
    title = "The Fabulous Form"

    async def description(self, user: str, solved: bool):
        # Warning: The JavaScript code here does not run on old IE versions.
        return """
        <h6>What's your favorite IP address?</h6>
        <form>
            <input name="ip" type="text" placeholder="0.0.0.0"/>
            <button>Submit</button>
            <div class="response"></div>
        </form>
        <script>{ // make sure to add a block here so that `let` is scoped.
        let form = document.currentScript.previousElementSibling;
        let resp = form.querySelector(".response")
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            let post = {
                ip: form.querySelector("[name=ip]").value
            };
            fetchApi(
                "/api/challenges/%s", 
                {method: "POST", body: JSON.stringify(post)}
            ).then(json => {
                resp.textContent = JSON.stringify(json);
            }).catch(e => {
                resp.textContent = "Error: " + e;
            })
        });
        }</script>
        """ % self.id

    async def handle_request(self, user: str, request: web.Request):
        json = await request.json()
        if json.get("ip", "") == "127.0.0.1":
            return web.json_response({"flag": self.log_and_create_flag(request, log_uid=user)})
        else:
            return web.HTTPBadRequest(reason="There are better ones.")
