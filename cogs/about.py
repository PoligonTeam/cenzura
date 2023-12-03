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
from femcord.http import Route
from datetime import datetime

class About(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def get_ping_text(self):
        data = await self.bot.get_latency_data()

        text = f"Current latency: `{data['gateway']}ms`"

        if data.get("previous"):
            text += f"\nPrevious: {', '.join('`' + str(ping) + 'ms`' for ping in data['previous'])}"
            text += f"\nAverage: `{data['average']}ms`"

        text += f"\nREST latency: `{data['rest']}ms`"

        return text

    @commands.command(description="pong")
    async def ping(self, ctx: commands.Context):
        await ctx.reply(await self.get_ping_text())

    @commands.command(description="Bot statistics", aliases=["stats", "botinfo"])
    async def botstats(self, ctx: commands.Context):
        diff = datetime.now() - self.bot.started_at
        stats = await self.bot.get_stats()

        description = f"Guilds: `{stats['guilds']}`\n" \
                      f"Users: `{stats['users']}`\n\n" \
                      f"Commands: `{stats['commands']}`\n\n" \
                      f"RAM: `{stats['ram']['current'] / 1000 / 1000:.1f} MB ({(stats['ram']['total'] - stats['ram']['available']) / 1000 / 1000 / 1000:.1f} GB / {stats['ram']['total'] / 1000 / 1000 / 1000:.1f} GB)`\n" \
                      f"CPU: `{stats['cpu']}%`\n\n" + \
                      await self.get_ping_text() + "\n\n" \
                      f"Uptime: `{diff.days} days, {(diff.days * 24 + diff.seconds // 3600) % 24} hours, {(diff.seconds % 3600) // 60} minutes, {diff.seconds % 60} seconds`"

        await ctx.reply(embed=femcord.Embed(title="Bot statistics:", description=description, color=self.bot.embed_color))

def setup(bot):
    bot.load_cog(About(bot))