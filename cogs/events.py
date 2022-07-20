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

import lib
from lib import commands
from models import Guilds

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Listener
    async def on_guild_create(self, guild):
        exists = await Guilds.exists(guild_id=guild.id)

        if not exists:
            await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[])

    @commands.Listener
    async def on_guild_delete(self, guild):
        await Guilds.delete(guild_id=guild.id)

    @commands.Listener
    async def on_message_create(self, message):
        if message.author.bot:
            return

        if message.guild.me and message.guild.me.user in message.mentions and not message.message_reference and len(message.content.split()) == 1:
            return await message.reply(f"Prefix na tym serwerze to `{await self.bot.get_prefix(None, message)}`")

def setup(bot):
    bot.load_cog(Events(bot))