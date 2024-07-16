"""
Copyright 2022-2024 PoligonTeam

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
from poligonlgbt import get_extension
from api_client import ApiClient, ApiError
from aiohttp import ClientSession, FormData
from datetime import datetime
from bs4 import BeautifulSoup
from enum import Enum
from typing import Tuple
import random, re, json, string

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context

URL_PATTERN = re.compile(r"((http|https):\/\/)?(www\.)?[-a-z0-9@:%._\+~#=]{1,256}\.[a-z0-9()]{1,69}\b[-a-z0-9()@:%_\+.~#!?&//=]*", re.IGNORECASE)

STATUS = [
    "No available data",
    "No unsafe content found",
    "This site is unsafe",
    "Some pages on this site are unsafe",
    "Check a specific URL",
    "This site hosts files that are not commonly downloaded",
    "No available data"
]

WARNINGS = [
    "Send visitors to harmful websites",
    "Install unwanted or malicious software on visitors' computers",
    "Try to trick visitors into sharing personal info or downloading software",
    "Contain unwanted or malicious software",
    "Distribute uncommon downloads"
]

class WebsiteStatus(Enum):
    NO_DATA = 0
    SAFE = 1
    UNSAFE = 2
    SOME_PAGES_UNSAFE = 3
    CHECK_URL = 4
    HOSTS_UNCOMMON_FILES = 5
    UNKNOWN = 6

class WebsiteInfo:
    def __init__(self, data: list) -> None:
        self.status = WebsiteStatus(data[1])
        self.warnings = [
            WARNINGS[index] for index, warning in enumerate(data[2:7]) if warning > 0
        ]
        self.last_update = datetime.fromtimestamp(int(data[7]) / 1000)

class Tools(commands.Cog):
    name = "Narzędzia"

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    # @commands.Listener
    # async def on_ready(self):
    #     # with open("./assets/images/attacl.png", "rb") as f:
    #     #     self.error_image = f.read()

    #     async with ClientSession() as session:
    #         async with session.get("https://data.iana.org/rdap/dns.json") as response:
    #             data = await response.json()

    #             self.rdap_services = data["services"]

    # @commands.command(description="wyszukuje informacje o domenie", usage="(domena)", aliases=["domain", "domena", "domaininfo", "domenainfo"])
    # async def whois(self, ctx: "Context", domain):
    #     tld = domain.split(".")[-1]

    #     rdap_service = None

    #     for service in self.rdap_services:
    #         if tld in service[0]:
    #             rdap_service = service[1][0]
    #             break

    #     assert rdap_service is not None, "Nie znaleziono takiej domeny"

    #     async with ClientSession() as session:
    #         async with session.get(rdap_service + "domain/" + domain) as response:
    #             assert response.status == 200, "Nie znaleziono takiej domeny"

    #             data = await response.json()

    #             nameservers = data["nameservers"]
    #             events = data["events"]
    #             entities = data["entities"]
    #             registrant = entities[0].get("remarks")
    #             registrar = entities[-1]["vcardArray"][1][1][3]

    #             events = sorted(parser.isoparse(event["eventDate"]) for event in events)

    #             embed = femcord.Embed(title=f"Informacje o domenie {domain}:", color=self.bot.embed_color)
    #             embed.add_field(name="Rejestrator:", value=registrar, inline=False)
    #             if registrant is not None:
    #                 embed.add_field(name="Abonent:", value=registrant[0]["title"], inline=False)
    #             embed.add_field(name="Utworzona:", value=femcord.types.t @ events[0], inline=True)
    #             embed.add_field(name="Ostatnia modyfikacja:", value=femcord.types.t @ events[1], inline=True)
    #             embed.add_field(name="Koniec okresu rozliczeniowego:", value=femcord.types.t @ events[2], inline=True)

    #             embed.add_field(name="Serwery DNS:", value=", ".join(nameserver["ldhName"] for nameserver in nameservers), inline=False)

    #             await ctx.reply(embed=embed)

    @commands.command(description="Checks Google Safe Browsing status", usage="(link)", aliases=["safe", "sb"])
    async def safebrowsing(self, ctx: "Context", url: str):
        async with ClientSession() as session:
            async with session.get("https://transparencyreport.google.com/transparencyreport/api/v3/safebrowsing/status", params={"site": url}) as response:
                if response.status != 200:
                    return await ctx.reply("google api error")

                data = await response.read()
                info = WebsiteInfo(json.loads(data[6:])[0])

                embed = femcord.Embed(title=f"Status for {url}:")
                embed.color = (
                    0xea4335,
                    0x34a853,
                    0xea4335,
                    0xfbbc05,
                    self.bot.embed_color,
                    0xfbbc05,
                    0xea4335
                )[info.status.value]
                if info.status != WebsiteStatus.UNKNOWN:
                    embed.set_footer(text="Last Update: " + info.last_update.strftime("%d %b %Y"))

                embed.add_field(name="Status:", value=STATUS[info.status.value], inline=False)
                if info.warnings:
                    embed.add_field(name="Warnings:", value="\n".join(info.warnings), inline=False)

                await ctx.reply(embed=embed)

    @commands.command(description="Pobiera film z youtube - max 2 minuty", usage="(link)", aliases=["yt", "youtube"])
    async def ytdl(self, ctx: "Context", url: str):
        async with ApiClient(self.bot.local_api_base_url) as client:
            try:
                data = await client.ytdl(url)
            except ApiError as e:
                return await ctx.reply(e)

        await ctx.reply(files=[("video.mp4", data.video)])

    @commands.command(description="Robi screenshot strony", aliases=["ss"])
    async def screenshot(self, ctx: "Context", url: str, full_page: bool = False):
        async with femcord.Typing(ctx.message):
            result = URL_PATTERN.match(url)

            if result is None:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

            if result.group(1) is None:
                url = "https://" + url

            async with ApiClient(self.bot.local_api_base_url) as client:
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

    @commands.command(description="Downloads video via cobalt", aliases=["ytdl", "tiktok", "shorts"])
    async def cobalt(self, ctx: "Context", url: str, audio_only: int = 0):
        async def get_file(url: str) -> Tuple[str, bytes]:
            async with session.get(url) as response:
                content = await response.content.read()

                if len(content) > 20 * 1024 * 1024:
                    raise Exception("Content too large")

                if response.headers.get("Content-Disposition"):
                    filename = re.search(r"filename=\"(.+)\"", response.headers["Content-Disposition"]).group(1)
                else:
                    filename = "output." + get_extension(content)
                return filename, content

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get("https://instances.hyper.lol/instances.json", headers={"User-Agent": self.bot.user_agent}) as response:
                    data = await response.json()
                    data = [instance for instance in data if instance["api_online"] and int(instance["score"]) == 100 and instance["protocol"] == "https" and instance["api"] != "api.cobalt.tools"]

                    cobalt = random.choice(data)["api"] if data else "cobalt.tools"

                async with session.post("https://" + cobalt + "/api/json", headers={"Accept": "application/json"}, json={"url": url, "isAudioOnly": bool(audio_only), "filenamePattern": "pretty"}) as response:
                    data = json.loads(await response.text())

                    match data["status"]:
                        case "stream":
                            return await ctx.reply(files=[await get_file(data["url"])])
                        case "picker":
                            files = [await get_file(item["url"]) for item in data["picker"]]
                            form = FormData()
                            form.add_field("MAX_FILE_SIZE", "1073741824")
                            form.add_field("target", "1")
                            for index, file in enumerate(files):
                                form.add_field("image[%s]" % index, file[1], filename=file[0])
                            async with session.post("https://en.bloggif.com/slide?id=" + "".join([random.choice(string.ascii_lowercase + string.digits) for _ in range(32)]), headers={"User-Agent": self.bot.user_agent}, data=form) as response:
                                content = await response.text()
                                soup = BeautifulSoup(content)
                                gif = soup.select_one(".result-image > img").attrs["src"]
                            for files in [files[i:i+10] for i in range(0, len(files), 10)]:
                                async with femcord.Typing(ctx.message):
                                    await ctx.reply(files=files)
                            async with femcord.Typing(ctx.message):
                                _, gif = await get_file("https://en.bloggif.com/" + gif)
                                await ctx.reply(files=[("output.gif", gif)])
                            if not data["audio"]:
                                return
                            async with femcord.Typing(ctx.message):
                                return await ctx.reply(files=[await get_file(data["audio"])])

            await ctx.reply("An unexpected error occurred")

    # @commands.command(description="Nagrywa filmik ze strony", aliases=["recban", "record"])
    # async def rec(self, ctx: "Context", url):
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

def setup(bot: "Bot") -> None:
    bot.load_cog(Tools(bot))
