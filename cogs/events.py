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

import femcord.femcord as femcord
from femcord.femcord import commands
from femcord.femcord.commands import Context
from femcord.femcord.types import Guild, Member, User, Message, Interaction
from femcord.femcord.enums import MessageFlags
from femcord.femcord.commands import Context
from femcord.femcord.http import Route, HTTPException
from femscript import Femscript
from utils import *
from models import Guilds
import hashlib, config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context

class Events(commands.Cog):
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

        @bot.before_call
        async def before_call(ctx: Context) -> None:
            print(f"{ctx.author.username}: {ctx.message.content}")

            if ctx.error is None:
                self.bot.loki.add_command_log(ctx)

    @commands.Listener
    async def on_guild_create(self, guild: Guild):
        exists = await Guilds.exists(guild_id=guild.id)

        if not exists:
            await Guilds.create(
                guild_id = guild.id,
                prefix = config.PREFIX,
                welcome_message = "",
                leave_message = "",
                autorole = "",
                custom_commands = [],
                database = {},
                permissions = {},
                schedules = [],
                language = "en",
                verification_role = "",
                verification_message = "",
                verification_channel = "",
                eventhandlers = {}
            )

        self.bot.loki.add_guild_log(guild)

    @commands.Listener
    async def on_guild_delete(self, guild: Guild):
        await Guilds.filter(guild_id=guild.id).delete()
        self.bot.loki.add_guild_log(guild, leave=True)

    @commands.Listener
    async def on_guild_member_add(self, guild: Guild, member: Member):
        if not hasattr(guild, "welcome_message") or not hasattr(guild, "autorole"):
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            guild.welcome_message = db_guild.welcome_message
            guild.leave_message = db_guild.leave_message
            guild.autorole = db_guild.autorole

        if guild.welcome_message:
            variables = [
                {
                    "name": key,
                    "value": Femscript.to_fs(value)
                }
                for key, value in convert(user=member.user, guild=guild).items()
            ]

            femscript = Femscript(guild.welcome_message, variables=variables, modules=self.bot.femscript_modules)

            @femscript.wrap_function()
            def set_channel(channel_id: str) -> None:
                femscript.channel_id = channel_id

            @femscript.wrap_function()
            async def set_nick(nick: str) -> None:
                await member.modify(nick=nick)

            femscript.wrap_function(get_random_username, func_name="random_nick")

            femscript.wrap_function(request)
            femscript.wrap_function(femcord.Embed)

            result = await femscript.execute()

            if hasattr(femscript, "channel_id"):
                channel = guild.get_channel(femscript.channel_id)

                if channel is not None:
                    await channel.send(**{"content" if not isinstance(result, femcord.Embed) else "embed": result})

        if guild.autorole:
            await member.add_role(guild.get_role(guild.autorole))

    @commands.Listener
    async def on_guild_member_remove(self, guild: Guild, user: User):
        if not hasattr(guild, "leave_message"):
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            guild.welcome_message = db_guild.welcome_message
            guild.leave_message = db_guild.leave_message
            guild.autorole = db_guild.autorole

        if guild.leave_message:
            variables = [
                {
                    "name": key,
                    "value": Femscript.to_fs(value)
                }
                for key, value in convert(user=user, guild=guild).items()
            ]

            femscript = Femscript(guild.leave_message, variables=variables, modules=self.bot.femscript_modules)

            @femscript.wrap_function()
            def set_channel(channel_id: str) -> None:
                femscript.channel_id = channel_id

            femscript.wrap_function(request)
            femscript.wrap_function(femcord.Embed)

            result = await femscript.execute()

            if hasattr(femscript, "channel_id"):
                channel = guild.get_channel(femscript.channel_id)

                if channel is not None:
                    await channel.send(**{"content" if not isinstance(result, femcord.Embed) else "embed": result})

    @commands.Listener
    async def on_message_create(self, message: Message):
        if message.author.bot or not message.guild:
            return

        if message.guild.me and message.guild.me.user in message.mentions and not message.message_reference and len(message.content.split()) == 1:
            if message.content in (await self.bot.get_prefix(self.bot, message))[:4]:
                return await message.reply(f"Prefix on this server is `{(await self.bot.get_prefix(self.bot, message))[-1]}`")

    @commands.Listener
    async def on_interaction_create(self, interaction: Interaction):
        if not interaction.guild:
            return

        if interaction.data.custom_id == "verification" + interaction.guild.id:
            query = Guilds.filter(guild_id=interaction.guild.id)
            guild_db = await query.first()

            if guild_db.verification_message == interaction.message.id and guild_db.verification_channel == interaction.channel.id:
                await self.bot.ipc.emit("new_captcha", {
                    "guild_id": interaction.guild.id,
                    "user_id": interaction.user.id,
                    "role_id": guild_db.verification_role,
                    "guild_icon": interaction.guild.icon_as("png"),
                    "user_avatar": interaction.user.avatar_as("png")
                }, nowait=True)

                captcha_id = hashlib.md5(f"{interaction.guild.id}:{interaction.user.id}".encode()).hexdigest()

                await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, "<https://cenzura.poligon.lgbt/captcha/" + captcha_id + ">", flags=[MessageFlags.EPHEMERAL])

def setup(bot: "Bot") -> None:
    bot.load_cog(Events(bot))