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
from femcord import commands, types
from femcord.permissions import Permissions
from femscript import run
from tortoise import Tortoise
from utils import modules, builtins
from models import Guilds
from scheduler import Scheduler
from poligonlgbt import Poligon
from datetime import datetime
from typing import Callable, Union, Optional, List
import asyncio, uvloop, socket, struct, json, random, re, os, time, config, logging

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

class FakeCtx:
    def __init__(self, copy_function: Callable, guild: types.Guild, channel: types.Channel, member: types.Member, su_role: types.Role) -> None:
        self.guild = guild
        self.channel = channel
        self.member = copy_function(member, deep=True)
        self.author = self.member.user

        self.member.roles.append(su_role)
        self.member.permissions = su_role.permissions

    async def send(self, *args, **kwargs) -> None:
        pass

    async def reply(self, *args, **kwargs) -> None:
        pass

class Bot(commands.Bot):
    def __init__(self, *, start_time: float = time.time()) -> None:
        super().__init__(name="benzura", command_prefix=self.get_prefix, intents=femcord.Intents.all(), owners=config.OWNERS)

        self.start_time = start_time

        self.presences: List[types.Presence] = None
        self.presence_update_interval: int = None
        self.random_presence: bool = False
        self.presence_index: int = 0
        self.presence_indexes: List[int] = []
        self.scheduler = Scheduler()
        self.poligon: Poligon = None
        self.socket: socket.socket = None

        self.embed_color = 0xb22487
        self.user_agent = "Mozilla/5.0 (SMART-TV; Linux; Tizen 2.3) AppleWebkit/538.1 (KHTML, like Gecko) SamsungBrowser/1.0 TV Safari/538.1"

        self.su_role: types.Role = types.Role(
            id = "su",
            name = "su",
            color = 0xffffff,
            hoist = True,
            icon = None,
            unicode_emoji = None,
            position = float("inf"),
            permissions = Permissions.all(),
            managed = False,
            mentionable = False,
            created_at = datetime.now()
        )

        for filename in os.listdir("./cogs"):
            if filename[-3:] == ".py":
                self.load_extension("cogs.%s" % filename[:-3])

                print("loaded %s" % filename)

        self.event(self.on_ready)
        self.event(self.on_close)

        self.loop.run_until_complete(self.async_init())

    async def on_ready(self) -> None:
        customcommand_command = self.get_command("customcommand")
        metadata_pattern = re.compile(r"# \w+: (\d+)")

        for guild in self.gateway.guilds:
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            if db_guild is None:
                db_guild = await Guilds.create(guild_id=guild.id, prefix="1", welcome_message="", leave_message="", autorole="", custom_commands=[], database={}, permissions={}, schedules=[])

            if db_guild.custom_commands:
                guild.owner = await guild.get_member(guild.owner)

            for custom_command in db_guild.custom_commands:
                channel_id, author_id = metadata_pattern.findall(custom_command)[2:4]
                fake_ctx = FakeCtx(self.gateway.copy, guild, guild.get_channel(channel_id), await guild.get_member(author_id), self.su_role)

                await customcommand_command(fake_ctx, code=custom_command)

        await self.scheduler.create_schedule(self.update_presences, "10m", name="update_presences")()

        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        if os.path.exists(config.FEMBOT_SOCKET_PATH):
            os.remove(config.FEMBOT_SOCKET_PATH)
        self.socket.bind(config.FEMBOT_SOCKET_PATH)

        receiver_schedule = self.scheduler.create_schedule(self.dashboard_receiver, "1s", name="dashboard_receiver")
        self.scheduler.hide_schedules(receiver_schedule)

        print(f"logged in {self.gateway.bot_user.username}#{self.gateway.bot_user.discriminator} ({time.time() - self.start_time:.2f}s)")

    async def on_close(self) -> None:
        await Tortoise.close_connections()
        self.socket.close()

        print("closed db connection")

    async def async_init(self) -> None:
        logging.getLogger("tortoise").setLevel(logging.WARNING)

        await Tortoise.init(config=config.DB_CONFIG, modules={"models": ["app.models"]})
        await Tortoise.generate_schemas()

        print("connected to database")

        self.poligon = await Poligon(config.POLIGON_LGBT_API_KEY, config.POLIGON_LGBT_UPLOAD_KEY)

        print("created poligon.lgbt client")

    async def dashboard_receiver(self) -> None:
        try:
            data, _ = self.socket.recvfrom(4)
            op = struct.unpack("<I", data)[0]

            if op == 1:
                for index, cog in enumerate(self.cogs):
                    data = {
                        "index": index,
                        "cogs_count": len(self.cogs),
                        "name": cog.name,
                        "description": cog.description,
                        "hidden": cog.hidden,
                        "commands_count": len(cog.walk_commands()),
                        "commands": []
                    }

                    data = json.dumps(data, separators=(",", ":")).encode()
                    header_data = struct.pack("<II", 1, len(data))

                    self.socket.sendto(header_data, config.DASHBOARD_SOCKET_PATH)
                    self.socket.sendto(data, config.DASHBOARD_SOCKET_PATH)
            elif op == 2:
                for index, command in enumerate(self.walk_commands()):
                    usage = []

                    if command.usage is not None:
                        arguments = command.usage.split(" ")

                        for argument in arguments:
                            if argument[0] == "(":
                                usage.append([argument[1:-1], 0])
                            elif argument[0] == "[":
                                usage.append([argument[1:-1], 1])

                    data = {
                        "index": index,
                        "commands_count": len(self.walk_commands()),
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
                    }

                    data = json.dumps(data, separators=(",", ":")).encode()
                    header_data = struct.pack("<II", 2, len(data))

                    self.socket.sendto(header_data, config.DASHBOARD_SOCKET_PATH)
                    self.socket.sendto(data, config.DASHBOARD_SOCKET_PATH)
        except socket.error:
            return

    async def update_presences(self) -> None:
        with open("presence.fem", "r") as file:
            code = file.read()

            self.presences = []

            def set_update_interval(interval: Union[str, int]):
                self.presence_update_interval = interval

            def set_random_presence(value: bool):
                self.random_presence = value

            def add_presence(name: str, *, status_type: femcord.StatusTypes = femcord.StatusTypes.ONLINE, activity_type: femcord.ActivityTypes = femcord.ActivityTypes.PLAYING):
                self.presences.append(presence := femcord.Presence(status_type, activities=[femcord.Activity(name, activity_type)]))
                return presence

            await run(
                code,
                modules = modules,
                builtins = {
                    **builtins,
                    "set_update_interval": set_update_interval,
                    "set_random_presence": set_random_presence,
                    "add_presence": add_presence
                },
                variables = {
                    "gateway": self.gateway,
                    "StatusTypes": femcord.StatusTypes,
                    "ActivityTypes": femcord.ActivityTypes
                }
            )

        if not (schedules := self.scheduler.get_schedules("update_presence")):
            return await self.scheduler.create_schedule(self.update_presence, self.presence_update_interval, name="update_presence")()

        self.scheduler.cancel_schedules(schedules)
        await self.scheduler.create_schedule(self.update_presence, self.presence_update_interval, name="update_presence")()

    async def update_presence(self) -> None:
        while not self.presences:
            await asyncio.sleep(1)

        if self.random_presence is True:
            while self.presence_index in self.presence_indexes:
                self.presence_index = random.randint(0, len(self.presences) - 1)

            self.presence_indexes.append(self.presence_index)

            if len(self.presence_indexes) >= len(self.presences):
                self.presence_indexes = [self.presence_index]

        await self.gateway.set_presence(self.presences[self.presence_index])

        if self.random_presence is False:
            self.presence_index += 1

            if self.presence_index >= len(self.presences):
                self.presence_index = 0

    async def get_prefix(self, _, message: femcord.types.Message) -> List[str]:
        prefixes = ["<@{}>", "<@!{}>", "<@{}> ", "<@!{}> "]
        prefixes = [prefix.format(self.gateway.bot_user.id) for prefix in prefixes]

        if hasattr(message.guild, "prefix"):
            return prefixes + [message.guild.prefix or config.PREFIX]

        db_guild = await Guilds.filter(guild_id=message.guild.id).first()
        message.guild.prefix = db_guild.prefix

        return prefixes + [message.guild.prefix or config.PREFIX]

    async def paginator(self, function: Callable, ctx: femcord.commands.Context, content: Optional[str] = None, **kwargs: dict) -> None:
        pages: list = kwargs.pop("pages", None)
        prefix: str = kwargs.pop("prefix", "")
        suffix: str = kwargs.pop("suffix", "")
        limit: int = kwargs.pop("limit", 2000)
        timeout: int = kwargs.pop("timeout", 60)
        page: int = kwargs.pop("page", 0)
        replace: bool = kwargs.pop("replace", True)
        buttons: bool = kwargs.pop("buttons", False)

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

        if len(pages) == 1 and buttons is False:
            return await function(pages[page], **kwargs)

        if page < 0:
            page = pages.index(pages[page])

        def get_components(disabled: Optional[bool] = False) -> femcord.Components:
            return femcord.Components(
                femcord.Row(
                    femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="first", disabled=disabled, emoji=types.Emoji("\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}")),
                    femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="previous", disabled=disabled, emoji=types.Emoji("\N{BLACK LEFT-POINTING TRIANGLE}")),
                    femcord.Button(f"{page + 1}/{len(pages)}", custom_id="cancel", disabled=disabled, style=femcord.ButtonStyles.DANGER),
                    femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="next", disabled=disabled, emoji=types.Emoji("\N{BLACK RIGHT-POINTING TRIANGLE}")),
                    femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="last", disabled=disabled, emoji=types.Emoji("\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"))
                )
            )

        message = await function(pages[page], components=get_components(), **kwargs)

        canceled = False

        async def change_page(interaction: femcord.types.Interaction) -> None:
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

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, pages[page], components=get_components(disabled=canceled), **kwargs)

            if not canceled:
                await self.wait_for("interaction_create", change_page, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=timeout, on_timeout=on_timeout)

        async def on_timeout():
            nonlocal canceled
            canceled = True

            await message.edit(pages[page], components=get_components(disabled=canceled), **kwargs)

        await self.wait_for("interaction_create", change_page, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=timeout, on_timeout=on_timeout)

if __name__ == "__main__":
    Bot().run(config.TOKEN)