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
from lib import commands, types, HTTPException
from cenzurascript import run
from utils import convert
from typing import Union
from models import Guilds

class Admin(commands.Cog):
    name = "Moderacyjne"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Wyrzuca użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("kick_members")
    async def kick(self, ctx, member: types.Member, *, reason = "nie podano powodu"):
        if ctx.member.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Nie możesz wyrzucić użytkownika równego lub wyższego od ciebie")

        if not ctx.guild.me.permissions.has("kick_members") or ctx.guild.me.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Bot nie może wyrzucić tego użytkownika")

        await member.kick(reason)

        await ctx.reply(f"Wyrzucono `{member.user}` z powodu `{reason}`")

        try:
            await member.user.send(f"Zostałes wyrzucony z serwera `{ctx.guild.name}` przez `{ctx.author.username}#{ctx.author.discriminator}` z powodu `{reason}`")
        except HTTPException:
            pass

    @commands.command(description="Banuje użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("ban_members")
    async def ban(self, ctx, member: types.Member, *, reason = "nie podano powodu"):
        if ctx.member.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Nie możesz zbanować użytkownika równego lub wyższego od ciebie")

        if not ctx.guild.me.permissions.has("ban_members") or ctx.guild.me.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Bot nie może zbanować tego użytkownika")

        await member.ban(reason)

        await ctx.reply(f"Zbanowano `{member.user}` z powodu `{reason}`")

        try:
            await member.user.send(f"Zostałes zbanowany na serwerze `{ctx.guild.name}` przez `{ctx.author.username}#{ctx.author.discriminator}` z powodu `{reason}`")
        except HTTPException:
            pass

    @commands.command(description="Odbanowuje użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("ban_members")
    async def unban(self, ctx, user: types.User, *, reason = "nie podano powodu"):
        if not ctx.guild.me.permissions.has("ban_members"):
            return await ctx.reply("Bot nie ma uprawnień (`ban_members`)")

        await ctx.guild.unban(user.id, reason)

        await ctx.reply(f"Odbanowano `{user.username}#{user.discriminator}` z powodu `{reason}`")

        try:
            await user.send(f"Zostałes odbanowany na serwerze `{ctx.guild.name}` przez `{ctx.author.username}#{ctx.author.discriminator}` z powodu `{reason}`")
        except HTTPException:
            pass

    @commands.command(description="Usuwa wiadomości na kanale", usage="(limit) [użytkownik]", aliases=["purge"])
    @commands.has_permissions("manage_messages")
    async def clear(self, ctx, limit: int, user: types.User = None):
        if not ctx.guild.me.permissions.has("manage_messages"):
            return await ctx.reply("Bot nie ma uprawnień (`manage_messages`)")

        if not 1000 > limit >= 1:
            return await ctx.reply("Limit wiadomości musi być pomiędzy `1` a `1000`")

        key = None

        if user is not None:
            key = lambda message: message.author.id == user.id

        await ctx.channel.purge(limit=limit, messages=[ctx.message], key=key)

        await ctx.reply(f"Usunięto `{limit}` wiadomości")

    @commands.group(description="Pomoc komendy set", aliases=["ustaw"])
    async def set(self, ctx):
        cog = self.bot.get_cog("Help")
        embed = cog.get_help_embed(ctx.command)

        await ctx.reply(embed=embed)

    @set.command(description="Ustawia prefix", usage="(prefix)")
    @commands.has_permissions("manage_guild")
    async def prefix(self, ctx, prefix):
        if len(prefix) > 5:
            return await ctx.reply(f"Prefix jest za długi (`{len(prefix)}/5`)")

        await Guilds.filter(guild_id=ctx.guild.id).update(prefix=prefix)

        await ctx.reply("Ustawiono prefix")

    @set.command(description="Ustawia wiadomość powitalną", usage="(kod)", aliases=["welcome", "welcomemsg"])
    @commands.has_permissions("manage_guild")
    async def welcomemessage(self, ctx, *, code):
        pass

def setup(bot):
    bot.load_cog(Admin(bot))