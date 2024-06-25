"""
Copyright 2022-2024 PoligonTeam

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
from femcord.femcord import commands, types, HTTPException
from femscript import Femscript
from utils import *
from aiohttp import ClientSession
from models import LastFM
from config import *
from typing import Union
from azuracast import NowPlaying
from lastfm import exceptions
import hashlib, datetime, asyncio, femlink, re, os

soundcloud_pattern = re.compile(r"(https?:\/\/)?(www.)?(m\.)?soundcloud\.com/.+/.+")

class Music(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client: femlink.Client = None
        self.templates = {}
        self.milestones = [50, 100, 250, 420, 500, 1000, 1337, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000]

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    def connect(self, guild, channel = None, *, mute = False, deaf = False) -> None:
        return self.bot.gateway.ws.send(femcord.enums.Opcodes.VOICE_STATE_UPDATE, {
            "guild_id": guild.id if isinstance(guild, types.Guild) else guild,
            "channel_id": channel.id if isinstance(channel, types.Channel) else channel,
            "self_mute": mute,
            "self_deaf": deaf
        })

    def sign(self, method, token) -> str:
        string = "api_key" + LASTFM_API_KEY + "method" + method + "token" + token + LASTFM_API_SECRET
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    def progress_bar(self, progress: int, length: int) -> str:
        return "[" + "=" * int(progress / length * 20) + "-" * (20 - int(progress / length * 20)) + "] " + \
               f"{(progress % 3600) // 60}:{progress % 60:02d}/{(length % 3600) // 60}:{length % 60:02d}"

    @commands.Listener
    async def on_ready(self) -> None:
        self.client = await femlink.Client(self.bot.gateway.bot_user.id, LAVALINK_IP, LAVALINK_PORT, LAVALINK_PASSWORD)
        print("created lavalink client")

        self.lastfm_users = {
            user.user_id: user for user in (await LastFM.all())
        }

    @commands.Listener
    async def on_voice_server_update(self, data: dict) -> None:
        await self.client.voice_server_update(data)

    @commands.Listener
    async def on_raw_voice_state_update(self, data) -> None:
        await self.client.voice_state_update(data)

    @commands.command(description="Łączy z kanałem głosowym", usage="[wyciszony_mikrofon] [wyciszone_słuchawki]")
    async def join(self, ctx: commands.Context, mute: int = 0, deaf: int = 0) -> None:
        channel = ctx.member.voice_state.channel

        if channel is None:
            return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

        await self.connect(ctx.guild, channel, mute=bool(mute), deaf=bool(deaf))

        await ctx.reply("Dołączyłem na kanał głosowy")

    @commands.command(description="Rozłącza z kanału głosowego")
    async def leave(self, ctx: commands.Context) -> None:
        await self.connect(ctx.guild, None)

        await ctx.reply("Wyszedłem z kanału głosowego")

    @commands.command(description="Odtwarza muzykę", usage="(tytuł)")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        player = self.client.get_player(ctx.guild.id)

        if player is None:
            if ctx.member.voice_state.channel is None:
                return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

            await self.join(ctx)

            for _ in range(5):
                player = self.client.get_player(ctx.guild.id)
                await asyncio.sleep(0.5)

        if query == r"%radio":
            query = "https://radio.poligon.lgbt/listen/station_1/radio.mp3"
        elif ctx.author.id in self.bot.owners or ctx.guild.id == "704439884340920441":
            pass
        elif not soundcloud_pattern.match(query):
            query = "scsearch:" + query

        tracks = await self.client.get_tracks(query)

        if not tracks:
            return await ctx.reply("Nie znaleziono żadnych utworów")

        track: femlink.Track = tracks[0]

        if player.track is None:
            await player.play(track)
            return await ctx.reply("Zaczynam grać `" + track.info.title + " - " + track.info.artist + "`")

        player.add(track)
        await ctx.reply("Dodano do kolejki `" + track.info.title + " - " + track.info.artist + "`")

    @commands.command(description="Skips a track")
    async def skip(self, ctx: commands.Context) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.skip()
        await ctx.reply("Skipped")

    @commands.command(description="Stops playback")
    async def stop(self, ctx: commands.Context) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        await player.stop()
        await ctx.reply("Stopped playback")

    @commands.command(description="Pauses playback")
    async def pause(self, ctx):
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("No audio playing")

        await player.pause()
        await ctx.reply("Paused playback")

    @commands.command(description="Resumes playback")
    async def resume(self, ctx) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None or player.track is None:
            return await ctx.reply("No audio playing")

        await player.resume()
        await ctx.reply("Resumed playback")

    @commands.command(description="Changes volume of audio", usage="[głośność]")
    async def volume(self, ctx, volume: float) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if volume < 0 or volume > 1000:
            return await ctx.reply("Głośność musi być pomiędzy 0 a 1000")

        await player.set_volume(volume)

        await ctx.reply(f"Ustawiono głośność na {volume:.1f}%")

    @commands.command(description="Toggles bassboost")
    async def bassboost(self, ctx: commands.Context) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("No audio playing")

        if player.filters.get("equalizer"):
            await player.set_filters(equalizer=None)
            return await ctx.reply("Turned off bassboost")

        await player.set_filters(equalizer=[{"band": 0, "gain": 0.15}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.0}, {"band": 3, "gain": 0.0}, {"band": 4, "gain": 0.0}, {"band": 5, "gain": 0.0}, {"band": 6, "gain": 0.0}, {"band": 7, "gain": 0.0}, {"band": 8, "gain": 0.0}, {"band": 9, "gain": 0.0}, {"band": 10, "gain": 0.0}, {"band": 11, "gain": 0.0}, {"band": 12, "gain": 0.0}, {"band": 13, "gain": 0.0}, {"band": 14, "gain": 0.0}])
        await ctx.reply("Turned on bassboost")

    @commands.command(description="Włącza/wyłącza pętlę utworu")
    async def loop(self, ctx) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        player.set_loop(not player.loop)
        await ctx.reply("Włączono pętlę" if player.loop is True else "Wyłączono pętlę")

    @commands.command(description="Pokazuje kolejkę utworów")
    async def queue(self, ctx: commands.Context) -> None:
        player: femlink.Player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if not player.queue:
            return await ctx.reply("Kolejka jest pusta")

        await ctx.reply("\n".join([f"`{track.info.artist} - {track.info.title} `" for track in player.queue]))

    @commands.command(description="Pokazuje informacje o odtwarzanym utworze", aliases=["np"])
    async def nowplaying(self, ctx: commands.Context) -> None:
        player = self.client.get_player(ctx.guild.id)

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")

        if player.track is None:
            return await ctx.reply("Nie gram żadnego utworu")

        elif player.track.info.title == "radio poligon":
            return await self.nowplayingradio(ctx)

        await ctx.reply(f"Gram teraz `{player.track.info.artist} - {player.track.info.title}`\n {self.progress_bar(player.position // 1000, player.track.info.length // 1000)}")

    @commands.command(description="Pokazuje informacje o odtwarzanym utworze w radiu poligon", aliases=["npr", "radiopoligon", "poligon"])
    async def nowplayingradio(self, ctx: commands.Context) -> None:
        async with ClientSession() as session:
            async with session.get("https://radio.poligon.lgbt/api/nowplaying/1") as response:
                data = await response.json()
                now_playing = NowPlaying.from_dict(data)
                song = now_playing.now_playing

                if now_playing.live.is_live is True:
                    streamer = now_playing.live.streamer_name

                    return await ctx.reply(
                        "Live" + (" by **" + streamer + "**" if streamer is not None else "") + ":\n" +
                        song.song.formatted_text
                    )

                next_song = now_playing.playing_next.song

                await ctx.reply(
                    "Gram teraz:\n" +
                    song.song.formatted_text +
                    (self.progress_bar(song.elapsed, song.duration) + "\n" if now_playing.live.is_live is False else "") +
                    "\nNastępnie:\n" +
                    next_song.formatted_text
                )

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
                except (exceptions.UnauthorizedToken, exceptions.InvalidApiKey, exceptions.InvalidSignature):
                    if attempt == 2:
                        return await message.edit("Logowanie się nie powiodło... link się przedawnił lub coś poszło nie tak")
                    continue

                user = self.lastfm_users.get(ctx.author.id)

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

            embed = femcord.Embed(title="Informacje o " + artist.name, url=artist.url, description=re.sub(r"<a href=\"(.+)\">(.+)</a>", r"[\2](\1)", artist.bio.summary), color=self.bot.embed_color, timestamp=datetime.datetime.now())
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

    # @commands.command(description="Informacje o użytkowniku LastFM", usage="[użytkownik]", aliases=["fui"])
    # async def fmuserinfo(self, ctx: commands.Context, *, user: types.User = None):
    #     user = user or ctx.author

    #     lastfm = self.lastfm_users.get(user.id)

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

    @commands.command(description="lastfm - now playing", usage="[user]", aliases=["fmstats", "fm"])
    async def lastfm(self, ctx: commands.Context, *, user: types.User = None):
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

        if lastfm is None:
            if ctx.author is user:
                return await ctx.reply("You don't have a linked lastfm account, use `login` to link them")

            return await ctx.reply("This user doesn't have a linked lastfm accont")

        async with femcord.Typing(ctx.message):
            async with Client(LASTFM_API_KEY) as client:
                try:
                    tracks = await client.recent_tracks(lastfm.username)
                except exceptions.NotFound:
                    return await ctx.reply(f"Account {lastfm.username} doesn't exist")

                if not tracks.tracks:
                    return await ctx.reply(f"{tracks.username} doesn't have any scrobbles")

                data = {
                    "tracks": [],
                    "user": {
                        "username": tracks.username,
                        "scrobbles": tracks.scrobbles
                    },
                    "nowplaying": False
                }

                if len(tracks.tracks) == 3:
                    data["nowplaying"] = True

                async def append_track(index: int, track: Track) -> None:
                    track_info = await client.track_info(track.artist.name, track.title, lastfm.username)
                    artist_info = await client.artist_info(track.artist.name, lastfm.username)

                    track_data = Track(
                        artist = artist_info,
                        image = track.image,
                        album = track.album,
                        title = track.title,
                        url = track.url,
                        duration = track.duration,
                        streamable = track.streamable,
                        listeners = track_info.listeners,
                        playcount = track_info.playcount,
                        scrobbles = track_info.scrobbles or "0",
                        tags = track_info.tags,
                        date = track.date
                    )

                    data["tracks"].append((index, track_data))

                for index, track in enumerate(tracks.tracks[:2]):
                    self.bot.loop.create_task(append_track(index, track))

                count = 0

                while len(data["tracks"]) < 2:
                    await asyncio.sleep(0.1)

                    count += 1

                    if count > 100:
                        return await ctx.reply("Timed out")

                data["tracks"].sort(key=lambda track: track[0])
                data["tracks"] = [track[1] for track in data["tracks"]]

                converted_data = convert(user=user, tracks=data["tracks"])

                variables = [
                    {
                        "name": "user",
                        "value": Femscript.to_fs(converted_data["user"])
                    },
                    {
                        "name": "lastfm",
                        "value": Femscript.to_fs({
                            "user": data["user"],
                            "nowplaying": data["nowplaying"],
                            "tracks": converted_data["tracks"]
                        })
                    }
                ]

                femscript = Femscript(lastfm.script, variables=variables)

                femscript.wrap_function(request)
                femscript.wrap_function(femcord.Embed)

                result = await femscript.execute(debug=ctx.author.id in self.bot.owners)

                if isinstance(result, femcord.Embed):
                    return await ctx.reply(embed=result)

                await ctx.reply(str(result))

    @commands.command(description="Custom script for lastfm", usage="(script)", aliases=["fms", "fmset"])
    async def fmscript(self, ctx: commands.Context, *, script):
        lastfm_user = self.lastfm_users.get(ctx.author.id)

        if lastfm_user is None:
            return await ctx.reply("You don't have a linked lastfm account, use `login` to link them")

        if re.match(r"get_code(\(\))?;?", script):
            return await self.bot.paginator(ctx.reply, ctx, lastfm_user.script, prefix="```py\n", suffix="```")

        script = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
                 f"# GUILD: {ctx.guild.id}\n" \
                 f"# CHANNEL: {ctx.channel.id}\n" \
                 f"# AUTHOR: {ctx.author.id}\n\n" \
               + script

        lastfm_user.script = script

        await lastfm_user.save()
        await ctx.reply("Script has been saved")

    @commands.command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": femcord.Embed(description="\nSzablony: `embedfull`, `embedsmall`, `embedmini`")})
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

                    account_age = (datetime.datetime.now() - datetime.timedelta(hours=1)) - datetime.datetime.fromtimestamp(int(data["user"]["registered"]["unixtime"]))
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

def setup(bot: commands.Bot) -> None:
    bot.load_cog(Music(bot))
