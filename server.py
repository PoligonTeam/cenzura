"""
Copyright 2022 PoligonTeam

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing per`mi`ssions and
limitations under the License.
"""

import asyncio, socket, struct, base64, hmac, hashlib, json, os, time, logging, config
from aiohttp import web, abc, ClientSession
from scheduler.scheduler import Scheduler
from enum import Enum
from typing import Union, List, Tuple, Sequence

logging.basicConfig(level=logging.DEBUG)

DISCORD_API = "https://discord.com/api/v10"

EPOCH = 1626559200

def to_url_safe(string: str) -> str:
    return string.replace("+", "-").replace("/", "_").replace("=", "")

def from_url_safe(string: str) -> str:
    return string.replace("-", "+").replace("_", "/")

def to_base64(data: Union[bytes, str]) -> str:
    if isinstance(data, str):
        data = data.encode()

    return to_url_safe(base64.b64encode(data).decode())

def from_base64(data: str) -> bytes:
    return base64.b64decode(from_url_safe(data + "=" * (len(data) % 4)))

class Opcodes(Enum):
    COGS = 1
    COMMANDS = 2
    DEFAULT_PREFIX = 3
    STATS = 4
    BOT = 5

class Cache:
    def __init__(self) -> None:
        self.cogs: List[dict] = []
        self.default_prefix: str = None
        self.stats: dict = None
        self.bot: dict = None
        self.tokens: List[Tuple[str, str]] = []

class AccessLogger(abc.AbstractAccessLogger):
    def log(self, request: web.Request, response: web.Response, time: float) -> None:
        self.logger.info(f"{request.headers.get('CF-Connecting-IP')} {request.method} {request.path} {response.status}")

router = web.RouteTableDef()

class Verify(web.View):
    async def get(self) -> web.Response:
        guild_id = self.request.match_info["guild_id"]
        token = self.request.match_info["token"]

        if token != "sex":
            return web.json_response({"error": "Invalid token"}, status=401)

        return web.json_response({"success": True})

    async def post(self) -> web.Response:
        guild_id = self.request.match_info["guild_id"]
        token = self.request.match_info["token"]

        if token != "10000000-aaaa-bbbb-cccc-000000000001":
            return web.json_response({"error": "Invalid token"}, status=401)

        return web.json_response({"success": True})

class Server(web.Application):
    def __init__(self) -> None:
        super().__init__()

        self.session: ClientSession = None

        self.scheduler: Scheduler = None
        self.cache = Cache()

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        if os.path.exists(config.DASHBOARD_SOCKET_PATH):
            os.remove(config.DASHBOARD_SOCKET_PATH)
        self.socket.bind(config.DASHBOARD_SOCKET_PATH)
        self.send_packets(Opcodes.BOT, Opcodes.STATS, Opcodes.DEFAULT_PREFIX, Opcodes.COGS)

        self.middlewares.append(self.middleware)
        self.add_routes(router)
        self.router.add_view("/verify/{guild_id}/{token}", Verify)

    async def run(self, *, host: str, port: int) -> None:
        runner = web.AppRunner(self, access_log_class=AccessLogger)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        self.session = ClientSession()

        self.scheduler = Scheduler(check_interval=0.1)

        self.scheduler.create_schedule(self.socket_handler, "0s", name="socket_handler")
        self.scheduler.create_schedule(self.update_cache, "1h", name="update_cache")
        self.scheduler.create_schedule(self.update_stats, "10m", name="update_stats")

    def send_packets(self, *ops: Sequence[Opcodes]) -> None:
        for op in ops:
            self.socket.sendto(struct.pack("<I", op.value), config.FEMBOT_SOCKET_PATH)

    async def socket_handler(self) -> None:
        try:
            data, _ = self.socket.recvfrom(8)
            op, length = struct.unpack("<II", data)
            op = Opcodes(op)
            data, _ = self.socket.recvfrom(length)
            data = json.loads(data)

            if op is Opcodes.COGS:
                if data["index"] + 1 == data["cogs_count"]:
                    self.send_packets(Opcodes.COMMANDS)

                for element in ("index", "cogs_count", "commands_count"):
                    data.pop(element)

                self.cache.cogs.append(data)
            elif op is Opcodes.COMMANDS:
                for cog in self.cache.cogs:
                    if cog["name"] == data["cog"]:
                        if data["guild_id"] is None:
                            for element in ("index", "commands_count"):
                                data.pop(element)

                            cog["commands"].append(data)
            elif op is Opcodes.DEFAULT_PREFIX:
                self.cache.default_prefix = data["default_prefix"]
            elif op is Opcodes.STATS:
                self.cache.stats = data
            elif op is Opcodes.BOT:
                self.cache.bot = data

            logging.info(f"Received {op.name} from {self.cache.bot['username']}")
        except socket.error:
            pass

    async def update_cache(self) -> None:
        self.cache.cogs = []
        self.send_packets(Opcodes.BOT, Opcodes.DEFAULT_PREFIX, Opcodes.COGS)

    async def update_stats(self) -> None:
        self.send_packets(Opcodes.STATS)

    def close(self) -> None:
        self.scheduler.task.cancel()
        self.socket.close()

    @classmethod
    def generate_token(cls, user_id: str, timestamp: int, secret_key: str) -> str:
        return "{}.{}.{}".format(
            to_base64(user_id),
            to_base64(struct.pack(">I", timestamp - EPOCH)),
            hmac.new(secret_key.encode(), f"{user_id}.{timestamp}".encode(), hashlib.sha256).hexdigest()[:38]
        )

    @classmethod
    def verify_token(cls, token: str, secret_key: str) -> Tuple[str, int]:
        try:
            user_id, timestamp, signature = token.split(".")
            user_id = from_base64(user_id).decode()
            timestamp = struct.unpack(">I", from_base64(timestamp))[0] + EPOCH
            if hmac.new(secret_key.encode(), f"{user_id}.{timestamp}".encode(), hashlib.sha256).hexdigest()[:38] == signature:
                return user_id, timestamp
        except (ValueError, struct.error):
            pass

        return None, None

    @web.middleware
    async def middleware(self, request: web.Request, handler: web.RequestHandler) -> web.Response:
        response = await handler(request)

        response.headers["Access-Control-Allow-Origin"] = "*"

        return response

    @router.get("/")
    async def index(request: web.Request) -> web.Response:
        return web.json_response(request.app.cache.bot)

    @router.get("/login")
    async def login(request: web.Request) -> web.Response:
        return web.HTTPFound(
            DISCORD_API + "/oauth2/authorize?client_id={}&scope=identify&response_type=code&redirect_uri={}".format(
                config.CLIENT_ID,
                config.REDIRECT_URI
            )
        )

    @router.get("/callback")
    async def callback(request: web.Request) -> web.Response:
        code = request.query.get("code")

        if code is None:
            return web.HTTPBadRequest()

        async with request.app.session.post(
            DISCORD_API + "/oauth2/token",
            headers = {
                "content-type": "application/x-www-form-urlencoded"
            },
            data = {
                "client_id": config.CLIENT_ID,
                "client_secret": config.CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.REDIRECT_URI
            }
        ) as response:
            if response.status != 200:
                return web.HTTPBadRequest()

            data = await response.json()

            if "access_token" not in data:
                return web.HTTPBadRequest()

            access_token = data["access_token"]

            async with request.app.session.get(
                DISCORD_API + "/users/@me",
                headers = {
                    "authorization": "Bearer " + access_token
                }
            ) as response:
                if response.status != 200:
                    return web.HTTPBadRequest()

                data = await response.json()

                if "id" not in data:
                    return web.HTTPBadRequest()

                user_id = data["id"]

        token = request.app.generate_token(user_id, int(time.time()), access_token)

        request.app.cache.tokens.append((token, access_token))

        return web.json_response({
            "token": token
        })

    @router.post("/checktoken")
    async def checktoken(request: web.Request) -> web.Response:
        token = request.headers.get("authorization")

        if token is None:
            return web.HTTPBadRequest()

        access_token = None

        for user_token, access_token in request.app.cache.tokens:
            if user_token == token:
                break

        if access_token is None:
            return web.HTTPUnauthorized()

        user_id, timestamp = request.app.verify_token(token, access_token)

        if user_id is None or timestamp is None:
            return web.HTTPUnauthorized()

        if timestamp < time.time() - 60 * 60 * 24:
            request.app.cache.tokens.remove((token, access_token))
            return web.HTTPUnauthorized()

        async with request.app.session.get(
            DISCORD_API + "/users/@me",
            headers = {
                "authorization": "Bearer " + access_token
            }
        ) as response:
            if response.status != 200:
                request.app.cache.tokens.remove((token, access_token))
                return web.HTTPUnauthorized()

            data = await response.json()

            if "id" not in data:
                request.app.cache.tokens.remove((token, access_token))
                return web.HTTPUnauthorized()

            if data["id"] != user_id:
                request.app.cache.tokens.remove((token, access_token))
                return web.HTTPUnauthorized()

        return web.json_response({
            "user_id": user_id,
            "timestamp": timestamp
        })

    @router.get("/stats")
    async def stats(request: web.Request) -> web.Response:
        return web.json_response({
            **request.app.cache.stats,
            "last_update": time.time()
        })

    @router.get("/commands")
    async def commands(request: web.Request) -> web.Response:
        return web.json_response({
            "cogs": request.app.cache.cogs,
            "default_prefix": request.app.cache.default_prefix
        })

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.create_task((server := Server()).run(host=config.DASHBOARD_HOST, port=config.DASHBOARD_PORT))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.close()