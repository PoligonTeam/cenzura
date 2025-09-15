"""
Copyright 2022-2025 PoligonTeam

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

import asyncio
import jwt
import os
import sys
import importlib.util
import logging
import config

from scheduler.scheduler import Scheduler, TempDict

from aiohttp import web, abc, ClientSession

from datetime import datetime, timedelta, UTC

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

from .ipc import IPC

logging.basicConfig(level=logging.DEBUG)

PATH = os.path.dirname(os.path.realpath(__file__))

FRONTEND_URL = "https://cenzura.poligon.lgbt"
API_URL = "https://cenzura-api.poligon.lgbt"
DISCORD_API = "https://discord.com/api/v10"
EPOCH = 1626559200

PUBLIC_KEY = "234531ebcd68b50ec442212248b412b8c9fa3f0d6b1d0ee4ad29da05ac693cad"
verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

class Cache:
    def __init__(self) -> None:
        self.scheduler = Scheduler()
        self.cogs: list[dict] = []
        self.default_prefix: str = None
        self.stats: dict = None
        self.bot: dict = None
        self.tokens: list[tuple[str, str]] = []
        self.captcha: dict[str, dict] = TempDict(self.scheduler, "10m")

class AccessLogger(abc.AbstractAccessLogger):
    def log(self, request: web.Request, response: web.Response, time: float) -> None:
        self.logger.info(f"{request.headers.get('CF-Connecting-IP')} {request.method} {request.path} {response.status}")

router = web.RouteTableDef()

class Server:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.app = web.Application(loop=loop)

        self.app.cache = Cache()

        self.app.ipc = IPC(self.app, config.DASHBOARD_SOCKET_PATH, [config.FEMBOT_SOCKET_PATH])

        self.app.middlewares.append(self.middleware)
        self.app.add_routes(router)

        for file in os.listdir(PATH + "/apps"):
            if file[-3:] != ".py":
                continue

            spec = importlib.util.spec_from_file_location(file[:-3], PATH + "/apps/" + file)
            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

            sys.modules[file[:-3]] = module

            @module.router.options(r"/{_:.*}")
            async def options(request: web.Request) -> web.Response:
                return web.Response(headers={"Access-Control-Allow-Headers": "Content-Type,authorization", "Access-Control-Allow-Methods": "GET,POST,PATCH,PUT,DELETE"})

            subapp = module.get_app(self.app)

            self.app.add_subapp(subapp.prefix, subapp.app)

    async def run(self, *, host: str, port: int) -> None:
        runner = web.AppRunner(self.app, access_log_class=AccessLogger)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

    def close(self) -> None:
        self.app.ipc.close()

    @web.middleware
    async def middleware(self, request: web.Request, handler: web.RequestHandler) -> web.Response:
        if request.method == "OPTIONS":
            response = web.Response(status=200)
        else:
            response: web.Response = await handler(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Expose-Headers"] = "Content-Length"

        return response

    @router.options(r"/{_:.*}")
    async def options(request: web.Request) -> web.Response:
        return web.Response(headers={"Access-Control-Allow-Headers": "Content-Type,authorization", "Access-Control-Allow-Methods": "GET,POST,PATCH,PUT,DELETE"})

    @router.get(r"/{route:stats|commands}")
    async def reroute(request: web.Request) -> web.Response:
        return web.HTTPFound("/bot/" + request.match_info.get("route"))

    @router.post("/callback")
    async def callback(request: web.Request) -> web.Response:
        data = await request.json()
        code = data.get("code")

        if code is None:
            return web.HTTPBadRequest()

        async with ClientSession() as session:
            async with session.post(
                DISCORD_API + "/oauth2/token",
                headers = {
                    "content-type": "application/x-www-form-urlencoded"
                },
                data = {
                    "client_id": config.CLIENT_ID,
                    "client_secret": config.CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "http://localhost:5173/callback"
                }
            ) as response:
                if response.status != 200:
                    return web.HTTPBadRequest()

                oauth = await response.json()

                if "access_token" not in oauth:
                    return web.HTTPBadRequest()

            async with session.get(
                DISCORD_API + "/users/@me",
                headers = {
                    "authorization": "Bearer " + oauth["access_token"]
                }
            ) as response:
                if response.status != 200:
                    return web.HTTPBadRequest()

                user = await response.json()

                if "id" not in user:
                    return web.HTTPBadRequest()

        token = jwt.encode({"user_id": user["id"], "exp": datetime.now(UTC) + timedelta(days=7)}, config.JWT_SECRET, "HS256")

        return web.json_response({"token": token})

    @router.post("/webhook")
    async def webhook(request: web.Request) -> web.Response:
        try:
            signature = request.headers["X-Signature-Ed25519"]
            timestamp = request.headers["X-Signature-Timestamp"]

            verify_key.verify(f"{timestamp}{(await request.read()).decode()}".encode(), bytes.fromhex(signature))
        except BadSignatureError:
            return web.HTTPUnauthorized()

        data = await request.json()

        if "event" not in data or "type" not in data["event"]:
            print("Invalid webhook data:", data)
            return web.HTTPBadRequest()

        if data["event"]["type"] == "APPLICATION_AUTHORIZED" and "integration_type" in data["event"]["data"]:
            await request.app.ipc.emit("webhook_event", data["event"]["data"])

        return web.HTTPNoContent()