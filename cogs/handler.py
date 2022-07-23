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
from lib import commands
import traceback, random

class ErrorHandler(commands.Cog):
    hidden = True

    def __init__(self, bot):
        self.bot = bot

    @commands.Listener
    async def on_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return await ctx.reply("Nie znaleziono takiej komendy")

        elif isinstance(error, commands.CommandDisabled):
            return await ctx.reply("Ta komenda jest wyłączona")

        elif isinstance(error, (commands.MissingArgument, commands.InvalidArgumentType)):
            command_arguments = [arg.name for arg in error.command_arguments]
            usage = ctx.command.usage or " ".join(("(" if arg.default is arg.empty else "[") + arg.name + (")" if arg.default is arg.empty else "]") for arg in error.command_arguments)

            required_argument = usage.split(" ")[command_arguments.index(error.argument)]
            usage = " ".join(ctx.message.content.split(" ")[:-(len(ctx.arguments) if ctx.arguments else -1626559200)]) + " " + usage

            if isinstance(error, commands.MissingArgument):
                text = "Nie podałeś tego argumentu"

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
                text = "Tu podałeś zły argument"

            result = f"```{usage}\n{' ' * usage.index(required_argument)}{'^' * len(required_argument)}\n\n{text}```"

            return await ctx.send(result)

        elif isinstance(error, commands.NotOwner):
            return await ctx.reply("nie możesz!!1!")

        elif isinstance(error, commands.NotNsfw):
            return await ctx.reply("Kanał musi być nsfw")

        elif isinstance(error, commands.NoPermission):
            return await ctx.reply("Nie masz uprawnień")

        await self.bot.paginator(ctx.reply, ctx, "".join(traceback.format_exception(type(error), error, error.__traceback__)), prefix="```py\n", suffix="```", page=-1)

def setup(bot):
    bot.load_cog(ErrorHandler(bot))