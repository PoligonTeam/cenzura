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
from lib import commands, types
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
            ctx.typing = lib.Typing(ctx.message)
            await ctx.typing.start()

        @self.after_call
        async def after_call(ctx):
            await ctx.typing.stop()

        @self.event
        async def on_ready():
            customcommand_command = self.get_command("customcommand")

            for guild in self.gateway.guilds:
                db_guild = await Guilds.get(guild_id=guild.id)

                if db_guild is None:
                    db_guild = await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[])

                if db_guild.custom_commands:
                    guild.owner = await guild.get_member(guild.owner)

                for custom_command in db_guild.custom_commands:
                    channel_id, author_id = re.findall(r"# \w+: (\d+)", custom_command)[2:4]
                    fake_ctx = FakeCtx(guild, guild.get_channel(channel_id), await guild.get_member(author_id))

                    await customcommand_command(fake_ctx, code=custom_command)

            await self.gateway.set_presence(lib.Presence(lib.StatusTypes.DND, activities=[lib.Activity(name="\u200b", type=lib.ActivityTypes.WATCHING)]))

            print(f"logged in {self.gateway.bot_user.username}#{self.gateway.bot_user.discriminator} ({time.time() - start_time:.2f}s)")

    async def get_prefix(self, _, message):
        guild = await Guilds.get(guild_id=message.guild.id)
        return guild.prefix or config.PREFIX

    async def create_psql_connection(self):
        await Tortoise.init(config=config.DB_CONFIG, modules={"models": ["app.models"]})
        await Tortoise.generate_schemas()

        print("connected to database")

    async def paginator(self, function, ctx, content: str = None, **kwargs):
        pages = kwargs.pop("pages", None)
        prefix = kwargs.pop("prefix", "")
        suffix = kwargs.pop("suffix", "")
        limit = kwargs.pop("limit", 2000)
        timeout = kwargs.pop("timeout", 60)
        page = kwargs.pop("page", 0)
        replace = kwargs.pop("replace", True)

        if limit > 2000:
            limit = 2000

        length = limit - len(prefix) - len(suffix)

        if pages is None:
            content = str(content)

            if replace is True:
                content = content.replace("`", "\`")

            pages = [prefix + content[i:i+length] + suffix for i in range(0, len(content), length)]
        else:
            pages = [prefix + (page if replace is False else page.replace("`", "\`")) + suffix for page in pages]

        if len(pages) == 1:
            return await function(pages[page], **kwargs)

        if page < 0:
            page = pages.index(pages[page])

        def get_components(disabled: bool = False):
            return lib.Components(
                lib.Row(
                    lib.Button(style=lib.ButtonStyles.PRIMARY, custom_id="first", disabled=disabled, emoji=types.Emoji("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}")),
                    lib.Button(style=lib.ButtonStyles.PRIMARY, custom_id="previous", disabled=disabled, emoji=types.Emoji("\N{BLACK LEFT-POINTING TRIANGLE}")),
                    lib.Button(f"{page + 1}/{len(pages)}", custom_id="cancel", disabled=disabled, style=lib.ButtonStyles.DANGER),
                    lib.Button(style=lib.ButtonStyles.PRIMARY, custom_id="next", disabled=disabled, emoji=types.Emoji("\N{BLACK RIGHT-POINTING TRIANGLE}")),
                    lib.Button(style=lib.ButtonStyles.PRIMARY, custom_id="last", disabled=disabled, emoji=types.Emoji("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"))
                )
            )

        message = await function(pages[page], components=get_components(), **kwargs)

        canceled = False

        async def change_page(interaction):
            nonlocal page, canceled

            if interaction.data.custom_id == "first":
                page = 0
            elif interaction.data.custom_id == "previous":
                page -= 1
                if page < 0:
                    page = len(pages) - 1
            elif interaction.data.custom_id == "next":
                page += 1
                if page >= len(pages):
                    page = 0
            elif interaction.data.custom_id == "last":
                page = len(pages) - 1
            elif interaction.data.custom_id == "cancel":
                canceled = True
                return await message.delete()

            await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, pages[page], components=get_components(disabled=canceled), **kwargs)

            if not canceled:
                await self.wait_for("interaction_create", change_page, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=timeout, on_timeout=on_timeout)

        async def on_timeout():
            nonlocal canceled
            canceled = True

            await message.edit(pages[page], components=get_components(disabled=canceled), **kwargs)

        await self.wait_for("interaction_create", change_page, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=timeout, on_timeout=on_timeout)

    def run(self, token, *, bot: bool = True):
        self.loop.run_until_complete(self.create_psql_connection())
        super().run(token, bot=bot)

if __name__ == "__main__":
    Bot().run(config.TOKEN)