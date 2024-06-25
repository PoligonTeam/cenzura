import femcord.femcord as femcord
from femcord.femcord import commands
from datetime import datetime, timedelta
from hafas import HafasClient, Station, NotFound
from utils import table

class Hafas(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_board(self, ctx, name, type, amount):
        async with HafasClient() as client:
            try:
                stations: list[Station] = await client.search_station(name)
            except NotFound:
                return "There is no such station"

            station = stations[0]

            if station.name[-1] == "-":
                station = stations[1]

            departures = await client._get_board(station, type, datetime.now())

            client_status = ctx.member.presence.client_status

            if not client_status.desktop or client_status.web:
                text = ""

                for departure in departures:
                    text += f"{departure.time.strftime('%H:%M')} {departure.dest} {departure.delay}\n"
            else:
                text = table(["Time", "Direction", "Delay (minutes)"], [[departure.time.strftime("%H:%M"), departure.destination, departure.delay] for departure in departures[:amount if len(departures) > amount else None]])

            return text

    @commands.command(description="Shows departures from a station")
    async def departures(self, ctx: commands.Context, amount: int, *, name: str):
        if not 0 < amount < 25:
            return await ctx.reply("You must provide a number from 1 to 24")

        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]

        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

    @commands.command(description="Shows arrivals to a station")
    async def arrivals(self, ctx: commands.Context, amount: int, *, name: str):
        if not 0 < amount < 25:
            return await ctx.reply("You must provide a number from 1 to 24")

        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]
        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

    @commands.command(description="Shows a journey between two stations")
    async def journey(self, ctx: commands.Context, *, string: str):
        try:
            departure, arrival = string.split("|")
        except ValueError:
            return await ctx.reply("You did not provide two stations separated by |")

        async with HafasClient() as client:
            departure = await client.search_station(departure)
            arrival = await client.search_station(arrival)

            journeys = await client.get_journey(departure[0], arrival[0], datetime.now())

            embeds = []

            for journey in journeys:
                embed = femcord.Embed(title=f"Route from {journey.stops[0].name} to {journey.stops[-1].name}", color=self.bot.embed_color, description=journey.means_of_transport.operator_image)
                embed.set_thumbnail(url=journey.means_of_transport.operator_image)
                embed.add_field(name="Train number", value=journey.means_of_transport.operator_id + " " + journey.means_of_transport.name, inline=True),
                embed.add_field(name="Direction", value=journey.arrival_station.name, inline=True)
                embed.add_blank_field()
                embed.add_field(name="Departure", value=datetime.fromtimestamp(journey.times.departure / 1000).strftime("%H:%M"), inline=True)
                embed.add_field(name="Arrival", value=datetime.fromtimestamp(journey.times.arrival / 1000).strftime("%H:%M"), inline=True)
                embed.add_blank_field()
                embed.add_field(name="Time", value=str(timedelta(seconds=journey.times.duration)), inline=True)
                embed.add_field(name="Delay", value=journey.times.delay // 60 if journey.times.delay else "OK", inline=True)
                embed.add_blank_field()

                embeds.append(embed)

            await ctx.reply(embeds=embeds)

def setup(bot: commands.Bot) -> None:
    bot.load_cog(Hafas(bot))