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
from femcord.femcord.enums import CommandOptionTypes, InteractionTypes, InteractionCallbackTypes
from femscript import Femscript, var, FemscriptException
from datetime import timezone
from poligonlgbt import get_extension
from utils import *
from types import CoroutineType
from models import Guilds
from enum import Enum
import config, datetime

from typing import Union, Literal, TypedDict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context

class CommandOperation(Enum):
    UPDATE = 0
    GET_CODE = 1
    GET_COMMANDS = 2
    REMOVE_COMMAND = 3
    MISSING_INIT = 4

class CommandData(TypedDict):
    name: str
    description: str
    usage: str
    aliases: list[str]
    arguments: dict[str, Literal["str", "int", "Channel", "Role", "User"]]
    prefix: str

class CustomCommands(commands.Cog):
    name = "Custom Commands"
    description = "Commands that are available only on this server"

    def __init__(self):
        self.prefixes = []

    def append_prefix(self, prefix):
        if prefix not in self.prefixes:
            self.prefixes.append(prefix)

class Other(commands.Cog):
    def __init__(self, bot: "Bot", custom_commands_cog: commands.Cog) -> None:
        self.bot = bot
        self.custom_commands_cog = custom_commands_cog

    def command_data_to_slash(self, command: CommandData) -> dict:
        return {
            "name": command["name"],
            "description": command["description"] if command["description"] else command["name"],
            "options": [
                {
                    "type": {
                        "str": CommandOptionTypes.STRING,
                        "int": CommandOptionTypes.INTEGER,
                        "Channel": CommandOptionTypes.CHANNEL,
                        "Role": CommandOptionTypes.ROLE,
                        "User": CommandOptionTypes.USER
                    }[_type].value,
                    "name": name,
                    "description": name,
                    "required": True
                }
                for name, _type in command["arguments"].items()
            ]
        }

    @commands.Listener
    async def on_ready(self):
        for guild in self.bot.gateway.guilds:
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
                    eventhandlers = {},
                    interaction_callbacks = {}
                )

            commands = []

            for custom_command in db_guild.custom_commands:
                try:
                    command_data = (await self.get_command_data(custom_command))[1]
                    commands.append(command_data)
                    self.create_custom_command(guild.id, command_data, custom_command)
                except FemscriptException:
                    pass
                except Exception:
                    pass

            if not commands:
                continue

            try:
                await self.bot.http.request(Route("PUT", "applications", self.bot.gateway.bot_user.id, "guilds", guild.id, "commands"), data=[self.command_data_to_slash(command) for command in commands])
            except femcord.HTTPException:
                pass

    @commands.hybrid_command(description="pisaju skrypt", usage="(code)", aliases=["fs", "fscript", "cs", "cscript"])
    async def femscript(self, ctx: Union["Context", "AppContext"], *, code):
        database = {}

        if ctx.guild:
            guild = Guilds.get(guild_id=ctx.guild.id)
            database = (await guild).database

        fake_token = var("token", "MTAwOTUwNjk4MjEyMzgwMjY4NA.G0LFJN.o7zP2DxrjQDQQIqjtVUEN98jmlB1bEQN1rTchQ")

        variables = [
            var("bot", variables = [
                fake_token,
                var("gateway", variables = [
                    fake_token
                ]),
                var("http", variables = [
                    fake_token
                ])
            ])
        ] + [
            {
                "name": key,
                "value": Femscript.to_fs(value)
            }
            for key, value in (convert(author=ctx.author, channel=ctx.channel, guild=ctx.guild, member=ctx.member) | database).items()
        ]

        femscript = Femscript(code, variables=variables, modules=self.bot.femscript_modules)

        if ctx.guild and ctx.member.permissions.has(femcord.enums.Permissions.MANAGE_GUILD):
            @femscript.wrap_function()
            def get_all() -> dict[str, object]:
                return database

            @femscript.wrap_function()
            def get_value(key: str) -> Any:
                return database.get(key)

            @femscript.wrap_function()
            def update[T](key: str, value: T) -> T:
                database[key] = value
                return value

            @femscript.wrap_function()
            def remove(key: str) -> Any:
                return database.pop(key)

        @femscript.wrap_function()
        async def get_user(user: str) -> dict:
            return convert(_=await self.bot.gateway.get_user(user)).get("_")

        @femscript.wrap_function()
        def get_channel(channel: str) -> dict:
            return convert(_=ctx.guild.get_channel(channel)).get("_")

        femscript.wrap_function(request)

        wrap_builtins(femscript)

        result = await femscript.execute(debug=ctx.author.id in self.bot.owners)

        if ctx.guild:
            await guild.update(database=database)

        if hasattr(femscript, "is_components_v2"):
            return await ctx.reply(components=result, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

        if isinstance(result, femcord.Embed):
            to_check = ("image", "thumbnail", "author", "footer")
            files = []

            for item in to_check:
                if hasattr(result, item):
                    image_key = "url" if item in ("image", "thumbnail") else "icon_url"
                    data = getattr(result, item)[image_key]
                    if not isinstance(data, bytes):
                        continue
                    files.append((item + ".png", bytes(data)))
                    getattr(result, item)[image_key] = "attachment://" + item + ".png"

            return await ctx.reply(embed=result, files=files)

        if isinstance(result, bytes) and get_extension(result) == "png":
            return await ctx.reply(files=[(ctx.author.id + ".png", result)])

        result = str(result)

        prefix_suffix = "```"

        if len(result) < 100:
            prefix_suffix = ""

        await ctx.reply_paginator(result or "(empty result)", prefix=prefix_suffix, suffix=prefix_suffix)

    @commands.Listener
    async def on_message_create(self, message):
        if message.author.bot or not message.guild:
            return

        for prefix in self.custom_commands_cog.prefixes:
            if prefix is not None and message.content.startswith(prefix):
                command_name = message.content.split(" ")[0][len(prefix):]
                command = self.bot.get_command(command_name, guild_id=message.guild.id)

                if not command or ("prefix" in command.other and not command.other["prefix"] == prefix):
                    return

                fake_message = self.bot.gateway.copy(message)
                fake_message.content = (await self.bot.get_prefix(self.bot, message))[-1] + message.content[len(prefix):]

                return await self.bot.process_commands(fake_message)

    async def get_command_data(self, code: str) -> tuple[CommandOperation, CommandData]:
        femscript = Femscript(code)

        command_data = {
            "operation": CommandOperation.UPDATE,
            "name": None,
            "description": None,
            "usage": None,
            "aliases": [],
            "arguments": {},
            "prefix": None
        }

        if not (len(femscript.ast) > 0 and femscript.ast[0]["type"] == "Token" and femscript.ast[0]["token"]["value"] in ("command", "remove_command", "get_commands", "get_command_code")):
            return CommandOperation.MISSING_INIT, command_data

        femscript.ast = femscript.ast[0:1]

        @femscript.wrap_function()
        def command(*, name: str, description: str = None, usage: str = None, aliases: list[str] = None, arguments: dict[str, str] = None, prefix: str = None) -> None:
            if not isinstance(name, str):
                raise FemscriptException("Name must be a string")
            if description and not isinstance(description, str):
                raise FemscriptException("Description must be a string")
            if usage and not isinstance(usage, str):
                raise FemscriptException("Usage must be a string")
            if aliases is not None:
                if not isinstance(aliases, list):
                    raise FemscriptException("Aliases must be a list with strings")
                for item in aliases:
                    if not isinstance(item, str):
                        raise FemscriptException("Aliases must be a list with strings")
            if arguments is not None:
                if not isinstance(arguments, dict):
                    raise FemscriptException("Arguments must be a scope")
                for value in arguments.values():
                    if value not in ("str", "int", "Channel", "Role", "User"):
                        raise FemscriptException("Values in arguments must be str, int, Channel, Role or User")
            if prefix and not isinstance(prefix, str):
                raise FemscriptException("Prefix must be a string")

            command_data["name"] = name
            command_data["description"] = description
            command_data["usage"] = usage
            command_data["aliases"] = aliases or []
            command_data["arguments"] = arguments or {}
            command_data["prefix"] = prefix

        @femscript.wrap_function()
        def get_command_code(name: str) -> None:
            command_data["operation"] = CommandOperation.GET_CODE
            command_data["name"] = name

        @femscript.wrap_function()
        def get_commands() -> None:
            command_data["operation"] = CommandOperation.GET_COMMANDS

        @femscript.wrap_function()
        def remove_command(name: str) -> None:
            command_data["operation"] = CommandOperation.REMOVE_COMMAND
            command_data["name"] = name

        await femscript.execute()

        if command_data["prefix"] is not None:
            self.custom_commands_cog.append_prefix(command_data["prefix"])

        return command_data.pop("operation"), command_data

    def create_custom_command(self, guild_id: str, command_data: CommandData, code: str) -> commands.Command:
        async def func(ctx: "Context", args: list = None) -> Any:
            async with femcord.Typing(ctx.channel):
                guild = Guilds.get(guild_id=ctx.guild.id)

                if args is not None:
                    args = args[0]
                    values = list(command_data["arguments"].values())

                    normal_types = {
                        "str": str,
                        "int": float
                    }

                    discord_types = {
                        "User": lambda item: types.User.from_arg(ctx, item),
                        "Channel": lambda item: types.Channel.from_arg(ctx, item),
                        "Role": lambda item: types.Role.from_arg(ctx, item)
                    }

                    for index, item in enumerate(args):
                        if index >= len(values):
                            break
                        
                        _type = values[index]

                        if _type == "str" and index + 1 >= len(values):
                            args[index] = " ".join(args[index:])
                            break
                        elif _type in normal_types:
                            args[index] = normal_types[_type](item)
                        elif _type in discord_types:
                            result = discord_types[_type](item)
                            if isinstance(result, CoroutineType):
                                result = await result

                            args[index] = convert(_=result)["_"]
                            continue

                    args = dict(zip(command_data["arguments"].keys(), args))

                converted = convert(guild=ctx.guild, channel=ctx.channel, author=ctx.author, member=ctx.member)
                database = (await guild).database

                variables = [
                    {
                        "name": key,
                        "value": Femscript.to_fs(value)
                    }
                    for key, value in (converted | (args or {}) | database).items()
                ]

                femscript = Femscript(code, variables=variables, modules=self.bot.femscript_modules)

                @femscript.wrap_function()
                def get_all() -> dict[str, object]:
                    return database

                @femscript.wrap_function()
                def get_value(key: str) -> Any:
                    return database.get(key)

                @femscript.wrap_function()
                def update[T](key: str, value: T) -> T:
                    database[key] = value
                    return value

                @femscript.wrap_function()
                def remove(key: str) -> Any:
                    return database.pop(key)

                @femscript.wrap_function()
                async def get_user(user: str) -> dict:
                    return convert(_=await self.bot.gateway.get_user(user)).get("_")

                @femscript.wrap_function()
                async def add_role(user_id: str, role_id: str) -> None:
                    member = await ctx.guild.get_member(user_id)
                    role = ctx.guild.get_role(role_id)
                    await member.add_role(role)

                @femscript.wrap_function()
                async def remove_role(user_id: str, role_id: str) -> None:
                    member = await ctx.guild.get_member(user_id)
                    role = ctx.guild.get_role(role_id)
                    await member.remove_role(role)

                @femscript.wrap_function()
                async def kick(user_id: str, reason: Optional[str] = None) -> None:
                    member = await ctx.guild.get_member(user_id)
                    await member.kick(reason)

                @femscript.wrap_function()
                async def ban(user_id: str, reason: Optional[str] = None) -> None:
                    member = await ctx.guild.get_member(user_id)
                    await member.ban(reason)

                @femscript.wrap_function()
                async def unban(user_id: str, reason: Optional[str] = None) -> None:
                    await ctx.guild.unban(user_id, reason)

                @femscript.wrap_function()
                async def timeout(user_id: str, seconds: int) -> None:
                    member = await ctx.guild.get_member(user_id)
                    await member.modify(communication_disabled_until=datetime.datetime.now(tz=timezone.utc) + datetime.timedelta(seconds=seconds))

                @femscript.wrap_function()
                def get_channel(channel: str) -> dict:
                    return convert(_=ctx.guild.get_channel(channel)).get("_")

                femscript.wrap_function(request)

                wrap_builtins(femscript)

                femscript.wrap_function(lambda *_, **__: None, func_name="command")

                result = await femscript.execute()

                await guild.update(database=database)

                if hasattr(femscript, "is_components_v2"):
                    return await ctx.reply(components=result, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

                if isinstance(result, femcord.Embed):
                    to_check = ("image", "thumbnail", "author", "footer")
                    files = []

                    for item in to_check:
                        if hasattr(result, item):
                            image_key = "url" if item in ("image", "thumbnail") else "icon_url"
                            data = getattr(result, item)[image_key]
                            if not isinstance(data, bytes):
                                continue
                            files.append((item + ".png", bytes(data)))
                            getattr(result, item)[image_key] = "attachment://" + item + ".png"

                    return await ctx.reply(embed=result, files=files)

                if isinstance(result, bytes) and get_extension(result) == "png":
                    return await ctx.reply(files=[(ctx.author.id + ".png", result)])

                await ctx.reply_paginator(str(result) or "(empty result)", replace=False)

        if command_data["usage"] is None and command_data["arguments"]:
            command_data["usage"] = " ".join(["(" + key + ":" + value + ")" for key, value in command_data["arguments"].items()])

        kwargs = {
            **command_data,
            "cog": self.custom_commands_cog,
            "guild_id": guild_id,
            "other": {
                "prefix": command_data["prefix"],
                "display_name": command_data["name"],
                "code": code
            }
        }

        kwargs["name"] = guild_id + "_" + command_data["name"]
        kwargs["aliases"].append(command_data["name"])
        del kwargs["prefix"]

        if command_data["arguments"]:
            @commands.command(**kwargs)
            async def command(_, ctx, *args):
                await func(ctx, args)
        else:
            @commands.command(**kwargs)
            async def command(_, ctx):
                await func(ctx)

        self.custom_commands_cog.commands.append(command)
        self.bot.commands.append(command)

        return command

    @commands.command(description="Creating a custom command", usage="(code)", aliases=["cc", "createcommand"])
    @commands.has_permissions("manage_guild", "manage_roles", "ban_members", "kick_members", "moderate_members")
    async def customcommand(self, ctx: "Context", *, code):
        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        guild = Guilds.get(guild_id=ctx.guild.id)
        custom_commands = (await guild).custom_commands

        operation, command_data = await self.get_command_data(code)

        if operation is CommandOperation.MISSING_INIT:
            return await ctx.reply("Your code hasn't initialised the command")
        elif operation is CommandOperation.GET_CODE:
            command = self.bot.get_command(command_data["name"], guild_id=ctx.guild.id)

            if not command:
                raise commands.CommandNotFound()

            return await ctx.reply_paginator(highlight(command.other["code"]), by_lines=True, base_embed=femcord.Embed(), prefix="```ansi\n", suffix="```")
        elif operation is CommandOperation.GET_COMMANDS:
            return await ctx.reply_paginator(pages=custom_commands, prefix="```py\n", suffix="```")
        elif operation is CommandOperation.REMOVE_COMMAND:
            command = self.bot.get_command(command_data["name"], guild_id=ctx.guild.id)

            if not command:
                raise commands.CommandNotFound()

            custom_commands.remove(command.other["code"])
            self.bot.remove_command(command)

            await guild.update(custom_commands=custom_commands)

            try:
                slash_commands = await self.bot.http.request(Route("GET", "applications", self.bot.gateway.bot_user.id, "guilds", ctx.guild.id, "commands"))
                command_id, = [slash_command["id"] for slash_command in slash_commands if slash_command["name"] == command_data["name"] and slash_command["type"] == 1]
                await self.bot.http.request(Route("DELETE", "applications", self.bot.gateway.bot_user.id, "guilds", ctx.guild.id, "commands", command_id))
            except femcord.HTTPException:
                pass

            return await ctx.reply("Removed")

        command_object = self.bot.get_command(command_data["name"], guild_id=ctx.guild.id)

        for alias in command_data["aliases"]:
            alias_command = self.bot.get_command(alias, guild_id=ctx.guild.id)
            if alias_command is not None and not alias_command.name == ctx.guild.id + "_" + command_data["name"]:
                return await ctx.reply(f"Alias `{alias}` is already used in the bot")

        text = "Created"

        if command_object is not None:
            custom_commands.remove(command_object.other["code"])
            self.bot.remove_command(command_object)

            text = "Updated"

        command = self.create_custom_command(ctx.guild.id, command_data, code)

        custom_commands.append(code)
        await guild.update(custom_commands=custom_commands)

        try:
            await self.bot.http.request(Route("POST", "applications", self.bot.gateway.bot_user.id, "guilds", ctx.guild.id, "commands"), data=self.command_data_to_slash(command_data))
        except femcord.HTTPException:
            pass

        await ctx.reply(text)

    async def handle_slash_command(self, interaction: femcord.types.Interaction, command: commands.Command):
        await interaction.callback(InteractionCallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)

        fake_channel = femcord.types.Channel(**interaction.channel.__dict__)
        async def start_typing_hook():
            pass
        fake_channel.start_typing = start_typing_hook

        fake_message = femcord.types.Message(self.bot, id="0", channel=fake_channel, guild=interaction.guild, author=interaction.user, member=interaction.member)
        context = commands.Context(self.bot, fake_message)

        args = []
        kwargs = {}

        async def reply_hook(*_args, **_kwargs):
            nonlocal args, kwargs
            args = _args
            kwargs = _kwargs

        async def paginator_reply_hook(*_args, **_):
            nonlocal args
            args = _args

        context.reply = reply_hook
        context.reply_paginator = paginator_reply_hook

        if interaction.data.options:
            await command(context, [
                {
                    CommandOptionTypes.STRING: lambda argument: argument,
                    CommandOptionTypes.INTEGER: lambda argument: argument,
                    CommandOptionTypes.CHANNEL: lambda argument: argument.id,
                    CommandOptionTypes.ROLE: lambda argument: argument.id,
                    CommandOptionTypes.USER: lambda argument: argument.id
                }[argument.type](argument.value)
                for argument in interaction.data.options]
            )
        else:
            await command(context)

        await interaction.edit(*args, **kwargs)

    @commands.Listener
    async def on_interaction_create(self, interaction: femcord.types.Interaction):
        if interaction.type is InteractionTypes.APPLICATION_COMMAND and interaction.guild and (command := self.bot.get_command(interaction.data.name, guild_id=interaction.guild.id)):
            await self.handle_slash_command(interaction, command)
        if not interaction.guild or interaction.data.custom_id not in interaction.guild.interaction_callbacks:
            return

        await interaction.callback(InteractionCallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE, flags=[femcord.MessageFlags.EPHEMERAL])

        guild = Guilds.get(guild_id=interaction.guild.id)
        converted = convert(guild=interaction.guild, channel=interaction.channel, user=interaction.user, member=interaction.member, interaction=interaction)
        database = (await guild).database

        variables = [
            {
                "name": key,
                "value": Femscript.to_fs(value)
            }
            for key, value in (converted | database).items()
        ]

        femscript = Femscript(interaction.guild.interaction_callbacks[interaction.data.custom_id], variables=variables, modules=self.bot.femscript_modules)

        @femscript.wrap_function()
        def get_all() -> dict[str, object]:
            return database

        @femscript.wrap_function()
        def get_value(key: str) -> Any:
            return database.get(key)

        @femscript.wrap_function()
        def update[T](key: str, value: T) -> T:
            database[key] = value
            return value

        @femscript.wrap_function()
        def remove(key: str) -> Any:
            return database.pop(key)

        @femscript.wrap_function()
        async def get_user(user: str) -> dict:
            return convert(_=await self.bot.gateway.get_user(user)).get("_")

        @femscript.wrap_function()
        def get_channel(channel: str) -> dict:
            return convert(_=ctx.guild.get_channel(channel)).get("_")

        @femscript.wrap_function()
        async def add_role(user_id: str, role_id: str) -> None:
            member = await interaction.guild.get_member(user_id)
            role = interaction.guild.get_role(role_id)
            await member.add_role(role)

        @femscript.wrap_function()
        async def remove_role(user_id: str, role_id: str) -> None:
            member = await interaction.guild.get_member(user_id)
            role = interaction.guild.get_role(role_id)
            await member.remove_role(role)

        @femscript.wrap_function()
        async def timeout(user_id: str, seconds: int) -> None:
            member = await interaction.guild.get_member(user_id)
            await member.modify(communication_disabled_until=datetime.datetime.now(tz=timezone.utc) + datetime.timedelta(seconds=seconds))

        femscript.wrap_function(request)

        wrap_builtins(femscript)

        result = await femscript.execute()

        await guild.update(database=database)

        if hasattr(femscript, "is_components_v2"):
            return await interaction.edit(components=result, flags=[femcord.MessageFlags.EPHEMERAL, femcord.MessageFlags.IS_COMPONENTS_V2])

        await interaction.edit(**{"content" if not isinstance(result, femcord.Embed) else "embed": result}, flags=[femcord.MessageFlags.EPHEMERAL])

    @commands.command(description="Creating an interaction callback", usage="(custom_id) [code]", aliases=["bind"])
    @commands.has_permissions("manage_guild", "manage_roles")
    async def callback(self, ctx: "Context", custom_id, *, code = None) -> None:
        guild = Guilds.get(guild_id=ctx.guild.id)
        interaction_callbacks = (await guild).interaction_callbacks

        if code == "remove":
            if custom_id not in interaction_callbacks:
                await ctx.reply("This callback doesn't exist")
                return

            interaction_callbacks.pop(custom_id)
            ctx.guild.interaction_callbacks = interaction_callbacks
            await guild.update(interaction_callbacks=interaction_callbacks)

            await ctx.reply("Callback has been removed")
            return

        if not code:
            if custom_id not in interaction_callbacks:
                await ctx.reply("This callback doesn't exist")
                return

            return await ctx.reply_paginator(highlight(interaction_callbacks[custom_id]), by_lines=True, base_embed=femcord.Embed(), prefix="```ansi\n", suffix="```")

        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        interaction_callbacks[custom_id] = code
        ctx.guild.interaction_callbacks = interaction_callbacks
        await guild.update(interaction_callbacks=interaction_callbacks)

        await ctx.reply("Callback has been set")

def setup(bot: "Bot") -> None:
    bot.load_cog(custom_commands_cog := CustomCommands())
    bot.load_cog(Other(bot, custom_commands_cog))