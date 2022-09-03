import femcord
from femcord import commands
from hafas import Client, Station, InvalidStation
from utils import table
import time

class Hafas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hafas = Client()

    async def get_board(self, ctx, name, type, amount):
        try:
            stations: list[Station] = await self.hafas.search_station(name)
        except InvalidStation:
            return "nie ma takiej stacji"

        station = stations[0]

        if station.name[-1] == "-":
            station = stations[1]

        departures = await self.hafas.list_journeys(station, type, amount)

        client_status = ctx.member.presence.client_status

        if not client_status.desktop or client_status.web:
            text = ""

            for departure in departures:
                text += f"{departure.time} {departure.dest} {departure.delay}\n"
        else:
            text = table(["Czas", "Kierunek", "Opóźnienie"], [[departure.time, departure.dest, departure.delay] for departure in departures])

        return text

    @commands.command(description="pokazuje odjazdy ze stacji")
    async def departures(self, ctx: commands.Context, amount: int, *, name: str):
        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]
        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

    @commands.command(description="pokazuje odjazdy ze stacji")
    async def arrivals(self, ctx: commands.Context, amount: int, *, name: str):
        text = await self.get_board(ctx, name, "arr", amount)
        text = text.splitlines()
        pages = ["\n".join(text[num:num+20]) for num in range(0, len(text), 20)]
        await self.bot.paginator(ctx.reply, ctx, pages=pages, prefix="```\n", suffix="```")

def setup(bot):
    bot.load_cog(Hafas(bot))