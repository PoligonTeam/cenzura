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
from lib import commands, types, HTTPException
from cenzurascript import run
from utils import convert, table
from aiohttp import ClientSession
from models import LastFM
from config import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL
import hashlib, asyncio

class Fm(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot
        self.templates = {
            "embedfull": "return \"jeszcze nie zrobione\"",
            "embedmini": """username = user.username
lastfm_username = lastfm_user.username
scrobbles = lastfm_user.scrobbles
last_track = tracks.0
title = last_track.title
track_url = last_track.url
artist = last_track.artist
album = last_track.album

embed_description = "[" + title + "](" + track_url + ")
Przez **" + artist + "** | _" + album + "_"
embed_color = hex("b22487")
author_name = "Ostatnie utwory dla " + username + ":"

embed = Embed(description: embed_description, color: embed_color)

footer_text = lastfm_username + " ma łącznie " + scrobbles + " scrobbli"

nowplaying == false {
    timestamp = last_track.timestamp
    date = from_timestamp(timestamp, "%Y/%m/%d %H:%M")
    footer_text = footer_text + " | Ostatni scrobble: " + date
}

Embed.set_author(embed, name: author_name, icon_url: user.avatar_url)
Embed.set_thumbnail(embed, url: last_track.image)
Embed.set_footer(embed, text: footer_text)

return embed""",
            "textfull": "return \"jeszcze nie zrobione\"",
            "textminit": "return \"jeszcze nie zrobione\""
        }

    def sign(self, method, token):
        string = "api_key" + LASTFM_API_KEY + "method" + method + "token" + token + LASTFM_API_SECRET
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    @commands.command(description="Łączenie konta LastFM do bota")
    async def login(self, ctx):
        async with ClientSession() as session:
            async with session.get(LASTFM_API_URL + f"?method=auth.getToken&api_key={LASTFM_API_KEY}&format=json") as response:
                data = await response.json()
                token = data["token"]

                try:
                    message = await ctx.author.send(f"Aby połączyć konto LastFM z botem musisz wejść w poniższy link\n<https://www.last.fm/api/auth?api_key={LASTFM_API_KEY}&token={token}>")
                except HTTPException:
                    return await ctx.reply("Bot nie może wysłać ci wiadomości prywatnej")

                await ctx.reply("Wiadomość z linkiem została wysłana w wiadomości prywatnej")

                signature = self.sign("auth.getSession", token)

                for attempt in range(3):
                    await asyncio.sleep(20)

                    async with session.get(LASTFM_API_URL + f"?method=auth.getSession&token={token}&api_key={LASTFM_API_KEY}&api_sig={signature}&format=json") as response:
                        if not response.status == 200:
                            if attempt == 8:
                                return await message.edit("Logowanie się nie powiodło... link się przedawnił lub coś poszło nie tak")

                            continue

                        data = await response.json()
                        data = data["session"]

                        query = LastFM.filter(user_id=ctx.author.id)

                        if await query.first() is None:
                            query = LastFM.create
                        else:
                            query = query.update

                        await query(user_id=ctx.author.id, username=data["name"], token=data["key"], script=self.templates["embedmini"])

                        return await message.edit("Pomyślnie połączono konto `" + data["name"] + "`")

    @commands.command(description="Statystyki konta LastFM", usage="[użytkownik]", aliases=["fmstats", "fm"])
    async def lastfm(self, ctx, *, user: types.User = None):
        user = user or ctx.author

        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with lib.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&user={lastfm.username}&limit=2&api_key={LASTFM_API_KEY}&format=json") as response:
                    if not response.status == 200:
                        return await ctx.reply("Takie konto LastFM nie istnieje")

                    data = await response.json()
                    data = data["recenttracks"]
                    tracks = data["track"]
                    lastfm_user = data["@attr"]

                    cs_data = {
                        "tracks": [],
                        "lastfm_user": {
                            "username": lastfm_user["user"],
                            "scrobbles": lastfm_user["total"],
                        },
                        "nowplaying": False
                    }

                    if not tracks:
                        return await ctx.reply("Nie ma żadnych utworów")

                    if len(tracks) == 3:
                        cs_data["nowplaying"] = True

                    for track in tracks:
                        cs_track = {
                            "artist": track["artist"]["#text"],
                            "image": track["image"][-1]["#text"],
                            "title": track["name"],
                            "url": track["url"],
                            "album": track["album"]["#text"]
                        }

                        if "date" in track:
                            cs_track["timestamp"] = int(track["date"]["uts"]) + 60 * 60 * 2

                        cs_data["tracks"].append(cs_track)

                    result = await run(
                        lastfm.script,
                        builtins = {
                            "Embed": lib.Embed,
                            "table": table
                        },
                        variables = {
                            **convert(
                                user = user
                            ),
                            **cs_data
                        }
                    )

                    if isinstance(result, lib.Embed):
                        return await ctx.reply(embed=result)

                    await ctx.reply(result)

    @commands.command(description="Ustawianie skryptu dla komendy lastfm", usage="(skrypt)", aliases=["fms", "fmset"])
    async def fmscript(self, ctx, *, script):
        query = LastFM.filter(user_id=ctx.author.id)

        if await query.first() is None:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        await query.update(script=script)
        await ctx.reply("Skrypt został ustawiony")

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": lib.Embed(description="\nSzablony: `embedfull`, `embedmini`, `textfull`, `textmini`")})
    async def fmtemplate(self, ctx, template):
        if not template in self.templates:
            return await ctx.reply("Nie ma takiego szablonu")

        await self.fmscript(ctx, script=self.templates[template])

def setup(bot):
    bot.load_cog(Fm(bot))