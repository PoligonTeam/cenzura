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
from femcord.femcord import commands, types, HTTPException
from femscript import Femscript, var
from utils import convert, highlight
from models import Guilds
import datetime, re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, Context

class Admin(commands.Cog):
    name = "Moderacyjne"

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.translations = self.bot.get_translations_for("mod")

    @commands.command(description="Wyrzuca użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("kick_members")
    async def kick(self, ctx: "Context", member: types.Member, *, reason = "nie podano powodu"):
        if not ctx.guild.me.permissions.has("kick_members"):
            return await ctx.reply("Bot nie ma uprawnień (`kick_members`)")

        if ctx.member.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Nie możesz wyrzucić użytkownika równego lub wyższego od ciebie")

        if ctx.guild.me.roles[-1].position <= member.roles[-1].position:
            return await ctx.reply("Bot nie może wyrzucić tego użytkownika")

        await member.kick(reason)

        await ctx.reply(f"Wyrzucono `{member.user}` z powodu `{reason}`")

        try:
            await member.user.send(f"Zostałeś wyrzucony z serwera `{ctx.guild.name}` przez `{ctx.author}` z powodu `{reason}`")
        except HTTPException:
            pass

    @commands.command(description="Banuje użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("ban_members")
    async def ban(self, ctx: "Context", member: types.Member | types.User, *, reason = "nie podano powodu"):
        if not ctx.guild.me.permissions.has("ban_members"):
            return await ctx.reply("Bot nie ma uprawnień (`ban_members`)")

        if isinstance(member, types.Member):
            if ctx.member.roles[-1].position <= member.roles[-1].position:
                return await ctx.reply("Nie możesz zbanować użytkownika równego lub wyższego od ciebie")

            if ctx.guild.me.roles[-1].position <= member.roles[-1].position:
                return await ctx.reply("Bot nie może zbanować tego użytkownika")

            await member.ban(reason)

            await ctx.reply(f"Zbanowano `{member.user}` z powodu `{reason}`")

            try:
                await member.user.send(f"Zostałeś zbanowany na serwerze `{ctx.guild.name}` przez `{ctx.author}` z powodu `{reason}`")
            except HTTPException:
                pass

            return

        await ctx.guild.ban(member, reason)

        await ctx.reply(f"Zbanowano `{member}` z powodu `{reason}`")

    @commands.command(description="Odbanowuje użytkownika", usage="(użytkownik) [powód]")
    @commands.has_permissions("ban_members")
    async def unban(self, ctx: "Context", user: types.User, *, reason = "nie podano powodu"):
        if not ctx.guild.me.permissions.has("ban_members"):
            return await ctx.reply("Bot nie ma uprawnień (`ban_members`)")

        await ctx.guild.unban(user.id, reason)

        await ctx.reply(f"Odbanowano `{user}` z powodu `{reason}`")

        try:
            await user.send(f"Zostałeś odbanowany na serwerze `{ctx.guild.name}` przez `{ctx.author}` z powodu `{reason}`")
        except HTTPException:
            pass

    @commands.command(description="Usuwa wiadomości na kanale", usage="(limit) [użytkownik]", aliases=["purge"])
    @commands.has_permissions("manage_messages")
    async def clear(self, ctx: "Context", limit: int, user: types.User = None):
        if not ctx.guild.me.permissions.has("manage_messages"):
            return await ctx.reply("Bot nie ma uprawnień (`manage_messages`)")

        if not 1000 > limit >= 1:
            return await ctx.reply("Limit wiadomości musi być pomiędzy `1` a `1000`")

        key = None

        if user is not None:
            key = lambda message: message.author.id == user.id

        await ctx.channel.purge(limit=limit, messages=[ctx.message], key=key)

        await ctx.reply(f"Usunięto `{limit}` wiadomości")

    @commands.group(description="Set commands")
    async def set(self, ctx: "Context"):
        cog = self.bot.get_cog("Help")
        embed = cog.get_help_embed(ctx.command)

        await ctx.reply(embed=embed)

    @set.command(description="Ustawia prefix", usage="(prefix)")
    @commands.has_permissions("manage_guild")
    async def prefix(self, ctx: "Context", prefix):
        if len(prefix) > 5:
            return await ctx.reply(f"Prefix jest za długi (`{len(prefix)}/5`)")

        await Guilds.filter(guild_id=ctx.guild.id).update(prefix=prefix)
        ctx.guild.prefix = prefix

        await ctx.reply("Ustawiono prefix")

    @set.command(description="Ustawia język", usage="(en/pl)", aliases=["lang"])
    @commands.has_permissions("manage_guild")
    async def language(self, ctx: "Context", lang: str):
        if lang not in ("en", "pl"):
            return await ctx.reply("Wybierz dostępny język (`en`/`pl`)")

        await Guilds.filter(guild_id=ctx.guild.id).update(language=lang)
        ctx.guild.language = lang

        await ctx.reply("Ustawiono język")

    @set.command(description="Verification", usage="[code]", aliases=["verification"])
    @commands.has_permissions("manage_guild")
    async def captcha(self, ctx: "Context", *, code):
        query = Guilds.filter(guild_id=ctx.guild.id)
        guild_db = await query.first()

        if (match := re.match(r"(?:<#)?(\d+)>? (?:<@&)?(\d+)>? ([\s\S]+)", code)) is not None:
            channel_id = match.group(1)
            role_id = match.group(2)
            message = match.group(3)

            args = re.findall(r"\{([^{}]+)\}", message)
            message = re.sub(r"\{([^{}]+)\}", r"{}", message)

            code = f"set_channel(\"{channel_id}\");\n" \
                   f"set_role(\"{role_id}\");\n" \
                   f"return format(\"{message}\", {", ".join(args)});"

        femscript = Femscript(code)

        @femscript.wrap_function()
        def set_channel(channel_id: str) -> None:
            femscript.channel_id = channel_id

        @femscript.wrap_function()
        def set_role(role_id: str) -> None:
            femscript.role_id = role_id

        femscript.wrap_function(femcord.Embed)

        @femscript.wrap_function()
        def Components() -> femcord.Components:
            femscript.is_components_v2 = True
            return femcord.Components()

        femscript.add_variable(var("ButtonStyles", {
            "PRIMARY": femcord.ButtonStyles.PRIMARY,
            "SECONDARY": femcord.ButtonStyles.SECONDARY,
            "SUCCESS": femcord.ButtonStyles.SUCCESS,
            "DANGER": femcord.ButtonStyles.DANGER,
            "LINK": femcord.ButtonStyles.LINK
        }))

        femscript.add_variable(var("PaddingSizes", {
            "SMALL": femcord.PaddingSizes.SMALL,
            "LARGE": femcord.PaddingSizes.LARGE
        }))

        femscript.add_variable(var("SelectDefaultValueTypes", {
            "USER": femcord.SelectDefaultValueTypes.USER,
            "ROLE": femcord.SelectDefaultValueTypes.ROLE,
            "CHANNEL": femcord.SelectDefaultValueTypes.CHANNEL
        }))

        femscript.wrap_function(femcord.ActionRow)
        femscript.wrap_function(femcord.Button)
        femscript.wrap_function(femcord.StringSelectOption)
        femscript.wrap_function(femcord.StringSelect)
        femscript.wrap_function(femcord.TextInput)
        femscript.wrap_function(femcord.SelectDefaultValue)
        femscript.wrap_function(femcord.UserSelect)
        femscript.wrap_function(femcord.RoleSelect)
        femscript.wrap_function(femcord.MentionableSelect)
        femscript.wrap_function(femcord.ChannelSelect)
        femscript.wrap_function(femcord.Section)
        femscript.wrap_function(femcord.TextDisplay)
        femscript.wrap_function(femcord.UnfurledMediaItem)
        femscript.wrap_function(femcord.MediaItem)
        femscript.wrap_function(femcord.Thumbnail)
        femscript.wrap_function(femcord.MediaGallery)
        femscript.wrap_function(femcord.File)
        femscript.wrap_function(femcord.Separator)
        femscript.wrap_function(femcord.Container)

        result = await femscript.execute()

        if not hasattr(femscript, "channel_id"):
            return await ctx.reply("You didn't set the channel id")

        if not hasattr(femscript, "role_id"):
            return await ctx.reply("You didn't set the role id")

        channel = ctx.guild.get_channel(femscript.channel_id)
        role = ctx.guild.get_role(femscript.role_id)

        if not channel:
            return await ctx.reply("This channel doesn't exist")

        if not role:
            return await ctx.reply("This role doesn't exist")

        if hasattr(femscript, "is_components_v2"):
            message = await channel.send(components=result, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])
        else:
            components = femcord.Components(
                components = [
                    femcord.ActionRow(
                        components = [
                            femcord.Button(
                                label = await ctx.get_translation("captcha_button_text"),
                                custom_id = "verification" + ctx.guild.id,
                                style = femcord.ButtonStyles.SECONDARY
                            )
                        ]
                    )
                ]
            )
            message = await channel.send(**{"content" if not isinstance(result, femcord.Embed) else "embed": result}, components=components)

        await query.update(verification_role=role.id, verification_message=message.id, verification_channel=channel.id)

        await ctx.reply("Sent verification message")

    @set.command(description="Welcome message", usage="[code]", aliases=["welcome", "welcomemsg"])
    @commands.has_permissions("manage_guild")
    async def welcomemessage(self, ctx: "Context", *, code = None):
        query = Guilds.filter(guild_id=ctx.guild.id)
        guild_db = await query.first()

        if code is None:
            await query.update(welcome_message="")
            ctx.guild.welcome_message = ""

            return await ctx.reply("Disabled")

        if code == "get_code()":
            return await ctx.reply_paginator(highlight(guild_db.welcome_message), by_lines=True, base_embed=femcord.Embed(), prefix="```ansi\n", suffix="```")
        elif code == "emit()":
            events = self.bot.get_cog("Events")
            return await events.on_guild_member_add(ctx.guild, ctx.member)

        if (match := re.match(r"(?:<#)?(\d+)>? ([\s\S]+)", code)) is not None:
            channel_id = match.group(1)
            message = match.group(2)

            args = re.findall(r"\{([^{}]+)\}", message)
            message = re.sub(r"\{([^{}]+)\}", r"{}", message)

            code = f"set_channel(\"{channel_id}\");\n" \
                   f"return format(\"{message}\", {", ".join(args)});"

        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        await query.update(welcome_message=code)
        ctx.guild.welcome_message = code

        await ctx.reply("Updated")

    @set.command(description="Leave message", usage="[code]", aliases=["leave", "leavemsg"])
    @commands.has_permissions("manage_guild")
    async def leavemessage(self, ctx: "Context", *, code = None):
        query = Guilds.filter(guild_id=ctx.guild.id)
        guild_db = await query.first()

        if code is None:
            await query.update(leave_message="")
            ctx.guild.leave_message = ""

            return await ctx.reply("Disabled")

        if code == "get_code()":
            return await ctx.reply_paginator(guild_db.leave_message, by_lines=True, base_embed=femcord.Embed(), prefix="```ansi\n", suffix="```")
        elif code == "emit()":
            events = self.bot.get_cog("Events")
            return await events.on_guild_member_remove(ctx.guild, ctx.author)

        if (match := re.match(r"(?:<#)?(\d+)>? ([\s\S]+)", code)) is not None:
            channel_id = match.group(1)
            message = match.group(2)

            args = re.findall(r"\{([^{}]+)\}", message)
            message = re.sub(r"\{([^{}]+)\}", r"{}", message)

            code = f"set_channel(\"{channel_id}\");\n" \
                   f"return format(\"{message}\", {", ".join(args)});"

        code = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
               f"# GUILD: {ctx.guild.id}\n" \
               f"# CHANNEL: {ctx.channel.id}\n" \
               f"# AUTHOR: {ctx.author.id}\n\n" \
             + code

        await query.update(leave_message=code)
        ctx.guild.leave_message = code

        await ctx.reply("Updated")

    @set.command(description="Ustawia autorole", usage="[rola]")
    @commands.has_permissions("manage_guild", "manage_roles")
    async def autorole(self, ctx: "Context", role: types.Role | str = None):
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

def setup(bot: "Bot") -> None:
    bot.load_cog(Admin(bot))