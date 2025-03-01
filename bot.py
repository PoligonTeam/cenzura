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
from femcord.femcord import commands, types
from femcord.femcord.http import Route
from femcord.femcord.permissions import Permissions
from femscript import Femscript, var, AST, FemscriptModules, FemscriptModule
from tortoise import Tortoise
from utils import request
from lokiclient import LokiClient
from models import Guilds
from scheduler.scheduler import Scheduler
from ipc import IPC
from poligonlgbt import Poligon
from datetime import datetime

import asyncio
import uvloop
import random
import psutil
import os
import time
import config
import logging

from typing import Callable, Awaitable, Optional, Any, Unpack, TypedDict

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

class PaginatorKwargs(TypedDict):
    pages: Optional[list]
    by_lines: bool
    base_embed: Optional[femcord.Embed]
    prefix: str
    suffix: str
    limit: int
    timeout: int
    page: int
    replace: bool
    buttons: bool

class HybridContext:
    async def get_translation(self, translation: str, args: tuple[Any] = None) -> str | femcord.Embed:
        if not hasattr(self.command.cog, "translations"):
            raise Exception(f"cog {self.command.cog.name} has no translations")

        if self.guild and not hasattr(self.guild, "language"):
            db_guild = await Guilds.filter(guild_id=self.guild.id).first()

            self.guild.prefix = db_guild.prefix
            self.guild.language = db_guild.language
            self.guild.welcome_message = db_guild.welcome_message
            self.guild.leave_message = db_guild.leave_message
            self.guild.autorole = db_guild.autorole

        femscript = Femscript(variables = [
            {
                "name": "arg%d" % index,
                "value": Femscript.to_fs(value)
            }
            for index, value in enumerate(args or [])
        ])

        femscript.ast = [
            self.command.cog.translations[self.guild.language if self.guild else "en"][translation],
            {
                "type": "Keyword",
                "token": {
                    "type": "Return",
                    "value": "",
                    "number": 0.0,
                    "list": [],
                    "bytes": b""
                },
                "children": [
                    {
                        "type": "Token",
                        "token": {
                            "type": "Var",
                            "value": translation,
                            "number": 0.0,
                            "list": [],
                            "bytes": b""
                        },
                        "children": [
                            {
                                "type": "Token",
                                "token": {
                                    "type": "List",
                                    "value": "",
                                    "number": 0.0,
                                    "list": [],
                                    "bytes": b""
                                },
                                "children": [
                                    {
                                        "type": "Token",
                                        "token": {
                                            "type": "Var",
                                            "value": "arg%d" % index,
                                            "number": 0.0,
                                            "list": [],
                                            "bytes": b""
                                        },
                                        "children": []
                                    }
                                    for index in range(len(args or []))
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        femscript.wrap_function(femcord.Embed)

        return await femscript.execute()

    async def send_translation(self, translation: str, format_args: tuple[Any] = None, *args, **kwargs) -> types.Message:
        result = await self.get_translation(translation, format_args)

        if isinstance(result, femcord.Embed):
            kwargs["embed"] = result
            result = None

        return await self.send(result, *args, **kwargs)

    async def reply_translation(self, translation: str, format_args: tuple[Any] = None, *args, **kwargs) -> types.Message:
        result = await self.get_translation(translation, format_args)

        if isinstance(result, femcord.Embed):
            kwargs["embed"] = result
            result = None

        return await self.reply(result, *args, **kwargs)

    async def paginator(self, function: Callable[..., Awaitable[dict]], check: Callable[[types.Interaction, types.Message | None], bool], content: Optional[str] = None, **kwargs: Unpack[PaginatorKwargs]) -> None:
        pages: Optional[list] = kwargs.pop("pages", None)
        by_lines: bool = kwargs.pop("by_lines", False)
        base_embed: Optional[femcord.Embed] = kwargs.pop("base_embed", None)
        prefix: str = kwargs.pop("prefix", "")
        suffix: str = kwargs.pop("suffix", "")
        limit: int = kwargs.pop("limit", 4096 if base_embed else 2000)
        timeout: int = kwargs.pop("timeout", 60)
        page: int = kwargs.pop("page", 0)
        replace: bool = kwargs.pop("replace", True)
        buttons: bool = kwargs.pop("buttons", False)

        if not base_embed and limit > 2000:
            limit = 2000

        length = limit - len(prefix) - len(suffix)

        if by_lines:
            length = limit - len(prefix) - len(suffix)
            if pages is None:
                content_lines = content.splitlines()
                pages = []
                current_page = []
                current_length = 0

                for line in content_lines:
                    if current_length + len(line) + 1 <= length:
                        current_page.append(line)
                        current_length += len(line) + 1
                    else:
                        current_page = "\n".join(current_page)
                        pages.append(prefix + (current_page if not replace else current_page.replace("`", "\\`")) + suffix)
                        current_page = [line]
                        current_length = len(line) + 1

                if current_page:
                    current_page = "\n".join(current_page)
                    pages.append(prefix + (current_page if not replace else current_page.replace("`", "\\`")) + suffix)
            else:
                pages = [prefix + (page if not replace else page.replace("`", "\\`")) + suffix for page in pages]
        else:
            length = limit - len(prefix) - len(suffix)
            if pages is None:
                content = str(content)
                if replace:
                    content = content.replace("`", "\\`")
                pages = [prefix + content[i:i+length] + suffix for i in range(0, len(content), length)]
            else:
                pages = [prefix + (page if not replace else page.replace("`", "\\`")) + suffix for page in pages]

        def get_page(page: int) -> dict[str, str | femcord.Embed]:
            if base_embed:
                return dict(embed=femcord.Embed(description=pages[page]) + base_embed)
            return dict(content=pages[page])

        if len(pages) == 1 and buttons is False:
            return await function(**get_page(page), **kwargs)

        if page < 0:
            page = pages.index(pages[page])

        def get_components(disabled: bool = False) -> femcord.Components:
            buttons = [
                femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="first", disabled=disabled, emoji=types.Emoji(self, "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}")),
                femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="previous", disabled=disabled, emoji=types.Emoji(self, "\N{BLACK LEFT-POINTING TRIANGLE}")),
                femcord.Button(f"{page + 1}/{len(pages)}", custom_id="cancel", disabled=disabled, style=femcord.ButtonStyles.DANGER),
                femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="next", disabled=disabled, emoji=types.Emoji(self, "\N{BLACK RIGHT-POINTING TRIANGLE}")),
                femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="last", disabled=disabled, emoji=types.Emoji(self, "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}"))
            ]

            if len(pages) > 4:
                select_button = femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="select", disabled=disabled, emoji=types.Emoji(self, "\u0023\uFE0F\u20E3"))

                if page in (0, 1):
                    buttons[0] = select_button
                elif page in (len(pages) - 1, len(pages) - 2):
                    buttons[-1] = select_button

            return femcord.Components(femcord.Row(*buttons))

        message = await function(**get_page(page), components=get_components(), **kwargs)

        if not message:
            message = self.interaction

        while True:
            interaction: types.Interaction

            try:
                interaction, = await self.bot.wait_for("interaction_create", lambda interaction: check(interaction, message), timeout=timeout)
            except TimeoutError:
                if isinstance(message, types.Interaction):
                    await self.edit(**get_page(page), components=get_components(True), **kwargs)
                    return
                await message.edit(**get_page(page), components=get_components(True), **kwargs)
                return

            match interaction.data.custom_id:
                case "first":
                    page = 0
                case "previous":
                    page -= 1
                    if page < 0:
                        page = len(pages) - 1
                case "next":
                    page += 1
                    if page >= len(pages):
                        page = 0
                case "last":
                    page = len(pages) - 1
                case "cancel":
                    return await message.delete()
                case "select":
                    await interaction.callback(
                        femcord.InteractionCallbackTypes.MODAL,
                        components = femcord.Components(
                            femcord.Row(
                                femcord.TextInput(
                                    "page",
                                    custom_id = "select_page_input",
                                    style = femcord.TextInputStyles.SHORT,
                                    min_length = 1,
                                    max_length = len(str(len(pages)))
                                )
                            ),
                            title = "Select page",
                            custom_id = "select_page_modal"
                        )
                    )

                    interaction, = await self.bot.wait_for("interaction_create", lambda interaction: check(interaction, message), timeout=timeout)

                    value = interaction.data.components[0].components[0].value

                    if value.isnumeric():
                        value = int(value) - 1

                        if 0 <= value < len(pages):
                            page = value

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, **get_page(page), components=get_components(), **kwargs)

class Context(HybridContext, commands.Context):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def send_paginator(self, content: Optional[str] = None, **kwargs: Unpack[PaginatorKwargs]) -> Awaitable[None]:
        return self.paginator(self.send, lambda interaction, message: interaction.user.id == self.author.id and interaction.channel.id == self.channel.id and interaction.message.id == message.id, content, **kwargs)

    def reply_paginator(self, content: Optional[str] = None, **kwargs: Unpack[PaginatorKwargs]) -> Awaitable[None]:
        return self.paginator(self.reply, lambda interaction, message: interaction.user.id == self.author.id and interaction.channel.id == self.channel.id and interaction.message.id == message.id, content, **kwargs)

class AppContext(HybridContext, commands.AppContext):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def send_paginator(self, content: Optional[str] = None, **kwargs: Unpack[PaginatorKwargs]) -> Awaitable[None]:
        return self.paginator(self.send, lambda interaction, _: interaction.user.id == self.author.id and interaction.channel.id == self.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == self.interaction.id, content, **kwargs)

    def reply_paginator(self, content: Optional[str] = None, **kwargs: Unpack[PaginatorKwargs]) -> Awaitable[None]:
        return self.paginator(self.reply, lambda interaction, _: interaction.user.id == self.author.id and interaction.channel.id == self.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == self.interaction.id, content, **kwargs)

class Bot(commands.Bot):
    def __init__(self, *, start_time: float = time.time()) -> None:
        super().__init__(name="fembot", command_prefix=self.get_prefix, intents=femcord.Intents().all(), mobile=True, owners=config.OWNERS, context=Context, app_context=AppContext)

        self.start_time = start_time
        self.user_install_count: int = None

        self.presences: list[types.Presence] = None
        self.presence_update_interval: int = None
        self.random_presence: bool = False
        self.presence_index: int = 0
        self.presence_indexes: list[int] = []
        self.scheduler = Scheduler()
        self.ipc = IPC(self, config.FEMBOT_SOCKET_PATH, [config.DASHBOARD_SOCKET_PATH,])
        self.loki = LokiClient(config.LOKI_BASE_URL, self.scheduler)
        self.poligon: Poligon = None

        self.embed_color = 0xb22487
        self.user_agent = "Mozilla/5.0 (SMART-TV; Linux; Tizen 2.3) AppleWebkit/538.1 (KHTML, like Gecko) SamsungBrowser/1.0 TV Safari/538.1"

        self.local_api_base_url = config.LOCAL_API_BASE_URL

        self.process = psutil.Process()

        self.su_role = types.Role(
            self,
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

        self.femscript_modules = FemscriptModules()

        for filename in os.listdir("./femscript_modules"):
            if filename[-4:] == ".fem":
                with open("./femscript_modules/" + filename, "r") as f:
                    self.femscript_modules.add_module(FemscriptModule(filename[:-4], f.read()))

        self.event(self.on_ready)
        self.event(self.on_close)

        self.loop.run_until_complete(self.async_init())

    async def on_ready(self) -> None:
        for guild in self.gateway.guilds:
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            if db_guild is None:
                db_guild = await Guilds.create(
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

            guild.prefix = db_guild.prefix
            guild.language = db_guild.language
            guild.welcome_message = db_guild.welcome_message
            guild.leave_message = db_guild.leave_message
            guild.autorole = db_guild.autorole

        await self.scheduler.create_schedule(self.update_presences, "10m", name="update_presences")()
        await self.scheduler.create_schedule(self.update_user_install_count, "1h", name="update_user_install_count")()

        await self.register_app_commands()

        print("registered application commands")

        print(f"logged in {self.gateway.bot_user.username} ({time.time() - self.start_time:.2f}s)")

    async def on_close(self) -> None:
        await Tortoise.close_connections()
        self.ipc.close()
        await self.loki.send()

        print("closed db connection")

    async def async_init(self) -> None:
        logging.getLogger("tortoise").setLevel(logging.WARNING)

        await Tortoise.init(config=config.DB_CONFIG, modules={"models": ["app.models"]})
        await Tortoise.generate_schemas()

        print("connected to database")

        self.poligon = await Poligon(config.POLIGON_LGBT_API_KEY, config.POLIGON_LGBT_UPLOAD_KEY)

        print("created poligon.lgbt client")

    async def get_latency_data(self):
        before = time.perf_counter()
        await self.http.request(Route("GET", "users", "@me"))
        after = time.perf_counter()

        return {
            "gateway": self.gateway.latency,
            **(
                {
                    "previous": self.gateway.last_latencies[-5:],
                    "average": (sum(self.gateway.last_latencies) + self.gateway.latency) // (len(self.gateway.last_latencies) + 1)
                }
                if self.gateway.last_latencies else
                {

                }
            ),
            "rest": round((after - before) * 1000)
        }

    async def get_stats(self):
        memory = psutil.virtual_memory()
        latency_data = await self.get_latency_data()

        return {
            "guilds": len(self.gateway.guilds),
            "user_install_count": self.user_install_count,
            "users": len(self.gateway.users),
            "commands": len(self.walk_commands()),
            "ram": {
                "current": self.process.memory_full_info().rss,
                "total": memory.total,
                "available": memory.available
            },
            "cpu": psutil.cpu_percent(),
            "latencies": latency_data,
            "timestamp": self.started_at.timestamp(),
            "last_update": time.time()
        }

    async def update_presences(self) -> None:
        with open("presence.fem", "r") as file:
            code = file.read()

            self.presences = []

            femscript = Femscript(code, variables = [
                var("guilds", str(len(self.gateway.guilds))),
                var("users", str(len(self.gateway.users))),
                var("StatusTypes", variables = [
                    var(status_type.name, status_type) for status_type in femcord.StatusTypes
                ]),
                var("ActivityTypes", variables = [
                    var(status_type.name, status_type) for status_type in femcord.ActivityTypes
                ])
            ], modules = self.femscript_modules)

            @femscript.wrap_function()
            def set_update_interval(interval: str | int):
                self.presence_update_interval = interval

            @femscript.wrap_function()
            def set_random_presence(value: bool):
                self.random_presence = value

            @femscript.wrap_function()
            def add_presence(*, name: str = None, status_type: femcord.StatusTypes = femcord.StatusTypes.ONLINE, activity_type: femcord.ActivityTypes = femcord.ActivityTypes.PLAYING):
                self.presences.append(femcord.Presence(self, status_type, activities=[femcord.Activity(self, name, activity_type)]))

            femscript.wrap_function(request)

            await femscript.execute(debug=True)

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

    async def update_user_install_count(self) -> None:
        data = await self.http.request(Route("GET", "applications", "@me"))
        self.user_install_count = data["approximate_user_install_count"]

    async def get_prefix(self, _, message: femcord.types.Message) -> list[str]:
        prefixes = ["<@{}>", "<@!{}>", "<@{}> ", "<@!{}> "]
        prefixes = [prefix.format(self.gateway.bot_user.id) for prefix in prefixes]

        if not message.guild:
            return prefixes

        if hasattr(message.guild, "prefix"):
            return prefixes + [message.guild.prefix or config.PREFIX]

        db_guild = await Guilds.filter(guild_id=message.guild.id).first()
        message.guild.prefix = db_guild.prefix

        return prefixes + [message.guild.prefix or config.PREFIX]

    def get_translations_for(self, name: str) -> dict[str, dict[str, AST]]:
        translations = {}

        for lang in os.listdir("./cogs/translations/" + name):
            lang, extension = lang.split(".")
            translations[lang] = {}

            with open("./cogs/translations/" + name + "/" + lang + "." + extension) as file:
                content = file.read()

            femscript = Femscript(content)

            for ast in femscript.ast:
                translations[lang][ast["children"][0]["token"]["value"]] = ast

        return translations

if __name__ == "__main__":
    Bot().run(config.TOKEN)