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
from femcord.femcord import commands, types, InvalidArgument, HTTPException
from femcord.femcord.commands import Max
from femcord.femcord.http import Route
from femcord.femcord.permissions import Permissions
from femcord.femcord.enums import Intents, ApplicationCommandTypes, PublicFlags
from femcord.femcord.utils import get_index
from aiohttp import ClientSession, FormData
from bs4 import BeautifulSoup, ResultSet
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from concurrent.futures import ThreadPoolExecutor
from pyfiglet import Figlet
from utils import *
from utils import _
from stickers import Sticker
import io
import random
import urllib.parse
import json
import re
import string

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext

class Fun(commands.Cog):
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.results = {}
        self.urls = {}
        self.translations = bot.get_translations_for("fun")

    @commands.hybrid_command(description="User avatar", usage="[user]", aliases=["av"], type=ApplicationCommandTypes.USER)
    async def avatar(self, ctx: Union["Context", "AppContext"], user: types.User = None):
        user = user or ctx.author

        async with ClientSession() as session:
            async with session.get(user.avatar_url + "?size=512") as response:
                content = await response.content.read()

        await ctx.reply(files=[("avatar." + ("gif" if user.avatar[:2] == "a_" else "png"), content)])

    @commands.hybrid_command(description="Shows the percentage of love between users", usage="(user) [user]", aliases=["love"], type=ApplicationCommandTypes.USER)
    async def ship(self, ctx: Union["Context", "AppContext"], user: types.User, user2: types.User = None):
        async with femcord.HybridTyping(ctx):
            user2 = user2 or ctx.author

            user_avatar_response = await self.bot.http.session.get(user.avatar_as("png"))
            user2_avatar_response = await self.bot.http.session.get(user2.avatar_as("png"))

            user_avatar = io.BytesIO(await user_avatar_response.content.read())
            user2_avatar = io.BytesIO(await user2_avatar_response.content.read())

            result_image = io.BytesIO()

            def create_image() -> None:
                nonlocal user2_avatar, user2_avatar, result_image

                ship_image = Image.open("./assets/images/ship2.jpg").convert("RGBA")

                user_image = Image.open(user_avatar).convert("RGBA")
                user2_image = Image.open(user2_avatar).convert("RGBA")

                user_image = ImageOps.fit(user_image, (250, 250))
                user2_image = ImageOps.fit(user2_image, (250, 250))

                ship_image.paste(user_image, (440, 80), user_image)
                ship_image.paste(user2_image, (700, 250), user2_image)

                ship_image.save(result_image, "PNG")

            async def async_create_image() -> None:
                await self.bot.loop.run_in_executor(ThreadPoolExecutor(), create_image)

            await self.bot.loop.create_task(async_create_image())

            await ctx.reply(await _(
                "**{}** + **{}** = **{}**\nThey love each other for **{}%**!",
                user.username,
                user2.username,
                user.username[:len(user.username) // 2].lower() + user2.username[len(user2.username) // 2:].lower(),
                get_int(user, user2)
            ), files=[("ship.png", result_image.getvalue())])

    @commands.command(description="dog", aliases=["ars", "6vz", "piesvz", "<@338075554937044994>", "<@!338075554937044994>"])
    async def dog(self, ctx: "Context"):
        alias = ctx.message.content.split()[0][len((await self.bot.get_prefix(self.bot, ctx.message))[-1]):]

        if alias in ("6vz", "piesvz", "<@338075554937044994>", "<@!338075554937044994>"):
            return await ctx.reply(files=[("dog.png", open("./assets/images/6vz.png", "rb")), ("dog2.png", open("./assets/images/6vz2.png", "rb"))])
        elif alias == "ars":
            return await ctx.reply(files=[("dog.jpg", open("./assets/images/ars.jpg", "rb"))])

        response = await self.bot.http.session.get("https://dog.ceo/api/breeds/image/random")
        response_data = await response.json()
        image = await self.bot.http.session.get(response_data["message"])
        content = await image.content.read()

        try:
            mimetype = femcord.utils.get_mime(content)
        except InvalidArgument:
            return await self.dog(ctx)

        extension = mimetype.split("/")[1]

        await ctx.reply(files=[("dog." + extension, content)])

    @commands.command(description="cat", aliases=["mesik", "<@563718132863074324>", "<@!563718132863074324>"])
    async def cat(self, ctx: "Context"):
        alias = ctx.message.content.split()[0][len((await self.bot.get_prefix(self.bot, ctx.message))[-1]):]

        if alias in ("mesik", "<@563718132863074324>", "<@!563718132863074324>"):
            return await ctx.reply(files=[("cat.jpg", open("./assets/images/mesik.jpg", "rb")), ("cat2.png", open("./assets/images/mesik2.jpg", "rb"))])

        image = await self.bot.http.session.get("https://cataas.com/cat" + ("/gif" if random.random() > .5 else ""))
        content = await image.content.read()

        try:
            mimetype = femcord.utils.get_mime(content)
        except InvalidArgument:
            return await self.cat(ctx)

        extension = mimetype.split("/")[1]

        await ctx.reply(files=[("cat." + extension, content)])

    @commands.command(description=".i.", usage="(text)", aliases=["ascii"])
    async def figlet(self, ctx: "Context", *, text):
        figlet = Figlet().renderText("\n".join(text.split()))

        if text[:3] == ".i." and (not text[4:] or text[4:].isdigit()):
            figlet = figlet.splitlines()[:6]
            num = int(text[4:]) if text[4:] else 3
            if num > 100:
                num = 100
            for _ in range(num):
                figlet.insert(3, figlet[2])
            figlet = "\n".join(figlet)

        await ctx.reply("```" + figlet + "```")

    @commands.hybrid_command(description="Orientation quiz", aliases=["howgay", "quiz"])
    async def orientation(self, ctx: Union["Context", "AppContext"]):
        is_app = isinstance(ctx, commands.AppContext)

        components = femcord.Components(
            components = [
                femcord.TextDisplay(
                    content = "I identify as a:"
                ),
                femcord.ActionRow(
                    components = [
                        femcord.Button(
                            label = "Man",
                            style = femcord.ButtonStyles.PRIMARY,
                            custom_id = "0"
                        ),
                        femcord.Button(
                            label = "Woman",
                            style = femcord.ButtonStyles.PRIMARY,
                            custom_id = "1"
                        )
                    ]
                )
            ]
        )

        timed_out_components = femcord.Components(
            components = [
                femcord.TextDisplay(
                    content = "Timed out"
                )
            ]
        )

        message = await ctx.reply(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
            if is_app:
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id
            return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id

        try:
            interaction: types.Interaction
            interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
        except TimeoutError:
            return await obj.edit(components=timed_out_components)

        questions = [
            ("Found a man attractive.", 1),
            ("Fantasized about non-sexual petting and/or bodily closeness with a man.", 1),
            ("Fantasized about sexual intercourse with a man.", 1),
            ("Entertained the fantasy of being in a long-term romantic relationship with a man.", 1),
            ("Found myself wanting to have real-life sexual intercourse with a man.", 1),
            ("Wanted to touch a man intimately and/or be naked in the company of a man.", 1),
            ("Found myself sexually aroused by a man.", 1),
            ("Found a woman attractive.", 0),
            ("Fantasized about non-sexual petting and/or bodily closeness with a woman.", 0),
            ("Fantasized about sexual intercourse with a woman.", 0),
            ("Entertained the fantasy of being in a long-term romantic relationship with a woman.", 0),
            ("Found myself wanting to have real-life sexual intercourse with a woman.", 0),
            ("Wanted to touch a woman intimately and/or be naked in the company of a woman.", 0),
            ("Found myself sexually aroused by a woman.", 0)
        ]

        gender = int(interaction.data.custom_id)

        max_points = 100 / len(questions)

        _map = {
            0: -max_points,
            1: -max_points/2,
            2: 0,
            3: max_points/2,
            4: max_points
        }

        point = [50, 50]

        action_row = femcord.ActionRow(components = [
            femcord.Button(label="No", style=femcord.ButtonStyles.DANGER, custom_id="0"),
            femcord.Button(label="Probably not", style=femcord.ButtonStyles.DANGER, custom_id="1"),
            femcord.Button(label="Idk", style=femcord.ButtonStyles.SECONDARY, custom_id="2"),
            femcord.Button(label="Probably yes", style=femcord.ButtonStyles.SUCCESS, custom_id="3"),
            femcord.Button(label="Yes", style=femcord.ButtonStyles.SUCCESS, custom_id="4")
        ])

        for index, (question, for_gender) in enumerate(questions, 1):
            components = femcord.Components()
            components.add_component(femcord.TextDisplay(content=f"({index}/{len(questions)}) " + question))
            components.add_component(action_row)

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, components=components)

            try:
                interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
            except TimeoutError:
                return await obj.edit(components=timed_out_components)

            axis = for_gender == gender
            value = _map[int(interaction.data.custom_id)]
            point[axis] += value

        y, x = round(point[0], 1), round(point[1], 1)

        if not y % 1:
            y = int(y)
        if not x % 1:
            x = int(x)

        text = f"Your sexual orientation is {x}% heterosexual, {y}% homosexual, which places you in "

        if y == 50 or x == 50:
            text += "between quadrants."
        else:
            if x > 50 and y > 50:
                quadrant = "bisexual"
            elif x < 50 and y < 50:
                quadrant = "asexual"
            elif x < 50 and y > 50:
                quadrant = "homosexual"
            elif x > 50 and y < 50:
                quadrant = "heterosexual"

            text += f"the {quadrant} quadrant."

        components = femcord.Components(
            components = [
                femcord.TextDisplay(
                    content = text
                ),
                femcord.MediaGallery(
                    items = [
                        femcord.MediaItem(
                            media = femcord.UnfurledMediaItem(
                                url = f"https://www.idrlabs.com/graphic/sexual-orientation?p={y},{x}"
                            )
                        )
                    ]
                )
            ]
        )

        await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, components=components)

    @commands.command(description="Achievement Get!", usage="(text)")
    async def achievement(self, ctx: "Context", *, text: replace_chars) -> None:
        if len(text) > 23:
            return await ctx.reply(await _("Provided text is too long (`{}`/`{}`)", len(text), 23))

        image = await self.bot.http.session.get(f"https://minecraftskinstealer.com/achievement/{random.randint(1, 40)}/Achievement+Get%21/{text}")

        await ctx.reply(files=[("achievement.png", await image.content.read())])

    @commands.command(description="Replaces text with garfield emojis", usage="(text)")
    async def garfield(self, ctx: "Context", *, text: replace_chars):
        if len(text) > 60:
            return await ctx.reply(await _("Provided text is too long (`{}`/`{}`)", len(text), 60))

        allowed_chars = [emoji.name.split("_")[1] for emoji in self.bot.gateway.emojis if emoji.name.startswith("garfield_")]

        garfield_text = ""

        for char in text:
            char = char.lower()
            if char in allowed_chars or char == " ":
                garfield_text += str(self.bot.gateway.get_emoji(name="garfield_" + (char if char != " " else "space")))
                continue

            garfield_text += char

        await ctx.reply(garfield_text)

    @commands.command(description="Adds a hidden message to text", usage="(text) | (hidden_text)", other={"embed": femcord.Embed().set_image(url="https://cdn.poligon.lgbt/riEyNGVIuO.png")})
    async def encode(self, ctx: "Context", *, text: replace_chars):
        text = text.split(" | ")

        if 2 > len(text):
            return await ctx.reply(_("You did not provide the hidden text"))

        text[1] = text[1].replace(" ", "_")

        if len(text[0]) < 2:
            return await ctx.reply(await _("Provided text is too short (`{}`/`{}`)", len(text[0]), 2))

        await ctx.reply(text[0][0] + encode_text(text[1]) + text[0][1:])

    @commands.command(description="Reveals the hidden message from text", usage="(text)", other={"embed": femcord.Embed().set_image(url="https://cdn.poligon.lgbt/fsdKWwqWKx.png")})
    async def decode(self, ctx: "Context", *, text):
        allowed_chars = [group[0] for group in CHARS] + [SEPARATOR]
        new_text = ""

        for char in text:
            if char in allowed_chars:
                new_text += char

        await ctx.reply(decode_text(new_text))

    @commands.Listener
    async def on_interaction_create(self, interaction: femcord.types.Interaction) -> None:
        if interaction.data.custom_id == "accept":
            await interaction.callback(femcord.InteractionCallbackTypes.CHANNEL_MESSAGE_WITH_SOURCE, content="Did we get you? [Add fembot](https://discord.com/oauth2/authorize?client_id=705552952600952960) to your profile to fool others!", flags=[femcord.enums.MessageFlags.EPHEMERAL])
            return

        # if ("calc", interaction.member.user.id, interaction.channel.id, interaction.message.id) in self.interactions:
        #     if not interaction.message.id in self.results:
        #         self.results[interaction.message.id] = ["", 0]

        #     if self.results[interaction.message.id][0] == "KABOOM!":
        #         self.results[interaction.message.id][0] = ""

        #     match interaction.data.custom_id:
        #         case "leftbracket":
        #             self.results[interaction.message.id][0] += "("
        #             self.results[interaction.message.id][1] = 0
        #         case "rightbracket":
        #             self.results[interaction.message.id][0] += ")"
        #             self.results[interaction.message.id][1] = 0
        #         case "power":
        #             self.results[interaction.message.id][0] += "**"
        #             self.results[interaction.message.id][1] = 0
        #         case "modulo":
        #             self.results[interaction.message.id][0] += "%"
        #             self.results[interaction.message.id][1] = 0
        #         case "backspace":
        #             self.results[interaction.message.id][0] = self.results[interaction.message.id][0][:-1]
        #             self.results[interaction.message.id][1] = 0
        #         case "clear":
        #             self.results[interaction.message.id][0] = ""
        #             self.results[interaction.message.id][1] = 0
        #         case "divide":
        #             self.results[interaction.message.id][0] += "/"
        #             self.results[interaction.message.id][1] = 0
        #         case "multiply":
        #             self.results[interaction.message.id][0] += "*"
        #             self.results[interaction.message.id][1] = 0
        #         case "minus":
        #             self.results[interaction.message.id][0] += "-"
        #             self.results[interaction.message.id][1] = 0
        #         case "dot":
        #             self.results[interaction.message.id][0] += "."
        #             self.results[interaction.message.id][1] = 0
        #         case "equal":
        #             if len(self.results[interaction.message.id][0]) <= 50:
        #                 try:
        #                     self.results[interaction.message.id][0] += "=" + str(round(eval(self.results[interaction.message.id][0]), 2))
        #                 except:
        #                     self.results[interaction.message.id][0] = "KABOOM!" if self.results[interaction.message.id][0] == "/0" else ""
        #                 self.results[interaction.message.id][1] = 0
        #         case "add":
        #             self.results[interaction.message.id][0] += "+"
        #             self.results[interaction.message.id][1] = 0
        #         case "0":
        #             if not self.results[interaction.message.id][0] == "0" and not len(self.results[interaction.message.id][0]) == 1:
        #                 self.results[interaction.message.id][0] += "0"
        #                 self.results[interaction.message.id][1] = 0
        #         case _:
        #             if self.results[interaction.message.id][1] <= 5:
        #                 self.results[interaction.message.id][0] += interaction.data.custom_id
        #                 self.results[interaction.message.id][1] += 1

        #     await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, "```" + (self.results[interaction.message.id][0] if self.results[interaction.message.id][0] else "0") + "```")

        #     if "=" in self.results[interaction.message.id][0]:
        #         self.results[interaction.message.id][0] = ""

    # @commands.command(description="liczydło", aliases=["kalkulator", "calculator"])
    # async def calc(self, ctx: "Context"):
    #     components = femcord.Components(
    #         components = [
    #             femcord.ActionRow(
    #                 components = [
    #                     femcord.Button(label="x\u02b8", style=femcord.ButtonStyles.SECONDARY, custom_id="power"),
    #                     femcord.Button(label="%", style=femcord.ButtonStyles.SECONDARY, custom_id="modulo"),
    #                     femcord.Button(label="<-", style=femcord.ButtonStyles.SECONDARY, custom_id="backspace"),
    #                     femcord.Button(label="C", style=femcord.ButtonStyles.DANGER, custom_id="clear")
    #                 ]
    #             ),
    #             femcord.ActionRow(
    #                 components = [
    #                     femcord.Button(label="7", style=femcord.ButtonStyles.SECONDARY, custom_id="7"),
    #                     femcord.Button(label="8", style=femcord.ButtonStyles.SECONDARY, custom_id="8"),
    #                     femcord.Button(label="9", style=femcord.ButtonStyles.SECONDARY, custom_id="9"),
    #                     femcord.Button(label="/", style=femcord.ButtonStyles.SECONDARY, custom_id="divide"),
    #                     femcord.Button(label="(", style=femcord.ButtonStyles.SECONDARY, custom_id="leftbracket")
    #                 ]
    #             ),
    #             femcord.ActionRow(
    #                 components = [
    #                     femcord.Button(label="4", style=femcord.ButtonStyles.SECONDARY, custom_id="4"),
    #                     femcord.Button(label="5", style=femcord.ButtonStyles.SECONDARY, custom_id="5"),
    #                     femcord.Button(label="6", style=femcord.ButtonStyles.SECONDARY, custom_id="6"),
    #                     femcord.Button(label="*", style=femcord.ButtonStyles.SECONDARY, custom_id="multiply"),
    #                     femcord.Button(label=")", style=femcord.ButtonStyles.SECONDARY, custom_id="rightbracket")
    #                 ]
    #             ),
    #             femcord.ActionRow(
    #                 components = [
    #                     femcord.Button(label="1", style=femcord.ButtonStyles.SECONDARY, custom_id="1"),
    #                     femcord.Button(label="2", style=femcord.ButtonStyles.SECONDARY, custom_id="2"),
    #                     femcord.Button(label="3", style=femcord.ButtonStyles.SECONDARY, custom_id="3"),
    #                     femcord.Button(label="-", style=femcord.ButtonStyles.SECONDARY, custom_id="minus")
    #                 ]
    #             ),
    #             femcord.ActionRow(
    #                 components = [
    #                     femcord.Button(label="0", style=femcord.ButtonStyles.SECONDARY, custom_id="0"),
    #                     femcord.Button(label=".", style=femcord.ButtonStyles.SECONDARY, custom_id="dot"),
    #                     femcord.Button(label="=", style=femcord.ButtonStyles.PRIMARY, custom_id="equal"),
    #                     femcord.Button(label="+", style=femcord.ButtonStyles.SECONDARY, custom_id="add")
    #                 ]
    #             )
    #         ]
    #     )

    #     message = await ctx.reply("```0```", components=components)
    #     self.interactions.append(("calc", ctx.author.id, ctx.channel.id, message.id))

    @commands.command(description="inside joke", usage="[user/text/attachment/reply]")
    async def cantseeme(self, ctx: "Context", *, arg: types.User | str = None):
        arg = arg or ctx.author

        if ctx.message.referenced_message and ctx.message.referenced_message.attachments:
            url = ctx.message.referenced_message.attachments[0].proxy_url
        elif ctx.message.attachments:
            url = ctx.message.attachments[0].proxy_url
        elif isinstance(arg, types.User):
            url = arg.avatar_url

        if isinstance(arg, str):
            if len(arg) > 105:
                return await ctx.reply(await _("Provided text is too long (`{}`/`{}`)", len(arg), 105))

            if len(arg) > 15:
                arg = "\n".join(arg[x:x+15] for x in range(0, len(arg), 15))

        image = await self.bot.http.session.get(url)
        arg = io.BytesIO(await image.content.read())
        result_image = io.BytesIO()

        def create_image() -> None:
            nonlocal arg, result_image

            bush = Image.open("./assets/images/bush.png")

            if isinstance(arg, str):
                draw = ImageDraw.Draw(bush)
                font = ImageFont.truetype("./assets/fonts/HKNova-Medium.ttf", 30)

                draw.text((round(bush.size[0] / 2) - 50, round(bush.size[1] / 2) - 60), arg, font=font)
            else:
                arg = Image.open(arg)
                width, height = arg.size

                width = 150 if width > 150 else width
                height = 150 if height > 150 else height

                arg.thumbnail((width, height))

                bush.paste(arg, (round(bush.size[0] / 2 - arg.size[0] / 2), round(bush.size[1] / 2 - arg.size[1] / 2 - 30)))

            bush.save(result_image, "PNG")

        async def async_create_image() -> None:
            await self.bot.loop.run_in_executor(ThreadPoolExecutor(), create_image)

        await self.bot.loop.create_task(async_create_image())

        await ctx.reply(files=[("cantseeme.png", result_image.getvalue())])

    @commands.command(description="lgbt", usage="[user]", aliases=["lgbt"])
    async def gay(self, ctx: "Context", user: types.User = None):
        user = user or ctx.author

        image = await self.bot.http.session.get(user.avatar_url)
        image = io.BytesIO(await image.content.read())
        result_image = io.BytesIO()

        def create_image() -> None:
            nonlocal image, result_image

            lgbt = Image.open("./assets/images/lgbt.png")
            image = Image.open(image)

            lgbt = ImageOps.fit(lgbt, (512, 512))
            image = ImageOps.fit(image, (512, 512))

            mask = Image.new("L", (512, 512), 128)

            avatar = Image.composite(image, lgbt, mask)

            avatar.save(result_image, "PNG")

        async def async_create_image() -> None:
            await self.bot.loop.run_in_executor(ThreadPoolExecutor(), create_image)

        await self.bot.loop.create_task(async_create_image())

        await ctx.reply(files=[("gay.png", result_image.getvalue())])

    @commands.hybrid_command(description="Select the cwel", usage="[user/attachment/reply]", type=ApplicationCommandTypes.USER)
    async def cwel(self, ctx: Union["Context", "AppContext"], user: types.User = None):
        user = user or ctx.author
        url = user.avatar_url

        if isinstance(ctx, commands.AppContext):
            await ctx.think()
        else:
            if ctx.message.referenced_message and ctx.message.referenced_message.attachments:
                url = ctx.message.referenced_message.attachments[0].proxy_url
            elif ctx.message.attachments:
                url = ctx.message.attachments[0].proxy_url

        async with ClientSession() as session:
            async with session.get(url) as response:
                image = io.BytesIO(await response.content.read())

        result_image = io.BytesIO()

        def create_image() -> None:
            nonlocal image, result_image

            cwel = Image.open("./assets/images/cwel.png")
            image = Image.open(image)

            image = ImageOps.fit(image, cwel.size)

            combined = Image.alpha_composite(image.convert("RGBA"), cwel.convert("RGBA"))

            combined.save(result_image, "PNG")

        async def async_create_image() -> None:
            await self.bot.loop.run_in_executor(ThreadPoolExecutor(), create_image)

        await self.bot.loop.create_task(async_create_image())

        await ctx.reply(files=[("cwel.gif", result_image.getvalue())])

    @commands.command(description="Random meme from jbzd", aliases=["mem"])
    @commands.is_nsfw
    async def meme(self, ctx: "Context"):
        memes = []

        while not memes:
            memes_page = await self.bot.http.session.get(f"https://jbzd.com.pl/str/{random.randint(1, 235)}")
            memes_soup = BeautifulSoup(await memes_page.content.read(), "lxml")

            memes = memes_soup.find_all("img", {"class": "article-image"})

        await ctx.reply(random.choice(memes)["src"])

    @commands.command(description="\U0001F633", usage="[user]")
    async def dick(self, ctx: "Context", user: types.User = None):
        await self.figlet(ctx, text=f".i. {get_int(user or ctx.author) // 5}")

    # @commands.command(description="taobao, aliexpress, and china", usage="(product)", aliases=["aliexpress"])
    # async def taobao(self, ctx: "Context", *, product):
    #     response = await self.bot.http.session.get("https://pl.aliexpress.com/wholesale?SearchText=" + urllib.parse.quote_plus(product))
    #     soup = BeautifulSoup(await response.content.read(), "lxml")

    #     raw_item_list = soup.find_all("script", {"type": "text/javascript"})[3].string.splitlines()[3].strip("window.runParams = ")[:-1]
    #     item_list = json.loads(raw_item_list)["mods"]["itemList"]["content"]

    #     random_product = random.choice(item_list)

    #     await ctx.reply(f"\"{random_product['title']['displayTitle']}\"\nhttps://aliexpress.com/item/{random_product['productId']}.html\n\n*from aliexpress.com*")

    # @commands.command(description="shopee wyszukiwarka", usage="(produkt)", aliases=["shopenis", "fakeali", "alisexpress"])
    # async def shopee(self, ctx: "Context", *, product):
    #     response = (await (await self.bot.http.session.get("https://shopee.pl/api/v4/search/search_items?by=relevancy&keyword=" + urllib.parse.quote_plus(product) + "&limit=60&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2")).json())["items"]

    #     if len(response) == 0:
    #         return await ctx.reply("Nie ma takiego produktu :cry:")

    #     random_product = random.choice(response)['item_basic']

    #     embed = femcord.Embed(title=f"{str(format(random_product['price'] / 100000, '.2f'))}PLN | {random_product['name']}", url=f"https://shopee.pl/{random_product['name'].replace(' ', '-')}-i.{random_product['shopid']}.{random_product['itemid']}")
    #     embed.set_thumbnail(url=f"https://cf.shopee.pl/file/{random_product['image']}")
    #     embed.set_author(name="shopee.pl")
    #     embed.set_footer(text="Your preferred online shopping platform.")

    #     await ctx.reply(f"\"{random_product['name']}\"\nhttps://shopee.pl/{random_product['name'].replace(' ', '-')}-i.{random_product['shopid']}.{random_product['itemid']} *z shopee.pl*", embed=embed)

    @commands.command(description="Random wallpaper from tapetus.pl", aliases=["tapeta"])
    async def tapetus(self, ctx: "Context"):
        response = await self.bot.http.session.get(f"https://tapetus.pl/,st_{random.randint(0, 5527)}.php")
        soup = BeautifulSoup(await response.content.read(), "lxml")

        images = soup.find_all("img", {"class": "img_srednie"})
        image = random.choice(images).parent

        await ctx.reply("https://tapetus.pl/obrazki/n/" + image["href"][:-3].replace(",", "_") + "jpg")

    @commands.hybrid_command(description="Shows information about user", usage="[user]", aliases=["ui", "user", "cotozacwel", "kimtykurwajestes"], type=ApplicationCommandTypes.USER)
    async def userinfo(self, ctx: Union["Context", "AppContext"], user: types.Member | types.User = None):
        user = user or ctx.member

        if isinstance(user, types.Member):
            member = user
            user = member.user

        elif isinstance(user, types.User):
            member = None

        raw_user = await self.bot.gateway.fetch_user(user.id)
        user.banner = raw_user["banner"]
        user.accent_color = raw_user["accent_color"]
        user.banner_color = raw_user["banner_color"]

        files = []

        if user.banner:
            banner_url = user.banner_url
        else:
            if user.banner_color:
                color = int(user.banner_color[1:], 16)
            else:
                color = user.accent_color or 0

            data = io.BytesIO()

            async def async_create_image() -> None:
                await self.bot.loop.run_in_executor(ThreadPoolExecutor(), lambda:
                    Image.new("RGB", (512, 180), ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)).save(data, "PNG"))

            await self.bot.loop.create_task(async_create_image())

            files.append(("banner.png", data.getvalue()))
            banner_url = "attachment://banner.png"

        components = femcord.Components()
        container = femcord.Container()
        components.add_component(container)

        text = []

        if user.public_flags:
            text.append(" ".join(str(self.bot.gateway.get_emoji(name=flag.name)) for flag in user.public_flags if flag is not PublicFlags.BOT_HTTP_INTERACTIONS))
        if user.primary_guild and user.primary_guild.identity_guild_id is not None:
            primary_guild = f"`{user.primary_guild.tag}`"

            if user.primary_guild.badge:
                if user.primary_guild.badge not in [emoji.name for emoji in self.bot.gateway.emojis]:
                    async with self.bot.http.session.get(user.primary_guild.badge_url) as response:
                        await self.bot.gateway.create_application_emoji(user.primary_guild.badge, await response.read())

                emoji = self.bot.gateway.get_emoji(name=user.primary_guild.badge)
                primary_guild = f"{emoji} " + primary_guild

            text.append(primary_guild)

        container.add_component(femcord.MediaGallery().add_item(femcord.MediaItem(media=femcord.UnfurledMediaItem(url=banner_url))))
        section = femcord.Section().set_accessory(femcord.Thumbnail(media=femcord.UnfurledMediaItem(url=user.avatar_url)))
        section.add_component(femcord.TextDisplay(content="# " + await _("Information about {}:", user.global_name or user.username)))
        if text:
            section.add_component(
                femcord.TextDisplay(
                    content = "### " + " **|** ".join(text)
                )
            )
        container.add_component(section)

        container.add_component(femcord.Separator())
        container.add_component(femcord.TextDisplay(content=f"**ID:** {user.id}"))
        container.add_component(femcord.TextDisplay(content=f"**{_("Username:")}** {user.username}"))
        container.add_component(femcord.TextDisplay(content=f"**{_("Date created:")}** {femcord.types.t @ user.created_at} ({femcord.types.t['R'] @ user.created_at})"))

        if member is not None:
            container.add_component(femcord.Separator())
            if member.nick is not None:
                container.add_component(femcord.TextDisplay(content=f"**{_("Nickname:")}** {member.nick}"))
            if member.roles[1:]:
                container.add_component(femcord.TextDisplay(content=f"**{_("Roles:")}** " + " ".join(types.m @ role for role in sorted(member.roles[1:], key=lambda role: role.position, reverse=True))))
            container.add_component(femcord.TextDisplay(content=f"**{_("Date joined:")}** {femcord.types.t @ member.joined_at} ({femcord.types.t['R'] @ member.joined_at})"))

        if user.bot is True:
            container.add_component(femcord.Separator())

            link = f"https://discord.com/oauth2/authorize?client_id={user.id}&permissions=0&scope=bot"

            try:
                data = await self.bot.http.request(Route("GET", "applications", user.id, "rpc"))
            except femcord.errors.HTTPException:
                data = {"flags": 0, "description": None}

            intents = []

            if data["flags"] & 1 << 12:
                intents.append(Intents.GUILD_PRESENCES)
            if data["flags"] & 1 << 14:
                intents.append(Intents.GUILD_MEMBERS)
            if data["flags"] & 1 << 18:
                intents.append(Intents.GUILD_MESSAGES)
            if data["flags"] & 1 << 23:
                section.add_component(
                    femcord.TextDisplay(
                        content = "### " + str(self.bot.gateway.get_emoji(name="APPLICATION_COMMAND_BADGE"))
                    )
                )

            if data["description"]:
                container.add_component(femcord.TextDisplay(content=data["description"]))
                container.add_component(femcord.Separator())
            if "guild_id" in data:
                try:
                    guild_data = await self.bot.http.request(Route("GET", "guilds", data["guild_id"], "widget.json"))

                    if "code" not in guild_data:
                        container.add_component(femcord.TextDisplay(content=f"**{_("Guild:")}** {guild_data['name']} ({guild_data['id']})"))
                except femcord.errors.HTTPException:
                    pass
            if "terms_of_service_url" in data:
                container.add_component(femcord.TextDisplay(content=f"**ToS:** {data["terms_of_service_url"]}"))
            if "privacy_policy_url" in data:
                container.add_component(femcord.TextDisplay(content=f"**{_("Privacy policy:")}** {data["privacy_policy_url"]}"))
            if "tags" in data:
                container.add_component(femcord.TextDisplay(content=f"**{_("Tags:")}** " + ", ".join(data["tags"])))
            if intents:
                container.add_component(femcord.TextDisplay(content=f"**{_("Intents:")}** " + ", ".join([intent.name for intent in intents])))
            if "install_params" in data:
                if data["install_params"]["permissions"] != "0":
                    container.add_component(femcord.TextDisplay(content=f"**{_("Permissions:")}** " + ", ".join([permission.name for permission in Permissions.from_int(int(data["install_params"]["permissions"])).permissions])))
                link = f"https://discord.com/oauth2/authorize?client_id={user.id}&permissions={data['install_params']['permissions']}&scope={'%20'.join(data['install_params']['scopes'])}"

            container.add_component(
                femcord.ActionRow(
                    components = [
                        femcord.Button(
                            label = _("Add bot"),
                            style = femcord.ButtonStyles.LINK,
                            url = link
                        )
                    ]
                )
            )

        if member is not None:
            custom_status = ""
            client_status = member.presence.client_status
            if client_status.desktop:
                desktop_status = client_status.desktop.name
                custom_status += str(self.bot.gateway.get_emoji(name=desktop_status))
            if client_status.web:
                web_status = client_status.web.name
                custom_status += str(self.bot.gateway.get_emoji(name=web_status))
            if client_status.mobile:
                mobile_status = client_status.mobile.name
                custom_status += str(self.bot.gateway.get_emoji(name="MOBILE" + mobile_status))
            for activity in member.presence.activities:
                if activity.type is femcord.ActivityTypes.CUSTOM:
                    if activity.emoji and not activity.emoji.id:
                        custom_status += activity.emoji.name + " "
                    if activity.state:
                        custom_status += activity.state
                else:
                    container.add_component(femcord.Separator())
                    asset = (activity.assets.large_image or activity.assets.small_image) if activity.assets else None
                    if activity.name == "Spotify":
                        asset = "https://i.scdn.co/image/" + asset.split(":")[1]
                    if asset:
                        activity_section = femcord.Section()
                        activity_section.set_accessory(
                            femcord.Thumbnail(
                                media = femcord.UnfurledMediaItem(
                                    url = (femcord.types.user.CDN_URL + f"/app-assets/{activity.application_id}/{asset}.png") if activity.name != "Spotify" else asset
                                )
                            )
                        )
                    else:
                        activity_section = container # type: ignore
                    activity_section.add_component(
                        femcord.TextDisplay(
                            content = f"# {activity.type.name[0].upper()}{activity.type.name[1:].lower()} {"to " if activity.type is femcord.ActivityTypes.LISTENING else ""}{activity.name}"
                        )
                    )
                    if activity.details:
                        activity_section.add_component(
                            femcord.TextDisplay(
                                content = f"### {activity.details}"
                            )
                        )
                    if activity.name == "Spotify":
                        activity_section.add_component(
                            femcord.TextDisplay(
                                content = f"### {activity.state}"
                            )
                        )
                    if asset:
                        container.add_component(activity_section)

            if custom_status:
                section.add_component(femcord.TextDisplay(content=custom_status))

        await ctx.reply(components=components, files=files, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

    @commands.command(description="Shows information about the guild", usage="[guild_id]", aliases=["si"])
    async def serverinfo(self, ctx: "Context", guild = None):
        guild = self.bot.gateway.get_guild(guild) or ctx.guild

        embed = femcord.Embed(title=await ctx.get_translation("information_about", (guild.name,)), color=self.bot.embed_color)
        embed.set_thumbnail(url=guild.icon_url)

        statuses = {
            femcord.StatusTypes.ONLINE: 0,
            femcord.StatusTypes.DND: 0,
            femcord.StatusTypes.IDLE: 0,
            femcord.StatusTypes.OFFLINE: 0
        }

        for member in guild.members:
            statuses[member.presence.status] += 1

        embed.add_field(name=await ctx.get_translation("si_owner"), value=types.m @ guild.owner)
        embed.add_field(name="ID:", value=guild.id)
        embed.add_field(name=await ctx.get_translation("si_users"), value=" ".join(f"{value}{self.bot.gateway.get_emoji(name=key.name)}" for key, value in statuses.items()), inline=True)
        embed.add_field(name=await ctx.get_translation("si_channels"), value=len(guild.channels), inline=True)
        embed.add_field(name=await ctx.get_translation("roles"), value=len(guild.roles), inline=True)
        embed.add_field(name=await ctx.get_translation("si_emojis"), value=len(guild.emojis), inline=True)
        embed.add_field(name=await ctx.get_translation("si_stickers"), value=len(guild.stickers), inline=True)
        embed.add_blank_field()
        embed.add_field(name=await ctx.get_translation("date_created"), value=f"{femcord.types.t @ guild.created_at} ({femcord.types.t['R'] @ guild.created_at})")
        embed.add_field(name=await ctx.get_translation("si_boosts"), value=guild.premium_subscription_count, inline=True)
        embed.add_field(name=await ctx.get_translation("si_level"), value=guild.premium_tier, inline=True)
        embed.add_blank_field()
        if guild.vanity_url is not None:
            embed.add_field(name=await ctx.get_translation("si_custom_url"), value="discord.gg/" + guild.vanity_url, inline=guild.banner is None)
        embed.add_field(name=await ctx.get_translation("si_icon"), value=f"[link]({guild.icon_url})", inline=True)
        if guild.banner is not None:
            embed.add_field(name=await ctx.get_translation("si_banner"), value=f"[link]({guild.banner_url})", inline=True)
            embed.set_image(url=guild.banner_url)
            embed.add_blank_field()

        await ctx.reply(embed=embed)

    @commands.command(description="Shows information about invite", usage="(invite)", aliases=["ii"])
    async def inviteinfo(self, ctx: "Context", invite):
        invite = invite.split("/")[-1]

        try:
            data = await self.bot.http.request(Route("GET", "invites", invite + "?with_counts=true"))
            guild = data["guild"]
        except HTTPException:
            return await ctx.reply("This invite does not exists")

        embed = femcord.Embed(title=await ctx.get_translation("information_about", (invite,)), color=self.bot.embed_color)

        embed.add_field(name="ID:", value=guild["id"])
        embed.add_field(name=await ctx.get_translation("ii_name"), value=guild["name"])
        if guild["description"] is not None:
            embed.add_field(name=await ctx.get_translation("ii_description"), value=guild["description"])
        embed.add_field(name=await ctx.get_translation("si_boosts"), value=guild["premium_subscription_count"])
        if guild["nsfw_level"] > 0:
            embed.add_field(name=await ctx.get_translation("ii_nsfw_level"), value=guild["nsfw_level"])
        embed.add_field(name=await ctx.get_translation("ii_member_count"), value=data["approximate_member_count"])
        if guild["icon"] is not None:
            embed.set_thumbnail(url=f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png")
            embed.add_field(name=await ctx.get_translation("si_icon"), value=f"[link](https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png)", inline=True)
        if guild["banner"] is not None:
            embed.set_image(url=f"https://cdn.discordapp.com/banners/{guild['id']}/{guild['banner']}.png")
            embed.add_field(name=await ctx.get_translation("si_banner"), value=f"[link](https://cdn.discordapp.com/banners/{guild['id']}/{guild['banner']}.png)", inline=True)
        if guild["splash"] is not None:
            embed.add_field(name=await ctx.get_translation("ii_splash"), value=f"[link](https://cdn.discordapp.com/splashes/{guild['id']}/{guild['splash']}.png)", inline=True)

        await ctx.reply(embed=embed)

    @commands.command(description="Information about TruckersMP account", usage="(name)", aliases=["tmp", "ets2", "ets"], other={"embed": femcord.Embed(description="\nName: `steamid64`, `steam name`")})
    async def truckersmp(self, ctx: "Context", *, _id):
        if not re.match(r"^\d+$", _id):
            response = await self.bot.http.session.get("https://steamcommunity.com/id/" + _id, headers={"User-Agent": self.bot.user_agent})

            try:
                soup = BeautifulSoup(await response.content.read(), "lxml")
                _id = json.loads(soup.find_all("script", {"type": "text/javascript"}, text=re.compile("g_rgProfileData"))[0].string.splitlines()[1][20:-1])["steamid"]
            except json.decoder.JSONDecodeError:
                return await ctx.reply("No such steam account was found")

        response = await self.bot.http.session.get("https://api.truckersmp.com/v2/player/" + _id)
        response = await response.json()

        if response["error"]:
            return await ctx.reply("No such TruckersMP account was found")

        response = response["response"]

        embed = femcord.Embed(title=f"Informacje o {response['name']}:", color=self.bot.embed_color)
        embed.set_thumbnail(url=response["avatar"])
        embed.add_field(name="ID:", value=response["id"])
        embed.add_field(name="Steam64 ID:", value=response["steamID64"])
        embed.add_field(name="Nick:", value=response["name"])
        embed.add_field(name="Created date:", value=femcord.types.t @ datetime.strptime(response["joinDate"], "%Y-%m-%d %H:%M:%S"))
        if response["banned"]:
            embed.add_field(name="Banned:", value="Yes")
        if response["patreon"]["isPatron"]:
            embed.add_field(name="Patreon support:", value="Yes")
        if response["vtc"]["inVTC"]:
            embed.add_field(name="Company name:", value=response["vtc"]["name"])
            embed.add_field(name="Company tags:", value=response["vtc"]["tag"])

        await ctx.reply(embed=embed)

    async def fetch(self, word, url, tag, attributes, expression):
        response = await self.bot.http.session.get(url, headers={"user-agent": self.bot.user_agent})

        soup = BeautifulSoup(await response.content.read(), "lxml")
        text = soup.find_all(tag, attributes)

        if text is None:
            return "No such word was found"

        text = text[0].get_text()

        return f"**{word}**\n{re.findall(expression, text)[-1]}\n*z <{url.replace(' ', '%20')}>*"

    @commands.group(description="Dictionary", aliases=["definition", "word", "dict", "def"])
    async def dictionary(self, ctx: "Context"):
        cog = self.bot.get_cog("Help")
        embed = cog.get_help_embed(ctx.command)

        await ctx.reply(embed=embed)

    @dictionary.command(usage="(word)", aliases=["pl"])
    async def polish(self, ctx: "Context", *, word):
        await ctx.reply(await self.fetch(word, "https://sjp.pwn.pl/szukaj/" + word + ".html", "div", {"class": "znacz"}, r"[\w,. ]+"))

    @dictionary.command(usage="(word)", aliases=["en"])
    async def english(self, ctx: "Context", *, word):
        await ctx.reply(await self.fetch(word, "https://dictionary.cambridge.org/pl/dictionary/english/" + word, "div", {"class": "def"}, r"[\w,. ]+"))

    @dictionary.command(usage="(word)", aliases=["es"])
    async def spanish(self, ctx: "Context", *, word):
        await ctx.reply(await self.fetch(word, "https://dictionary.cambridge.org/pl/dictionary/spanish-english/" + word, "div", {"class": "def"}, r"[\w,. ]+"))

    @dictionary.command(usage="(word)")
    @commands.is_nsfw
    async def urban(self, ctx: "Context", *, word):
        await ctx.reply(await self.fetch(word, "https://www.urbandictionary.com/define.php?term=" + word, "div", {"class": "meaning"}, r".+"))

    @commands.command(description="Information about meme from KnowYourMeme", usage="(name)", aliases=["kym", "meme"])
    @commands.is_nsfw
    async def knowyourmeme(self, ctx: "Context", *, name):
        async with ClientSession() as session:
            async with session.get(f"http://rkgk.api.searchify.com/v1/indexes/kym_production/instantlinks?query={name}&field=name&fetch=name%2Curl&function=10&len=1") as response:
                data = await response.json()

                if not data["results"]:
                    return await ctx.reply("No such meme was found")

                async with session.get("https://knowyourmeme.com" + data["results"][0]["url"]) as response:
                    content = await response.content.read()

                    soup = BeautifulSoup(content, "lxml")
                    text: ResultSet = soup.find_all("section", {"class": "bodycopy"})[0]
                    about = text.find("h2", {"id": "about"}).find_next("p").get_text()

                    await ctx.reply(f"**Information about {urllib.parse.unquote(data['results'][0]['name'])}**\n\n{about}\n\n*z <https://knowyourmeme.com{data['results'][0]['url']}>*")

    @commands.command(description="Information about gihub account", usage="(user_name)", aliases=["gh"])
    async def github(self, ctx: "Context", *, name):
        async with ClientSession() as session:
            async with session.get(f"https://api.github.com/users/{name}") as response:
                if not response.status == 200:
                    return await ctx.reply("No such github account was found")

                data = await response.json()

                embed = femcord.Embed(title=f"Information about {data['login']}:", color=self.bot.embed_color)
                embed.add_field(name="ID:", value=data["id"], inline=True)
                embed.add_field(name="Name:", value=data["name"], inline=True)
                embed.add_blank_field()
                if data["avatar_url"]:
                    embed.set_thumbnail(url=data["avatar_url"])
                embed.add_field(name="Followers count:", value=data["followers"], inline=True)
                embed.add_field(name="Following count:", value=data["following"], inline=True)
                embed.add_blank_field()
                embed.add_field(name="Public repositories count:", value=data["public_repos"], inline=True)
                embed.add_field(name="Public gists count:", value=data["public_gists"], inline=True)
                embed.add_blank_field()
                embed.add_field(name="Created date:", value=femcord.types.t @ datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ"), inline=True)
                embed.add_field(name="Last update:", value=femcord.types.t @ datetime.strptime(data["updated_at"], "%Y-%m-%dT%H:%M:%SZ"), inline=True)
                embed.add_blank_field()
                if data["bio"]:
                    embed.add_field(name="Bio:", value=data["bio"])

                await ctx.reply(embed=embed)

    @commands.command(description="guess who it is")
    async def who(self, ctx: "Context"):
        members = []

        members_with_pfp = [member for member in ctx.guild.members if member.user.avatar]

        if len(members_with_pfp) < 10:
            return await ctx.reply("There is not enough users with avatar on this server")

        while not len(members) == 10:
            member = random.choice(members_with_pfp)

            if not member in members:
                members.append(member)

        correct = random.choice(members)

        color = self.bot.embed_color

        if correct.hoisted_role is not None:
            color = correct.hoisted_role.color

        embed = femcord.Embed(title="Guess who it is:", color=color)
        embed.set_image(url=correct.user.avatar_url)

        def get_components():
            return femcord.Components(
                components = [
                    femcord.ActionRow(
                        components = [
                            femcord.StringSelect(
                                custom_id = "members",
                                placeholder = "Choose a member",
                                options = [
                                    femcord.StringSelectOption(
                                        label = member.user.username,
                                        value = member.user.id
                                    )
                                    for member in members
                                ]
                            )
                        ]
                    )
                ]
            )

        message = await ctx.reply(embed=embed, components=get_components())

        while True:
            try:
                interaction, = await self.bot.wait_for("interaction_create", lambda interaction: interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60 * 5)
            except TimeoutError:
                return await message.edit("No one guessed", embeds=[], components=[])

            selected_member = members[get_index(members, interaction.data.values[0], key=lambda member: member.user.id)]

            if selected_member == correct:
                return await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, f"{types.m @ interaction.member} guessed!", embeds=[], components={})
            elif len(members) == 4:
                return await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, "No one guessed", embeds=[], components={})
            else:
                members.remove(selected_member)
                await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, embed=embed, components=get_components())

    @commands.command(description="Random nickname")
    async def nick(self, ctx: "Context"):
        await ctx.reply(get_random_username())

    @commands.hybrid_command()
    async def sticker(self, ctx: Union["Context", "AppContext"], *, text: Max[str, 20]):
        is_app = isinstance(ctx, commands.AppContext)
        kwargs = {"flags": [femcord.enums.MessageFlags.EPHEMERAL]} if is_app else {}

        if len(text) > 20:
            return await ctx.reply(await _("Provided text is too long (`{}`/`{}`)", len(text), 20))

        characters = Sticker.get_characters()

        def get_components(character_name: str) -> femcord.Components:
            character, = [character for character in characters if character["name"] == character_name]

            return femcord.Components(
                components = [*[
                    femcord.ActionRow(
                        components = [
                            femcord.StringSelect(
                                custom_id = f"characters:{i}-{i+25}",
                                placeholder = "more characters",
                                options = [
                                    femcord.StringSelectOption(
                                        label = character["name"],
                                        value = character["name"],
                                        default = character["name"] == character_name
                                    )
                                    for character in characters[i:i+25]
                                ]
                            )
                        ]
                    )
                    for i in range(0, len(characters), 25)
                ] + [
                    femcord.ActionRow(
                        components = [
                            femcord.StringSelect(
                                custom_id = f"image:{i}-{i+25}",
                                placeholder = "select image" if i == 0 else "more images",
                                options = [
                                    femcord.StringSelectOption(
                                        label = str(i + index),
                                        value = image
                                    )
                                    for index, image in enumerate(character["images"][i:i+25])
                                ]
                            )
                        ]
                    )
                    for i in range(0, len(character["images"]), 25)
                ]]
            )

        message = await ctx.reply(files=[("image.png", characters[0]["pregen_showcase"])], components=get_components(characters[0]["name"]), **kwargs)

        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
            if is_app:
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id
            return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id

        while True:
            interaction: femcord.types.Interaction

            try:
                interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
            except TimeoutError:
                return await obj.edit(components=[])

            if interaction.data.custom_id.split(":")[0] == "characters":
                character, = [character for character in characters if character["name"] == interaction.data.values[0]]
                await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, files=[("image.png", character["pregen_showcase"])], components=get_components(character["name"]))
            elif interaction.data.custom_id.split(":")[0] == "image":
                image = interaction.data.values[0]
                await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
                break

        sticker = Sticker(image)

        sticker.set_text(text)

        components = femcord.Components(
            components = [
                femcord.ActionRow(
                    components = [
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="move_left", emoji=types.Emoji(self.bot, "\N{BLACK LEFT-POINTING TRIANGLE}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="move_up", emoji=types.Emoji(self.bot, "\N{UP-POINTING SMALL RED TRIANGLE}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="move_down", emoji=types.Emoji(self.bot, "\N{DOWN-POINTING SMALL RED TRIANGLE}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="move_right", emoji=types.Emoji(self.bot, "\N{BLACK RIGHT-POINTING TRIANGLE}"))
                    ]
                ),
                femcord.ActionRow(
                    components = [
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="rotate_left", emoji=types.Emoji(self.bot, "\N{RIGHTWARDS ARROW WITH HOOK}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="rotate_right", emoji=types.Emoji(self.bot, "\N{LEFTWARDS ARROW WITH HOOK}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="decrease_size", emoji=types.Emoji(self.bot, "\N{HEAVY MINUS SIGN}")),
                        femcord.Button(style=femcord.ButtonStyles.PRIMARY, custom_id="increase_size", emoji=types.Emoji(self.bot, "\N{HEAVY PLUS SIGN}"))
                    ]
                )
            ]
        )

        action_row = femcord.ActionRow()

        if is_app:
            action_row.add_component(femcord.Button(label="show", style=femcord.ButtonStyles.SUCCESS, custom_id="show"))
        if ctx.guild and ctx.member.permissions.has(femcord.enums.Permissions.MANAGE_GUILD_EXPRESSIONS):
            action_row.add_component(femcord.Button(label="add sticker", style=femcord.ButtonStyles.SUCCESS, custom_id="add_sticker"))

        if action_row["components"]:
            components.add_component(action_row)

        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        message = await obj.edit(components=components, files=[("sticker.gif", await sticker.generate())])

        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        while True:
            interaction: femcord.types.Interaction

            try:
                interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
            except TimeoutError:
                return await obj.edit(components=[])

            match interaction.data.custom_id:
                case "move_left":
                    sticker.move_text(-10, 0)
                case "move_right":
                    sticker.move_text(10, 0)
                case "move_down":
                    sticker.move_text(0, 10)
                case "move_up":
                    sticker.move_text(0, -10)
                case "rotate_left":
                    sticker.rotate_text(sticker._angle + 10)
                case "rotate_right":
                    sticker.rotate_text(sticker._angle - 10)
                case "decrease_size":
                    sticker.set_text_size(sticker._text_size - 10)
                case "increase_size":
                    sticker.set_text_size(sticker._text_size + 10)
                case "show":
                    await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
                    return await ctx.reply(files=[("sticker.gif", await sticker.generate())])
                case "add_sticker":
                    data = FormData()

                    if len(text) < 3:
                        text += ";" * (3 - len(text))

                    data.add_field("name", text)
                    data.add_field("tags", text)
                    data.add_field("file", await sticker.get_thumbnail(), content_type="image/png", filename=text)

                    await self.bot.http.request(Route("POST", "guilds", ctx.guild.id, "stickers"), data=data)

                    return await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, "Sticker added", components=[], files=[], other={"attachments": []})

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, components=components, files=[("sticker.gif", await sticker.generate())])

    @commands.hybrid_command()
    async def nitro(self, ctx: Union["Context", "AppContext"]):
        code = "".join([random.choice(string.ascii_letters) for _ in range(16)])

        components = femcord.Components(
            components = [
                femcord.TextDisplay(content=f"<https://discord.gift/{code}>"),
                femcord.Container(
                    components = [
                        femcord.Section(
                            components = [
                                femcord.TextDisplay(content="# You've been gifted a subscription!"),
                                femcord.TextDisplay(content=f"You've been gifted Nitro for **1 {"month" if random.random() < 0.9 else "year"}**!")
                            ],
                            accessory = femcord.Thumbnail(
                                media = femcord.UnfurledMediaItem(
                                    url = "https://cdn.poligon.lgbt/XKWFuQpaPi.png"
                                )
                            )
                        ),
                        femcord.ActionRow(
                            components = [
                                femcord.Button(
                                    style = femcord.ButtonStyles.PRIMARY,
                                    label = "Accept",
                                    custom_id = "accept"
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        await ctx.reply(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

    @commands.command()
    async def cowsay(self, ctx: "Context", *, text: Max[str, 1000]):
        if len(text) > 1000:
            return await ctx.reply(await _("Provided text is too long (`{}`/`{}`)", len(text), 1000))

        cow = f""" {"_" * (len(text) + 2)}
< {text} >
 {"-" * (len(text) + 2)}
        \\   ^__^
         \\  (oo)\\_______
            (__)\\       )\\/\\
                ||----w |
                ||     ||"""

        await ctx.reply("```" + cow + "```")

def setup(bot: "Bot") -> None:
    bot.load_cog(Fun(bot))