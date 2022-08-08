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
from femcord import commands, types, HTTPException
from models import Guilds
from typing import Union
import datetime, re

class Admin(commands.Cog):
    name = "Moderacyjne"

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command(description="Wyrzuca użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("kick_members")
    async def kick(self, ctx: commands.Context, member: types.Member, *, reason = "nie podano powodu"):
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
    async def ban(self, ctx: commands.Context, member: types.Member, *, reason = "nie podano powodu"):
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
    async def unban(self, ctx: commands.Context, user: types.User, *, reason = "nie podano powodu"):
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
    async def clear(self, ctx: commands.Context, limit: int, user: types.User = None):
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
    async def set(self, ctx: commands.Context):
        cog = self.bot.get_cog("Help")
        embed = cog.get_help_embed(ctx.command)

        await ctx.reply(embed=embed)

    @set.command(description="Ustawia prefix", usage="(prefix)")
    @commands.has_permissions("manage_guild")
    async def prefix(self, ctx: commands.Context, prefix):
        if len(prefix) > 5:
            return await ctx.reply(f"Prefix jest za długi (`{len(prefix)}/5`)")

        await Guilds.filter(guild_id=ctx.guild.id).update(prefix=prefix)
        ctx.guild.prefix = prefix

        await ctx.reply("Ustawiono prefix")

    @set.command(description="Ustawia wiadomość powitalną", usage="[kod]", aliases=["welcome", "welcomemsg"])
    @commands.has_permissions("manage_guild")
    async def welcomemessage(self, ctx: commands.Context, *, code = None):
        query = Guilds.filter(guild_id=ctx.guild.id)
        guild_db = await query.first()

        if code is None:
            await query.update(welcome_message="")
            ctx.guild.welcome_message = ""

            return await ctx.reply("Wyłączono wiadomość powitalną")

        if code == "get_code()":
            return await self.bot.paginator(ctx.reply, ctx, guild_db.welcome_message, prefix="```py\n", suffix="```")
        elif code == "emit()":
            events = self.bot.get_cog("Events")
            return await events.on_guild_member_add(ctx.guild, ctx.member)

        if (match := re.match(r"(<#)?(\d+)>? ([\s\S]+)", code)) is not None:
            channel_id = match.group(2)
            message = match.group(3)

            code = f"set_channel(\"{channel_id}\")\n\n" \
                   f"message = \"{message}\"\n\n" \
                    "return str.format(message, guild: guild, user: user)"

        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        await query.update(welcome_message=code)
        ctx.guild.welcome_message = code

        await ctx.reply("Ustawiono wiadomość powitalną")

    @set.command(description="Ustawia wiadomość pożegnalną", usage="[kod]", aliases=["leave", "leavemsg"])
    @commands.has_permissions("manage_guild")
    async def leavemessage(self, ctx: commands.Context, *, code = None):
        query = Guilds.filter(guild_id=ctx.guild.id)
        guild_db = await query.first()

        if code is None:
            await query.update(leave_message="")
            ctx.guild.leave_message = ""

            return await ctx.reply("Wyłączono wiadomość pożegnalną")

        if code == "get_code()":
            return await self.bot.paginator(ctx.reply, ctx, guild_db.leave_message, prefix="```py\n", suffix="```")
        elif code == "emit()":
            events = self.bot.get_cog("Events")
            return await events.on_guild_member_remove(ctx.guild, ctx.author)

        if (match := re.match(r"(<#)?(\d+)>? ([\s\S]+)", code)) is not None:
            channel_id = match.group(2)
            message = match.group(3)

            code = f"set_channel(\"{channel_id}\")\n\n" \
                   f"message = \"{message}\"\n\n" \
                    "return str.format(message, guild: guild, user: user)"

        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        await query.update(leave_message=code)
        ctx.guild.leave_message = code

        await ctx.reply("Ustawiono wiadomość pożegnalną")

    @set.command(description="Ustawia autorole", usage="[rola]")
    @commands.has_permissions("manage_guild", "manage_roles")
    async def autorole(self, ctx: commands.Context, role: Union[types.Role, str] = None):
        query = Guilds.filter(guild_id=ctx.guild.id)

        if role is None:
            await query.update(autorole="")
            ctx.guild.autorole = ""

            return await ctx.reply("Wyłączono autorole")

        if ctx.member.roles[-1].position < role.position:
            return await ctx.reply("Nie możesz ustawić roli która jest wyższa od ciebie")

        await query.update(autorole=role.id)
        ctx.guild.autorole = role.id

        await ctx.reply("Ustawiono autorole")

def setup(bot):
    bot.load_cog(Admin(bot))