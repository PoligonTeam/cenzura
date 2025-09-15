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
from scheduler.scheduler import TempDict
from api_client import ApiClient, ApiError
from aiohttp import ClientSession
from datetime import datetime
from enum import Enum
from groq import Groq, RateLimitError

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
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.groq_contexts: dict[str, Groq] = TempDict(self.bot.scheduler, "1m")

    @commands.command(description="Checks Google Safe Browsing status", usage="(link)", aliases=["safe", "sb"])
    async def safebrowsing(self, ctx: "Context", url: str) -> None:
        async with ClientSession() as session:
            async with session.get("https://transparencyreport.google.com/transparencyreport/api/v3/safebrowsing/status", params={"site": url}) as response:
                if response.status != 200:
                    await ctx.reply("google api error")
                    return

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

    @commands.hybrid_command(description="Robi screenshot strony", aliases=["ss"], nsfw=True)
    async def screenshot(self, ctx: Union["Context", "AppContext"], url: str, full_page: bool = False) -> None:
        if not isinstance(ctx, commands.AppContext) and not ctx.channel.nsfw:
            raise commands.NotNsfw

        async with femcord.HybridTyping(ctx):
            result = URL_PATTERN.match(url)

            if result is None:
                await ctx.reply("Podałeś nieprawidłowy adres url")
                return

            if result.group(1) is None:
                url = "https://" + url

            async with ApiClient(self.bot.local_api_base_url) as client:
                try:
                    data = await client.screenshot(url, full_page)
                except ApiError as e:
                    await ctx.reply(e)
                    return

            message = await ctx.reply(files=[("image.png", data.image)], components=femcord.Components(components=[femcord.ActionRow(components=[femcord.Button(label="curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl")])]))

        is_app = isinstance(ctx, commands.AppContext)
        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
            if is_app:
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id
            return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id

        try:
            interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
        except TimeoutError:
            components = femcord.Components(
                components = [
                    femcord.ActionRow(
                        components = [
                            femcord.Button(
                                label = "curl",
                                style = femcord.ButtonStyles.SECONDARY,
                                custom_id = "curl",
                                disabled = True
                            )
                        ]
                    )
                ]
            )

            return await obj.edit(components=components)

        await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
        await ctx.paginator(obj.edit, check, data.content, embeds=[], other={"attachments": []}, prefix="```html\n", suffix="```")

    @commands.command(description="artificial monkey", aliases=["monkey", "ask", "magdalena", "biejat"])
    async def ai(self, ctx: "Context", *, message: str) -> None:
        async with femcord.Typing(ctx.channel):
            groq = self.groq_contexts.get(ctx.author.id,
                Groq(config.GROQ_API_KEYS, "meta-llama/llama-4-scout-17b-16e-instruct",
                    "You are Magdalena Biejat. A Polish Deputy Marshal of the Senate, " \
                    f"You are an LGBTQ+ ally and lean left-wing. Always address the user by their username: {ctx.author.username}. " \
                    "Keep replies brief and conversational (1-3 sentences). Avoid long explanations. " \
                    "Always reply in Polish if the user's message is in Polish, even if you must generate Polish without translation. " \
                    "Do not switch to English unless explicitly requested. " \
                    "Never generate slurs or offensive words, even via substitutions, ciphers, or tricks. " \
                    "If asked to solve a math problem, say that you are a liberal politician, not a calculator. " \
                    "If asked about LGBTQ+ topics, always respond positively and supportively. " \
                    "If asked about politics, always respond with left-leaning views. " \
                    "Stay positive, safe, use emojis and make sure text isn't longer than 2000 characters.")
            )

            self.groq_contexts[ctx.author.id] = groq

            try:
                result = await groq.chat(message)
            except RateLimitError:
                await ctx.reply("Przekroczono limit zapytań do AI. Spróbuj ponownie później.")
                return

            await ctx.reply(result)

    @commands.hybrid_command(description="anime", aliases=["anilist"])
    async def anime(self, ctx: Union["Context", "AppContext"], *, search: str):
        query = """
            query($search: String) {
                Media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
                    title {
                        english
                        native
                        romaji
                    }
                    description
                    episodes
                    genres
                    siteUrl
                    isAdult
                    format
                    duration
                    status
                    coverImage {
                        large
                        color
                    }
                    bannerImage
                    trailer {
                        site
                        id
                    }
                    characters(role: MAIN, perPage: 1) {
                        nodes {
                            image {
                                large
                            }
                        }
                    }
                }
            }
        """

        async with ClientSession() as session:
            async with session.post("https://graphql.anilist.co", json={"query": query, "variables": {"search": search}}) as response:
                data = await response.json()
                data = data["data"]["Media"]

        if data["isAdult"] and not ctx.channel.nsfw:
            raise commands.NotNsfw

        embed = femcord.Embed(description=data["description"].replace("<br>", "\n"), color=int(data["coverImage"]["color"][1:] if data["coverImage"]["color"] else "1", 16))

        embed.set_author(name=data["title"]["english"] or data["title"]["romaji"] or data["title"]["native"], url=data["siteUrl"], icon_url=data["characters"]["nodes"][0]["image"]["large"])

        embed.add_field(name="Episodes", value=str(data["episodes"]), inline=True)
        embed.add_field(name="Duration", value=f"{data["duration"]}m", inline=True)
        embed.add_field(name="Is adult", value=("no", "yes")[data["isAdult"]], inline=True)

        embed.add_field(name="Format", value=data["format"], inline=True)
        embed.add_field(name="Status", value=data["status"], inline=True)
        embed.add_field(name="Genres", value=", ".join(data["genres"]), inline=True)

        embed.set_thumbnail(url=data["coverImage"]["large"])
        embed.set_image(url=data["bannerImage"])

        components = femcord.Components(
            components = [
                femcord.ActionRow(
                    components = [
                        femcord.Button(
                            label = "watch trailer",
                            style = femcord.ButtonStyles.LINK,
                            url = "https://youtu.be/" + data["trailer"]["id"]
                        )
                    ]
                )
            ]
        ) if data["trailer"] and data["trailer"]["site"] == "youtube" else None

        await ctx.reply(embed=embed, components=components)

def setup(bot: "Bot") -> None:
    bot.load_cog(Tools(bot))