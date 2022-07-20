"""
Copyright 2022 PoligonTeam

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

import asyncio, random, io
from PIL import Image, ImageDraw, ImageFont
from .client import Client

class Renderer:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.client: Client = None

        self.image = Image.new("RGB", (1920, 1080), (32, 32, 32))
        self.draw = ImageDraw.Draw(self.image)

        self.image_data = io.BytesIO()

    def update(self):
        self.image.paste((32, 32, 32), (0, 0) + self.image.size)

        for player in self.client.players + [self.client]:
            self.image.paste(Image.open(f"./korrumzthegame/assets/players/player{player.image_number}.png"), (player.x, player.y))
            font = ImageFont.truetype("./assets/fonts/HKNova-Medium.ttf", 15)
            self.draw.text((player.x, player.y - 25), player.username, (255, 255, 255), font=font)

        for bug in self.client.bugs:
            self.image.paste(Image.open(f"./korrumzthegame/assets/bugs/bug{bug.image_number}.png"), (bug.x, bug.y))

        self.image.save(self.image_data, "PNG")

    def get_image(self):
        image = self.image_data.getvalue()
        self.image_data = io.BytesIO()

        return image

    def start(self, username, image_number: int):
        self.client = Client(username, random.randint(0, 1920), random.randint(0, 1080), 0, image_number)
        self.loop.create_task(self.client.run())