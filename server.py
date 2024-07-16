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

import asyncio, socket, struct, base64, hmac, hashlib, json, os, math, io, random, time, logging, config
from aiohttp import web, abc, ClientSession
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from scheduler.scheduler import Scheduler
from enum import Enum
from typing import Union, List, Tuple, Sequence, Any

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

BACKGROUND_SIZE = 1000, 1000
IMAGE_SIZE = 200, 200
BACKGROUNDS = os.listdir("./assets/captcha/backgrounds")
IMAGES = os.listdir("./assets/captcha/images")

def get_positions(x, y) -> List[Tuple[int, int]]:
    x_start = math.floor(x / IMAGE_SIZE[0])
    y_start = math.floor(y / IMAGE_SIZE[1])

    x_end = math.floor((x + IMAGE_SIZE[0] - 1) / IMAGE_SIZE[0])
    y_end = math.floor((y + IMAGE_SIZE[1] - 1) / IMAGE_SIZE[1])

    positions = []

    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            positions.append((x, y))

    return positions

def get_random_position() -> Tuple[int, int]:
    return random.randint(0, BACKGROUND_SIZE[0] - IMAGE_SIZE[1]), random.randint(0, BACKGROUND_SIZE[1] - IMAGE_SIZE[1])

def get_random_background() -> str:
    return "./assets/captcha/backgrounds/" + random.choice(BACKGROUNDS)

def get_random_image() -> str:
    return "./assets/captcha/images/" + random.choice(IMAGES)

def create_image(image1: io.BytesIO, image2: io.BytesIO, future: asyncio.Future) -> None:
    image = Image.open(get_random_background()).resize(BACKGROUND_SIZE, Image.Resampling.LANCZOS)

    image1 = Image.open(image1).convert("RGB").resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
    image2 = Image.open(image2).convert("RGB").resize(IMAGE_SIZE, Image.Resampling.LANCZOS)

    for _ in range(4):
        random_image = Image.open(get_random_image()).convert("RGB").resize(IMAGE_SIZE, Image.Resampling.LANCZOS)
        x, y = get_random_position()
        image.paste(random_image, (x, y))

    x1, y1 = get_random_position()
    x2, y2 = get_random_position()

    if x1 / 200 % 1 > 0.85 or x1 / 200 % 1 < 0.15:
        x1 = round(x1 / 200) * 200
    if y1 / 200 % 1 > 0.85 or y1 / 200 % 1 < 0.15:
        y1 = round(y1 / 200) * 200
    if x2 / 200 % 1 > 0.85 or x2 / 200 % 1 < 0.15:
        x1 = round(x1 / 200) * 200
    if y2 / 200 % 1 > 0.85 or y2 / 200 % 1 < 0.15:
        y2 = round(y2 / 200) * 200

    image.paste(image1, (x1, y1))
    image.paste(image2, (x2, y2))

    captcha = io.BytesIO()
    image.save(captcha, "PNG")

    future.set_result(
        (
            list(set(get_positions(x1, y1) + get_positions(x2, y2))),
            captcha.getvalue()
        )
    )

async def generate_captcha(image1: io.BytesIO, image2: io.BytesIO) -> Tuple[str, bytes]:
    async def async_create_image(image1: io.BytesIO, image2: io.BytesIO) -> Tuple[Any]:
        future = loop.create_future()
        await loop.run_in_executor(ThreadPoolExecutor(), create_image, image1, image2, future)
        return await future

    positions, captcha = await loop.create_task(async_create_image(image1, image2))

    data = "".join([str(item) for item in sorted([int("%d%d" % (x, y)) for x, y in positions])])

    _hash = hashlib.sha256(data.encode()).hexdigest()

    return _hash, captcha

class Opcodes(Enum):
    COGS = 1
    COMMANDS = 2
    DEFAULT_PREFIX = 3
    STATS = 4
    BOT = 5
    CAPTCHA = 6

class Cache:
    def __init__(self) -> None:
        self.cogs: List[dict] = []
        self.default_prefix: str = None
        self.stats: dict = None
        self.bot: dict = None
        self.tokens: List[Tuple[str, str]] = []
        self.captcha: Dict[str, dict] = {}

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

        for opcode in (Opcodes.BOT, Opcodes.STATS, Opcodes.DEFAULT_PREFIX, Opcodes.COGS):
            self.send_packet(opcode, {})

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

    def send_packet(self, op: Opcodes, data: dict) -> None:
        data = json.dumps(data, separators=(",", ":")).encode()
        header_data = struct.pack("<II", op.value, len(data))

        self.socket.sendto(header_data, config.FEMBOT_SOCKET_PATH)
        self.socket.sendto(data, config.FEMBOT_SOCKET_PATH)

    async def socket_handler(self) -> None:
        try:
            data, _ = self.socket.recvfrom(8)
            op, length = struct.unpack("<II", data)
            op = Opcodes(op)
            data, _ = self.socket.recvfrom(length)
            data = json.loads(data)

            if op is Opcodes.COGS:
                if data["index"] + 1 == data["cogs_count"]:
                    self.send_packet(Opcodes.COMMANDS, {})

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
            elif op is Opcodes.CAPTCHA:
                captcha_id = hashlib.md5(f"{data["guild_id"]}:{data["user_id"]}".encode()).hexdigest()

                async with ClientSession() as session:
                    async with session.get(data["guild_icon"]) as response:
                        data["guild_icon"] = io.BytesIO(await response.content.read())
                    async with session.get(data["user_avatar"]) as response:
                        data["user_avatar"] = io.BytesIO(await response.content.read())

                _hash, captcha = await generate_captcha(data["guild_icon"], data["user_avatar"])

                self.cache.captcha[captcha_id] = data | {"hash": _hash, "captcha": captcha}

            logging.info(f"Received {op.name} from {self.cache.bot['username']}")
        except socket.error:
            pass

    async def update_cache(self) -> None:
        self.cache.cogs = []

        for opcode in (Opcodes.BOT, Opcodes.DEFAULT_PREFIX, Opcodes.COGS):
            self.send_packet(opcode, {})

    async def update_stats(self) -> None:
        self.send_packet(Opcodes.STATS, {})

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

        # async with request.app.session.get(
        #     DISCORD_API + "/users/@me",
        #     headers = {
        #         "authorization": "Bearer " + access_token
        #     }
        # ) as response:
        #     if response.status != 200:
        #         request.app.cache.tokens.remove((token, access_token))
        #         return web.HTTPUnauthorized()

        #     data = await response.json()

        #     if "id" not in data:
        #         request.app.cache.tokens.remove((token, access_token))
        #         return web.HTTPUnauthorized()

        #     if data["id"] != user_id:
        #         request.app.cache.tokens.remove((token, access_token))
        #         return web.HTTPUnauthorized()

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

    @router.options("/captcha/{captcha_id}")
    async def captcha(request: web.Request) -> web.Response:
        return web.Response(headers={"Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "GET,POST"})

    @router.get("/captcha/{captcha_id}")
    async def captcha(request: web.Request) -> web.Response:
        captcha_id = request.match_info.get("captcha_id")

        if not captcha_id in request.app.cache.captcha:
            return web.Response(status=404)

        captcha = request.app.cache.captcha[captcha_id]

        return web.Response(body=captcha["captcha"], content_type="image/png")

    @router.post("/captcha/{captcha_id}")
    async def captcha(request: web.Request) -> web.Response:
        captcha_id = request.match_info.get("captcha_id")

        if not captcha_id in request.app.cache.captcha:
            return web.Response(status=404)

        captcha = request.app.cache.captcha[captcha_id]

        data = await request.json()
        _hash = data.get("hash")

        if not _hash:
            return web.Response(status=400)

        if not _hash == captcha["hash"]:
            return web.Response(status=400)

        request.app.send_packet(Opcodes.CAPTCHA, {
            "guild_id": captcha["guild_id"],
            "user_id": captcha["user_id"],
            "role_id": captcha["role_id"]
        })

        del request.app.cache.captcha[captcha_id]

        return web.Response(status=200)

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