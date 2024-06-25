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
from datetime import datetime, timedelta
from typing import Union
import asyncio, time, ast, inspect, models

class Dev(commands.Cog):
    hidden = True

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def insert_returns(self, body: list) -> None:
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        if isinstance(body[-1], ast.If):
            self.insert_returns(body[-1].body)
            self.insert_returns(body[-1].orelse)

        if isinstance(body[-1], ast.With):
            self.insert_returns(body[-1].body)

    def _eval(self, code: str, env: dict = None) -> asyncio.Future:
        env = {} or env

        content = "\n".join(f"    {x}" for x in code.splitlines())
        body = f"async def _eval():\n{content}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        self.insert_returns(body)

        exec(compile(parsed, filename="_eval", mode="exec"), env)

        return eval("_eval()", env)

    @commands.command(description="cenzura is a bot, the bot is cenzura", usage="(code)")
    async def eval(self, ctx: commands.Context, *, code):
        if not ctx.author.id in self.bot.owners:
            return await self.bot.get_command("femscript")(ctx, code=code)

        result = await self._eval(code, {
            "femcord": femcord,
            "models": models,
            "ctx": ctx,
            "bot": self.bot,
            "src": inspect.getsource
        })

        if isinstance(result, femcord.Embed):
            return await ctx.reply(embed=result)

        result = str(result)

        prefix = "```py\n"
        suffix = "```"

        if len(result) < 100:
            prefix = ""
            suffix = ""

        await self.bot.paginator(ctx.reply, ctx, str(result), prefix=prefix, suffix=suffix)

    @commands.command(description="cenzura is a bot, the bot is cenzura")
    @commands.is_owner
    async def command_stats(self, ctx: commands.Context, *, command: commands.Command = None):
        query = "{type=\"command\"}" if not command else f"{{type=\"command\", command=\"{command.name}\"}}"

        stats = await self.bot.loki.get_logs(query, start=(datetime.utcnow() - timedelta(days=1)).timestamp(), limit=1000)
        streams = stats["data"]["result"]
        command_names = [stream["stream"]["command"] for stream in streams]

        commands = dict.fromkeys(command_names, 0)

        for command in commands.keys():
            commands[command] = len([command_name for command_name in command_names if command_name == command])

        commands = {
            k: v for k, v in sorted(commands.items(), key=lambda item: item[1], reverse=True)
        }

        description = "\n".join(f"{command}: {count}" for command, count in commands.items())

        embed = femcord.Embed(title="Command stats", description=description, color=self.bot.embed_color)

        await ctx.reply(embed=embed)

    @commands.command(description="cenzura is a bot, the bot is cenzura", usage="(command)", aliases=["src"])
    @commands.is_owner
    async def source(self, ctx: commands.Context, *, command):
        command = command.split(" ")
        command_object = self.bot.get_command(command[0])

        if len(command) > 1:
            while command_object.type is commands.CommandTypes.GROUP:
                command = command[1:]
                if command:
                    command_object = command_object.get_subcommand(command[0])

        code = inspect.getsource(command_object.callback)

        await self.bot.paginator(ctx.reply, ctx, code, prefix="```py\n", suffix="```")

    @commands.command(description="cenzura is a bot, the bot is cenzura")
    @commands.is_owner
    async def load(self, ctx: commands.Context, extensions: str):
        loaded = []

        for extension in extensions.split():
            self.bot.load_extension(extension)

            loaded.append(extension)

        await ctx.reply("\n".join("\N{INBOX TRAY} `%s`" % extension_name for extension_name in loaded))

    @commands.command(description="cenzura is a bot, the bot is cenzura")
    @commands.is_owner
    async def reload(self, ctx: commands.Context, extensions: str):
        reloaded = []

        for extension in extensions.split():
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)

            reloaded.append(extension)

        await ctx.reply("\n".join("\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} `%s`" % extension_name for extension_name in reloaded))

    @commands.command(description="cenzura is a bot, the bot is cenzura")
    @commands.is_owner
    async def unload(self, ctx: commands.Context, extensions: str):
        unloaded = []

        for extension in extensions.split():
            self.bot.unload_extension(extension)

            unloaded.append(extension)

        await ctx.reply("\n".join("\N{OUTBOX TRAY} `%s`" % extension_name for extension_name in unloaded))

    @commands.command(description="cenzura is a bot, the bot is cenzura", usage="[user] (command) [arguments]")
    @commands.is_owner
    async def su(self, ctx: commands.Context, member: Union[types.Member, str], command = None, *, args = None):
        if isinstance(member, str):
            if command is not None:
                _args = command
                if args is not None:
                    _args += " " + args
                args = _args

            command = member
            member = ctx.member

        fake_member = self.bot.gateway.copy(member)
        fake_message = self.bot.gateway.copy(ctx.message)

        fake_member.roles.append(self.bot.su_role)
        fake_member.hoisted_role = self.bot.su_role
        fake_member.permissions = self.bot.su_role.permissions

        fake_message.author = fake_member.user
        fake_message.member = fake_member
        fake_message.content = (await self.bot.get_prefix(self.bot, ctx.message))[-1] + command

        if args is not None:
            fake_message.content += " " + args

        async def before_call(ctx):
            self.bot.owners.append(ctx.author.id)

        async def after_call(ctx):
            self.bot.owners.remove(ctx.author.id)

        await self.bot.process_commands(fake_message, before_call_functions=before_call, after_call_functions=after_call)

    @commands.command(description="cenzura is a bot, the bot is cenzura", usage="(command) [arguments]")
    @commands.is_owner
    async def perf(self, ctx: commands.Context, command, *, args = None):
        fake_message = self.bot.gateway.copy(ctx.message)

        fake_message.content = (await self.bot.get_prefix(self.bot, ctx.message))[-1] + command

        if args is not None:
            fake_message.content += " " + args

        before = None
        after = None

        async def before_call(ctx):
            nonlocal before
            before = time.perf_counter()

        async def after_call(ctx):
            nonlocal after
            after = time.perf_counter()

        await self.bot.process_commands(fake_message, before_call_functions=before_call, after_call_functions=after_call)

        while after is None:
            await asyncio.sleep(0.01)

        await ctx.reply(f"Executed in `{after - before:.2f}s`")

def setup(bot: commands.Bot) -> None:
    bot.load_cog(Dev(bot))