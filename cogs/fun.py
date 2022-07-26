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

import lib
from lib import commands, types, InvalidArgument, HTTPException
from lib.http import Route
from lib.utils import get_index
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pyfiglet import Figlet
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from typing import Union
from datetime import datetime
from utils import *
import io, random, urllib.parse, json, re

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.garfield_emojis = {"0": "930949123979477043", "1": "930949123706880011", "2": "930949123757203456", "3": "930949123752984586",
                                "4": "930949123752984587", "5": "930949124017238026", "6": "930949124109500436", "7": "930949125413941268",
                                "8": "930949123732021258", "9": "930949123849461760", "a": "930949124151443546", "b": "930949123870429286",
                                "c": "930949123836895312", "d": "930949123757203457", "e": "930949123866263572", "f": "930949124172419152",
                                "g": "930949124017238027", "h": "930949124050808892", "i": "930949124046590032", "j": "930949123719430196",
                                "k": "930949124147277894", "l": "930949124008849408", "m": "930949124835131402", "n": "930949124235362344",
                                "o": "930949124008865882", "p": "930949123706880014", "q": "930949125426528357", "r": "930949124336021564",
                                "s": "930949124226961408", "t": "930949123966898207", "u": "930949124466032740", "v": "930949124046590033",
                                "w": "930949123866263573", "x": "930949124105334795", "y": "930949124172419153", "z": "930949124046594049",
                                " ": "930949124138889236"}
        self.public_flags_emojis = {"DISCORD_EMPLOYEE": "933476948343144508", "PARTNERED_SERVER_OWNER": "933476948246675506",
                                    "HYPESQUAD_EVENTS": "933476948234096661", "BUG_HUNTER_LEVEL_1": "933476948225687623",
                                    "BRAVERY": "933476948234096660", "BRILLIANCE": "933476948389294170", "BALANCE": "933476948292796427",
                                    "EARLY_SUPPORTER": "933476948338966578", "BUG_HUNTER_LEVEL_2": "933476948276019220",
                                    "VERIFIED_BOT_DEVELOPER": "933476948594790460", "CERTIFIED_MODERATOR": "933476947915333633"}
        self.status_emojis = {"ONLINE": "977693019279077399", "IDLE": "977693019321028649", "DND": "977693019430076456",
                              "INVISIBLE": "977693019518160916", "OFFLINE": "977693019518160916"}
        self.interactions = []
        self.results = {}
        self.urls = {}

    @commands.command(description="arwatar", usage="[użytkownik]")
    async def avatar(self, ctx, user: types.User = None):
        user = user or ctx.author
        image = await self.bot.http.session.get(user.avatar_url)

        await ctx.reply(files=[("avatar." + ("gif" if user.avatar[:2] == "a_" else "png"), await image.content.read())])

    @commands.command(description="Pokazuje w ilu procentach użytkownicy się kochają", usage="(użytkownik) [użytkownik]", aliases=["love"])
    async def ship(self, ctx, user: types.User, user2: types.User = None):
        user2 = user2 or ctx.author

        user_avatar_resp = await self.bot.http.session.get(user.avatar_as("png"))
        user2_avatar_resp = await self.bot.http.session.get(user2.avatar_as("png"))

        user_avatar = io.BytesIO(await user_avatar_resp.content.read())
        user2_avatar = io.BytesIO(await user2_avatar_resp.content.read())

        ship_image = Image.open("./assets/images/ship.jpg").convert("RGBA")

        user_image = Image.open(user_avatar).convert("RGBA")
        user2_image = Image.open(user2_avatar).convert("RGBA")

        user_image = ImageOps.fit(user_image, (300, 300))
        user2_image = ImageOps.fit(user2_image, (300, 300))

        ship_image.paste(user_image, (360, 250), user_image)
        ship_image.paste(user2_image, (890, 180), user2_image)

        image = io.BytesIO()
        ship_image.save(image, "PNG")

        percent = get_int(user, user2)

        await ctx.reply(f"**{user.username}** + **{user2.username}** = **{user.username[:len(user.username) // 2].lower()}{user2.username[len(user2.username) // 2:].lower()}**\nIch miłość jest równa **{percent}%**!", files=[("ship.png", image.getvalue())])

    @commands.command(description="pies", aliases=["pies", "sterzi", "ars", "mesik", "6vz", "piesvz", "<@338075554937044994>", "<@!338075554937044994>"])
    async def dog(self, ctx):
        alias = ctx.message.content.split()[0][len(await self.bot.get_prefix(self.bot, ctx.message)):]

        if alias in ("sterzi", "mesik"):
            return await ctx.reply("to pies")
        elif alias in ("6vz", "piesvz", "<@338075554937044994>", "<@!338075554937044994>"):
            return await ctx.reply("to pies, ten niżej to też pies", files=[("dog.png", open("./assets/images/6vz.png", "rb")), ("dog2.png", open("./assets/images/6vz2.png", "rb"))])
        elif alias == "ars":
            return await ctx.reply("to pies, ten niżej to też pies", files=[("dog.jpg", open("./assets/images/ars.jpg", "rb"))])

        resp = await self.bot.http.session.get("https://some-random-api.ml/img/dog")
        resp_data = await resp.json()
        image = await self.bot.http.session.get(resp_data["link"])
        content = await image.content.read()

        try:
            mimetype = lib.utils.get_mime(content)
        except InvalidArgument:
            return await self.dog(ctx)

        extension = mimetype.split("/")[1]

        await ctx.reply(files=[("dog." + extension, content)])

    @commands.command(description="kot", aliases=["kot"])
    async def cat(self, ctx):
        image = await self.bot.http.session.get("https://cataas.com/cat" + ("/gif" if random.random() > .5 else ""))
        content = await image.content.read()

        try:
            mimetype = lib.utils.get_mime(content)
        except InvalidArgument:
            return await self.cat(ctx)

        extension = mimetype.split("/")[1]

        await ctx.reply(files=[("cat." + extension, content)])

    @commands.command(description=".i.", usage="(tekst)", aliases=["ascii"])
    async def figlet(self, ctx, *, text):
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

    @commands.command(description="dżej", usage="[użytkownik]")
    async def howgay(self, ctx, user: types.User = None):
        user = user or ctx.author

        await ctx.reply(f"{user.username} jest gejem w {get_int(user)}%")

    @commands.command(description="Achievement Get!", usage="(tekst)")
    async def achievement(self, ctx, *, text: replace_chars):
        if len(text) > 23:
            return await ctx.reply(f"Tekst jest za długi (`{len(text)}/23`)")

        image = await self.bot.http.session.get(f"https://minecraftskinstealer.com/achievement/{random.randint(1, 40)}/Achievement+Get%21/{text}")

        await ctx.reply(files=[("achievement.png", await image.content.read())])

    @commands.command(description="Wysyła tekst w emotkach garfielda", usage="(tekst)")
    async def garfield(self, ctx, *, text: replace_chars):
        if len(text) > 60:
            return await ctx.reply(f"Tekst jest za długi (`{len(text)}`/`60`)")

        garfield_text = ""

        for char in text:
            char = char.lower()
            if char in self.garfield_emojis:
                garfield_text += f"<:garfield_{'space' if char == ' ' else char}:{self.garfield_emojis[char]}>"
                continue

            garfield_text += char

        await ctx.reply(garfield_text)

    @commands.command(description="Ukrywa niewidzialny tekst w tekście", usage="(pokazany_tekst) | (ukryty_tekst)", other={"embed": lib.Embed().set_image(url="https://cdn.poligon.lgbt/riEyNGVIuO.png")})
    async def encode(self, ctx, *, text: replace_chars):
        text = text.split(" | ")
        text[1] = text[1].replace(" ", "_")

        if 2 > len(text):
            return await ctx.reply("Nie podałeś ukrytego tekstu")

        if len(text[0]) < 2:
            return await ctx.reply(f"Tekst jest za krótki (`{len(text[0])}/2`)")

        await ctx.reply(text[0][0] + encode_text(text[1]) + text[0][1:])

    @commands.command(description="Pokazuje niewidzialny tekst", usage="(tekst)", other={"embed": lib.Embed().set_image(url="https://cdn.poligon.lgbt/fsdKWwqWKx.png")})
    async def decode(self, ctx, *, text):
        allowed_chars = [group[0] for group in CHARS] + [SEPARATOR]
        new_text = ""

        for char in text:
            if char in allowed_chars:
                new_text += char

        await ctx.reply(decode_text(new_text))

    # @commands.Listener
    # async def on_interaction_create(self, interaction):
    #     if ("calc", interaction.member.user.id, interaction.channel.id, interaction.message.id) in self.interactions:
    #         if not interaction.message.id in self.results:
    #             self.results[interaction.message.id] = ["", 0]

    #         if self.results[interaction.message.id][0] == "KABOOM!":
    #             self.results[interaction.message.id][0] = ""

    #         match interaction.data.custom_id:
    #             case "leftbracket":
    #                 self.results[interaction.message.id][0] += "("
    #                 self.results[interaction.message.id][1] = 0
    #             case "rightbracket":
    #                 self.results[interaction.message.id][0] += ")"
    #                 self.results[interaction.message.id][1] = 0
    #             case "power":
    #                 self.results[interaction.message.id][0] += "**"
    #                 self.results[interaction.message.id][1] = 0
    #             case "modulo":
    #                 self.results[interaction.message.id][0] += "%"
    #                 self.results[interaction.message.id][1] = 0
    #             case "backspace":
    #                 self.results[interaction.message.id][0] = self.results[interaction.message.id][0][:-1]
    #                 self.results[interaction.message.id][1] = 0
    #             case "clear":
    #                 self.results[interaction.message.id][0] = ""
    #                 self.results[interaction.message.id][1] = 0
    #             case "divide":
    #                 self.results[interaction.message.id][0] += "/"
    #                 self.results[interaction.message.id][1] = 0
    #             case "multiply":
    #                 self.results[interaction.message.id][0] += "*"
    #                 self.results[interaction.message.id][1] = 0
    #             case "minus":
    #                 self.results[interaction.message.id][0] += "-"
    #                 self.results[interaction.message.id][1] = 0
    #             case "dot":
    #                 self.results[interaction.message.id][0] += "."
    #                 self.results[interaction.message.id][1] = 0
    #             case "equal":
    #                 if len(self.results[interaction.message.id][0]) <= 50:
    #                     try:
    #                         self.results[interaction.message.id][0] += "=" + str(round(eval(self.results[interaction.message.id][0]), 2))
    #                     except:
    #                         self.results[interaction.message.id][0] = "KABOOM!" if self.results[interaction.message.id][0] == "/0" else ""
    #                     self.results[interaction.message.id][1] = 0
    #             case "add":
    #                 self.results[interaction.message.id][0] += "+"
    #                 self.results[interaction.message.id][1] = 0
    #             case "0":
    #                 if not self.results[interaction.message.id][0] == "0" and not len(self.results[interaction.message.id][0]) == 1:
    #                     self.results[interaction.message.id][0] += "0"
    #                     self.results[interaction.message.id][1] = 0
    #             case _:
    #                 if self.results[interaction.message.id][1] <= 5:
    #                     self.results[interaction.message.id][0] += interaction.data.custom_id
    #                     self.results[interaction.message.id][1] += 1

    #         await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, "```" + (self.results[interaction.message.id][0] if self.results[interaction.message.id][0] else "0") + "```")

    #         if "=" in self.results[interaction.message.id][0]:
    #             self.results[interaction.message.id][0] = ""

    # @commands.command(description="liczydło", aliases=["kalkulator", "calculator"], enabled=False)
    # async def calc(self, ctx):
    #     components = lib.Components(
    #         lib.Row(
    #             lib.Button("x\u02b8", style=lib.ButtonStyles.SECONDARY, custom_id="power"),
    #             lib.Button("%", style=lib.ButtonStyles.SECONDARY, custom_id="modulo"),
    #             lib.Button("<-", style=lib.ButtonStyles.SECONDARY, custom_id="backspace"),
    #             lib.Button("C", style=lib.ButtonStyles.DANGER, custom_id="clear")
    #         ),
    #         lib.Row(
    #             lib.Button("7", style=lib.ButtonStyles.SECONDARY, custom_id="7"),
    #             lib.Button("8", style=lib.ButtonStyles.SECONDARY, custom_id="8"),
    #             lib.Button("9", style=lib.ButtonStyles.SECONDARY, custom_id="9"),
    #             lib.Button("/", style=lib.ButtonStyles.SECONDARY, custom_id="divide"),
    #             lib.Button("(", style=lib.ButtonStyles.SECONDARY, custom_id="leftbracket")
    #         ),
    #         lib.Row(
    #             lib.Button("4", style=lib.ButtonStyles.SECONDARY, custom_id="4"),
    #             lib.Button("5", style=lib.ButtonStyles.SECONDARY, custom_id="5"),
    #             lib.Button("6", style=lib.ButtonStyles.SECONDARY, custom_id="6"),
    #             lib.Button("*", style=lib.ButtonStyles.SECONDARY, custom_id="multiply"),
    #             lib.Button(")", style=lib.ButtonStyles.SECONDARY, custom_id="rightbracket")
    #         ),
    #         lib.Row(
    #             lib.Button("1", style=lib.ButtonStyles.SECONDARY, custom_id="1"),
    #             lib.Button("2", style=lib.ButtonStyles.SECONDARY, custom_id="2"),
    #             lib.Button("3", style=lib.ButtonStyles.SECONDARY, custom_id="3"),
    #             lib.Button("-", style=lib.ButtonStyles.SECONDARY, custom_id="minus")
    #         ),
    #         lib.Row(
    #             lib.Button("0", style=lib.ButtonStyles.SECONDARY, custom_id="0"),
    #             lib.Button(".", style=lib.ButtonStyles.SECONDARY, custom_id="dot"),
    #             lib.Button("=", style=lib.ButtonStyles.PRIMARY, custom_id="equal"),
    #             lib.Button("+", style=lib.ButtonStyles.SECONDARY, custom_id="add")
    #         )
    #     )

    #     message = await ctx.reply("```0```", components=components)
    #     self.interactions.append(("calc", ctx.author.id, ctx.channel.id, message.id))

    @commands.command(description="nie widać mnie", usage="[użytkownik/tekst/obrazek]")
    async def cantseeme(self, ctx, *, arg: Union[types.User, str] = None):
        arg = arg or ctx.author

        if ctx.message.attachments:
            image = await self.bot.http.session.get(ctx.message.attachments[0].url)
            arg = io.BytesIO(await image.content.read())

        if isinstance(arg, types.User):
            image = await self.bot.http.session.get(arg.avatar_url)
            arg = io.BytesIO(await image.content.read())

        bush = Image.open("./assets/images/bush.png")

        if isinstance(arg, str):
            if len(arg) > 105:
                 return await ctx.reply(f"Tekst jest za długi (`{len(arg)}/105`)")

            if len(arg) > 15:
                arg = "\n".join(arg[x:x+15] for x in range(0, len(arg), 15))

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

        image = io.BytesIO()
        bush.save(image, "PNG")

        await ctx.reply(files=[("cantseeme.png", image.getvalue())])

    @commands.command(description="lgbt", usage="[użytkownik]", aliases=["lgbt"])
    async def gay(self, ctx, user: types.User = None):
        user = user or ctx.author

        image = await self.bot.http.session.get(user.avatar_url)
        image = io.BytesIO(await image.content.read())

        lgbt = Image.open("./assets/images/lgbt.png")
        image = Image.open(image)

        lgbt = ImageOps.fit(lgbt, (512, 512))
        image = ImageOps.fit(image, (512, 512))

        mask = Image.new("L", (512, 512), 128)

        avatar = Image.composite(image, lgbt, mask)
        image = io.BytesIO()

        avatar.save(image, "PNG")

        await ctx.reply(files=[("gay.png", image.getvalue())])

    @commands.command(description="losowy mem z jbzd", aliases=["mem"])
    @commands.is_nsfw
    async def meme(self, ctx):
        memes = []

        while not memes:
            memes_page = await self.bot.http.session.get(f"https://jbzd.com.pl/str/{random.randint(1, 235)}")
            memes_soup = BeautifulSoup(await memes_page.content.read(), "lxml")

            memes = memes_soup.find_all("img", {"class": "article-image"})

        await ctx.reply(random.choice(memes)["src"])

    @commands.command(description="\U0001F633", usage="[użytkownik]")
    async def dick(self, ctx, user: types.User = None):
        await self.figlet(ctx, text=f".i. {get_int(user or ctx.author) // 5}")

    @commands.command(description="taobao aliexpress i chiny", usage="(produkt)", aliases=["aliexpress"])
    async def taobao(self, ctx, *, product):
        resp = await self.bot.http.session.get("https://pl.aliexpress.com/wholesale?SearchText=" + urllib.parse.quote_plus(product))
        soup = BeautifulSoup(await resp.content.read(), "lxml")

        raw_item_list = soup.find_all("script", {"type": "text/javascript"})[3].string.splitlines()[3].strip("window.runParams = ")[:-1]
        item_list = json.loads(raw_item_list)["mods"]["itemList"]["content"]

        random_product = random.choice(item_list)
        await ctx.reply(f"\"{random_product['title']['displayTitle']}\"\nhttps://aliexpress.com/item/{random_product['productId']}.html\n\n*z aliexpress.com*")

    @commands.command(description="shopee wyszukiwarka", usage="shopee (produkt)", aliases=["shopenis", "fakeali", "alisexpress"])
    async def shopee(self, ctx, *, product):
        resp = (await (await self.bot.http.session.get("https://shopee.pl/api/v4/search/search_items?by=relevancy&keyword=" + urllib.parse.quote_plus(product) + "&limit=60&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2")).json())["items"]

        if len(resp) == 0:
            return await ctx.reply("Nie ma takiego produktu :cry:")

        random_product = random.choice(resp)['item_basic']

        embed = lib.Embed(title=f"{str(format(random_product['price'] / 100000, '.2f'))}PLN | {random_product['name']}", url=f"https://shopee.pl/{random_product['name'].replace(' ', '-')}-i.{random_product['shopid']}.{random_product['itemid']}")
        embed.set_thumbnail(url=f"https://cf.shopee.pl/file/{random_product['image']}")
        embed.set_author(name="shopee.pl")
        embed.set_footer(text="Your preferred online shopping platform.")

        await ctx.reply(f"\"{random_product['name']}\"\nhttps://shopee.pl/{random_product['name'].replace(' ', '-')}-i.{random_product['shopid']}.{random_product['itemid']} *z shopee.pl*", embed=embed)

    @commands.command(description="losowa tapeta z tapetus.pl", aliases=["tapeta"])
    async def tapetus(self, ctx):
        resp = await self.bot.http.session.get(f"https://tapetus.pl/,st_{random.randint(0, 5527)}.php")
        soup = BeautifulSoup(await resp.content.read(), "lxml")

        images = soup.find_all("img", {"class": "img_srednie"})
        image = random.choice(images).parent

        await ctx.reply("https://tapetus.pl/obrazki/n/" + image["href"][:-3].replace(",", "_") + "jpg")

    @commands.command(description="Pokazuje informacje o użytkowniku", usage="[użytkownik]", aliases=["ui", "user", "cotozacwel", "kimtykurwajestes"])
    async def userinfo(self, ctx, user: Union[types.Member, types.User] = None):
        user = user or ctx.member

        if isinstance(user, types.Member):
            member = user
            user = member.user

        elif isinstance(user, types.User):
            member = None

        color = self.bot.embed_color

        if member is not None:
            if member.hoisted_role is not None:
                color = member.hoisted_role.color

        embed = lib.Embed(title=f"Informacje o {user.username}{' (bot)' if user.bot else ''}:", color=color)
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(name="ID:", value=user.id)
        embed.add_field(name="Nick z tagiem:", value=str(user))
        if member is not None:
            if member.nick is not None:
                embed.add_field(name="Nick na serwerze:", value=member.nick)
            if member.roles[1:]:
                embed.add_field(name="Role:", value=" ".join(types.m @ role for role in member.roles[1:]))
            if member.presence:
                for activity in member.presence.activities:
                    status = member.presence.status.name
                    text = f"<:{status}:{self.status_emojis[status]}> "
                    if activity.type is lib.ActivityTypes.CUSTOM:
                        if activity.emoji and not activity.emoji.id:
                            text += activity.emoji.name + " "
                        if activity.state:
                            text += activity.state
                        embed.add_field(name="Status:", value=text)
                        break
            embed.add_field(name="Dołączył na serwer:", value=f"<t:{int(member.joined_at.timestamp())}> (<t:{int(member.joined_at.timestamp())}:R>)")
        embed.add_field(name="Utworzył konto:" if not user.bot else "Stworzony dnia:", value=f"<t:{int(user.created_at.timestamp())}> (<t:{int(user.created_at.timestamp())}:R>)")
        if user.public_flags:
            embed.add_field(name="Odznaki:", value=" ".join(f"<:{flag.name}:{self.public_flags_emojis[flag.name]}>" for flag in user.public_flags if flag.name in self.public_flags_emojis))
        embed.add_field(name="Avatar:", value=f"[link]({user.avatar_url})")
        if user.bot is True:
            embed.add_field(name="Zaproszenie:", value=f"[link](https://discord.com/oauth2/authorize?client_id={user.id}&scope=bot)")

        await ctx.reply(types.m @ user, embed=embed)

    @commands.command(description="Pokazuje informacje o serwerze", aliases=["si"])
    async def serverinfo(self, ctx):
        embed = lib.Embed(title=f"Informacje o {ctx.guild.name}:", color=self.bot.embed_color)
        embed.set_thumbnail(url=ctx.guild.icon_url)

        embed.add_field(name="Właściciel:", value=types.m @ ctx.guild.owner)
        embed.add_field(name="ID:", value=ctx.guild.id)
        embed.add_field(name="Użytkownicy:", value=len(ctx.guild.members), inline=True)
        embed.add_field(name="Kanały:", value=len(ctx.guild.channels), inline=True)
        embed.add_field(name="Role:", value=len(ctx.guild.roles), inline=True)
        embed.add_field(name="Emotki:", value=len(ctx.guild.emojis), inline=True)
        embed.add_field(name="Naklejki:", value=len(ctx.guild.stickers), inline=True)
        embed.add_field(name="Został stworzony:", value=f"<t:{int(ctx.guild.created_at.timestamp())}> (<t:{int(ctx.guild.created_at.timestamp())}:R>)")
        embed.add_field(name="Ulepszenia:", value=ctx.guild.premium_subscription_count, inline=True)
        embed.add_field(name="Poziom:", value=ctx.guild.premium_tier, inline=True)
        if ctx.guild.vanity_url is not None:
            embed.add_field(name="Własny url:", value="discord.gg/" + ctx.guild.vanity_url)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="Ikona:", value=f"[link]({ctx.guild.icon_url})", inline=True)
        if ctx.guild.banner is not None:
            embed.add_field(name="Baner:", value=f"[link]({ctx.guild.banner_url})", inline=True)
            embed.set_image(url=ctx.guild.banner_url)

        await ctx.reply(embed=embed)

    @commands.command(description="Pokazuje informacje o zaproszeniu", usage="(zaproszenie)", aliases=["ii"])
    async def inviteinfo(self, ctx, invite):
        invite = invite.split("/")[-1]

        try:
            resp = (await self.bot.http.request(Route("GET", "invites", invite)))["guild"]
        except HTTPException:
            return await ctx.reply("Takie zaproszenie nie istnieje")

        embed = lib.Embed(title=f"Informacje o {invite}:", color=self.bot.embed_color)

        embed.add_field(name="ID:", value=resp["id"])
        embed.add_field(name="Nazwa:", value=resp["name"])
        embed.add_field(name="Ulepszenia:", value=resp["premium_subscription_count"])

        if resp["description"] is not None:
            embed.add_field(name="Opis:", value=resp["description"])
        if resp["nsfw_level"] > 0:
            embed.add_field(name="Poziom NSFW:", value=resp["nsfw_level"])
        if resp["icon"] is not None:
            embed.set_thumbnail(url=f"https://cdn.discordapp.com/icons/{resp['id']}/{resp['icon']}.png")
            embed.add_field(name="Ikona:", value=f"[link](https://cdn.discordapp.com/icons/{resp['id']}/{resp['icon']}.png)", inline=True)
        if resp["banner"] is not None:
            embed.set_image(url=f"https://cdn.discordapp.com/banners/{resp['id']}/{resp['banner']}.png")
            embed.add_field(name="Banner:", value=f"[link](https://cdn.discordapp.com/banners/{resp['id']}/{resp['banner']}.png)", inline=True)
        if resp["splash"] is not None:
            embed.add_field(name="Splash:", value=f"[link](https://cdn.discordapp.com/splashes/{resp['id']}/{resp['splash']}.png)", inline=True)

        await ctx.reply(embed=embed)

    @commands.command(description="Robi screenshot strony", aliases=["ss"])
    async def screenshot(self, ctx, url, delay: int):
        if not ctx.author.id in self.bot.owners:
            return await ctx.reply("nie możesz!!1!")

        if not url.startswith("local:"):
            result = re.match(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,69}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", url)

            if not result:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

        async with async_playwright() as p:
            browser = await p.firefox.launch()
            page = await browser.new_page()
            url = url.replace("local:", "file://")

            try:
                await page.goto(url)
                await page.main_frame.wait_for_timeout(delay)
                screenshot_bytes = await page.screenshot()
            except Exception:
                screenshot_bytes = open("./assets/images/attacl.png", "rb").read()

            image = io.BytesIO(screenshot_bytes)
            components = lib.Components(lib.Row(lib.Button("curl", style=lib.ButtonStyles.SECONDARY, custom_id="curl")))

            message = await ctx.reply(files=[("image.png", image)], components=components)

            async def curl(interaction):
                await interaction.callback(lib.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
                await self.bot.paginator(message.edit, ctx, (await (await self.bot.http.session.get(url)).content.read()).decode(), embeds=[], other={"attachments": []}, prefix="```html\n", suffix="```")

            async def on_timeout():
                components = lib.Components(lib.Row(lib.Button("curl", style=lib.ButtonStyles.SECONDARY, custom_id="curl", disabled=True)))
                await message.edit(components=components)

            await self.bot.wait_for("interaction_create", curl, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60, on_timeout=on_timeout)

            await browser.close()

    @commands.command(description="Nagrywa filmik ze strony", aliases=["recban", "record"])
    async def rec(self, ctx, url):
        if not ctx.author.id in self.bot.owners:
            return await ctx.reply("nie możesz!!1!")

        if not url.startswith("local:"):
            result = re.match(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,69}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", url)

            if not result:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

        async with async_playwright() as p:
            browser = await p.firefox.launch()
            context = await browser.new_context(
                record_video_dir="videos/",
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            url = url.replace("local:", "file://")

            await page.goto(url)
            await page.main_frame.wait_for_timeout(5000)

            await context.close()

            await ctx.reply(files=[("video.webm", open(await page.video.path(), "rb"))])

            await browser.close()

    @commands.command(description="Informacje o koncie TruckersMP", usage="(nazwa)", aliases=["tmp", "ets2", "ets"], other={"embed": lib.Embed(description="\nNazwa: `steamid64`, `nazwa steam`")})
    async def truckersmp(self, ctx, *, _id):
        if not re.match(r"^\d+$", _id):
            resp = await self.bot.http.session.get("https://steamcommunity.com/id/" + _id, headers={"User-Agent": self.bot.user_agent})

            try:
                soup = BeautifulSoup(await resp.content.read(), "lxml")
                _id = json.loads(soup.find_all("script", {"type": "text/javascript"}, text=re.compile("g_rgProfileData"))[0].string.splitlines()[1][20:-1])["steamid"]
            except json.decoder.JSONDecodeError:
                return await ctx.send("Nie znaleziono takiego konta steam")

        resp = await self.bot.http.session.get("https://api.truckersmp.com/v2/player/" + _id)
        resp = await resp.json()

        if resp["error"]:
            return await ctx.send("Nie znaleziono takiego konta TruckersMP")

        resp = resp["response"]

        embed = lib.Embed(title=f"Informacje o {resp['name']}:", color=self.bot.embed_color)
        embed.set_thumbnail(url=resp["avatar"])
        embed.add_field(name="ID:", value=resp["id"])
        embed.add_field(name="ID Steam64:", value=resp["steamID64"])
        embed.add_field(name="Nick:", value=resp["name"])
        embed.add_field(name="Utworzył konto:", value="<t:" + str(round(datetime.strptime(resp["joinDate"], "%Y-%m-%d %H:%M:%S").timestamp())) + ">")
        if resp["banned"]:
            embed.add_field(name="Zbanowany:", value="Tak")
        if resp["patreon"]["isPatron"]:
            embed.add_field(name="Supporter Patreon:", value="Tak")
        if resp["vtc"]["inVTC"]:
            embed.add_field(name="Nazwa firmy:", value=resp["vtc"]["name"])
            embed.add_field(name="Tag firmy:", value=resp["vtc"]["tag"])

        await ctx.reply(embed=embed)

    @commands.command(description="Słownik", usage="(język) (słowo)", aliases=["definition", "word", "dict", "def"], other={"embed": lib.Embed(description="\nJęzyki: `pl`, `en`, `es`, `urban`")})
    @commands.is_nsfw
    async def dictionary(self, ctx, language: lambda arg: arg if arg in "pl" + "en" + "es" + "urban" else None, *, word):
        async def fetch(url, tag, attributes, expression):
            resp = await self.bot.http.session.get(url, headers={"user-agent": self.bot.user_agent})

            soup = BeautifulSoup(await resp.content.read(), "lxml")
            text = soup.find_all(tag, attributes)

            if not text:
                return "Nie znaleziono takiego słowa"

            text = text[0].get_text()

            return f"**{word}**\n{re.findall(expression, text)[-1]}\n*z <{url.replace(' ', '%20')}>*"

        match language:
            case "en":
                definition = await fetch("https://dictionary.cambridge.org/pl/dictionary/english/" + word, "div", {"class": "def"}, r"[\w,. ]+")

            case "pl":
                definition = await fetch("https://sjp.pwn.pl/szukaj/" + word + ".html", "div", {"class": "znacz"}, r"[\w,. ]+")

            case "es":
                definition = await fetch("https://dictionary.cambridge.org/pl/dictionary/spanish-english/" + word, "div", {"class": "def"}, r"[\w,. ]+")

            case "urban":
                definition = await fetch("https://www.urbandictionary.com/define.php?term=" + word, "div", {"class": "meaning mb-4"}, r".+")

        await ctx.reply(definition)

    @commands.command(description="zgadnij kto to", aliases=["who", "ktoto", "coto"])
    async def whois(self, ctx):
        members = []

        members_with_pfp = [member for member in ctx.guild.members if member.user.avatar]

        if len(members_with_pfp) < 10:
            return await ctx.reply("Na tym serwerze nie ma wymaganej ilości użytkowników z avatarem")

        while not len(members) == 10:
            member = random.choice(members_with_pfp)

            if not member in members:
                members.append(member)

        correct = random.choice(members)

        color = self.bot.embed_color

        if correct.hoisted_role is not None:
            color = correct.hoisted_role.color

        embed = lib.Embed(title="Zgadnij kto to:", color=color)
        embed.set_image(url=correct.user.avatar_url)

        def get_components():
            return lib.Components(
                lib.Row(
                    lib.SelectMenu(
                        custom_id = "members",
                        placeholder = "Wybierz użytkownika",
                        options = [
                            lib.Option(member.user.username, member.user.id) for member in members
                        ]
                    )
                )
            )

        message = await ctx.reply(embed=embed, components=get_components())

        async def on_select(interaction):
            nonlocal members

            selected_member = members[get_index(members, interaction.data.values[0], key=lambda member: member.user.id)]

            if selected_member == correct:
                return await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, f"{types.m @ interaction.member} zgadł!", embeds=[], components={})
            elif len(members) == 4:
                return await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, "Nie udało sie nikomu zgadnąć", embeds=[], components={})
            else:
                members.remove(selected_member)
                await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, embed=embed, components=get_components())
                await self.bot.wait_for("interaction_create", on_select, lambda interaction: interaction.channel.id == ctx.channel.id, timeout=60 * 5)

        async def on_timeout():
            await message.edit("Nie udało się nikomu zgadnąć", embeds=[])

        await self.bot.wait_for("interaction_create", on_select, lambda interaction: interaction.channel.id == ctx.channel.id, timeout=60 * 5, on_timeout=on_timeout)

def setup(bot):
    bot.load_cog(Fun(bot))