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
from femcord.femcord import commands
from utils import fg
import traceback
import random

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext

class ErrorHandler(commands.Cog):
    hidden = True

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    @commands.Listener
    async def on_error(self, ctx: Union["Context", "AppContext"], error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return await ctx.reply("Command not found")

        elif isinstance(error, commands.CommandDisabled):
            return await ctx.reply("This command is disabled")

        elif isinstance(error, (commands.MissingArgument, commands.InvalidArgumentType)):
            command_arguments = [arg.name for arg in error.command_arguments]
            usage = ctx.command.usage or " ".join(("(" if arg.default is arg.empty else "[") + arg.name + (")" if arg.default is arg.empty else "]") for arg in error.command_arguments)

            required_argument = usage.split(" ")[command_arguments.index(error.argument)]
            usage = usage.replace(required_argument, required_argument := (fg.red + required_argument[0] + fg.reset + required_argument[1:-1] + fg.red + required_argument[-1] + fg.reset))
            usage = " ".join(ctx.message.content.split(" ")[:-(len(ctx.arguments) if ctx.arguments else -1626559200)]) + " " + usage

            if isinstance(error, commands.MissingArgument):
                text = "You did not provide this argument"

                if random.random() < 0.1:
                    text = """            No arguments?
⠀⣞⢽⢪⢣⢣⢣⢫⡺⡵⣝⡮⣗⢷⢽⢽⢽⣮⡷⡽⣜⣜⢮⢺⣜⢷⢽⢝⡽⣝
⠸⡸⠜⠕⠕⠁⢁⢇⢏⢽⢺⣪⡳⡝⣎⣏⢯⢞⡿⣟⣷⣳⢯⡷⣽⢽⢯⣳⣫⠇
⠀⠀⢀⢀⢄⢬⢪⡪⡎⣆⡈⠚⠜⠕⠇⠗⠝⢕⢯⢫⣞⣯⣿⣻⡽⣏⢗⣗⠏
⠀⠪⡪⡪⣪⢪⢺⢸⢢⢓⢆⢤⢀⠀⠀⠀⠀⠈⢊⢞⡾⣿⡯⣏⢮⠷⠁
⠀⠀⠀⠈⠊⠆⡃⠕⢕⢇⢇⢇⢇⢇⢏⢎⢎⢆⢄⠀⢑⣽⣿⢝⠲⠉
⠀⠀⠀⠀⠀⡿⠂⠠⠀⡇⢇⠕⢈⣀⠀⠁⠡⠣⡣⡫⣂⣿⠯⢪⠰⠂
⠀⠀⠀⠀⡦⡙⡂⢀⢤⢣⠣⡈⣾⡃⠠⠄⠀⡄⢱⣌⣶⢏⢊⠂
⠀⠀⠀⠀⢝⡲⣜⡮⡏⢎⢌⢂⠙⠢⠐⢀⢘⢵⣽⣿⡿⠁⠁
⠀⠀⠀⠀⠨⣺⡺⡕⡕⡱⡑⡆⡕⡅⡕⡜⡼⢽⡻⠏
⠀⠀⠀⠀⣼⣳⣫⣾⣵⣗⡵⡱⡡⢣⢑⢕⢜⢕⡝
⠀⠀⠀⣴⣿⣾⣿⣿⣿⡿⡽⡑⢌⠪⡢⡣⣣⡟
⠀⠀⠀⡟⡾⣿⢿⢿⢵⣽⣾⣼⣘⢸⢸⣞⡟
⠀⠀⠀⠀⠁⠇⠡⠩⡫⢿⣝⡻⡮⣒⢽⠋"""
            else:
                text = "You provided an invalid argument here"

            result = f"```ansi\n{usage}\n{' ' * usage.index(required_argument)}{fg.red + '^' * (len(required_argument) - (len(fg.blue) * 2 + len(fg.reset) * 2)) + fg.white}\n\n{fg.blue + text}```"

            return await ctx.send(result)

        elif isinstance(error, commands.NotOwner):
            return await ctx.reply("You are not the owner of this bot")

        elif isinstance(error, commands.NotNsfw):
            return await ctx.reply("This channel is not nsfw")

        elif isinstance(error, commands.NoPermission):
            return await ctx.reply("You do not have permission to use this command")

        elif isinstance(error, femcord.HTTPException):
            formatted_error = "".join(traceback.format_exception(type(error), error, error.__traceback__))

            if "errors" not in error.original_error:
                return await ctx.reply_paginator(formatted_error, prefix="```py\n", suffix="```", page=-1)

            def walk(data, indent=0):
                text = ""
                prefix = " " * (indent * 2)

                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, (dict, list)):
                            text += f"{prefix}{fg.magenta}{key}{fg.white}:{fg.reset}\n" + walk(value, indent + 1)
                        else:
                            text += f"{prefix}{fg.magenta}{key}{fg.white}:{fg.reset} {fg.green}{value}{fg.reset}\n"
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, (dict, list)):
                            text += f"{prefix}-\n" + walk(item, indent + 1)
                        else:
                            text += f"{prefix}- {fg.yellow}{item}{fg.reset}\n"

                return text

            return await ctx.reply_paginator(pages=[f"```py\n{formatted_error}```", f"```ansi\n{walk(error.original_error["errors"])}```"], replace=False)

        elif isinstance(error, AssertionError):
            return await ctx.reply(error)

        formatted_error = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        if not isinstance(ctx, commands.AppContext):
            self.bot.loki.add_command_exception_log(ctx, error, formatted_error)

        await ctx.reply_paginator(formatted_error, prefix="```py\n", suffix="```", page=-1)

def setup(bot: "Bot") -> None:
    bot.load_cog(ErrorHandler(bot))