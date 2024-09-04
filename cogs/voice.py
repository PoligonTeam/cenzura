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

import femcord.femcord as femcord
from femcord.femcord import commands
from femcord.femcord.voice import Player, PCMAudio
import math, numpy, io

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot

class Voice(commands.Cog):
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    # @commands.Listener
    async def on_voice_server_update(self, data: dict) -> None:
        self.voice = await Player(self.bot, **data)

        with open("./assets/palion_zielone.raw", "rb") as file:
            content = file.read()

        # content = numpy.array([math.sin(2 * math.pi * x * (174.61 + math.sin(x)) / 48000) for x in range(48000 * 60 * 2)], dtype=numpy.float32)
        # content = numpy.int16(content * 32767).tobytes()

        self.voice.play(PCMAudio(io.BytesIO(content)))

def setup(bot: "Bot") -> None:
    bot.load_cog(Voice(bot))