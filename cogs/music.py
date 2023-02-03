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
from models import LastFM
from config import *
from typing import Union
from lastfm import exceptions
import hashlib, datetime, asyncio, femlink, re, os

soundcloud_pattern = re.compile(r"(https?:\/\/)?(www.)?(m\.)?soundcloud\.com/.+/.+")

class Music(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot
        self.client: femlink.Client = None
        self.templates = {}
        self.milestones = [50, 100, 250, 420, 500, 1000, 1337, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000]

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    async def on_load(self):
        if self.bot.gateway is not None:
            self.client = await femlink.Client(self.bot.gateway.bot_user.id, "127.0.0.1", 6968, "Dupa123@")

            await asyncio.sleep(1)
            await self.connect("704439884340920441", "853657308152070144", mute=True, deaf=True)

            player: femlink.Player = self.client.get_player("704439884340920441")

            while player is None:
                player = self.client.get_player("704439884340920441")
                await asyncio.sleep(0.5)

            tracks = await self.client.get_tracks("https://radio.poligon.lgbt/listen/station_1/radio.mp3")

            await player.play(tracks[0])

            print("joined poligon and started playing radio")

            self.lastfm_users = {
                user.user_id: user for user in (await LastFM.all())
            }

    def connect(self, guild, channel = None, *, mute = False, deaf = False):
        return self.bot.gateway.ws.send(femcord.enums.Opcodes.VOICE_STATE_UPDATE, {
            "guild_id": guild.id if isinstance(guild, types.Guild) else guild,
            "channel_id": channel.id if isinstance(channel, types.Channel) else channel,
            "self_mute": mute,
            "self_deaf": deaf
        })

    def sign(self, method, token):
        string = "api_key" + LASTFM_API_KEY + "method" + method + "token" + token + LASTFM_API_SECRET
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    @commands.Listener
    async def on_ready(self):
        await self.on_load()

    @commands.Listener
    async def on_voice_server_update(self, data):
        await self.client.voice_server_update(data)

    @commands.Listener
    async def on_raw_voice_state_update(self, data):
        await self.client.voice_state_update(data)

    @commands.command(description="Łączy z kanałem głosowym", usage="join [wyciszony_mikrofon] [wyciszone_słuchawki]")
    async def join(self, ctx: commands.Context, mute: int = 0, deaf: int = 0):
        channel = ctx.member.voice_state.channel

        if channel is None:
            return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

        await self.connect(ctx.guild, channel, mute=bool(mute), deaf=bool(deaf))

        await ctx.reply("Dołączyłem na kanał głosowy")

    @commands.command(description="Rozłącza z kanału głosowego")
    async def leave(self, ctx: commands.Context):
        await self.connect(ctx.guild, None)

        await ctx.reply("Wyszedłem z kanału głosowego")

    @commands.command(description="Odtwarza muzykę", usage="play [tytuł]")
    async def play(self, ctx: commands.Context, *, query):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

            await self.join(ctx)

            for _ in range(5):
                player = self.client.get_player(ctx.guild.id)
                await asyncio.sleep(0.5)

        if query == r"%radio":
            query = "https://radio.poligon.lgbt/listen/station_1/radio.mp3"

        elif not soundcloud_pattern.match(query):
            query = "scsearch:" + query

        tracks = await self.client.get_tracks(query)

        if tracks is None:
            return await ctx.reply("Nie znaleziono żadnych utworów")

        track: femlink.Track = tracks[0]

        if player.track is None:
            await player.play(track)
            return await ctx.reply("Zaczynam grać `" + track.info.title + " - " + track.info.artist + "`")

        player.add(track)
        await ctx.reply("Dodano do kolejki `" + track.info.title + " - " + track.info.artist + "`")

    @commands.command(description="Pomija utwór")
    async def skip(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.skip()
        await ctx.reply("Pominięto utwór")

    @commands.command(description="Zatrzymuje odtwarzanie")
    async def stop(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.stop()
        await ctx.reply("Zatrzymałem odtwarzanie")

    @commands.command(description="Pauzuje odtwarzanie")
    async def pause(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.pause()
        await ctx.reply("Pauzuje odtwarzanie")

    @commands.command(description="Wznawia odtwarzanie")
    async def resume(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.resume()
        await ctx.reply("Wznawiam odtwarzanie")

    @commands.command(description="Zmienia głośność", usage="volume [głośność]")
    async def volume(self, ctx, volume: float):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if volume < 0 or volume > 1000:
            return await ctx.reply("Głośność musi być pomiędzy 0 a 1000")

        await player.set_volume(volume)

        await ctx.reply(f"Ustawiono głośność na {volume:.1f}%")

    @commands.command()
    async def bassboost(self, ctx: commands.Context):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.filters.get("equalizer"):
            await player.set_filters(equalizer=None)
            return await ctx.reply("Wyłączyłem bassboost")

        await player.set_filters(equalizer=[{"band": 0, "gain": 0.15}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.0}, {"band": 3, "gain": 0.0}, {"band": 4, "gain": 0.0}, {"band": 5, "gain": 0.0}, {"band": 6, "gain": 0.0}, {"band": 7, "gain": 0.0}, {"band": 8, "gain": 0.0}, {"band": 9, "gain": 0.0}, {"band": 10, "gain": 0.0}, {"band": 11, "gain": 0.0}, {"band": 12, "gain": 0.0}, {"band": 13, "gain": 0.0}, {"band": 14, "gain": 0.0}])
        await ctx.reply("Włączyłem bassboost")

    @commands.command(description="Włącza/wyłącza pętlę utworu")
    async def loop(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        player.set_loop(not player.loop)
        await ctx.reply("Włączono pętlę" if player.loop is True else "Wyłączono pętlę")

    @commands.command(description="Pokazuje kolejkę utworów")
    async def queue(self, ctx: commands.Context):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if not player.queue:
            return await ctx.reply("Kolejka jest pusta")

        await ctx.reply("\n".join([f"`{track.info.artist} - {track.info.title} `" for track in player.queue]))

    @commands.command(description="Pokazuje informacje o odtwarzanym utworze", aliases=["np"])
    async def nowplaying(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)
        get_time = lambda position, duration: f"{(position % 3600) // 60}:{position % 60:02d}/{(duration % 3600) // 60}:{duration % 60:02d}"

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.track is None:
            return await ctx.reply("Nie gram żadnego utworu")

        elif player.track.info.title == "radio poligon":
            async with ClientSession() as session:
                async with session.get("https://radio.poligon.lgbt/api/nowplaying/1") as response:
                    data = await response.json()

                    return await ctx.reply(f"Gram teraz `{data['now_playing']['song']['text']}` {get_time(data['now_playing']['elapsed'], data['now_playing']['duration'])}")

        await ctx.reply(f"Gram teraz `{player.track.info.artist} - {player.track.info.title}` {get_time(int(player.position / 1000), int(player.track.info.length / 1000))}")

    @commands.command(description="Łączenie konta LastFM do bota")
    async def login(self, ctx: commands.Context):
        async with Client(LASTFM_API_KEY, LASTFM_API_SECRET) as client:
            token = await client.get_token()

            try:
                message = await ctx.author.send(f"Aby połączyć konto LastFM z botem musisz wejść w poniższy link\n<https://www.last.fm/api/auth?api_key={LASTFM_API_KEY}&token={token}>")
            except HTTPException:
                return await ctx.reply("Bot nie może wysłać ci wiadomości prywatnej")

            await ctx.reply("Wiadomość z linkiem została wysłana w wiadomości prywatnej")

            for attempt in range(3):
                await asyncio.sleep(20)

                try:
                    session = await client.get_session(token)
                except (exceptions.UnauthorizedToken, exceptions.InvalidApiKey):
                    if attempt == 8:
                        return await message.edit("Logowanie się nie powiodło... link się przedawnił lub coś poszło nie tak")

                    continue

                user: LastFM = self.lastfm_users.get(ctx.author.id)

                if user is None:
                    user = LastFM(user_id=ctx.author.id, username=session["name"], token=session["key"], script=self.templates["embedmini"])
                else:
                    user.username = session["name"]
                    user.token = session["key"]

                await user.save()

                self.lastfm_users[ctx.author.id] = user

                return await message.edit("Pomyślnie połączono konto `" + session["name"] + "`")

    @commands.command(description="Informacje o artyście", aliases=["ai", "artist"])
    async def artistinfo(self, ctx: commands.Context, *, artist_name: str):
        lastfm = self.lastfm_users.get(ctx.author.id)

        if lastfm is None:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

        async with Client(LASTFM_API_KEY) as client:
            try:
                artist = await client.artist_info(artist_name, lastfm.username)
            except exceptions.NotFound:
                return await ctx.reply("Nie znaleziono takiego artysty")

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

        lastfm = self.lastfm_users.get(user.id)

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with Client(LASTFM_API_KEY) as client:
            try:
                recent_tracks = await client.recent_tracks(lastfm.username, limit=1)
            except exceptions.NotFound:
                return await ctx.reply("Nie znaleziono takiego użytkownika")

            track = recent_tracks.tracks[0]

            track_info = await client.track_info(track.artist.name, track.title, lastfm.username)
            track_info.image = track.image

            embed = femcord.Embed(title=f"Informacje o utworze", url=track_info.url, color=self.bot.embed_color)
            embed.add_field(name="Wykonawca", value=track_info.artist.name, inline=True)
            embed.add_field(name="Nazwa utworu", value=track_info.title, inline=True)
            embed.add_blank_field()
            embed.add_field(name="Gatunki", value="\n".join(["- " + genere.name.title() for genere in track_info.tags]))

            embed.set_thumbnail(url=track_info.image[-1].url)

            await ctx.reply(embed=embed)

    @commands.command(description="Informacje o użytkowniku LastFM", usage="[użytkownik]", aliases=["fui"])
    async def fmuserinfo(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        async with femcord.Typing(ctx.message):
            result = await run(
                lastfm.uiscript,
                modules = await get_modules(self.bot, ctx.guild, ctx=ctx, user=user),
                builtins = builtins,
                variables = convert(user=user)
            )

            if isinstance(result, femcord.Embed):
                return await ctx.reply(embed=result)

            await ctx.reply(result)

    @commands.command(description="Statystyki konta LastFM", usage="[użytkownik]", aliases=["fmstats", "fm"])
    async def lastfm(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

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
        lastfm_user = self.lastfm_users.get(ctx.author.id)

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

        lastfm_user.script = script

        await lastfm_user.save()
        await ctx.reply("Skrypt został ustawiony")

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": femcord.Embed(description="\nSzablony: `embedfull`, `embedsmall`, `embedmini`, `textfull`, `textmini`")})
    async def fmtemplate(self, ctx: commands.Context, template):
        if not template in self.templates:
            return await ctx.reply("Nie ma takiego szablonu")

        await self.fmscript(ctx, script=self.templates[template])

    @commands.command(description="Tempo do ilości scrobbli", usage="[użytkownik]", aliases=["pc"])
    async def pace(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

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
    async def whoknows(self, ctx: commands.Context, *, user_or_track: Union[types.User, str] = None):
        lastfm_users = self.lastfm_users.values()

        user = ctx.author

        if isinstance(user_or_track, types.User):
            user = user_or_track

        if not user.id in self.lastfm_users.keys():
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == user.id][0]
        lastfm_scrobbles = []

        async with femcord.Typing(ctx.message):
            async with Client(LASTFM_API_KEY) as client:
                if isinstance(user_or_track, str):
                    try:
                        artist = await client.artist_info(user_or_track, lastfm_user.username)
                    except exceptions.NotFound:
                        return await ctx.reply("Nie znaleziono artysty")
                else:
                    tracks = await client.recent_tracks(lastfm_user.username)
                    artist = tracks.tracks[0].artist

                artist_name = artist.name
                artist_url = artist.url

                artist_thumbnail = await get_artist_image(artist_name)

                async def get_scrobbles(lastfm_user):
                    nonlocal lastfm_scrobbles, artist_url
                    artist_info = await client.artist_info(artist_name, lastfm_user.username)

                    userplaycount = "0"

                    if artist_info.stats.userplaycount is not None:
                        userplaycount = artist_info.stats.userplaycount

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

                description += f"{index} [{member.user.username}](https://www.last.fm/user/{lastfm_user.username}/library/{artist_url[20:]}) - **{scrobbles}** odtworzeń\n"

            embed = femcord.Embed(title="Użytkownicy którzy znają " + artist_name + ":", url=artist_url, description=description or f"Nikt nie zna **{artist_name}**", color=self.bot.embed_color, timestamp=datetime.datetime.now())
            embed.set_thumbnail(url=artist_thumbnail)

            await ctx.reply(embed=embed)

    @commands.command(description="Użytkownicy którzy znają utwór", usage="[nazwa]", aliases=["wt", "wkt", "whoknowst"])
    async def whoknowstrack(self, ctx: commands.Context, *, user_or_track: Union[types.User, str] = None):
        lastfm_users = self.lastfm_users.values()

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
            async with Client(LASTFM_API_KEY) as client:
                if isinstance(user_or_track, str):
                    try:
                        tracks = await client.track_search(user_or_track)
                    except exceptions.NotFound:
                        return await ctx.reply("Nie znaleziono utworu")

                else:
                    recent_tracks = await client.recent_tracks(lastfm_user.username)
                    tracks = recent_tracks.tracks

                artist_name = tracks[0].artist.name
                track_name = tracks[0].title
                track_url = tracks[0].url

                artist_thumbnail = await get_artist_image(artist_name)

                async def get_scrobbles(lastfm_user: LastFM):
                    nonlocal lastfm_scrobbles, artist_name, track_name

                    track = await client.track_info(artist_name, track_name, lastfm_user.username)

                    userplaycount = "0"

                    if track.scrobbles is not None:
                        userplaycount = track.scrobbles

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

            description += f"{index} [{member.user.username}](https://www.last.fm/user/{lastfm_user.username}/library/{track_url[20:]}) - **{scrobbles}** odtworzeń\n"

        embed = femcord.Embed(title="Użytkownicy którzy znają " + track_name + " przez " + artist_name + ":", url=track_url, description=description or f"Nikt nie zna {track_name} przez **{artist_name}**", color=self.bot.embed_color, timestamp=datetime.datetime.now())
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
                    lastfm = self.lastfm_users.get(ctx.author.id)

                    if lastfm is None:
                        return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

                    async with Client(LASTFM_API_KEY, session=session) as client:
                        recent_tracks = await client.recent_tracks(lastfm.username, limit=1)

                        if not recent_tracks.tracks:
                            return await ctx.reply("Nie ma żadnych utworów")

                        if len(recent_tracks.tracks) == 2:
                            name = recent_tracks.tracks[0].title
                            artist = recent_tracks.tracks[0].artist.name

                if name is None:
                    return await ctx.reply("Nie podałeś nazwy")

                lyrics: Lyrics = await get_track_lyrics(artist, name, session)

                if lyrics is None:
                    return await ctx.reply("Nie ma tekstu dla tej piosenki")

                lyrics = f"# SOURCE: {lyrics.source}\n" \
                         f"# ARTIST NAME: {lyrics.artist}\n" \
                         f"# TRACK NAME: {lyrics.title}\n\n" \
                       + lyrics.lyrics

        await self.bot.paginator(ctx.reply, ctx, lyrics, prefix="```md\n", suffix="```", buttons=True)

def setup(bot):
    bot.load_cog(Music(bot))