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
from femcord import commands, types, HTTPException
from femscript import run
from utils import *
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from models import LastFM
from config import GENIUS, LAVALINK_IP, LAVALINK_PORT, LAVALINK_PASSWORD, LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL, MUSIXMATCH
import hashlib, datetime, asyncio, lavalink, re, os, logging

youtube_pattern = re.compile(
    "(https?://)?(www\.)?"
    "(youtube|youtu|youtube-nocookie)\.(com|be)/"
    "(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
)

soundcloud_pattern = re.compile(
    r"^(https?:\/\/)?(www.)?(m\.)?soundcloud\.com\/[\w\-\.]+(\/)+[\w\-\.]+/?$"
)

class Music(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot
        self.templates = {}

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    def on_load(self):
        if self.bot.gateway is not None:
            self.client = lavalink.Client(int(self.bot.gateway.bot_user.id))
            self.client.add_node(LAVALINK_IP, LAVALINK_PORT, LAVALINK_PASSWORD, "eu", None, 10, "default_node", -1)

    def connect(self, guild, channel, *, mute = False, deaf = False):
        return self.bot.gateway.ws.send(femcord.enums.Opcodes.VOICE_STATE_UPDATE, {
            "guild_id": guild.id,
            "channel_id": channel.id if channel else None,
            "self_mute": mute,
            "self_deaf": deaf
        })

    def get_player(self, guild) -> lavalink.DefaultPlayer:
        return self.client.player_manager.get(int(guild.id))

    def sign(self, method, token):
        string = "api_key" + LASTFM_API_KEY + "method" + method + "token" + token + LASTFM_API_SECRET
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    @commands.Listener
    async def on_ready(self):
        logging.getLogger("lavalink").setLevel(logging.CRITICAL)

        self.on_load()

    @commands.Listener
    async def on_voice_server_update(self, data):
        await self.client.voice_update_handler({
            "t": "VOICE_SERVER_UPDATE",
            "d": data
        })

    @commands.Listener
    async def on_raw_voice_state_update(self, data):
        await self.client.voice_update_handler({
            "t": "VOICE_STATE_UPDATE",
            "d": data
        })

    @commands.command()
    async def join(self, ctx: commands.Context, mute: int = 0, deaf: int = 0):
        channel = ctx.member.voice_state.channel

        if channel is None:
            return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

        await self.connect(ctx.guild, channel, mute=bool(mute), deaf=bool(mute))

        self.client.player_manager.create(guild_id=int(ctx.guild.id))

        await ctx.reply("Dołączyłem na kanał głosowy")

    @commands.command()
    async def leave(self, ctx: commands.Context):
        await self.connect(ctx.guild, None)

        await ctx.reply("Wyszedłem z kanału głosowego")

    @commands.command()
    async def bassboost(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if player is None:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

        if any(player.equalizer) is True:
            await player.reset_equalizer()
            return await ctx.reply("wyłączyłem bassboost")

        await player.set_gains((0, 0.15), (1, 0.20))
        await ctx.reply("włączyłem bassboost")

    @commands.command()
    async def play(self, ctx: commands.Context, *, query):
        player = self.get_player(ctx.guild)

        if player is None:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

            await self.join(ctx)

            for _ in range(6):
                player = self.get_player(ctx.guild)
                await asyncio.sleep(0.5)

        if query == r"%radio":
            query = "https://radio.poligon.lgbt/listen/station_1/radio.mp3"

        elif not youtube_pattern.match(query) or soundcloud_pattern.match(query):
            query = "ytsearch:" + query

        result = await player.node.get_tracks(query)

        if not result or not result["tracks"]:
            return await ctx.reply("Nie znaleziono żadnych utworów")

        track = lavalink.models.AudioTrack(result["tracks"][0], ctx.author.id)
        player.add(requester=ctx.author.id, track=track)

        if not player.is_playing:
            await ctx.reply("Zaczynam grać `" + track.title + "`")
            await player.play()
        else:
            await ctx.reply("Dodano do kolejki `" + track.title + "`")

    @commands.command()
    async def resume(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if (player is None) or player.is_playing is False:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.paused is False:
            return await ctx.reply("Muzyka nie jest zatrzymana")

        await player.set_pause(False)
        await ctx.reply("Wznowiłem muzykę")

    @commands.command()
    async def pause(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if (player is None) or player.is_playing is False:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.paused is True:
            return await ctx.reply("Muzyka jest już zatrzymana")

        await player.set_pause(True)
        await ctx.reply("Wstrzymałem muzykę")

    @commands.command()
    async def skip(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if not player:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.is_playing:
            await player.skip()
            await ctx.reply("Pominięto utwór")

    @commands.command()
    async def volume(self, ctx: commands.Context, volume: float):
        player = self.get_player(ctx.guild)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if volume < 0 or volume > 1000:
            return await ctx.reply("Głośność musi być pomiędzy 0 a 1000")

        await player.set_volume(volume)

        await ctx.reply(f"Zmieniono głośność na {volume:.1f}%")

    @commands.command()
    async def queue(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        text = ""

        for track in player.queue:
            text += track.title + "\n"

        await ctx.reply(text or "nie ma nic")

    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if not player:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if not player.current:
            return await ctx.reply("Nie gram żadnego utworu")

        if player.current.title == "radio poligon":
            async with ClientSession() as session:
                async with session.get("https://radio.poligon.lgbt/api/live/nowplaying/station_1") as response:
                    data = await response.json()
                    now_playing = data["now_playing"]
                    playing_next = data["playing_next"]

                    return await ctx.reply(f"Gram teraz: `{now_playing['song']['text']}` {(now_playing['elapsed'] % 3600) // 60}:{now_playing['elapsed'] % 60:02d}/{(now_playing['duration'] % 3600) // 60}:{now_playing['duration'] % 60:02d}\nPotem będę grał: `{playing_next['song']['text']}`")

        position = int(player.position / 1000)
        duration = int(player.current.duration / 1000)

        await ctx.reply(f"Gram teraz: `{player.current.title}` {(position % 3600) // 60}:{position % 60:02d}/{(duration % 3600) // 60}:{duration % 60:02d}")

    @commands.command(description="Łączenie konta LastFM do bota")
    async def login(self, ctx: commands.Context):
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

    @commands.command(description="Informacje o obecnie grającej piosence", usage="[użytkownik]", aliases=["ti", "track", "trackstats"])
    async def trackinfo(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&user={lastfm.username}&limit=2&api_key={LASTFM_API_KEY}&format=json") as response:
                    if not response.status == 200:
                        return await ctx.reply("Takie konto LastFM nie istnieje")

                    data = await response.json()
                    data = data["recenttracks"]["track"][0]
                    track_name = data["name"]
                    artist_name = data["artist"]["#text"]

                    async with session.get(LASTFM_API_URL + f"?method=track.getInfo&username={lastfm.username}&artist={artist_name}&track={track_name}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()
                        track = data["track"]

                        embed = femcord.Embed(title=f"Informacje o utworze", url=track["url"], color=self.bot.embed_color)
                        embed.add_field(name="Wykonawca", value=track["artist"]["name"], inline=True)
                        embed.add_field(name="Nazwa utworu", value=track["name"], inline=True)
                        embed.add_field(name="\u200b", value="\u200b", inline=True)
                        embed.add_field(name="Gatunki", value="\n".join(["- " + genere["name"].title() for genere in track["toptags"]["tag"]]))

                        embed.set_thumbnail(url=track["album"]["image"][-1]["#text"])

                        await ctx.reply(embed=embed)

    @commands.command(description="Statystyki konta LastFM", usage="[użytkownik]", aliases=["fmstats", "fm"])
    async def lastfm(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&user={lastfm.username}&limit=2&extended=1&api_key={LASTFM_API_KEY}&format=json") as response:
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

                    async def append_track(index, track):
                        async with session.get(LASTFM_API_URL + f"?method=track.getInfo&user={lastfm.username}&artist={track['artist']['name']}&track={track['name']}&api_key={LASTFM_API_KEY}&format=json") as response:
                            data = await response.json()
                            track_info = data["track"]

                        async with session.get(LASTFM_API_URL + f"?method=artist.getInfo&user={lastfm.username}&artist={track['artist']['name']}&api_key={LASTFM_API_KEY}&format=json") as response:
                            data = await response.json()
                            artist_info = data["artist"]

                        cs_track = {
                            "artist": {
                                "name": track["artist"]["name"],
                                "url": track["artist"]["url"],
                                "listeners": artist_info["stats"]["listeners"],
                                "playcount": artist_info["stats"]["playcount"],
                                "scrobbles": artist_info["stats"]["userplaycount"],
                                "tags": artist_info["tags"]["tag"]
                            },
                            "image": track["image"][-1]["#text"],
                            "title": track["name"],
                            "url": track["url"],
                            "album": track["album"]["#text"],
                            "listeners": track_info["listeners"],
                            "playcount": track_info["playcount"],
                            "scrobbles": track_info["userplaycount"],
                            "tags": track_info["toptags"]["tag"]
                        }

                        if "date" in track:
                            cs_track["timestamp"] = int(track["date"]["uts"]) + 60 * 60 * 2

                        cs_data["tracks"].append((index, cs_track))

                    for index, track in enumerate(tracks):
                        self.bot.loop.create_task(append_track(index, track))

                    while len(cs_data["tracks"]) < 2:
                        await asyncio.sleep(0.1)

                    cs_data["tracks"].sort(key=lambda track: track[0])
                    cs_data["tracks"] = [track[1] for track in cs_data["tracks"]]

                    result = await run(
                        lastfm.script,
                        modules = modules,
                        builtins = builtins,
                        variables = {
                            **convert(
                                user = user
                            ),
                            **cs_data
                        }
                    )

                    if isinstance(result, femcord.Embed):
                        return await ctx.reply(embed=result)

                    await ctx.reply(result)

    @commands.command(description="Ustawianie skryptu dla komendy lastfm", usage="(skrypt)", aliases=["fms", "fmset"])
    async def fmscript(self, ctx: commands.Context, *, script):
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

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": femcord.Embed(description="\nSzablony: `embedfull`, `embedmini`, `textfull`, `textmini`")})
    async def fmtemplate(self, ctx: commands.Context, template):
        if not template in self.templates:
            return await ctx.reply("Nie ma takiego szablonu")

        await self.fmscript(ctx, script=self.templates[template])

    @commands.command(description="Użytkownicy którzy znają artyste", aliases=["wk"])
    async def whoknows(self, ctx: commands.Context):
        lastfm_users = await LastFM.all()

        if not ctx.author.id in [lastfm_user.user_id for lastfm_user in lastfm_users]:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_scrobbles = []

        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == ctx.author.id][0]

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&username={lastfm_user.username}&limit=1&extended=1&api_key={LASTFM_API_KEY}&format=json") as response:
                    data = await response.json()

                    artist = data["recenttracks"]["track"][0]["artist"]
                    artist_name = artist["name"]
                    artist_url = artist["url"]

                    async def get_scrobbles(lastfm_user):
                        nonlocal lastfm_scrobbles, artist_url

                        async with session.get(LASTFM_API_URL + f"?method=artist.getInfo&artist={artist_name}&username={lastfm_user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                            data = await response.json()

                            lastfm_scrobbles.append((await ctx.guild.get_member(lastfm_user.user_id), lastfm_user, data["artist"]["stats"]["userplaycount"]))

                    for lastfm_user in lastfm_users:
                        self.bot.loop.create_task(get_scrobbles(lastfm_user))

                    while len(lastfm_scrobbles) < len(lastfm_users):
                        await asyncio.sleep(0.1)

                    lastfm_scrobbles.sort(key=lambda scrobbles: int(scrobbles[2]), reverse=True)

                    description = ""

                    for index, (member, lastfm_user, scrobbles) in zip(range(len(lastfm_scrobbles)), lastfm_scrobbles):
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

                    embed = femcord.Embed(title="Użytkownicy którzy znają " + artist_name + ":", url=artist_url, description=description, color=self.bot.embed_color)

                    await ctx.reply(embed=embed)

    @commands.command(description="Pokazuje tekst piosenki", usage="[nazwa]")
    async def lyrics(self, ctx: commands.Context, *, name = None):
        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                if name == r"%radio":
                    async with session.get("https://radio.poligon.lgbt/api/live/nowplaying/station_1") as response:
                        data = await response.json()
                        track = data["now_playing"]["song"]

                        name = track["title"] + " " + track["artist"]

                if name is None:
                    activities = ctx.member.presence.activities
                    index = femcord.utils.get_index(activities, "Spotify", key=lambda activity: activity.name)

                    if index is not None:
                        activity = activities[index]
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
                            name = tracks[0]["name"] + " " + tracks[0]["artist"]["#text"]

                if name is None:
                    return await ctx.reply("Nie podałeś nazwy")

                lyrics = None

                async with session.get(f"https://api.musixmatch.com/ws/1.1/track.search?q_track_artist={name}&page_size=1&page=1&s_track_rating=desc&s_artist_rating=desc&country=us&apikey={MUSIXMATCH}") as response:
                    data = await response.json(content_type=None)

                    track_list = data["message"]["body"]["track_list"]

                    if track_list:
                        track = track_list[0]["track"]

                        artist_name = track["artist_name"]
                        track_name = track["track_name"]
                        track_share_url = track["track_share_url"]

                        async with session.get(track_share_url, headers={"user-agent": self.bot.user_agent}) as response:
                            content = await response.content.read()
                            soup = BeautifulSoup(content, features="lxml")

                            elements = soup.find_all("p", {"class": "mxm-lyrics__content"})

                            if elements:
                                source = "Musixmatch"
                                lyrics = "\n".join([element.get_text() for element in elements])

                if lyrics is None:
                    async with session.get(f"https://api.genius.com/search?q={name}&access_token={GENIUS}") as response:
                        data = await response.json()

                        hits = data["response"]["hits"]

                        if hits:
                            track = hits[0]["result"]

                            artist_name = track["artist_names"]
                            track_name = track["title"]
                            track_share_url = track["url"]

                            async with session.get(track_share_url, headers={"user-agent": self.bot.user_agent}) as response:
                                content = await response.content.read()
                                soup = BeautifulSoup(content, features="lxml")

                                element = soup.find("div", {"data-lyrics-container": True})

                                if element:
                                    source = "Genius"
                                    lyrics = element.get_text("\n")

                if lyrics is None:
                    return await ctx.reply("Nie ma tekstu dla tej piosenki")

                lyrics = f"# SOURCE: {source}\n" \
                         f"# ARTIST NAME: {artist_name}\n" \
                         f"# TRACK NAME: {track_name}\n\n" \
                       + lyrics

        await self.bot.paginator(ctx.reply, ctx, lyrics, prefix="```md\n", suffix="```", buttons=True)

def setup(bot):
    bot.load_cog(Music(bot))