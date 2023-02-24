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
from api_client import ApiClient, ApiError
from aiohttp import ClientSession
from dateutil import parser
import re

URL_PATTERN = re.compile(r"((http|https):\/\/)?(www\.)?[-a-z0-9@:%._\+~#=]{1,256}\.[a-z0-9()]{1,69}\b[-a-z0-9()@:%_\+.~#!?&//=]*", re.IGNORECASE)
# tiktok_pattern = re.compile(r"(?x)https?://(?:(?:www|m)\.(?:tiktok.com)\/(?:v|embed|trending)(?:\/)?(?:\?shareId=)?)(?P<id>[\da-z]+)")

class Tools(commands.Cog):
    name = "Narzędzia"

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Listener
    async def on_ready(self):
        # with open("./assets/images/attacl.png", "rb") as f:
        #     self.error_image = f.read()

        async with ClientSession() as session:
            async with session.get("https://data.iana.org/rdap/dns.json") as response:
                data = await response.json()

                self.rdap_services = data["services"]

    @commands.command(description="wyszukuje informacje o domenie", usage="(domena)", aliases=["domain", "domena", "domaininfo", "domenainfo"])
    async def whois(self, ctx: commands.Context, domain):
        tld = domain.split(".")[-1]

        rdap_service = None

        for service in self.rdap_services:
            if tld in service[0]:
                rdap_service = service[1][0]
                break

        assert rdap_service is not None, "Nie znaleziono takiej domeny"

        async with ClientSession() as session:
            async with session.get(rdap_service + "domain/" + domain) as response:
                assert response.status == 200, "Nie znaleziono takiej domeny"

                data = await response.json()

                nameservers = data["nameservers"]
                events = data["events"]
                entities = data["entities"]
                registrant = entities[0].get("remarks")
                registrar = entities[-1]["vcardArray"][1][1][3]

                events = sorted(parser.isoparse(event["eventDate"]) for event in events)

                embed = femcord.Embed(title=f"Informacje o domenie {domain}:", color=self.bot.embed_color)
                embed.add_field(name="Rejestrator:", value=registrar, inline=False)
                if registrant is not None:
                    embed.add_field(name="Abonent:", value=registrant[0]["title"], inline=False)
                embed.add_field(name="Utworzona:", value=femcord.types.t @ events[0], inline=True)
                embed.add_field(name="Ostatnia modyfikacja:", value=femcord.types.t @ events[1], inline=True)
                embed.add_field(name="Koniec okresu rozliczeniowego:", value=femcord.types.t @ events[2], inline=True)

                embed.add_field(name="Serwery DNS:", value=", ".join(nameserver["ldhName"] for nameserver in nameservers), inline=False)

                await ctx.reply(embed=embed)

    @commands.command(description="Pobiera film z youtube - max 2 minuty", usage="(link)", aliases=["yt", "youtube"])
    async def ytdl(self, ctx: commands.Context, url: str):
        async with ApiClient() as client:
            try:
                data = await client.ytdl(url)
            except ApiError as e:
                return await ctx.reply(e)

        await ctx.reply(files=[("video.mp4", data.video)])

    @commands.command(description="Robi screenshot strony", aliases=["ss"])
    async def screenshot(self, ctx: commands.Context, url: str, full_page: bool = False):
        async with femcord.Typing(ctx.message):
            result = URL_PATTERN.match(url)

            if result is None:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

            if result.group(1) is None:
                url = "https://" + url

            async with ApiClient() as client:
                try:
                    data = await client.screenshot(url, full_page)
                except ApiError as e:
                    return await ctx.reply(e)

            components = femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl")))

            message = await ctx.reply(files=[("image.png", data.image)], components=components)

        async def curl(interaction: femcord.types.Interaction):
            await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
            await self.bot.paginator(message.edit, ctx, data.content, embeds=[], other={"attachments": []}, prefix="```html\n", suffix="```")

        async def on_timeout():
            components = femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl", disabled=True)))
            await message.edit(components=components)

        await self.bot.wait_for("interaction_create", curl, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60, on_timeout=on_timeout)

    # @commands.command(description="Nagrywa filmik ze strony", aliases=["recban", "record"])
    # async def rec(self, ctx: commands.Context, url):
    #     if not ctx.author.id in self.bot.owners:
    #         return await ctx.reply("nie możesz!!1!")

    #     async with femcord.Typing(ctx.message):
    #         result = re.match(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,69}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", url)

    #         if not result:
    #             return await ctx.reply("Podałeś nieprawidłowy adres url")

    #         async with async_playwright() as p:
    #             browser = await p.firefox.launch()
    #             context = await browser.new_context(
    #                 record_video_dir="/tmp/",
    #                 record_video_size={"width": 1920, "height": 1080},
    #                 viewport={"width": 1920, "height": 1080}
    #             )
    #             page = await context.new_page()

    #             await page.goto(url)
    #             await page.wait_for_load_state("domcontentloaded")

    #             await context.close()

    #             await ctx.reply(files=[("video.webm", open(await page.video.path(), "rb"))])

    #             await browser.close()

def setup(bot):
    bot.load_cog(Tools(bot))