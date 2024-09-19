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

from femipc.femipc import Client, listener

from aiohttp import ClientSession

from scheduler.scheduler import Scheduler

from concurrent.futures import ThreadPoolExecutor
from PIL import Image

import asyncio
import hashlib
import io
import math
import ast
import os
import random

from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp.web import Application

BACKGROUND_SIZE = 1000, 1000
IMAGE_SIZE = 200, 200
BACKGROUNDS = os.listdir("./assets/captcha/backgrounds")
IMAGES = os.listdir("./assets/captcha/images")

def get_positions(x, y) -> list[tuple[int, int]]:
    x_start = math.floor(x / IMAGE_SIZE[0])
    y_start = math.floor(y / IMAGE_SIZE[1])

    x_end = math.floor((x + IMAGE_SIZE[0] - 1) / IMAGE_SIZE[0])
    y_end = math.floor((y + IMAGE_SIZE[1] - 1) / IMAGE_SIZE[1])

    positions = []

    for y in range(y_start, y_end + 1):
        for x in range(x_start, x_end + 1):
            positions.append((x, y))

    return positions

def get_random_position() -> tuple[int, int]:
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

async def generate_captcha(image1: io.BytesIO, image2: io.BytesIO, loop: asyncio.AbstractEventLoop) -> tuple[str, bytes]:
    async def async_create_image(image1: io.BytesIO, image2: io.BytesIO) -> tuple[Any]:
        future = loop.create_future()
        await loop.run_in_executor(ThreadPoolExecutor(), create_image, image1, image2, future)
        return await future

    positions, captcha = await loop.create_task(async_create_image(image1, image2))

    data = "".join([str(item) for item in sorted([int("%d%d" % (x, y)) for x, y in positions])])

    _hash = hashlib.sha256(data.encode()).hexdigest()

    return _hash, captcha

class IPC(Client):
    def __init__(self, app: "Application", path: str, peers: list[str]) -> None:
        super().__init__(path, peers)

        self.app = app
        self.scheduler = Scheduler()

        self.app.loop.create_task(self.create_schedules())

    async def create_schedules(self) -> None:
        await self.scheduler.create_schedule(self.update_cache, "10m", name="update_cache")()
        await self.scheduler.create_schedule(self.update_cogs, "1h", name="update_cogs")()

    async def update_cache(self) -> None:
        self.app.cache.default_prefix, self.app.cache.stats, self.app.cache.bot = await self.emit("get_cache")

    async def update_cogs(self) -> None:
        self.app.cache.cogs = await self.emit("get_cogs")

    def close(self) -> None:
        super().close()
        self.scheduler.task.cancel()

    def insert_returns(self, body: list) -> None:
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        if isinstance(body[-1], ast.If):
            self.insert_returns(body[-1].body)
            self.insert_returns(body[-1].orelse)

        if isinstance(body[-1], ast.With):
            self.insert_returns(body[-1].body)

    def _eval(self, code: str, env: Optional[dict[str, Any]] = None) -> asyncio.Future:
        env = {} or env

        content = "\n".join(f"    {x}" for x in code.splitlines())
        body = f"async def _eval():\n{content}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        self.insert_returns(body)

        exec(compile(parsed, filename="_eval", mode="exec"), env)

        return eval("_eval()", env)

    @listener("eval")
    async def on_eval(self, code: str) -> str:
        try:
            return str(await self._eval(code, {"app": self.app}))
        except Exception as exc:
            return str(exc)

    @listener("new_captcha")
    async def on_new_captcha(self, captcha: dict) -> None:
        captcha_id = hashlib.md5(f"{captcha["guild_id"]}:{captcha["user_id"]}".encode()).hexdigest()

        async with ClientSession() as session:
            async with session.get(captcha["guild_icon"]) as response:
                captcha["guild_icon"] = io.BytesIO(await response.content.read())
            async with session.get(captcha["user_avatar"]) as response:
                captcha["user_avatar"] = io.BytesIO(await response.content.read())

        _hash, captcha_image = await generate_captcha(captcha["guild_icon"], captcha["user_avatar"], self.app.loop)

        self.app.cache.captcha[captcha_id] = captcha | {"hash": _hash, "captcha": captcha_image}