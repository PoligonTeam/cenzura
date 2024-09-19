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
from api_client import ApiClient, ApiError
from aiohttp import ClientSession, FormData
from datetime import datetime
from bs4 import BeautifulSoup
from enum import Enum
from cobaltpy import Cobalt

import asyncio
import random
import re
import json
import string
import config
import base64

from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext

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

    @commands.hybrid_command(description="Robi screenshot strony", aliases=["ss"], nsfw=True)
    async def screenshot(self, ctx: Union["Context", "AppContext"], url: str, full_page: bool = False):
        if not isinstance(ctx, commands.AppContext) and not ctx.channel.nsfw:
            raise commands.NotNsfw

        async with femcord.Typing(ctx.message):
            result = URL_PATTERN.match(url)

            if result is None:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

            if result.group(1) is None:
                url = "https://" + url

            if isinstance(ctx, commands.AppContext):
                await ctx.think()

            async with ApiClient(self.bot.local_api_base_url) as client:
                try:
                    data = await client.screenshot(url, full_page)
                except ApiError as e:
                    return await ctx.reply(e)

            message = await ctx.reply(files=[("image.png", data.image)], components=femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl"))))

        is_app = isinstance(ctx, commands.AppContext)
        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
            if is_app:
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id
            return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id

        try:
            interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
        except TimeoutError:
            components = femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl", disabled=True)))
            return await obj.edit(components=components)

        await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
        await ctx.paginator(obj.edit, check, data.content, embeds=[], other={"attachments": []}, prefix="```html\n", suffix="```")

    @commands.hybrid_command(description="Downloads video via cobalt", aliases=["ytdl", "tiktok", "shorts"])
    async def cobalt(self, ctx: Union["Context", "AppContext"], url: str, audio_only: bool | int = 0):
        if isinstance(ctx, commands.AppContext):
            await ctx.think()

        async with femcord.Typing(ctx.message):
            try:
                async with Cobalt() as cobalt:
                    instance = await cobalt.get_best_instance()
                    cobalt.set_instance(instance)

                    download = await cobalt.download(url, {
                        "isAudioOnly": bool(audio_only),
                    })

                    match download.type:
                        case "stream" | "audio":
                            return await ctx.reply(files=[(file.file_name, file.file) for file in download.files])
                        case "picker":
                            files = download.files
                            form = FormData()
                            form.add_field("MAX_FILE_SIZE", "1073741824")
                            form.add_field("target", "1")
                            for index, file in enumerate(files):
                                if not file.is_audio:
                                    form.add_field("image[%s]" % index, file.file, filename=file.file_name)
                            async with cobalt._session.post("https://en.bloggif.com/slide?id=" + "".join([random.choice(string.ascii_lowercase + string.digits) for _ in range(32)]), headers={"User-Agent": self.bot.user_agent}, data=form) as response:
                                content = await response.text()
                                soup = BeautifulSoup(content)
                                gif = soup.select_one(".result-image > img").attrs["src"]
                            for files in [files[i:i+10] for i in range(0, len(files), 10)]:
                                async with femcord.Typing(ctx.message):
                                    await ctx.reply(files=[(file.file_name, file.file) for file in files if not file.is_audio])
                            async with femcord.Typing(ctx.message):
                                async with ClientSession() as session:
                                    async with session.get("https://en.bloggif.com/" + gif) as response:
                                        if response.status == 200:
                                            await ctx.reply(files=[("output.gif", await response.content.read())])
                            async with femcord.Typing(ctx.message):
                                await ctx.reply(files=[(file.file_name, file.file) for file in files if file.is_audio])
                            return
            except asyncio.TimeoutError:
                return await ctx.reply("Request timed out")

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

    @commands.hybrid_command(description="test", type=femcord.enums.ApplicationCommandTypes.MESSAGE)
    async def upload(self, ctx: Union["Context", "AppContext"], message: femcord.types.Message = None):
        message = message or ctx.message
        url = None

        if isinstance(message, str):
            return await ctx.reply("To use this command the bot must be on the server")

        if message.referenced_message and message.referenced_message.attachments:
            url = message.referenced_message.attachments[0].proxy_url
        elif message.attachments:
            url = message.attachments[0].proxy_url

        if not url:
            return await ctx.reply("An unexpected error occurred")

        if isinstance(ctx, commands.AppContext):
            await ctx.think()

        async with femcord.Typing(ctx.message):
            token = random.choice(config.TOKENS)
            bot_id = token.split(".", 1)[0]
            bot_id = bot_id + "=" * (len(bot_id) % 6)
            bot_id = base64.b64decode(bot_id).decode()
            api_url = f"https://discord.com/api/v10/applications/{bot_id}/achievements"

            async with ClientSession() as session:
                async with session.get(url) as response:
                    image = await response.content.read()

            async with ClientSession(headers={"authorization": "Bot " + token}) as session:
                async with session.post(api_url, json={"name": ctx.author.id, "description": ctx.author.id, "icon": "data:image/png;base64," + base64.b64encode(image).decode()}) as response:
                    data = await response.json()
                    achievement_url = f"https://cdn.discordapp.com/app-assets/{bot_id}/achievements/{data["id"]}/icons/{data["icon_hash"]}.png?size=4096"
                async with session.delete(api_url + "/" + data["id"]):
                    pass

            await ctx.reply("<" + achievement_url + ">")

def setup(bot: "Bot") -> None:
    bot.load_cog(Tools(bot))