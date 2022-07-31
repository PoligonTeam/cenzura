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
from cenzurascript import Lexer, Parser, run
from utils import convert, table
from types import CoroutineType
from httpx import AsyncClient, Timeout
from json.decoder import JSONDecodeError
from models import Guilds
import re, random, datetime, config

class CustomCommands(commands.Cog):
    name = "Komendy serwerowe"
    description = "Komendy które są dostępne tylko na tym serwerze ([dokumentacja](https://cenzura.poligon.lgbt/docs))"

    def __init__(self):
        self.prefixes = []

class Other(commands.Cog):
    name = "Inne"

    def __init__(self, bot):
        self.bot = bot
        self.custom_commands_cog = CustomCommands()
        self.builtins = {
            "Embed": lib.Embed,
            "get": lambda *args, **kwargs: self.request("GET", *args, **kwargs),
            "post": lambda *args, **kwargs: self.request("POST", *args, **kwargs),
            "patch": lambda *args, **kwargs: self.request("PATCH", *args, **kwargs),
            "put": lambda *args, **kwargs: self.request("PUT", *args, **kwargs),
            "delete": lambda *args, **kwargs: self.request("DELETE", *args, **kwargs),
            "execute_webhook": self.execute_webhook,
            "table": table
        }
        self.void = lambda *args, **kwargs: False

    async def request(self, method, url, *, headers = None, data = None, proxy = None):
        proxy_address = random.choice(list(config.PROXIES.values()))

        if proxy and proxy in config.PROXIES:
            proxy_address = config.PROXIES[proxy]

        proxy = config.PROXY_TEMPLATE.format(proxy_address)

        proxies = {
            "https://": proxy,
            "http://": proxy
        }

        async with AsyncClient(proxies=proxies, timeout=Timeout(60)) as session:
            response = await session.request(method, url, headers=headers, json=data)

            try:
                json = response.json()
            except JSONDecodeError:
                json = {}

            return {
                "text": response.text,
                "json": json
            }

    async def execute_webhook(self, webhook_id, webhook_token, *, username = None, avatar_url = None, content = None, embed: lib.Embed = None):
        data = {}

        if username:
            data["username"] = username
        if avatar_url:
            data["avatar_url"] = avatar_url
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed.__dict__]

        await self.request("POST", lib.http.URL + "/webhooks/" + webhook_id + "/" + webhook_token, data=data)

    @commands.command(description="pisaju skrypt", usage="(kod)", aliases=["cs", "cscript"])
    async def cenzurascript(self, ctx, *, code):
        result = await run(
            code,
            builtins = {
                **self.builtins,
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

        if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], lib.Embed):
            return await ctx.reply(result[0], embed=result[1])

        if isinstance(result, lib.Embed):
            return await ctx.reply(embed=result)

        result = str(result)

        prefix_suffix = "```"

        if len(result) < 100:
            prefix_suffix = ""

        await self.bot.paginator(ctx.reply, ctx, result, prefix=prefix_suffix, suffix=prefix_suffix)

    # @commands.Listener
    # async def on_message_create(self, message):
    #     if message.author.bot:
    #         return

    #     for prefix in self.custom_commands_cog.prefixes:
    #         if message.content.startswith(prefix):
    #             command_name = message.content.split(" ")[0][len(prefix):]
    #             command = self.bot.get_command(command_name, guild=message.guild)

    #             if not command:
    #                 return

    #             fake_message = types.Message(**message.__dict__)
    #             fake_message.content = (await self.bot.get_prefix(self.bot, message)) + message.content[len(prefix):]

    #             await self.bot.listeners[0](fake_message)

    @commands.command(description="Tworzenie komendy serwerowej", usage="(kod)", aliases=["cc", "createcommand"])
    @commands.has_permissions("manage_guild")
    async def customcommand(self, ctx, *, code):
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

            command = self.bot.get_command(name, guild=ctx.guild)

            if not command or not "code" in command.other or not command.guild.id == ctx.guild.id:
                raise lib.CommandNotFound()

            await self.bot.paginator(ctx.reply, ctx, re.sub(r"hide\(\".+\"\)", "HIDDEN", command.other["code"]), prefix="```py\n", suffix="```")

            return_text = ""

        async def get_commands():
            nonlocal return_text

            await self.bot.paginator(ctx.reply, ctx, pages=[re.sub(r"hide\(\".+\"\)", "HIDDEN", command) for command in custom_commands], prefix="```py\n", suffix="```")

            return_text = ""

        def delete_command(name):
            nonlocal return_text

            command = self.bot.get_command(ctx.guild.id + "_" + name, guild=ctx.guild)

            custom_commands.remove(command.other["code"])
            self.bot.remove_command(command)

            return_text = "Komenda została usunięta"

        lexer = Lexer(code)
        parser = Parser(
            lexer,
            builtins = {
                **self.builtins,
                **{
                    "set_command_name": set_command_name,
                    "set_command_description": set_command_description,
                    "set_command_usage": set_command_usage,
                    "set_command_aliases": set_command_aliases,
                    "set_command_arguments": set_command_arguments,
                    "get_command_code": get_command_code,
                    "get_commands": get_commands,
                    "delete_command": delete_command,
                    "get": lambda *args, **kwargs: {"text": "", "json": {}},
                    "post": lambda *args, **kwargs: {"text": "", "json": {}},
                    "patch": lambda *args, **kwargs: {"text": "", "json": {}},
                    "put": lambda *args, **kwargs: {"text": "", "json": {}},
                    "delete": lambda *args, **kwargs: {"text": "", "json": {}},
                    "execute_webhook": self.void,
                    "hide": lambda item: item
                }
            },
            variables = {
                **convert(
                    guild = ctx.guild,
                    channel = ctx.channel,
                    author = ctx.author
                ),
                **{
                    "str": "str",
                    "int": "int",
                    "Channel": "channel",
                    "Role": "role",
                    "User": "user"
                }
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

        command_object = self.bot.get_command(command_name, guild=ctx.guild)

        for alias in command_aliases:
            _command = self.bot.get_command(alias, guild=ctx.guild)
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
            "guild": ctx.guild,
            "other": {
                "prefix": command_prefix,
                "display_name": command_name,
                "code": code
            }
        }

        async def command_function(ctx, args = None):
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
                builtins = {
                    **self.builtins,
                    **{
                        "set_command_name": self.void,
                        "set_command_description": self.void,
                        "set_command_usage": self.void,
                        "set_command_aliases": self.void,
                        "set_command_arguments": self.void,
                        "get_command_code": self.void,
                        "get_commands": self.void,
                        "delete_command": self.void,
                        "hide": lambda item: item
                    }
                },
                variables = {
                    **convert(
                        guild = ctx.guild,
                        channel = ctx.channel,
                        author = ctx.author
                    ),
                    **{
                        "str": "str",
                        "int": "int",
                        "Channel": "channel",
                        "Role": "role",
                        "User": "user"
                    },
                    **(
                        args if args is not None else {}
                    )
                }
            )

            if isinstance(result, list) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], lib.Embed):
                return await ctx.reply(result[0], embed=result[1])

            if isinstance(result, lib.Embed):
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

        #DODAC DO PAGINATORA TO ZEBY ROBIL PAGINATOR NA PAGES JAK SIE MU DA
        #LIMIT DO INTOW W CS
        #LIB.COMMANDS.EVENTHANDLERS
        #DODAC WSZEDZIE GDZIE TRZEBA ASYNC WITH TYPING
        #ZROBIC ZEBY PO PREFIXIE DALO SIE ZNALESC KOMENDE W ON MESSAGE CREATE PRZY OKAZJI TO NAPRAWIC
        #NAPRAWIC LIB.EVENTHANDLERS W NIEKTORYCH MIEJSCACH
        #HTTP PROXY
        #NAPRAWIC RETURNY W IFACH
        #COS W PEWNYM RODZAJU BAZA DANYCH
        #HANDLOWANIE PRAWIE WSZYSTKICH ERROROW W PARSER.PY
        #VOICESTATE

        self.custom_commands_cog.commands.append(command)
        self.bot.commands.append(command)

        if isinstance(ctx, commands.Context):
            custom_commands.append(code)
            await guild.update(custom_commands=custom_commands)

        await ctx.reply(text + " komende")

def setup(bot):
    other = Other(bot)
    bot.load_cog(other.custom_commands_cog)
    bot.load_cog(other)