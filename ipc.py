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

from femipc.femipc import Client, listener

from femcord import femcord

from femcord.femcord.http import HTTPException

from femcord.femcord.utils import get_index

from models import Guilds

import hashlib
import config
import aiohttp

from typing import TypedDict, NotRequired, TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot
    from femcord.femcord.types import Guild

class UserDict(TypedDict):
    id: str
    username: str
    avatar: str
    global_name: NotRequired[str]

class ChannelDict(TypedDict):
    id: str
    name: str

class RoleDict(TypedDict):
    id: str
    name: str

class GuildDict(TypedDict):
    id: str
    name: str
    icon: str
    channels: list[ChannelDict]
    roles: list[RoleDict]

class Event(TypedDict):
    integration_type: int
    user: UserDict
    scopes: list[str]
    guild: NotRequired[GuildDict]

class IPC(Client):
    def __init__(self, bot: "Bot", path: str, peers: list[str]) -> None:
        super().__init__(path, peers)

        self.bot = bot

    def user_has_permissions(self, guild: "Guild", user_id: str) -> bool:
        if user_id in (member.user.id for member in guild.members):
            index = get_index(guild.members, user_id, key=lambda m: m.user.id)
            member = guild.members[index]

            return guild.owner.user.id == user_id or member.permissions.has("ADMINISTRATOR")

        return False

    def guild_to_dict(self, guild: "Guild") -> GuildDict:
        return GuildDict(
            id = guild.id,
            name = guild.name,
            icon = guild.icon,
            channels = [
                ChannelDict(
                    id = channel.id,
                    name = channel.name
                )
                for channel in guild.channels
            ],
            roles = [
                RoleDict(
                    id = role.id,
                    name = role.name
                )
                for role in guild.roles
            ]
        )

    @listener("get_cogs")
    async def get_cogs(self) -> list[dict]:
        cogs = []

        for cog in self.bot.cogs:
            commands = []

            for command in cog.walk_commands():
                if command.guild_id is not None:
                    continue

                usage = []

                if command.usage is not None:
                    arguments = command.usage.split(" ")

                    for argument in arguments:
                        if argument[0] == "(":
                            usage.append([argument[1:-1], 0])
                        elif argument[0] == "[":
                            usage.append([argument[1:-1], 1])

                commands.append({
                    "type": command.type.value,
                    "parent": command.parent,
                    "cog": command.cog.name,
                    "name": command.name,
                    "description": command.description,
                    "usage": usage,
                    "enabled": command.enabled,
                    "hidden": command.hidden,
                    "aliases": command.aliases,
                    "guild_id": command.guild_id
                })

            cogs.append({
                "name": cog.name,
                "description": cog.description,
                "hidden": cog.hidden,
                "commands_count": len(cog.walk_commands()),
                "commands": commands
            })

        return cogs

    @listener("get_cache")
    async def get_cache(self) -> tuple:
        return config.PREFIX, await self.bot.get_stats(), {
            "id": self.bot.gateway.bot_user.id,
            "username": self.bot.gateway.bot_user.username,
            "avatar": self.bot.gateway.bot_user.avatar
        }

    @listener("add_role")
    async def add_role(self, guild_id: str, user_id: str, role_id: str) -> None:
        guild = self.bot.gateway.get_guild(guild_id)

        if guild is None:
            return

        member = await guild.get_member(user_id)

        if member is None:
            return

        try:
            await member.add_role(guild.get_role(role_id))
        except HTTPException:
            pass

    @listener("get_user")
    async def get_user(self, user_id: str) -> UserDict:
        user = await self.bot.gateway.get_user(user_id)

        return UserDict(
            id = user.id,
            username = user.username,
            avatar = user.avatar
        )

    @listener("get_guilds_for")
    async def get_guilds_for(self, user_id: str) -> GuildDict:
        guilds: list[GuildDict] = []

        for guild in self.bot.gateway.guilds:
            if self.user_has_permissions(guild, user_id):
                guilds.append(self.guild_to_dict(guild))

        return guilds

    @listener("get_guild_db")
    async def get_guild_db(self, guild_id: str, user_id: str) -> Guilds | int:
        guild = self.bot.gateway.get_guild(guild_id)

        if not guild:
            return 404

        if not self.user_has_permissions(guild, user_id):
            return 403

        guild = self.bot.gateway.get_guild(guild_id)
        guild_db = await Guilds.get(guild_id=guild_id)
        guild_db = guild_db.__dict__

        for element in ("_partial", "_saved_in_db", "_custom_generated_pk", "id", "guild_id"):
            del guild_db[element]

        guild_db["custom_commands"] = [
            {
                "name": next(filter(lambda command: command.other.get("code") == custom_command and command.guild_id == guild_id, self.bot.commands)).other["display_name"],
                "metadata": {
                    key[2:]: value
                    for key, value in (custom_command.split(": ", 1) for custom_command in custom_command.split("\n", 4)[:4])
                },
                "value": custom_command.split("\n", 5)[5]
            }
            for custom_command in guild_db["custom_commands"]
        ]
        guild_db["guild"] = self.guild_to_dict(guild)

        return guild_db

    @listener("webhook_event")
    async def webhook_event(self, event: Event) -> None:
        channel = self.bot.gateway.get_channel("1369001448372699167")

        components = femcord.Components()
        container = femcord.Container(accent_color=0x4ac926)

        text = f"# {event["user"]["global_name"] or event["user"]["username"]} ({event["user"]["id"]})"

        if event["integration_type"] == 1:
            text += " dodał bota do swojego konta"
        elif event["integration_type"] == 0:
            text += " dodał bota na serwer"

        container.add_component(femcord.Section(
            components = [
                femcord.TextDisplay(
                    content = text
                )
            ],
            accessory = femcord.Thumbnail(
                media = femcord.UnfurledMediaItem(
                    url = f"https://cdn.discordapp.com/avatars/{event["user"]["id"]}/{event["user"]["avatar"]}.png"
                )
            )
        ))

        if event["integration_type"] == 0:
            container.add_component(femcord.Section(
                components = [
                    femcord.TextDisplay(
                        content = f"# {event["guild"]["name"]}"
                    )
                ],
                accessory = femcord.Thumbnail(
                    media = femcord.UnfurledMediaItem(
                        url = f"https://cdn.discordapp.com/icons/{event["guild"]["id"]}/{event["guild"]["icon"]}.png"
                    )
                )
            ))

        components.add_component(container)

        await channel.send(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])