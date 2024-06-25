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
import io

class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # @commands.Listener
    async def on_voice_server_update(self, data: dict) -> None:
        self.voice = await Player(self.bot, **data)

        with open("./assets/palion_zielone.raw", "rb") as file:
            data = file.read()

        self.voice.play(PCMAudio(io.BytesIO(data)))

def setup(bot: commands.Bot) -> None:
    bot.load_cog(Voice(bot))