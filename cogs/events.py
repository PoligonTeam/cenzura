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

import femcord
from femcord import commands
from femcord.commands import Context
from femcord.types import Guild, Member, User, Message
from femcord.http import Route
from femcord.commands.context import Context
from femscript import Femscript
from typing import TYPE_CHECKING
from utils import *
from models import Guilds

if TYPE_CHECKING:
    from bot import Bot

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot

        @bot.before_call
        async def before_call(ctx: Context) -> None:
            print(f"{ctx.author.username}: {ctx.message.content}")

            if ctx.error is None:
                self.bot.loki.add_command_log(ctx)

    @commands.Listener
    async def on_guild_create(self, guild: Guild):
        exists = await Guilds.exists(guild_id=guild.id)

        if not exists:
            await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[], database={}, permissions={}, schedules=[])

        await self.bot.loki.add_guild_log(guild)

    @commands.Listener
    async def on_guild_delete(self, guild: Guild):
        await Guilds.filter(guild_id=guild.id).delete()
        await self.bot.loki.add_guild_log(guild, leave=True)

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

            femscript = Femscript(guild.welcome_message, variables=variables)
            
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
                    if isinstance(result, femcord.Embed):
                        await channel.send(embed=result)
                    else:
                        await channel.send(result)

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

            femscript = Femscript(guild.leave_message, variables=variables)
            
            @femscript.wrap_function()
            def set_channel(channel_id: str) -> None:
                femscript.channel_id = channel_id

            femscript.wrap_function(request)
            femscript.wrap_function(femcord.Embed)

            result = await femscript.execute()

            if hasattr(femscript, "channel_id"):
                channel = guild.get_channel(femscript.channel_id)

                if channel is not None:
                    if isinstance(result, femcord.Embed):
                        await channel.send(embed=result)
                    else:
                        await channel.send(result)

    @commands.Listener
    async def on_message_create(self, message: Message):
        if message.author.bot:
            return

        if message.guild.me and message.guild.me.user in message.mentions and not message.message_reference and len(message.content.split()) == 1:
            if message.content in (await self.bot.get_prefix(self.bot, message))[:4]:
                return await message.reply(f"Prefix on this server is `{(await self.bot.get_prefix(self.bot, message))[-1]}`")

def setup(bot):
    bot.load_cog(Events(bot))