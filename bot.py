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
from tortoise import Tortoise
from models import Guilds
import re, os, time, config

class FakeCtx:
    def __init__(self, guild, channel, member):
        self.guild = guild
        self.channel = channel
        self.member = member
        self.author = member.user

    async def send(self, *args, **kwargs):
        pass

    async def reply(self, *args, **kwargs):
        pass

class Bot(commands.Bot):
    def __init__(self, *, start_time: float):
        super().__init__(command_prefix=self.get_prefix, intents=lib.Intents.all(), owners=config.OWNERS)

        self.embed_color = 0xb22487
        self.user_agent = "Mozilla/5.0 (SMART-TV; Linux; Tizen 2.3) AppleWebkit/538.1 (KHTML, like Gecko) SamsungBrowser/1.0 TV Safari/538.1"

        for filename in os.listdir("./cogs"):
            if filename[-3:] == ".py":
                self.load_extension("cogs.%s" % filename[:-3])

                print("loaded %s" % filename)

        @self.before_call
        async def before_call(ctx):
            await ctx.channel.start_typing()

        @self.event
        async def on_ready():
            customcommand_command = self.get_command("customcommand")

            for guild in self.gateway.guilds:
                db_guild = await Guilds.filter(guild_id=guild.id).first()

                if db_guild is None:
                    db_guild = await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[])

                if db_guild.custom_commands:
                    guild.owner = await guild.get_member(guild.owner)

                for custom_command in db_guild.custom_commands:
                    channel_id, author_id = re.findall(r"# \w+: (\d+)", custom_command)[1:3]
                    fake_ctx = FakeCtx(guild, guild.get_channel(channel_id), await guild.get_member(author_id))

                    await customcommand_command(fake_ctx, code=custom_command)

            await self.gateway.set_presence(lib.Presence(lib.StatusTypes.DND, activities=[lib.Activity(name="\u200b", type=lib.ActivityTypes.WATCHING)]))

            print(f"logged in {self.gateway.bot_user.username}#{self.gateway.bot_user.discriminator} ({time.time() - start_time:.2f}s)")

    async def get_prefix(self, _, message):
        guild = await Guilds.get(guild_id=message.guild.id).first()
        return guild.prefix or config.PREFIX

    async def create_psql_connection(self):
        await Tortoise.init(config=config.DB_CONFIG, modules={"models": ["app.models"]})
        await Tortoise.generate_schemas()

        print("connected to database")

    def run(self, token, *, bot: bool = True):
        self.loop.run_until_complete(self.create_psql_connection())
        super().run(token, bot=bot)

if __name__ == "__main__":
    Bot().run(config.TOKEN)