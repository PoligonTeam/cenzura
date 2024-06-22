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

from .extension import Command

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot
    from ..types import Guild, Channel, Member, User, Message

class Context:
    def __init__(self, bot: "Bot", message: "Message") -> None:
        self.bot: "Bot" = bot
        self.bot_user: User = self.bot.gateway.bot_user

        self.guild: Guild = message.guild
        self.channel: Channel = message.channel or message.thread

        if isinstance(self.channel, str):
            self.channel = self.guild.get_channel(self.channel)

        self.message: "Message" = message

        self.author: "User" = message.author
        self.member: "Member" = message.member

        self.command: Command = None
        self.arguments: List[str] = []
        self.error: Exception = None

        self.send = self.channel.send
        self.reply = self.channel.reply

    def __str__(self) -> None:
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)

    def __repr__(self) -> None:
        return "<Context guild={!r} channel={!r} message={!r} command={!r} arguments={!r}>".format(self.guild, self.channel, self.message, self.command, self.arguments)