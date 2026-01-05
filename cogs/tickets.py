import femcord.femcord as femcord
from femcord.femcord import commands, components, types, HTTPException
from femcord.femcord.enums import ChannelTypes, InteractionTypes, InteractionCallbackTypes
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from ..bot import Bot, Context

class Tickets(commands.Cog):
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.templates = {}

        for filename in os.listdir("./cogs/templates/tickets"):
            with open("./cogs/templates/tickets/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    @commands.Listener
    async def on_interaction_create(self, interaction: types.Interaction):
        if interaction.data.custom_id == "tickets_manage":
            return await interaction.callback(InteractionCallbackTypes.MODAL,
                components = components.Components(
                    title = "Manage Tickets System",
                    custom_id = "tickets_manage_modal",
                    components = [
                        components.Label(
                            label = "Logs Channel:",
                            description = "Channel where ticket logs will be sent.",
                            component = components.ChannelSelect(
                                custom_id = "tickets_log_channel",
                                channel_types = [
                                    ChannelTypes.GUILD_TEXT
                                ]
                            )
                        ),
                        components.Label(
                            label = "Channel Category:",
                            description = "Where tickets will be created. If your server doesn't have categories, you'll need to create one.",
                            component = components.StringSelect(
                                custom_id = "tickets_category",
                                options = [
                                    components.StringSelectOption(
                                        label = category.name,
                                        value = category.id
                                    ) for category in interaction.guild.channels if category.type == ChannelTypes.GUILD_CATEGORY
                                ] # TODO: handle no categories
                            )
                        ),
                        components.Label(
                            label = "Tickets Role:",
                            description = "Role that can manage tickets. You should choose a role that only staff have, or create a new one.",
                            component = components.RoleSelect(
                                custom_id = "tickets_role"
                            )
                        ),
                        components.Label(
                            label = "Create Ticket Channel:",
                            description = "Channel where create ticket message will be sent.",
                            component = components.ChannelSelect(
                                custom_id = "tickets_create_channel",
                                channel_types = [
                                    ChannelTypes.GUILD_TEXT
                                ]
                            )
                        ),
                        components.Label(
                            label = "Ticket Categories:",
                            description = "Categories for users to choose from when creating a ticket. Separate categories with commas.",
                            component = components.TextInput(
                                custom_id = "ticket_categories",
                                style = components.TextInputStyles.PARAGRAPH,
                                value = "General, Support, Ban Appeal",
                                min_length = 5,
                                max_length = 200
                            )
                        )
                    ]
                )
            )
        elif interaction.data.custom_id == "tickets_manage_messages":
            return await interaction.callback(InteractionCallbackTypes.MODAL,
                components = components.Components(
                    title = "Manage Ticket Messages",
                    custom_id = "tickets_manage_messages_modal",
                    components = [
                        components.Label(
                            label = "Create Ticket Message:",
                            description = "Message sent in the create ticket channel. This uses FemScript: https://czubix.github.io/femscript/",
                            component = components.TextInput(
                                custom_id = "tickets_create_message",
                                style = components.TextInputStyles.PARAGRAPH,
                                value = self.templates["create_ticket_message"],
                                min_length = 10,
                                max_length = 4000
                            )
                        ),
                        components.Label(
                            label = "Create Message:",
                            description = "Message sent when a ticket is created. This uses FemScript: https://czubix.github.io/femscript/",
                            component = components.TextInput(
                                custom_id = "tickets_message",
                                style = components.TextInputStyles.PARAGRAPH,
                                value = self.templates["create_message"],
                                min_length = 10,
                                max_length = 4000
                            )
                        )
                    ]
                )
            )
        elif interaction.data.custom_id == "tickets_disable":
            await interaction.callback(InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, "Disabled the tickets system.")

    @commands.group()
    @commands.has_permissions("manage_guild")
    async def tickets(self, ctx):
        cog = self.bot.get_cog("Help") # type: ignore
        embed = cog.get_help_embed(ctx.command) # type: ignore

        await ctx.reply(embed=embed)

    @tickets.command(description="Manage tickets system")
    @commands.has_permissions("manage_guild")
    async def manage(self, ctx: "Context") -> None:
        await ctx.reply("Click the button below to manage the tickets system.",
            components = components.Components(
                components = [
                    components.ActionRow(
                        components = [
                            components.Button(
                                style = components.ButtonStyles.PRIMARY,
                                label = "Settings",
                                emoji = femcord.Emoji(self.bot, name="⚙️"),
                                custom_id = "tickets_manage"
                            ),
                            components.Button(
                                style = components.ButtonStyles.SECONDARY,
                                label = "Manage Messages",
                                emoji = femcord.Emoji(self.bot, name="📝"),
                                custom_id = "tickets_manage_messages"
                            ),
                            components.Button(
                                style = components.ButtonStyles.DANGER,
                                label = "Disable Tickets",
                                emoji = femcord.Emoji(self.bot, name="⏹️"),
                                custom_id = "tickets_disable"
                            )
                        ]
                    )
                ]
            )
        )

def setup(bot: "Bot") -> None:
    bot.load_cog(Tickets(bot))