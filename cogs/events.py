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

import femcord
from femcord import commands
from femscript import run
from utils import *
from models import Guilds

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Listener
    async def on_guild_create(self, guild):
        exists = await Guilds.exists(guild_id=guild.id)

        if not exists:
            await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[])

    @commands.Listener
    async def on_guild_delete(self, guild):
        await Guilds.filter(guild_id=guild.id).delete()

    @commands.Listener
    async def on_guild_member_add(self, guild, member):
        if not hasattr(guild, "welcome_message"):
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            guild.welcome_message = db_guild.welcome_message
            guild.leave_message = db_guild.leave_message
            guild.autorole = db_guild.autorole

        if guild.welcome_message:
            channel = None

            def set_channel(channel_id):
                nonlocal channel

                channel = guild.get_channel(channel_id)

            result = await run(
                guild.welcome_message,
                builtins = {
                    **builtins,
                    "set_channel": set_channel
                },
                variables = convert(
                    guild = guild,
                    user = member.user
                )
            )

            if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], femcord.Embed):
                await channel.send(result[0], embed=result[1])
            elif isinstance(result, femcord.Embed):
                await channel.send(embed=result)
            else:
                await channel.send(result)

        if guild.autorole:
            await member.add_role(guild.get_role(guild.autorole))

    @commands.Listener
    async def on_guild_member_remove(self, guild, user):
        if not hasattr(guild, "leave_message"):
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            guild.welcome_message = db_guild.welcome_message
            guild.leave_message = db_guild.leave_message
            guild.autorole = db_guild.autorole

        if guild.leave_message:
            channel = None

            def set_channel(channel_id):
                nonlocal channel

                channel = guild.get_channel(channel_id)

            result = await run(
                guild.leave_message,
                builtins = {
                    **builtins,
                    "set_channel": set_channel
                },
                variables = convert(
                    guild = guild,
                    user = user
                )
            )

            if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], femcord.Embed):
                await channel.send(result[0], embed=result[1])
            elif isinstance(result, femcord.Embed):
                await channel.send(embed=result)
            else:
                await channel.send(result)

    @commands.Listener
    async def on_message_create(self, message):
        if message.author.bot:
            return

        if message.guild.me and message.guild.me.user in message.mentions and not message.message_reference and len(message.content.split()) == 1:
            if message.content in (await self.bot.get_prefix(self.bot, message))[:4]:
                return await message.reply(f"Prefix na tym serwerze to `{(await self.bot.get_prefix(self.bot, message))[-1]}`")

def setup(bot):
    bot.load_cog(Events(bot))