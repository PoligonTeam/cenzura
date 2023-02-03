import femcord
from femcord import commands
from datetime import datetime, timedelta
from hafas import HafasClient, Station, NotFound
from utils import table

class Hafas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_board(self, ctx, name, type, amount):
        async with HafasClient() as client:
            try:
                stations: list[Station] = await client.search_station(name)
            except NotFound:
                return "nie ma takiej stacji"

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
                text = table(["Czas", "Kierunek", "Opóźnienie (minuty)"], [[departure.time.strftime("%H:%M"), departure.destination, departure.delay] for departure in departures[:amount if len(departures) > amount else None]])

            return text

    @commands.command(description="pokazuje odjazdy ze stacji")
    async def departures(self, ctx: commands.Context, amount: int, *, name: str):
        if not 0 < amount < 25:
            return await ctx.reply("musisz podać liczbę od 1 do 24")

        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]
        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

    @commands.command(description="pokazuje odjazdy ze stacji")
    async def arrivals(self, ctx: commands.Context, amount: int, *, name: str):
        if not 0 < amount < 25:
            return await ctx.reply("musisz podać liczbę od 1 do 24")

        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]
        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

    @commands.command(description="pokazuje trase z punktu A do punktu B")
    async def journey(self, ctx: commands.Context, *, string: str):
        try:
            departure, arrival = string.split("|")
        except ValueError:
            return await ctx.reply("brakuje czegoś gamoniu")

        async with HafasClient() as client:
            departure = await client.search_station(departure)
            arrival = await client.search_station(arrival)

            journeys = await client.get_journey(departure[0], arrival[0], datetime.now())

            embeds = []

            for journey in journeys:
                embed = femcord.Embed(title=f"Trasa z {journey.stops[0].name} do {journey.stops[-1].name}", color=self.bot.embed_color, description=journey.means_of_transport.operator_image)
                embed.set_thumbnail(url=journey.means_of_transport.operator_image)
                embed.add_field(name="Numer Pociągu", value=journey.means_of_transport.operator_id + " " + journey.means_of_transport.name, inline=True),
                embed.add_field(name="Kierunek", value=journey.arrival_station.name, inline=True)
                embed.add_blank_field()
                embed.add_field(name="Odjazd", value=datetime.fromtimestamp(journey.times.departure / 1000).strftime("%H:%M"), inline=True)
                embed.add_field(name="Przyjazd", value=datetime.fromtimestamp(journey.times.arrival / 1000).strftime("%H:%M"), inline=True)
                embed.add_blank_field()
                embed.add_field(name="Czas", value=str(timedelta(seconds=journey.times.duration)), inline=True)
                embed.add_field(name="Opóźnienie", value=journey.times.delay // 60 if journey.times.delay else "OK", inline=True)
                embed.add_blank_field()

                embeds.append(embed)

            await ctx.reply(embeds=embeds)

def setup(bot):
    bot.load_cog(Hafas(bot))