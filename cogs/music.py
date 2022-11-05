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
from urllib.parse import quote_plus
from models import LastFM
from config import *
from lastfm import PartialTrack, TrackArtist
from typing import Union
import hashlib, datetime, asyncio, lavalink, re, os, logging

soundcloud_pattern = re.compile(
    r"(https?:\/\/)?(www.)?(m\.)?soundcloud\.com/.+/.+"
)

class Music(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot
        self.templates = {}
        self.milestones = [50, 100, 250, 420, 500, 1000, 1337, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000]

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    async def on_load(self):
        if self.bot.gateway is not None:
            self.client: lavalink.Client = lavalink.Client(int(self.bot.gateway.bot_user.id))

            for node in LAVALINK_NODES:
                self.client.add_node(*node)

            await asyncio.sleep(1)

            await self.connect("704439884340920441", "853657308152070144", mute=True, deaf=True)

            player = self.client.player_manager.create(guild_id=704439884340920441)
            result = await player.node.get_tracks("https://radio.poligon.lgbt/listen/station_1/radio.mp3")
            track = lavalink.models.AudioTrack(result["tracks"][0], "921822086102679572")
            player.add(requester="921822086102679572", track=track)
            await player.play()
            print("joined poligon and started playing radio")

    def connect(self, guild, channel = None, *, mute = False, deaf = False):
        return self.bot.gateway.ws.send(femcord.enums.Opcodes.VOICE_STATE_UPDATE, {
            "guild_id": guild.id if isinstance(guild, types.Guild) else guild,
            "channel_id": channel.id if isinstance(channel, types.Channel) else channel,
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

        await self.on_load()

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

        await self.connect(ctx.guild, channel, mute=bool(mute), deaf=bool(deaf))

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
            return await ctx.reply("Wyłączyłem bassboost")

        await player.set_gains((0, 0.15), (1, 0.20))
        await ctx.reply("Włączyłem bassboost")

    @commands.command()
    async def play(self, ctx: commands.Context, *, query):
        player: lavalink.DefaultPlayer = self.get_player(ctx.guild)

        if player is None:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

            await self.join(ctx)

            for _ in range(6):
                player: lavalink.DefaultPlayer = self.get_player(ctx.guild)
                await asyncio.sleep(0.5)

        if query == r"%radio":
            query = "https://radio.poligon.lgbt/listen/station_1/radio.mp3"

        elif not soundcloud_pattern.match(query):
            query = "scsearch:" + query

        result = await player.node.get_tracks(query)

        if not result or not result["tracks"]:
            return await ctx.reply("Nie znaleziono żadnych utworów")

        track = lavalink.models.AudioTrack(result["tracks"][0], ctx.author.id)
        player.add(requester=ctx.author.id, track=track)

        if not player.is_playing:
            await ctx.reply("Zaczynam grać `" + track.title + " - " + track.author + "`")
            return await player.play()

        await ctx.reply("Dodano do kolejki `" + track.title + " - " + track.author + "`")

    @commands.command()
    async def resume(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if player is None or player.is_playing is False:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.paused is False:
            return await ctx.reply("Muzyka nie jest zatrzymana")

        await player.set_pause(False)
        await ctx.reply("Wznowiłem muzykę")

    @commands.command()
    async def pause(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if player is None or player.is_playing is False:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.paused is True:
            return await ctx.reply("Muzyka jest już zatrzymana")

        await player.set_pause(True)
        await ctx.reply("Wstrzymałem muzykę")

    @commands.command()
    async def skip(self, ctx: commands.Context):
        player = self.get_player(ctx.guild)

        if not player:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

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
    async def nowplaying(self, ctx: commands.Context, *, query: str = None):
        player = self.get_player(ctx.guild)

        async def nowplaying_poligon():
            async with ClientSession() as session:
                async with session.get("https://radio.poligon.lgbt/api/live/nowplaying/station_1") as response:
                    data = await response.json()
                    now_playing = data["now_playing"]
                    playing_next = data["playing_next"]

                    return await ctx.reply(f"Gram teraz: `{now_playing['song']['text']}` {(now_playing['elapsed'] % 3600) // 60}:{now_playing['elapsed'] % 60:02d}/{(now_playing['duration'] % 3600) // 60}:{now_playing['duration'] % 60:02d}\nPotem będę grał: `{playing_next['song']['text']}`")

        if query == r"%radio":
            return await nowplaying_poligon()

        if not player:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if not player.current:
            return await ctx.reply("Nie gram żadnego utworu")

        if player.current.title == "radio poligon":
            return await nowplaying_poligon()


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

    @commands.command(description="Informacje o artyście", aliases=["ai", "artist"])
    async def artistinfo(self, ctx: commands.Context, *, artist_name: str):
        lastfm = await LastFM.filter(user_id=ctx.author.id).first()

        if lastfm is None:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        async with ClientSession() as session:
            async with session.get(LASTFM_API_URL + f"?method=artist.getinfo&user={lastfm.username}&artist={quote_plus(artist_name)}&api_key={LASTFM_API_KEY}&format=json") as response:
                if not response.status == 200:
                    return await ctx.reply("Nie znaleziono artysty")

                data = await response.json()
                artist = TrackArtist.from_raw(data["artist"])

                embed = femcord.Embed(title="Informacje o " + artist.name, url=artist.url, description=artist.bio.summary, color=self.bot.embed_color, timestamp=datetime.datetime.now())
                embed.add_field(name="Liczba słuchaczy", value=artist.stats.listeners, inline=True)
                embed.add_field(name="Liczba odtworzeń", value=artist.stats.playcount, inline=True)
                embed.add_field(name="Liczba twoich odtworzeń", value=artist.stats.userplaycount, inline=True)
                embed.add_field(name="Gatunki", value="\n".join(["- " + genere.name.title() for genere in artist.tags]), inline=False)

                embed.set_thumbnail(url=artist.image[-1].url)
                embed.set_footer(text="hejka tu lenka", icon_url=ctx.author.avatar_url)

                await ctx.reply(embed=embed)

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
                    track_image = data["image"]
                    artist_name = data["artist"]["#text"]

                    async with session.get(LASTFM_API_URL + f"?method=track.getInfo&username={lastfm.username}&artist={quote_plus(artist_name)}&track={quote_plus(track_name)}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()
                        track = PartialTrack.from_raw({
                            "images": track_image,
                            **data["track"]
                        })

                        embed = femcord.Embed(title=f"Informacje o utworze", url=track.url, color=self.bot.embed_color)
                        embed.add_field(name="Wykonawca", value=track.artist.name, inline=True)
                        embed.add_field(name="Nazwa utworu", value=track.title, inline=True)
                        embed.add_blank_field()
                        embed.add_field(name="Gatunki", value="\n".join(["- " + genere.name.title() for genere in track.tags]))

                        embed.set_thumbnail(url=track.images[-1].url)

                        await ctx.reply(embed=embed)

    # @commands.command(description="Informacje o użytkowniku LastFM", usage="[użytkownik]", aliases=["fui"])
    # async def fmuserinfo(self, ctx: commands.Context, *, user: types.User = None):
    #     user = user or ctx.author

    #     lastfm = await LastFM.filter(user_id=user.id).first()

    #     if lastfm is None:
    #         if ctx.author is user:
    #             return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

    #         return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

    #     async with femcord.Typing(ctx.message):
    #         result = await run(
    #             lastfm.uiscript,
    #             modules = await get_modules(self.bot, ctx.guild, ctx=ctx, user=user),
    #             builtins = builtins,
    #             variables = convert(user=user)
    #         )

    #         if isinstance(result, femcord.Embed):
    #             return await ctx.reply(embed=result)

    #         await ctx.reply(result)

    @commands.command(description="Statystyki konta LastFM", usage="[użytkownik]", aliases=["fmstats", "fm"])
    async def lastfm(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with femcord.Typing(ctx.message):
            femscript_modules = await get_modules(self.bot, ctx.guild, ctx=ctx, user=user, message_errors=True)

            if not femscript_modules:
                return

            result = await run(
                lastfm.script,
                modules = femscript_modules,
                builtins = builtins,
                variables = convert(user=user)
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
                 "import lastfm\n\n" \
               + script

        await query.update(script=script)
        await ctx.reply("Skrypt został ustawiony")

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": femcord.Embed(description="\nSzablony: `embedfull`, `embedsmall`, `embedmini`, `textfull`, `textmini`")})
    async def fmtemplate(self, ctx: commands.Context, template):
        if not template in self.templates:
            return await ctx.reply("Nie ma takiego szablonu")

        await self.fmscript(ctx, script=self.templates[template])

    @commands.command(description="Tempo do ilości scrobbli", usage="[użytkownik]", aliases=["pc"])
    async def pace(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getInfo&user={lastfm.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                    data = await response.json()

                    if "error" in data:
                        return await ctx.reply("Nie znaleziono użytkownika LastFM")

                    account_age = (datetime.datetime.now() -  datetime.timedelta(hours=2)) - datetime.datetime.fromtimestamp(int(data["user"]["registered"]["unixtime"]))
                    scrobbles = int(data["user"]["playcount"])

                    if not scrobbles:
                        return await ctx.reply("Ten użytkownik nie ma żadnych scrobbli")


                    for _milestone in self.milestones:
                        if _milestone > scrobbles:
                            milestone = _milestone
                            break

                    scrobbles_per_day = scrobbles / account_age.days
                    days_to_milestone = (milestone - scrobbles) / scrobbles_per_day
                    pace = datetime.datetime.now() + datetime.timedelta(days=days_to_milestone)

                    await ctx.reply(f"{types.t['D'] @ pace} ({scrobbles_per_day:.2f} scrobbli dziennie | {scrobbles} w {account_age.days} dni)")

    @commands.command(description="Użytkownicy którzy znają artyste", aliases=["wk"])
    async def whoknows(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm_users = await LastFM.all()

        if not user.id in [lastfm_user.user_id for lastfm_user in lastfm_users]:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == user.id][0]
        lastfm_scrobbles = []

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&username={lastfm_user.username}&limit=1&extended=1&api_key={LASTFM_API_KEY}&format=json") as response:
                    data = await response.json()

                    artist = data["recenttracks"]["track"][0]["artist"]
                    artist_name = artist["name"]
                    artist_url = artist["url"]

                    artist_thumbnail = await get_artist_image(artist_name)

                    async def get_scrobbles(lastfm_user):
                        nonlocal lastfm_scrobbles, artist_url

                        async with session.get(LASTFM_API_URL + f"?method=artist.getInfo&artist={artist_name}&username={lastfm_user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                            data = await response.json()

                            userplaycount = "0"

                            if "userplaycount" in data["artist"]["stats"]:
                                userplaycount = data["artist"]["stats"]["userplaycount"]

                            lastfm_scrobbles.append((await ctx.guild.get_member(lastfm_user.user_id), lastfm_user, userplaycount))

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

            embed = femcord.Embed(title="Użytkownicy którzy znają " + artist_name + ":", url=artist_url, description=description, color=self.bot.embed_color, timestamp=datetime.datetime.now())
            embed.set_thumbnail(url=artist_thumbnail)

            await ctx.reply(embed=embed)

    @commands.command(description="Użytkownicy którzy znają utwór", usage="[nazwa]", aliases=["wt", "wkt", "whoknowst"])
    async def whoknowstrack(self, ctx: commands.Context, *, user_or_track: Union[types.User, str] = None):
        lastfm_users = await LastFM.all()

        user = ctx.author

        if isinstance(user_or_track, types.User):
            user = user_or_track

        if not user.id in [lastfm_user.user_id for lastfm_user in lastfm_users]:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == user.id][0]
        lastfm_scrobbles = []

        async with femcord.Typing(ctx.message):
            async with ClientSession() as session:
                if isinstance(user_or_track, types.User) or user_or_track is None:
                    async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&username={lastfm_user.username}&limit=1&extended=1&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()

                        track = data["recenttracks"]["track"][0]
                        track_name = track["name"]

                        artist_name = track["artist"]["name"]
                elif isinstance(user_or_track, str):
                    async with session.get(LASTFM_API_URL + f"?method=track.search&track={user_or_track}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()

                        if not len(data["results"]["trackmatches"]["track"]):
                            return await ctx.reply("Nie znaleziono utworu")

                        track = data["results"]["trackmatches"]["track"][0]
                        track_name = track["name"]

                        artist_name = track["artist"]

                track_url = f"https://last.fm/music/{quote_plus(artist_name)}/_/{quote_plus(track_name)}"
                artist_thumbnail = await get_artist_image(artist_name)

                async def get_scrobbles(lastfm_user: LastFM):
                    nonlocal lastfm_scrobbles, artist_name, track_name

                    async with session.get(LASTFM_API_URL + f"?method=track.getInfo&track={quote_plus(track_name)}&artist={quote_plus(artist_name)}&autocorrect=1&username={lastfm_user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()

                        userplaycount = "0"

                        if "track" in data and "userplaycount" in data["track"]:
                            userplaycount = data["track"]["userplaycount"]

                        lastfm_scrobbles.append((await ctx.guild.get_member(lastfm_user.user_id), lastfm_user, userplaycount))

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

        embed = femcord.Embed(title="Użytkownicy którzy znają " + track_name + " przez " + artist_name + ":", url=track_url, description=description, color=self.bot.embed_color, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=artist_thumbnail)

        await ctx.reply(embed=embed)

    @commands.command(description="Pokazuje tekst piosenki", usage="[nazwa]")
    async def lyrics(self, ctx: commands.Context, *, name = None):
        async with femcord.Typing(ctx.message):
            artist = ""

            async with ClientSession() as session:
                if name == r"%radio":
                    async with session.get("https://radio.poligon.lgbt/api/live/nowplaying/station_1") as response:
                        data = await response.json()
                        track = data["now_playing"]["song"]

                        name = track["title"]
                        artist = track["artist"]

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
                            name = tracks[0]["name"]
                            artist = tracks[0]["artist"]["#text"]

                if name is None:
                    return await ctx.reply("Nie podałeś nazwy")

                lyrics: Lyrics = await get_track_lyrics(artist, name, self.bot.user_agent)

                if lyrics is None:
                    return await ctx.reply("Nie ma tekstu dla tej piosenki")

                lyrics = f"# SOURCE: {lyrics.source}\n" \
                         f"# ARTIST NAME: {lyrics.artist}\n" \
                         f"# TRACK NAME: {lyrics.title}\n\n" \
                       + lyrics.lyrics

        await self.bot.paginator(ctx.reply, ctx, lyrics, prefix="```md\n", suffix="```", buttons=True)

def setup(bot):
    bot.load_cog(Music(bot))