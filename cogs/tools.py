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
from yt_dlp import YoutubeDL
from playwright.async_api import async_playwright
import re, io

tiktok_pattern = re.compile(r"(?x)https?://(?:(?:www|m)\.(?:tiktok.com)\/(?:v|embed|trending)(?:\/)?(?:\?shareId=)?)(?P<id>[\da-z]+)")

class Tools(commands.Cog):
    name = "Narzędzia"

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.command()
    async def tiktok(self, ctx: commands.Context, *, url):
        # if not tiktok_pattern.match(url):
        #     return await ctx.reply("to nie jest film tiktok")

        with YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

            embed = femcord.Embed(title="TikTok")
            embed.add_field(name="Tytuł", value=f"[{info['title']}]({info['webpage_url']})", inline=True)
            embed.add_field(name="Nazwa twórcy", value=f"[{info['uploader']}]({info['uploader_url']})", inline=True)
            embed.add_blank_field()
            embed.add_field(name="Wyświetlenia", value=info["view_count"], inline=True)
            embed.add_field(name="Polubienia", value=info["like_count"], inline=True)
            embed.add_blank_field()
            embed.add_field(name="Komentarze", value=info["comment_count"], inline=True)
            embed.add_field(name="Udostępnienia", value=info["repost_count"], inline=True)
            embed.add_blank_field()
            embed.add_field(name="Link", value=f"[Link]({info['formats'][3]['url']})", inline=True)

            await ctx.reply(embed=embed)

    @commands.command(description="Robi screenshot strony", aliases=["ss"])
    async def screenshot(self, ctx: commands.Context, url):
        if not ctx.author.id in self.bot.owners:
            return await ctx.reply("nie możesz!!1!")

        async with femcord.Typing(ctx.message):
            result = re.match(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,69}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", url)

            if not result:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

            async with async_playwright() as p:
                browser = await p.firefox.launch()
                context = await browser.new_context(
                    storage_state={
                        "cookies": [
                            {
                                "name": "CONSENT",
                                "value": "YES+0",
                                "domain": ".google.com",
                                "path": "/"
                            }
                        ]
                    }
                )
                page = await context.new_page()

                try:
                    await page.goto(url)
                    await page.wait_for_load_state("domcontentloaded")
                    screenshot_bytes = await page.screenshot()
                except Exception:
                    screenshot_bytes = open("./assets/images/attacl.png", "rb").read()

                await browser.close()

                image = io.BytesIO(screenshot_bytes)
                components = femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl")))

            message = await ctx.reply(files=[("image.png", image)], components=components)

            async def curl(interaction):
                await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_UPDATE_MESSAGE)
                await self.bot.paginator(message.edit, ctx, (await (await self.bot.http.session.get(url)).content.read()).decode(), embeds=[], other={"attachments": []}, prefix="```html\n", suffix="```")

            async def on_timeout():
                components = femcord.Components(femcord.Row(femcord.Button("curl", style=femcord.ButtonStyles.SECONDARY, custom_id="curl", disabled=True)))
                await message.edit(components=components)

            await self.bot.wait_for("interaction_create", curl, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60, on_timeout=on_timeout)

    @commands.command(description="Nagrywa filmik ze strony", aliases=["recban", "record"])
    async def rec(self, ctx: commands.Context, url):
        if not ctx.author.id in self.bot.owners:
            return await ctx.reply("nie możesz!!1!")

        async with femcord.Typing(ctx.message):
            result = re.match(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,69}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)", url)

            if not result:
                return await ctx.reply("Podałeś nieprawidłowy adres url")

            async with async_playwright() as p:
                browser = await p.firefox.launch()
                context = await browser.new_context(
                    record_video_dir="/tmp/",
                    record_video_size={"width": 1920, "height": 1080},
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()

                await page.goto(url)
                await page.wait_for_load_state("domcontentloaded")

                await context.close()

                await ctx.reply(files=[("video.webm", open(await page.video.path(), "rb"))])

                await browser.close()

def setup(bot):
    bot.load_cog(Tools(bot))