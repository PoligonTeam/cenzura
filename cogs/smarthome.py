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
from femcord import commands
import socket

class SmartHome(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = "192.168.100.67", 8317

    @commands.command()
    @commands.is_owner
    async def mute(self, ctx):
        self.socket.sendto(b"\x01\x00", self.address)
        await ctx.reply("zmutowano czubixa")

    @commands.command()
    @commands.is_owner
    async def unmute(self, ctx):
        self.socket.sendto(b"\x00\x00", self.address)
        await ctx.reply("odmutowano czubixa")

    @commands.command()
    @commands.is_owner
    async def deafen(self, ctx):
        self.socket.sendto(b"\x00\x01", self.address)
        await ctx.reply("zmutowano czubixa")

    @commands.command()
    @commands.is_owner
    async def undeafen(self, ctx):
        self.socket.sendto(b"\x00\x00", self.address)
        await ctx.reply("odmutowano czubixa")

def setup(bot):
    bot.load_cog(SmartHome(bot))