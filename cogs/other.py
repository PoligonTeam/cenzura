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
from femscript import Lexer, Parser, run
from utils import *
from types import CoroutineType
from models import Guilds
import re, datetime, copy

class CustomCommands(commands.Cog):
    name = "Komendy serwerowe"
    description = "Komendy które są dostępne tylko na tym serwerze ([dokumentacja](https://cenzura.poligon.lgbt/docs))"

    def __init__(self):
        self.prefixes = []

class Other(commands.Cog):
    name = "Inne"

    def __init__(self, bot, custom_commands_cog):
        self.bot: commands.Bot = bot
        self.custom_commands_cog = custom_commands_cog

    @commands.command(description="pisaju skrypt", usage="(kod)", aliases=["fs", "fscript", "cs", "cscript"])
    async def femscript(self, ctx: commands.Context, *, code):
        result = await run(
            code,
            modules = {
                **await get_modules(ctx.guild),
                **(
                    {
                        "database": {}
                    }
                    if not ctx.member.permissions.has("manage_guild") else
                    {

                    }
                )
            },
            builtins = {
                **builtins,
                **(
                    {
                        "send": ctx.send,
                        "reply": ctx.reply
                    }
                    if ctx.author.id in self.bot.owners else
                    {

                    }
                )
            },
            variables = convert(
                guild = ctx.guild,
                channel = ctx.channel,
                author = ctx.author
            )
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

                fake_message = copy.deepcopy(message)
                fake_message.content = (await self.bot.get_prefix(self.bot, message))[-1] + message.content[len(prefix):]

                return await self.bot.process_commands(fake_message)

    @commands.command(description="Tworzenie komendy serwerowej", usage="(kod)", aliases=["cc", "createcommand"])
    @commands.has_permissions("manage_guild")
    async def customcommand(self, ctx: commands.Context, *, code):
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
                self.custom_commands_cog.prefixes.append(prefix)

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
                raise femcord.CommandNotFound()

            await self.bot.paginator(ctx.reply, ctx, re.sub(r"hide\(\".+\"\)", "HIDDEN", command.other["code"]), prefix="```py\n", suffix="```")

            return_text = ""

        async def get_commands():
            nonlocal return_text

            await self.bot.paginator(ctx.reply, ctx, pages=[re.sub(r"hide\(\".+\"\)", "HIDDEN", command) for command in custom_commands], prefix="```py\n", suffix="```")

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
                **await get_modules(ctx.guild),
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
                "delete_command": delete_command,
                "hide": lambda item: item
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
                self.custom_commands_cog.prefixes.append(command_object.other["prefix"])

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
                    modules = await get_modules(ctx.guild),
                    builtins = {
                        **builtins,
                        "set_command_name": void,
                        "set_command_description": void,
                        "set_command_usage": void,
                        "set_command_aliases": void,
                        "set_command_arguments": void,
                        "get_command_code": void,
                        "get_commands": void,
                        "delete_command": void,
                        "hide": lambda item: item
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

        #AUTOPATCH DO DISCORD VOICE
        #CUSTOMOWE PERMISJE
        #DODAC LOOPY DO FEMSCRIPT
        #OGRANICZYC RPS DO 16
        #LIMIT DO INTOW W CS
        #NAPRAWIC LIB.EVENTHANDLERS W NIEKTORYCH MIEJSCACH
        #HTTP PROXY
        #NAPRAWIC RETURNY W IFACH
        #HANDLOWANIE PRAWIE WSZYSTKICH ERROROW W PARSER.PY

        self.custom_commands_cog.commands.append(command)
        self.bot.commands.append(command)

        if isinstance(ctx, commands.Context):
            custom_commands.append(code)
            await guild.update(custom_commands=custom_commands)

        await ctx.reply(text + " komende")

def setup(bot):
    bot.load_cog(custom_commands_cog := CustomCommands())
    bot.load_cog(Other(bot, custom_commands_cog))