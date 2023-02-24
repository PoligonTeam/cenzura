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

from .extension import Command
from ..embed import Embed
from ..components import Components
from ..types import Guild, Channel, Member, User, Message, Sticker
from typing import Optional, Iterable, Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot

class Context:
    def __init__(self, bot: "Bot", message: Message):
        self.bot: "Bot" = bot
        self.bot_user: User = self.bot.gateway.bot_user

        self.guild: Guild = message.guild
        self.channel: Channel = message.channel or message.thread

        if isinstance(self.channel, str):
            self.channel = self.guild.get_channel(self.channel)

        self.message: Message = message

        self.author: User = message.author
        self.member: Member = message.member

        self.command: Command = None
        self.arguments: List[str] = []

    def __str__(self):
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)

    def __repr__(self):
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)

    async def send(self, content = None, *, embed: Optional[Embed] = None, embeds: Optional[List[Embed]] = None, components: Optional[Components] = None, files: Optional[List[Iterable[str]]] = None, mentions: list = [], stickers: Optional[List[Sticker]] = [], other: Dict[str, Any] = {}):
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

    async def reply(self, content = None, *, embed: Optional[Embed] = None, embeds: Optional[List[Embed]] = None, components: Optional[Components] = None, files: Optional[List[Iterable[str]]] = None, mentions: list = [], stickers: Optional[List[Sticker]] = [], other: Dict[str, Any] = {}):
        other["message_reference"] = {"guild_id": self.guild.id, "channel_id": self.channel.id, "message_id": self.message.id}
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)