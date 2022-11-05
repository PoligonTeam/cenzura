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
from femcord.types import Guild, Member, User, Message
from femscript import run
from aiohttp import ClientSession, FormData
from utils import *
from models import Guilds, Users
import time

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Listener
    async def on_guild_create(self, guild: Guild):
        exists = await Guilds.exists(guild_id=guild.id)

        if not exists:
            await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[], database={}, permissions={}, schedules=[])

    @commands.Listener
    async def on_guild_delete(self, guild: Guild):
        await Guilds.filter(guild_id=guild.id).delete()

    @commands.Listener
    async def on_guild_member_add(self, guild: Guild, member: Member):
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
                modules = await get_modules(self.bot, guild),
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
    async def on_guild_member_remove(self, guild: Guild, user: User):
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
                modules = await get_modules(self.bot, guild),
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

    # @commands.Listener
    # async def on_user_update(self, old_user: User, user: User):
    #     if old_user.avatar == user.avatar:
    #         return

    #     print(1)

    #     query = Users.filter(user_id=user.id)
    #     user_db = await query.first()

    #     if not user_db:
    #         await Users.create(user_id=user.id, avatars=[])
    #         user_db = await query.first()

    #     async with ClientSession() as session:
    #         async with session.get(user.avatar_url + "?size=2048") as response:
    #             if not response.status == 200:
    #                 return

    #             data = await response.content.read()

    #             headers = {
    #                 "authorization": POLIGON_LGBT
    #             }

    #             form = FormData()
    #             form.add_field("file", data, filename="avatar.png")

    #             async with session.post("https://poligon.lgbt/api/upload", headers=headers, data=form) as response:
    #                 if not response.status == 201:
    #                     return

    #                 data = await response.json()

    #                 avatars = user_db.avatars
    #                 avatars.append({
    #                     "name": data["name"],
    #                     "time": time.time()
    #                 })
    #                 print(avatars)

    #                 await query.update(avatars=avatars)

    @commands.Listener
    async def on_message_create(self, message: Message):
        if message.author.id == "1010932694693199972":
            return await (await self.bot.gateway.get_user("740349770165518347")).send(message.content)

        if message.author.bot:
            return

        if message.guild.me and message.guild.me.user in message.mentions and not message.message_reference and len(message.content.split()) == 1:
            if message.content in (await self.bot.get_prefix(self.bot, message))[:4]:
                return await message.reply(f"Prefix na tym serwerze to `{(await self.bot.get_prefix(self.bot, message))[-1]}`")

def setup(bot):
    bot.load_cog(Events(bot))