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
from femcord.femcord.permissions import Permissions

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context

permissions = Permissions("kick_members", "ban_members", "manage_channels", "add_reactions", "view_channel", "send_messages", "manage_messages", "embed_links", "attach_files", "read_message_history", "manage_roles", "change_nickname")

BOTINVITE = f"https://discord.com/oauth2/authorize?client_id=%s&permissions={permissions.get_int()}&scope=bot"
SUPPORT = "https://discord.gg/tDQURnVtGC"
SOURCECODE = "https://github.com/PoligonTeam/cenzura"
WEBSITE = "https://cenzura.poligon.lgbt"

class Help(commands.Cog):
    hidden = True

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.interactions = []

    def get_help_embed(self, command):
        embed = femcord.Embed(title="Help:", color=self.bot.embed_color)
        embed.add_field(name=command.other.get("display_name", False) or command.name + ":", value="> " + ", ".join("`" + (subcommand.other.get("display_name", False) or subcommand.name) + "`" for subcommand in command.subcommands if not (subcommand.hidden and subcommand.enabled)))
        embed.add_field(name="\u200b", value=f"\[ [Bot invite]({BOTINVITE}) \] "
                                             f"\[ [Support]({SUPPORT}) \] "
                                             f"\[ [Source code]({SOURCECODE}) \] "
                                             f"\[ [Website]({WEBSITE}) \]" % self.bot.gateway.bot_user.id)

        return embed

    @commands.Listener
    async def on_interaction_create(self, interaction):
        if interaction.message is None:
            return

        if ("help", interaction.user.id, interaction.channel.id, interaction.message.id) in self.interactions:
            embed = femcord.Embed(title="Help:", color=self.bot.embed_color)

            if interaction.data.custom_id == "cog":
                selected_command = None

                for option in interaction.message.components[1].components[0].options:
                    if option.default is True:
                        selected_command = option.value

                selected_command = self.bot.get_command(selected_command)
                selected_cog = self.bot.get_cog(interaction.data.values[0])

                if selected_cog.description is not None:
                    embed.description = selected_cog.description

                embed.add_field(name=selected_cog.name + ":", value="> " + ", ".join("`" + (command.other.get("display_name", False) or command.name) + "`" for command in selected_cog.commands if ((not (command.hidden and command.enabled or command.type == commands.CommandTypes.SUBCOMMAND)) if not command.guild_id else command.guild_id == interaction.guild.id)))
                embed.add_field(name="\u200b", value=f"\[ [Bot invite]({BOTINVITE}) \] "
                                                     f"\[ [Support]({SUPPORT}) \] "
                                                     f"\[ [Source code]({SOURCECODE}) \] "
                                                     f"\[ [Website]({WEBSITE}) \]" % self.bot.gateway.bot_user.id)
            elif interaction.data.custom_id == "command":
                selected_cog = None

                for option in interaction.message.components[0].components[0].options:
                    if option.default is True:
                        selected_cog = option.value

                selected_cog = self.bot.get_cog(selected_cog)
                selected_command = self.bot.get_command(interaction.data.values[0])

                description = ""

                if selected_command.description is not None:
                    description += "Description: `%s`\n" % selected_command.description
                if selected_command.usage is not None:
                    description += "Usage: `%s`\n" % ((selected_command.other.get("display_name", False) or selected_command.name) + " " + selected_command.usage)
                if selected_command.aliases != []:
                    description += "Aliases: %s" % ", ".join("`" + alias + "`" for alias in selected_command.aliases)

                embed.description = description
                embed.set_footer(text="() - required, [] - optional")

                if "embed" in selected_command.other:
                    embed += selected_command.other["embed"]

            components = femcord.Components(
                components = [
                    femcord.ActionRow(
                        components = [
                            femcord.StringSelect(
                                custom_id = "cog",
                                placeholder = "",
                                options = [
                                    femcord.StringSelectOption(
                                        label = cog.name,
                                        value = cog.name,
                                        default=True if selected_cog == cog else False
                                    )
                                    for cog in self.bot.cogs if cog.commands and not cog.hidden
                                ]
                            )
                        ]
                    ),
                    femcord.ActionRow(
                        components = [
                            femcord.StringSelect(
                                custom_id = "command",
                                placeholder = "Select command",
                                options = [
                                    femcord.StringSelectOption(
                                        label = command.other.get("display_name", False) or command.name,
                                        value = command.name,
                                        default = True if selected_command == command else False
                                    )
                                    for command in selected_cog.commands if ((not (command.hidden and command.enabled or command.type == commands.CommandTypes.SUBCOMMAND)) if not command.guild_id else command.guild_id == interaction.guild.id)
                                ]
                            )
                        ]
                    )
                ]
            )

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, embed=embed, components=components)

    @commands.command(description="Shows help", usage="[command]", aliases=["hlep", "hepl"])
    async def help(self, ctx: "Context", *, command = None):
        if command is not None:
            command = command.split(" ")
            command_object = self.bot.get_command(command[0])

            if command_object is None:
                raise commands.CommandNotFound(command)

            usage = command_object.other.get("display_name", False) or command_object.name

            if command_object.usage:
                usage += " " + command_object.usage

            if len(command) > 1:
                while command_object.type is commands.CommandTypes.GROUP:
                    command = command[1:]
                    if command:
                        command_object = command_object.get_subcommand(command[0])
                        if command_object is None:
                            raise commands.CommandNotFound(command)
                        usage += " " + (command_object.other.get("display_name", False) or command_object.name)
                        if command_object.usage and command_object.type is commands.CommandTypes.SUBCOMMAND:
                            usage += " " + command_object.usage

            command = command_object
            description = ""

            if command.description is not None:
                description += "Description: `%s`\n" % command.description
            if command.usage is not None:
                description += "Usage: `%s`\n" % usage
            if command.aliases != []:
                description += "Aliases: %s" % ", ".join("`" + alias + "`" for alias in command.aliases)

            embed = femcord.Embed(title="Help:", description=description, color=self.bot.embed_color)
            embed.set_footer(text="() - required, [] - optional")

            if "embed" in command.other:
                embed += command.other["embed"]

            return await ctx.send(embed=embed)

        components = femcord.Components(
            components = [
                femcord.ActionRow(
                    components = [
                        femcord.StringSelect(
                            custom_id = "cog",
                            placeholder = "Select module",
                            options = [
                                femcord.StringSelectOption(
                                    label = cog.name,
                                    value = cog.name
                                )
                                for cog in self.bot.cogs if cog.commands and not cog.hidden
                            ]
                        )
                    ]
                )
            ]
        )

        selected_cog = self.bot.get_cog(components[0]["components"][0]["options"][0]["value"])

        components.add_component(
            femcord.ActionRow(
                components = [
                    femcord.StringSelect(
                        custom_id = "command",
                        placeholder = "Select command",
                        options = [
                            femcord.StringSelectOption(
                                label = command.other.get("display_name", False) or command.name,
                                value = command.name
                            )
                            for command in selected_cog.commands if ((not (command.hidden and command.enabled or command.type == commands.CommandTypes.SUBCOMMAND)) if not command.guild_id else command.guild_id == ctx.guild.id)
                        ]
                    )
                ]
            )
        )

        components[0]["components"][0]["options"][0]["default"] = True

        embed = femcord.Embed(title="Help:", color=self.bot.embed_color)
        embed.add_field(name=selected_cog.name + ":", value="> " + ", ".join("`" + (command.other.get("display_name", False) or command.name) + "`" for command in selected_cog.commands if ((not (command.hidden and command.enabled or command.type == commands.CommandTypes.SUBCOMMAND)) if not command.guild_id else command.guild_id == ctx.guild.id)))
        embed.add_field(name="\u200b", value=f"\[ [Bot invite]({BOTINVITE}) \] "
                                             f"\[ [Support]({SUPPORT}) \] "
                                             f"\[ [Source code]({SOURCECODE}) \] "
                                             f"\[ [Website]({WEBSITE}) \]" % self.bot.gateway.bot_user.id)

        message = await ctx.reply(embed=embed, components=components)
        self.interactions.append(("help", ctx.author.id, ctx.channel.id, message.id))

def setup(bot: "Bot") -> None:
    bot.load_cog(Help(bot))