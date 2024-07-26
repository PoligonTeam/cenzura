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

class Bot:
    prefix = "/bot"

    def __init__(self, root: web.Application) -> None:
        self.app = web.Application()
        self.app.root = root

        self.app.add_routes(router)

    @router.get("")
    async def index(request: web.Request) -> web.Response:
        return web.json_response(request.app.root.cache.bot)
    
    @router.get("/stats")
    async def stats(request: web.Request) -> web.Response:
        return web.json_response(request.app.root.cache.stats)

    @router.get("/commands")
    async def commands(request: web.Request) -> web.Response:
        return web.json_response({
            "cogs": request.app.root.cache.cogs,
            "default_prefix": request.app.root.cache.default_prefix
        })

def get_app(root: web.Application) -> Bot:
    return Bot(root)