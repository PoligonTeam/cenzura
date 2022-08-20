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
import psutil
from datetime import datetime

class About(commands.Cog):
    name = "O bocie"

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.process = psutil.Process()

    def get_ping_text(self):
        text = f"Obecny ping: `{self.bot.gateway.latency}ms`"

        if self.bot.gateway.last_latencies:
            text += f"\nPoprzednie: {', '.join('`' + str(ping) + 'ms`' for ping in self.bot.gateway.last_latencies[-5:])}"
            text += f"\nŚrednia: `{(sum(self.bot.gateway.last_latencies) + self.bot.gateway.latency) // (len(self.bot.gateway.last_latencies) + 1)}ms`"

        return text

    @commands.command(description="pong")
    async def ping(self, ctx: commands.Context):
        await ctx.reply(self.get_ping_text())

    @commands.command(description="Statystyki bota", aliases=["stats", "botinfo"])
    async def botstats(self, ctx: commands.Context):
        diff = datetime.now() - self.bot.started_at
        memory = psutil.virtual_memory()

        description = f"Serwery: `{len(self.bot.gateway.guilds)}`\n" \
                      f"Użytkownicy: `{len(self.bot.gateway.users)}`\n\n" \
                      f"Komendy: `{len(self.bot.commands)}`\n\n" \
                      f"RAM: `{self.process.memory_full_info().rss / 1000 / 1000:.1f} MB ({(memory.total - memory.available) / 1000 / 1000 / 1000:.1f} GB / {memory.total / 1000 / 1000 / 1000:.1f} GB)`\n" \
                      f"Procesor: `{psutil.cpu_percent()}%`\n\n" + \
                      self.get_ping_text() + "\n\n" \
                      f"Uptime: `{diff.days} dni, {(diff.days * 24 + diff.seconds) // 3600} godzin, {(diff.seconds % 3600) // 60} minut, {diff.seconds % 60} sekund`\n\n"

        await ctx.reply(embed=femcord.Embed(title="Statystyki bota:", description=description, color=self.bot.embed_color))

def setup(bot):
    bot.load_cog(About(bot))