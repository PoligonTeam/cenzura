from femcord.femcord import commands
from femcord.femcord.enums import InteractionContextTypes, ApplicationIntegrationTypes
from typing import TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from models import Giveaways
from femcord import femcord
import re, random

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext
    from scheduler.scheduler import Schedule

class GiveawayManager:
    schedule: "Schedule"

    def __init__(self, giveaways: list[Giveaways], bot: "Bot") -> None:
        self.giveaways = {
           giveaway.id: giveaway for giveaway in giveaways
        }
        self.bot = bot

    async def send_message(self, giveaway: Giveaways) -> None:
        channel = self.bot.gateway.get_channel(giveaway.channel_id)

        if channel is not None:
            try:
                if not giveaway.participants:
                    await channel.send(f"No one entered the giveaway for **{giveaway.prize}**. No winners can be chosen.")
                else:
                    if len(giveaway.participants) < giveaway.winner_count:
                        winners = giveaway.participants
                    else:
                        winners = random.sample(giveaway.participants, giveaway.winner_count)

                    winner_mentions = ", ".join(f"<@{winner}>" for winner in winners)

                    await channel.send(f"Congratulations {winner_mentions}! You won the giveaway for **{giveaway.prize}**!", mentions=["users"], components=femcord.Components(
                        components = [
                            femcord.ActionRow(components = [
                                femcord.Button(style=femcord.ButtonStyles.SECONDARY, label="Reroll", custom_id=f"reroll_giveaway_{giveaway.id}")
                            ])
                        ]
                    ))
            except femcord.HTTPException as e:
                print(e.original_error)
                pass

    async def task(self) -> None:
        for _id, giveaway in self.giveaways.items():
            if giveaway.ended:
                continue

            if giveaway.end_time <= datetime.now(tz=timezone.utc):
                self.bot.loop.create_task(self.send_message(giveaway))
                del self.giveaways[_id]
                giveaway.ended = True
                await giveaway.save()

    async def run(self) -> None:
        if not self.bot.scheduler.get_schedules("giveaway_manager"):
            await self.bot.scheduler.create_schedule(
                self.task,
                "5s",
                name="giveaway_manager" # type: ignore
            )()

class Giveaway(commands.Cog):
    manager: GiveawayManager

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    def on_load(self) -> None:
        self.bot.loop.create_task(self.load_active_giveaways())

    def on_unload(self) -> None:
        if (schedules := self.bot.scheduler.get_schedules("giveaway_manager")):
            self.bot.scheduler.cancel_schedules(schedules)

    async def load_active_giveaways(self) -> None:
        active_giveaways = await Giveaways.filter(ended=False)
        self.manager = GiveawayManager(active_giveaways, self.bot)
        await self.manager.run()

    def parse_time(self, text: str) -> timedelta:
        pattern = r"(\d+)([dhms])"
        matches = re.findall(pattern, text.strip().lower().replace(" ", ""))

        if not matches:
            raise ValueError(f"Invalid time format: {text}")

        days = hours = minutes = seconds = 0
        for value, unit in matches:
            value = int(value)
            if unit == "d":
                days += value
            elif unit == "h":
                hours += value
            elif unit == "m":
                minutes += value
            elif unit == "s":
                seconds += value

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @commands.Listener
    async def on_interaction_create(self, interaction: femcord.types.Interaction) -> None:
        if interaction.guild is None or interaction.type != femcord.enums.InteractionTypes.MESSAGE_COMPONENT:
            return

        is_data = interaction.data is not None
        is_enter_giveaway = is_data and interaction.data.custom_id.startswith("enter_giveaway_")
        is_reroll_giveaway = is_data and interaction.data.custom_id.startswith("reroll_giveaway_")

        if not (is_enter_giveaway or is_reroll_giveaway):
            return

        giveaway_id = interaction.data.custom_id.split("_")[-1]
        giveaway = self.manager.giveaways.get(int(giveaway_id))

        if is_reroll_giveaway:
            if not interaction.member.permissions.has("manage_guild"): # type: ignore
                await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content="You do not have permission to reroll this giveaway.", flags=[femcord.enums.MessageFlags.EPHEMERAL])
                return

            giveaway = await Giveaways.get_or_none(id=int(giveaway_id))

            if not giveaway or not giveaway.participants:
                await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content="No one entered the giveaway. No winners can be chosen.", flags=[femcord.enums.MessageFlags.EPHEMERAL])
                return

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, flags=[femcord.enums.MessageFlags.EPHEMERAL])
            await self.manager.send_message(giveaway)
            return

        if not giveaway or giveaway.ended:
            await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content="This giveaway has ended or does not exist.", flags=[femcord.enums.MessageFlags.EPHEMERAL])
            return

        if interaction.user.id in giveaway.participants:
            await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content="You have already entered this giveaway!", flags=[femcord.enums.MessageFlags.EPHEMERAL])
            return

        giveaway.participants.append(interaction.user.id)
        await giveaway.save()

        await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content=f"You have successfully entered the giveaway for **{giveaway.prize}**!", flags=[femcord.enums.MessageFlags.EPHEMERAL])

    @commands.hybrid_command(description="Start a giveaway", usage="[winner_count] [time] [prize]", integration_types=[ApplicationIntegrationTypes.GUILD_INSTALL], interaction_context_types=[InteractionContextTypes.GUILD])
    @commands.has_permissions("manage_guild")
    async def giveaway(self, ctx: "Context | AppContext", winner_count: int, time: str, *, prize: str) -> None:
        try:
            duration = self.parse_time(time)
        except ValueError as e:
            await ctx.reply(str(e))
            return

        end_time = datetime.now(tz=timezone.utc) + duration
        giveaway = await Giveaways.create(
            message_id=ctx.message.id if ctx.message else "0", # type: ignore
            channel_id=ctx.channel.id, # type: ignore
            guild_id=ctx.guild.id,
            prize=prize,
            host_id=ctx.author.id,
            winner_count=winner_count,
            end_time=end_time,
            participants=[],
            ended=False
        )

        self.manager.giveaways[giveaway.id] = giveaway

        await ctx.send(
            f"Giveaway started for **{prize}** and {winner_count} winner(s)! It will end in {femcord.types.t @ giveaway.end_time}. React to this message to enter!",
            components=femcord.Components(components = [
                femcord.ActionRow(components = [
                    femcord.Button(style=femcord.ButtonStyles.PRIMARY, label="Enter Giveaway", custom_id=f"enter_giveaway_{giveaway.id}")
                ])
            ])
        )

        if ctx.message and not hasattr(ctx, "interaction"):
            await ctx.message.delete()


def setup(bot: "Bot") -> None:
    bot.load_cog(Giveaway(bot))