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
from bs4 import BeautifulSoup
from models import LastFM
from config import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL, MUSIXMATCH
import urllib.parse, hashlib, datetime, asyncio, os

class Fm(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot
        self.templates = {}

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

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
                            "artist_url": "https://www.last.fm/music/" + urllib.parse.quote(track["artist"]["#text"]),
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
        lastfm_user = await query.first()

        if lastfm_user is None:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        if script == "get_code()":
            return await self.bot.paginator(ctx.reply, ctx, lastfm_user.script, prefix="```py\n", suffix="```")

        script = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
                 f"# GUILD: {ctx.guild.id}\n" \
                 f"# CHANNEL: {ctx.channel.id}\n" \
                 f"# AUTHOR: {ctx.author.id}\n\n" \
               + script

        await query.update(script=script)
        await ctx.reply("Skrypt został ustawiony")

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": lib.Embed(description="\nSzablony: `embedfull`, `embedmini`, `textfull`, `textmini`")})
    async def fmtemplate(self, ctx, template):
        if not template in self.templates:
            return await ctx.reply("Nie ma takiego szablonu")

        await self.fmscript(ctx, script=self.templates[template])

    @commands.command(description="Użytkownicy którzy znają artyste", aliases=["wk"])
    async def whoknows(self, ctx):
        lastfm_users = await LastFM.all()

        if not ctx.author.id in [lastfm_user.user_id for lastfm_user in lastfm_users]:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_scrobbles = []

        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == ctx.author.id][0]

        async with lib.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&username={lastfm_user.username}&limit=1&api_key={LASTFM_API_KEY}&format=json") as response:
                    data = await response.json()

                    artist = data["recenttracks"]["track"][0]["artist"]["#text"]
                    artist_url = "https://www.last.fm/music/" + urllib.parse.quote(artist)

                    async def get_scrobbles(lastfm_user):
                        nonlocal lastfm_scrobbles, artist_url

                        async with session.get(LASTFM_API_URL + f"?method=artist.getInfo&artist={artist}&username={lastfm_user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                            data = await response.json()

                            lastfm_scrobbles.append((await ctx.guild.get_member(lastfm_user.user_id), lastfm_user, data["artist"]["stats"]["userplaycount"]))

                    for lastfm_user in lastfm_users:
                        self.bot.loop.create_task(get_scrobbles(lastfm_user))

                    while len(lastfm_scrobbles) < len(lastfm_users):
                        await asyncio.sleep(0.1)

                    lastfm_scrobbles.sort(key=lambda scrobbles: int(scrobbles[2]), reverse=True)

                    description = ""

                    for (member, lastfm_user, scrobbles), index in zip(lastfm_scrobbles, range(len(lastfm_scrobbles))):
                        if scrobbles == "0":
                            continue

                        index += 1

                        if index == 1:
                            index = "\N{CROWN}"
                        elif member is ctx.member:
                            index = f"**{index}**."
                        else:
                            index = f"{index}."

                        description += f"{index} [{member.user.username}](https://www.last.fm/user/{lastfm_user.username}) - **{scrobbles}** odtworzeń\n"

                    embed = lib.Embed(title="Użytkownicy którzy znają " + artist + ":", url=artist_url, description=description, color=self.bot.embed_color)

                    await ctx.reply(embed=embed)

    @commands.command(description="Pokazuje tekst piosenki", usage="[nazwa]")
    async def lyrics(self, ctx, *, name = None):
        source = "Command Argument"

        async with lib.Typing(ctx.message):
            async with ClientSession() as session:
                if name is None:
                    activities = ctx.member.presence.activities
                    index = lib.utils.get_index(activities, "Spotify", key=lambda activity: activity.name)

                    if index is not None:
                        activity = activities[index]
                        source = "Discord Spotify Activity"
                        name = activity.details + " " + activity.state

                if name is None:
                    lastfm = await LastFM.filter(user_id=ctx.author.id).first()

                    if lastfm is None:
                        return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

                    async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&username={lastfm.username}&limit=1&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()
                        tracks = data["recenttracks"]["track"]

                        if not tracks:
                            return await ctx.reply("Nie ma żadnych utworów")

                        if len(tracks) == 2:
                            source = "LastFM"
                            name = tracks[0]["name"] + " " + tracks[0]["artist"]["#text"]

                if name is None:
                    async with session.get("https://radio.poligon.lgbt/api/live/nowplaying/station_1") as response:
                        data = await response.json()
                        track = data["now_playing"]["song"]

                        source = "Poligon Radio"
                        name = track["title"] + " " + track["artist"]

                async with session.get(f"https://api.musixmatch.com/ws/1.1/track.search?q_track_artist={urllib.parse.quote_plus(name)}&page_size=1&page=1&s_track_rating=desc&s_artist_rating=desc&country=us&apikey={MUSIXMATCH}") as response:
                    data = await response.json(content_type=None)

                    track_list = data["message"]["body"]["track_list"]

                    if not track_list:
                        return await ctx.reply("Nie znaleziono takiego utworu")

                    track = track_list[0]["track"]

                    artist_name = track["artist_name"]
                    track_name = track["track_name"]
                    album_name = track["album_name"]
                    track_share_url = track["track_share_url"]

                    async with session.get(track_share_url, headers={"user-agent": self.bot.user_agent}) as response:
                        soup = BeautifulSoup(await response.content.read(), features="lxml")

                        elements = soup.find_all("p", {"class": "mxm-lyrics__content"})
                        lyrics = "\n".join([element.get_text() for element in elements])

                        if not lyrics:
                            return await ctx.reply("Nie znaleziono takiego utworu")

                        lyrics = f"# SOURCE: {source}\n" \
                                 f"# ARTIST NAME: {artist_name}\n" \
                                 f"# TRACK NAME: {track_name}\n" \
                                 f"# ALBUM NAME: {album_name}\n\n" \
                               + lyrics

        await self.bot.paginator(ctx.reply, ctx, lyrics, prefix="```md\n", suffix="```")

def setup(bot):
    bot.load_cog(Fm(bot))