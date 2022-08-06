import lib
from lib import commands
from yt_dlp import YoutubeDL
import re

tiktok_pattern = re.compile(r"(?x)https?://(?:(?:www|m)\.(?:tiktok.com)\/(?:v|embed|trending)(?:\/)?(?:\?shareId=)?)(?P<id>[\da-z]+)")

class Downloaders(commands.Cog):
    name = "Downloadery"

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tiktok(self, ctx, *, url):
        # if not tiktok_pattern.match(url):
        #     return await ctx.reply("to nie jest film tiktok")

        with YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

            embed = lib.Embed(title="TikTok")
            embed.add_field(name="Tytuł", value=f"[{info['title']}]({info['webpage_url']})", inline=True)
            embed.add_field(name="Nazwa twórcy", value=f"[{info['uploader']}]({info['uploader_url']})", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.add_field(name="Wyświetlenia", value=info["view_count"], inline=True)
            embed.add_field(name="Polubienia", value=info["like_count"], inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.add_field(name="Komentarze", value=info["comment_count"], inline=True)
            embed.add_field(name="Udostępnienia", value=info["repost_count"], inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            embed.add_field(name="Link", value=f"[Link]({info['formats'][3]['url']})", inline=True)

            await ctx.reply(embed=embed)

def setup(bot):
    bot.load_cog(Downloaders(bot))