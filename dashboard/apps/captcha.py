"""
Copyright 2022-2024 PoligonTeam

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from aiohttp import web

router = web.RouteTableDef()

class Captcha:
    prefix = "/captcha"

    def __init__(self, root: web.Application) -> None:
        self.app = web.Application()
        self.app.root = root

        self.app.add_routes(router)

    @router.get("/{captcha_id}")
    async def captcha(request: web.Request) -> web.Response:
        captcha_id = request.match_info.get("captcha_id")

        if captcha_id not in request.app.root.cache.captcha:
            return web.HTTPNotFound()

        captcha = request.app.root.cache.captcha[captcha_id]

        return web.Response(body=captcha["captcha"], content_type="image/png")

    @router.post("/{captcha_id}")
    async def captcha(request: web.Request) -> web.Response:
        captcha_id = request.match_info.get("captcha_id")

        if captcha_id not in request.app.root.cache.captcha:
            return web.HTTPNotFound()

        captcha = request.app.root.cache.captcha[captcha_id]

        data = await request.json()
        _hash = data.get("hash")

        if not _hash:
            return web.HTTPBadRequest()

        if not _hash == captcha["hash"]:
            return web.HTTPBadRequest()

        await request.app.root.ipc.emit("add_role", captcha["guild_id"], captcha["user_id"], captcha["role_id"], nowait=True)

        del request.app.root.cache.captcha[captcha_id]

        return web.HTTPOk()

def get_app(root: web.Application) -> Captcha:
    return Captcha(root)