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

import femcord.femcord as femcord
from femcord.femcord import commands, types
from femscript import Femscript, var, FemscriptException
from utils import *
from types import CoroutineType
from models import Guilds
from typing import List, Dict, Tuple, Literal, TypedDict, Any
from enum import Enum
import config, datetime

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
    aliases: List[str]
    arguments: Dict[str, Literal["str", "int", "Channel", "Role", "User"]]
    prefix: str

class CustomCommands(commands.Cog):
    name = "Custom Commands"
    description = "Commands that are available only on this server"

    def __init__(self):
        self.prefixes = []

    def append_prefix(self, prefix):
        self.prefixes.append(prefix)

        if "" in self.prefixes:
            self.prefixes.remove("")
            self.prefixes.append("")

class Other(commands.Cog):
    def __init__(self, bot: commands.Bot, custom_commands_cog: commands.Cog) -> None:
        self.bot = bot
        self.custom_commands_cog = custom_commands_cog

    @commands.Listener
    async def on_ready(self):
        for guild in self.bot.gateway.guilds:
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            if db_guild is None:
                db_guild = await Guilds.create(guild_id=guild.id, prefix=config.PREFIX, welcome_message="", leave_message="", autorole="", custom_commands=[], database={}, permissions={}, schedules=[])

            for custom_command in db_guild.custom_commands:
                try:
                    self.create_custom_command(guild.id, (await self.get_command_data(custom_command))[1], custom_command)
                except FemscriptException:
                    pass
                except Exception:
                    pass

    @commands.command(description="pisaju skrypt", usage="(code)", aliases=["fs", "fscript", "cs", "cscript"])
    async def femscript(self, ctx: commands.Context, *, code):
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
            for key, value in (convert(author=ctx.author, channel=ctx.channel, guild=ctx.guild) | database).items()
        ]

        femscript = Femscript(code, variables=variables)

        if ctx.member.permissions.has(femcord.enums.Permissions.MANAGE_GUILD):
            @femscript.wrap_function()
            def get_all() -> Dict[str, object]:
                return database

            @femscript.wrap_function()
            def get(key: str) -> Any:
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
        femscript.wrap_function(femcord.Embed)

        result = await femscript.execute(debug=ctx.author.id in self.bot.owners)

        await guild.update(database=database)

        if isinstance(result, femcord.Embed):
            return await ctx.reply(embed=result)

        result = str(result)

        prefix_suffix = "```"

        if len(result) < 100:
            prefix_suffix = ""

        await self.bot.paginator(ctx.reply, ctx, result or "(empty result)", prefix=prefix_suffix, suffix=prefix_suffix)

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

    async def get_command_data(self, code: str) -> Tuple[CommandOperation, CommandData]:
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
        def command(*, name: str, description: str = None, usage: str = None, aliases: List[str] = None, arguments: Dict[str, str] = None, prefix: str = None) -> None:
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
        async def func(ctx: commands.Context, args: list = None) -> Any:
            async with femcord.Typing(ctx.message):
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
                        _type = values[index]

                        if _type == "str" and index + 1 >= len(values):
                            args = [" ".join(args[index:])]
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

                converted = convert(guild=ctx.guild, channel=ctx.channel, author=ctx.author)
                database = (await guild).database

                variables = [
                    {
                        "name": key,
                        "value": Femscript.to_fs(value)
                    }
                    for key, value in (converted | (args or {}) | database).items()
                ]

                femscript = Femscript(code, variables=variables)

                @femscript.wrap_function()
                def get_all() -> Dict[str, object]:
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
                femscript.wrap_function(femcord.Embed)

                femscript.wrap_function(lambda *_, **__: None, func_name="command")

                result = await femscript.execute()

                await guild.update(database=database)

                if isinstance(result, femcord.Embed):
                    return await ctx.reply(embed=result)

                await self.bot.paginator(ctx.reply, ctx, str(result) or "(empty result)", replace=False)

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
    @commands.has_permissions("manage_guild")
    async def customcommand(self, ctx: commands.Context, *, code):
        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        guild = Guilds.get(guild_id=ctx.guild.id)
        custom_commands = (await guild).custom_commands

        operation, command_data = await self.get_command_data(code)

        if operation == CommandOperation.MISSING_INIT:
            return await ctx.reply("Your code hasn't initialised the command")
        elif operation == CommandOperation.GET_CODE:
            command = self.bot.get_command(command_data["name"], guild_id=ctx.guild.id)

            if not command:
                raise commands.CommandNotFound()

            return await self.bot.paginator(ctx.reply, ctx, command.other["code"], prefix="```py\n", suffix="```")
        elif operation == CommandOperation.GET_COMMANDS:
            return await self.bot.paginator(ctx.reply, ctx, pages=custom_commands, prefix="```py\n", suffix="```")
        elif operation == CommandOperation.REMOVE_COMMAND:
            command = self.bot.get_command(command_data["name"], guild_id=ctx.guild.id)

            if not command:
                raise commands.CommandNotFound()

            custom_commands.remove(command.other["code"])
            self.bot.remove_command(command)

            await guild.update(custom_commands=custom_commands)

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

        await ctx.reply(text)

def setup(bot: commands.Bot) -> None:
    bot.load_cog(custom_commands_cog := CustomCommands())
    bot.load_cog(Other(bot, custom_commands_cog))