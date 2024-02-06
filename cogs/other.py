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
from femscript import Lexer, Parser, run, Dict, Femscript, var, FemscriptException
from utils import *
from types import CoroutineType
from models import Guilds
from typing import List, Dict, Literal, TypedDict
import config, re, datetime

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
    def __init__(self, bot, custom_commands_cog):
        self.bot: commands.Bot = bot
        self.custom_commands_cog = custom_commands_cog

    @commands.Listener
    async def on_ready(self):
        for guild in self.bot.gateway.guilds:
            db_guild = await Guilds.filter(guild_id=guild.id).first()

            if db_guild is None:
                db_guild = await Guilds.create(guild_id=guild.id, prefix=config.PREFIX, welcome_message="", leave_message="", autorole="", custom_commands=[], database={}, permissions={}, schedules=[])

            for custom_command in db_guild.custom_commands:
                try:
                    self.create_custom_command(guild.id, await self.get_command_data(custom_command), custom_command)
                except FemscriptException:
                    pass
                except Exception:
                    pass

    @commands.command(description="pisaju skrypt", usage="(kod)", aliases=["fs", "fscript", "cs", "cscript"])
    async def femscript(self, ctx: commands.Context, *, code):
        result = await run(
            code,
            modules = {
                **await get_modules(self.bot, ctx.guild, ctx=ctx),
                **(
                    {
                        "database": {}
                    }
                    if not ctx.member.permissions.has("manage_guild") else
                    {

                    }
                ),
                **(
                    {
                        "owneronly": {
                            "builtins": {
                                "call": lambda function, *args, **kwargs: function(*args, **kwargs),
                                "py_builtins": Dict(**__builtins__),
                                "send": ctx.send,
                                "reply": ctx.reply
                            },
                            "variables": {
                                "femcord": femcord,
                                "_bot": self.bot,
                                "ctx": ctx
                            }
                        }
                    }
                    if ctx.author.id in self.bot.owners else
                    {

                    }
                )
            },
            builtins = builtins,
            variables = {
                **convert(
                    guild = ctx.guild,
                    channel = ctx.channel,
                    author = ctx.author
                ),
                "bot": {
                    "token": "MTAwOTUwNjk4MjEyMzgwMjY4NA.G0LFJN.o7zP2DxrjQDQQIqjtVUEN98jmlB1bEQN1rTchQ",
                    "gateway": {
                        "token": "MTAwOTUwNjk4MjEyMzgwMjY4NA.G0LFJN.o7zP2DxrjQDQQIqjtVUEN98jmlB1bEQN1rTchQ"
                    },
                    "http": {
                        "token": "MTAwOTUwNjk4MjEyMzgwMjY4NA.G0LFJN.o7zP2DxrjQDQQIqjtVUEN98jmlB1bEQN1rTchQ"
                    }
                },
                "sex": 69,
                "dupa": True
            }
        )

        if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], femcord.Embed):
            return await ctx.reply(result[0], embed=result[1])

        if isinstance(result, femcord.Embed):
            return await ctx.reply(embed=result)

        result = str(result)

        prefix_suffix = "```"

        if len(result) < 100:
            prefix_suffix = ""

        await self.bot.paginator(ctx.reply, ctx, result, prefix=prefix_suffix, suffix=prefix_suffix)

    @commands.command(description="pisaju skrypt w rewrite", usage="(kod)", aliases=["fsr"])
    async def femscriptrewrite(self, ctx: commands.Context, *, code):
        fake_token = var("token", "MTAwOTUwNjk4MjEyMzgwMjY4NA.G0LFJN.o7zP2DxrjQDQQIqjtVUEN98jmlB1bEQN1rTchQ")

        variables = [
            var("author", variables = [
                var("id", ctx.author.id),
                var("username", ctx.author.username),
                var("avatar_url", ctx.author.avatar_url),
                var("bot", ctx.author.bot)
            ]),
            var("bot", variables = [
                fake_token,
                var("gateway", variables = [
                    fake_token
                ]),
                var("http", variables = [
                    fake_token
                ])
            ])
        ]

        femscript = Femscript(code, variables=variables)

        logs = []

        @femscript.wrap_function()
        def log(text):
            logs.append(text)

        femscript.wrap_function(request)
        femscript.wrap_function(femcord.Embed)

        result = await femscript.execute(debug=ctx.author.id in self.bot.owners)

        if isinstance(result, femcord.Embed):
            return await ctx.reply(embed=result)

        result = str(result)

        result = "\n".join([f"{index}. {log}" for index, log in enumerate(logs, 1)]) + "\n\n" + result

        prefix_suffix = "```"

        if len(result) < 100:
            prefix_suffix = ""

        await self.bot.paginator(ctx.reply, ctx, result, prefix=prefix_suffix, suffix=prefix_suffix)

    @commands.Listener
    async def on_message_create(self, message):
        if message.author.bot:
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
            
    async def get_command_data(self, code: str) -> CommandData:
        femscript = Femscript(code)

        if not (len(femscript.ast) > 0 and femscript.ast[0]["type"] == "Token" and femscript.ast[0]["token"]["value"] == "command"):
            raise Exception("Missing initialization")

        femscript.ast = femscript.ast[0:1]

        command_data = {
            "name": None,
            "description": None,
            "usage": None,
            "aliases": [],
            "arguments": {},
            "prefix": None
        }

        @femscript.wrap_function()
        def command(*, name: str, description: str = None, usage: str = None, aliases: List[str] = None, arguments: Dict[str, str] = None, prefix: str = None):
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

        await femscript.execute()

        if command_data["prefix"] is not None:
            self.custom_commands_cog.append_prefix(command_data["prefix"])
        
        return command_data
            
    def create_custom_command(self, guild_id: str, command_data: CommandData, code: str) -> commands.Command:
        async def func(ctx, args = None) -> object:
            async with femcord.Typing(ctx.message):
                converted = convert(guild=ctx.guild, channel=ctx.channel, author=ctx.author)

                variables = [
                    {
                        "name": key,
                        "value": Femscript.to_fs(value)
                    }
                    for key, value in converted.items()
                ]

                femscript = Femscript(code, variables=variables)

                femscript.wrap_function(request)
                femscript.wrap_function(femcord.Embed)

                femscript.wrap_function(void, func_name="command")

                result = await femscript.execute()

                if isinstance(result, femcord.Embed):
                    return await ctx.reply(embed=result)
                
                await self.bot.paginator(ctx.reply, ctx, str(result), replace=False)                

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

        if command_data["usage"] is not None:
            command.usage = "(" + command_data["usage"][0] + ")" + (" " if len(command_data["usage"]) > 1 else "") + " ".join("[" + item + "]" for item in command_data["usage"][1:])

        self.custom_commands_cog.commands.append(command)
        self.bot.commands.append(command)

        return command

    @commands.command(description="Creating a custom command", usage="(code)", aliases=["cc", "createcommand"])
    @commands.has_permissions("manage_guild")
    async def customcommand(self, ctx: commands.Context, *, code):
        guild = Guilds.get(guild_id=ctx.guild.id)
        custom_commands = (await guild).custom_commands

        try:
            command_data = await self.get_command_data(code)
        except FemscriptException as exc:
            return await ctx.reply(exc)
        except Exception:
            return await ctx.reply("Your code hasn't initialised the command")

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

    # @commands.command(description="Creating a custom command", usage="(code)", aliases=["cc", "createcommand"])
    # @commands.has_permissions("manage_guild")
    async def _(self, ctx: commands.Context, *, code):
        guild = Guilds.get(guild_id=ctx.guild.id)
        custom_commands = (await guild).custom_commands

        command_prefix = None
        command_name = None
        command_description = None
        command_usage = None
        command_aliases = []
        command_arguments = {}

        return_text = None

        def set_command_name(name, *, prefix = None):
            nonlocal command_prefix, command_name, code
            command_prefix = prefix
            command_name = name

            if prefix is not None and not prefix in self.custom_commands_cog.prefixes:
                self.custom_commands_cog.append_prefix(prefix)

            if not re.findall(r"# (DATE|GUILD|CHANNEL|AUTHOR): \d+", code) == ["DATE", "GUILD", "CHANNEL", "AUTHOR"]:
                code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
                       f"# GUILD: {ctx.guild.id}\n" \
                       f"# CHANNEL: {ctx.channel.id}\n" \
                       f"# AUTHOR: {ctx.author.id}\n\n" \
                     + code

        def set_command_description(description):
            nonlocal command_description
            command_description = description

        def set_command_usage(*usage):
            nonlocal command_usage
            command_usage = usage

        def set_command_aliases(*aliases):
            nonlocal command_aliases
            command_aliases = list(aliases)

        def set_command_arguments(**arguments):
            nonlocal command_arguments

            _types = {
                "str": str,
                "int": int,
                "user": types.User,
                "channel": types.Channel,
                "role": types.Role
            }

            for key, value in arguments.items():
                if value in _types:
                    command_arguments[key] = _types[value]
                    if value == "str":
                        parser.variables[key] = ""
                    elif value == "int":
                        parser.variables[key] = 0
                    elif value == "user":
                        parser.variables[key] = convert(_=ctx.author)["_"]
                    elif value == "channel":
                        parser.variables[key] = convert(_=ctx.channel)["_"]
                    elif value == "role":
                        parser.variables[key] = convert(_=ctx.member.roles[0])["_"]
                    continue

                command_arguments[key] = value
                parser.variables[key] = value

        async def get_command_code(name):
            nonlocal return_text

            command = self.bot.get_command(name, guild_id=ctx.guild.id)

            if not command or not "code" in command.other or not command.guild_id == ctx.guild.id:
                raise commands.CommandNotFound()

            await self.bot.paginator(ctx.reply, ctx, command.other["code"], prefix="```py\n", suffix="```")

            return_text = ""

        async def get_commands():
            nonlocal return_text

            await self.bot.paginator(ctx.reply, ctx, pages=custom_commands, prefix="```py\n", suffix="```")

            return_text = ""

        def delete_command(name):
            nonlocal return_text

            command = self.bot.get_command(ctx.guild.id + "_" + name, guild_id=ctx.guild.id)

            custom_commands.remove(command.other["code"])
            self.bot.remove_command(command)

            return_text = "Komenda została usunięta"

        lexer = Lexer(code)
        parser = Parser(
            lexer,
            modules = {
                **await get_modules(self.bot, ctx.guild),
                "requests": {
                    "builtins": {
                        "request": lambda *args, **kwargs: {"text": "", "json": {}},
                        "get": lambda *args, **kwargs: {"text": "", "json": {}},
                        "post": lambda *args, **kwargs: {"text": "", "json": {}},
                        "patch": lambda *args, **kwargs: {"text": "", "json": {}},
                        "put": lambda *args, **kwargs: {"text": "", "json": {}},
                        "delete": lambda *args, **kwargs: {"text": "", "json": {}}
                    }
                }
            },
            builtins = {
                **builtins,
                "set_command_name": set_command_name,
                "set_command_description": set_command_description,
                "set_command_usage": set_command_usage,
                "set_command_aliases": set_command_aliases,
                "set_command_arguments": set_command_arguments,
                "get_command_code": get_command_code,
                "get_commands": get_commands,
                "delete_command": delete_command
            },
            variables = {
                **convert(
                    guild = ctx.guild,
                    channel = ctx.channel,
                    author = ctx.author
                ),
                "str": "str",
                "int": "int",
                "Channel": "channel",
                "Role": "role",
                "User": "user"
            }
        )

        await parser.parse()

        if return_text is not None:
            if return_text == "":
                return

            await guild.update(custom_commands=custom_commands)
            return await ctx.reply(return_text)

        if command_name is None:
            return await ctx.reply("Nie ustawiono nazwy komendy")

        command_object = self.bot.get_command(command_name, guild_id=ctx.guild.id)

        for alias in command_aliases:
            _command = self.bot.get_command(alias, guild_id=ctx.guild.id)
            if _command is not None and not _command.name == ctx.guild.id + "_" + command_name:
                return await ctx.reply("Alias `%s` jest już używany w bocie" % alias)

        text = "Stworzono"

        if command_object:
            if command_prefix is not None and not command_prefix in self.custom_commands_cog.prefixes:
                self.custom_commands_cog.append_prefix(command_object.other["prefix"])

            custom_commands.remove(command_object.other["code"])
            self.bot.remove_command(command_object)

            text = "Zaktualizowano"

        command_info = {
            "name": ctx.guild.id + "_" + command_name,
            "description": command_description,
            "usage": command_usage,
            "aliases": [command_name] + command_aliases,
            "cog": self.custom_commands_cog,
            "guild_id": ctx.guild.id,
            "other": {
                "prefix": command_prefix,
                "display_name": command_name,
                "code": code
            }
        }

        async def command_function(ctx, args = None):
            async with femcord.Typing(ctx.message):
                if args is not None:
                    args = args[0]
                    values = list(command_arguments.values())
                    _break = False

                    for index, item in enumerate(args):
                        _type = values[index]

                        if _type is str and index + 1 >= len(values):
                            item = " ".join(args[index:])
                            _break = True

                        if _type in (types.User, types.Channel, types.Role):
                            result = _type.from_arg(ctx, item)
                            if isinstance(result, CoroutineType):
                                result = await result

                            args[index] = convert(_=result)["_"]
                            continue

                        args[index] = _type(item)

                        if _break is True:
                            break

                    args = dict(zip(command_arguments.keys(), args))

                result = await run(
                    code,
                    modules = await get_modules(self.bot, ctx.guild),
                    builtins = {
                        **builtins,
                        "set_command_name": void,
                        "set_command_description": void,
                        "set_command_usage": void,
                        "set_command_aliases": void,
                        "set_command_arguments": void,
                        "get_command_code": void,
                        "get_commands": void,
                        "delete_command": void
                    },
                    variables = {
                        **convert(
                            guild = ctx.guild,
                            channel = ctx.channel,
                            author = ctx.author
                        ),
                        "str": "str",
                        "int": "int",
                        "Channel": "channel",
                        "Role": "role",
                        "User": "user",
                        **(
                            args if args is not None else {}
                        )
                    }
                )

                if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], femcord.Embed):
                    return await ctx.reply(result[0], embed=result[1])

                if isinstance(result, femcord.Embed):
                    return await ctx.reply(embed=result)

            await self.bot.paginator(ctx.reply, ctx, result, replace=False)

        if not command_arguments:
            @commands.command(**command_info)
            async def command(_, ctx):
                await command_function(ctx)
        else:
            @commands.command(**command_info)
            async def command(_, ctx, *args):
                await command_function(ctx, args)

        if command_usage is not None:
            command.usage = "(" + command_usage[0] + ")" + (" " if len(command_usage) > 1 else "") + " ".join("[" + item + "]" for item in command_usage[1:])

        self.custom_commands_cog.commands.append(command)
        self.bot.commands.append(command)

        if isinstance(ctx, commands.Context):
            custom_commands.append(code)
            await guild.update(custom_commands=custom_commands)

        await ctx.reply(text + " komende")

def setup(bot):
    bot.load_cog(custom_commands_cog := CustomCommands())
    bot.load_cog(Other(bot, custom_commands_cog))