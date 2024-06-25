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
from femcord.femcord import commands
import socket, aiohttp

class SmartHome(commands.Cog):
    hidden = True

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = "192.168.100.4", 8080

    @commands.group()
    @commands.is_owner
    async def leds(self, ctx):
        cog = self.bot.get_cog("Help")
        embed = cog.get_help_embed(ctx.command)

        await ctx.reply(embed=embed)

    @leds.command()
    @commands.is_owner
    async def on(self, ctx):
        self.socket.sendto(bytearray([0x7e, 0x00, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0xef]), self.address)

        await ctx.reply("ok")

    @leds.command()
    @commands.is_owner
    async def off(self, ctx):
        self.socket.sendto(bytearray([0x7e, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0xef]), self.address)

        await ctx.reply("ok")

    @leds.command()
    async def color(self, ctx, r, g = None, b = None):
        if g is not None and b is None:
            return await ctx.reply("You did not provide 'b' argument")

        if g is None:
            if r[0] == "#":
                r = r[1:]
            r, g, b = [int(r[x:x+2], 16) for x in (0, 2, 4)]

        if r is not None and g is not None and b is not None:
            r, g, b = [int(x) for x in (r, g, b)]

        self.socket.sendto(bytearray([0x7e, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xef]), self.address)

        await ctx.reply("ok")

    @commands.command()
    @commands.is_owner
    async def mute(self, ctx):
        async with aiohttp.ClientSession() as session:
            await session.get("http://192.168.100.67:8080/apps/discord/mute")

        await ctx.reply("ok")

    @commands.command()
    @commands.is_owner
    async def unmute(self, ctx):
        async with aiohttp.ClientSession() as session:
            await session.get("http://192.168.100.67:8080/apps/discord/unmute")

        await ctx.reply("ok")

    @commands.command()
    @commands.is_owner
    async def deaf(self, ctx):
        async with aiohttp.ClientSession() as session:
            await session.get("http://192.168.100.67:8080/apps/discord/deaf")

        await ctx.reply("ok")

    @commands.command()
    @commands.is_owner
    async def undeaf(self, ctx):
        async with aiohttp.ClientSession() as session:
            await session.get("http://192.168.100.67:8080/apps/discord/undeaf")

        await ctx.reply("ok")

def setup(bot: commands.Bot) -> None:
    bot.load_cog(SmartHome(bot))