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

from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor
import os
import io
import math
import asyncio

from typing import TypedDict

class Character(TypedDict):
    name: str
    color: int
    images: list[str]
    pregen_showcase: bytes

class StickerNotFound(Exception):
    pass

class Sticker:
    PATH = "./assets/stickers"
    FONT_PATH = "./assets/fonts/YurukaStd.woff2"

    def __init__(self, image: str) -> None:
        dr = image.split("_")[0]

        if not os.path.exists(Sticker.PATH + f"/{dr}/{image}.png"):
            raise StickerNotFound

        color_path = Sticker.PATH + f"/{dr}/color"

        self.loop = asyncio.get_event_loop()

        self.image = image
        self.path = Sticker.PATH + f"/{dr}/{image}.png"

        with open(color_path, "rb") as file:
            r, g, b = file.read()
            self.color = r, g, b

        self._data = io.BytesIO()

        self._pos: tuple[int, int] = 0, 0
        self._angle = 0
        self._text = ""
        self._text_size = 45

    def move_text(self, x: int, y: int) -> None:
        self._pos = self._pos[0] + x, self._pos[1] + y

    def rotate_text(self, angle: int) -> None:
        self._angle = angle % 360

    def set_text(self, text: str) -> None:
        self._text = text

    def set_text_size(self, text_size: int) -> None:
        if text_size <= 0:
            return

        self._text_size = text_size

    def _generate(self) -> None:
        image = Image.open(self.path)
        draw = ImageDraw.Draw(image)

        font = ImageFont.truetype(Sticker.FONT_PATH, self._text_size)

        _, _, text_width, text_height = font.getbbox(self._text, stroke_width=5)
        text_image = Image.new("RGBA", (text_width + 10, text_height + 10), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_image)

        x = text_image.width // 2 - text_width // 2
        y = text_image.height // 2 - text_height // 2

        draw.text((x - 1, y), self._text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
        draw.text((x + 1, y), self._text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
        draw.text((x, y - 1), self._text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
        draw.text((x, y + 1), self._text, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(255, 255, 255, 255), font=font)
        draw.text((x, y), self._text, fill=self.color, font=font)

        if self._angle != 0:
            text_image = text_image.rotate(self._angle, resample=Image.BICUBIC, expand=True)

        image.paste(text_image, (image.width // 2 - text_image.width // 2 + self._pos[0], 30 + self._pos[1]), mask=text_image.split()[3])

        image.save(self._data, format="PNG")

    async def render(self) -> None:
        await self.loop.run_in_executor(ThreadPoolExecutor(), self._generate)

    async def generate(self) -> bytes:
        await self.loop.create_task(self.render())
        data = self._data.getvalue()
        self._data = io.BytesIO()
        return data

    @staticmethod
    def get_characters() -> list[Character]:
        characters: list[Character] = []

        for dr in os.listdir(Sticker.PATH):
            if dr == "pregen.py":
                continue

            character = Character(name=dr, color=0, images=[], pregen_showcase=b"")

            for file in os.listdir(Sticker.PATH + "/" + dr):
                if file == "color":
                    with open(Sticker.PATH + f"/{dr}/color", "rb") as f:
                        r, g, b = f.read()
                        character["color"] = (r << 16) | (g << 8) | b
                        continue
                elif file == "pregen.png":
                    continue
                character["images"].append(file.split(".")[0])

            with open(Sticker.PATH + f"/{dr}/pregen.png", "rb") as f:
                character["pregen_showcase"] = f.read()

            characters.append(character)

        return characters