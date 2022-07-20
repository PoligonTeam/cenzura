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

from ..embed import Embed
from ..components import Components
from typing import Sequence

class Context:
    def __init__(self, bot, message):
        self.bot = bot
        self.bot_user = self.bot.gateway.bot_user

        self.guild = message.guild
        self.channel = message.channel
        self.message = message

        self.author = message.author
        self.member = message.member

        self.command = None
        self.arguments = []

    def __str__(self):
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)

    def __repr__(self):
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)

    async def send(self, content = None, *, embed: Embed = None, embeds: Sequence[Embed] = None, components: Components = None, files: list = None, mentions: list = [], other: dict = {}):
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)

    async def reply(self, content = None, *, embed: Embed = None, embeds: Sequence[Embed] = None, components: Components = None, files: list = None, mentions: list = [], other: dict = {}):
        other["message_reference"] = {"guild_id": self.guild.id, "channel_id": self.channel.id, "message_id": self.message.id}
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)