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
from deezer import DeezerClient
from femcord.femcord import commands, types, HTTPException
from femscript import Femscript # type: ignore
from utils import convert, wrap_builtins, request, get_artist_image, generate_waveform_from_audio_bytes, highlight
from aiohttp import ClientSession
from models import LastFM as LastFMModel
from config import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL, GROQ_API_KEYS
from lastfm import Client, Track, Artist, exceptions
from groq import Groq
from api_client import ApiClient
import hashlib, datetime, asyncio, femlink, re, os

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext

class LastFM(commands.Cog):
    client: femlink.Client

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot
        self.templates = {}
        self.milestones = [50, 100, 250, 420, 500, 1000, 1337, 2500, 5000, 10000, 25000, 50000, 100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000]

        for filename in os.listdir("./cogs/templates/lastfm"):
            with open("./cogs/templates/lastfm/" + filename, "r") as file:
                self.templates[filename.split(".")[0]] = file.read()

    def progress_bar(self, progress: int, length: int) -> str:
        return "[" + "=" * int(progress / length * 20) + "-" * (20 - int(progress / length * 20)) + "] " + \
               f"{(progress % 3600) // 60}:{progress % 60:02d}/{(length % 3600) // 60}:{length % 60:02d}"

    async def _on_load(self) -> None:
        self.lastfm_users = {
            user.user_id: user for user in (await LastFMModel.all())
        }

    def on_load(self) -> None:
        self.bot.loop.create_task(self._on_load())

    def sign(self, method, token) -> str:
        string = "api_key" + LASTFM_API_KEY + "method" + method + "token" + token + LASTFM_API_SECRET
        return hashlib.md5(string.encode("utf-8")).hexdigest()

    @commands.command(description="Łączenie konta LastFM do bota")
    async def login(self, ctx: "Context") -> None:
        async with Client(LASTFM_API_KEY, LASTFM_API_SECRET) as client:
            token = await client.get_token()

            try:
                message = await ctx.author.send(f"Aby połączyć konto LastFM z botem musisz wejść w poniższy link\n<https://www.last.fm/api/auth?api_key={LASTFM_API_KEY}&token={token}>")
            except HTTPException:
                await ctx.reply("Bot nie może wysłać ci wiadomości prywatnej")
                return

            await ctx.reply("Wiadomość z linkiem została wysłana w wiadomości prywatnej")

            for attempt in range(3):
                await asyncio.sleep(20)

                try:
                    session = await client.get_session(token)
                except (exceptions.UnauthorizedToken, exceptions.InvalidApiKey, exceptions.InvalidSignature):
                    if attempt == 2:
                        await message.edit("Logowanie się nie powiodło... link się przedawnił lub coś poszło nie tak")
                        return
                    continue

                user = self.lastfm_users.get(ctx.author.id)

                if user is None:
                    user = LastFMModel(user_id=ctx.author.id, username=session["name"], token=session["key"], script=self.templates["embedmini"])
                else:
                    user.username = session["name"]
                    user.token = session["key"]

                await user.save()

                self.lastfm_users[ctx.author.id] = user

                await message.edit("Pomyślnie połączono konto `" + session["name"] + "`")
                return

    @commands.command(description="Informacje o artyście", aliases=["ai", "artist"])
    async def artistinfo(self, ctx: "Context", *, artist_name: str) -> None:
        lastfm = self.lastfm_users.get(ctx.author.id)

        if lastfm is None:
            await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
            return

        async with Client(LASTFM_API_KEY) as client:
            try:
                artist = await client.artist_info(artist_name, lastfm.username)
            except exceptions.NotFound:
                await ctx.reply("Nie znaleziono takiego artysty")
                return

            embed = femcord.Embed(title="Informacje o " + artist.name, url=artist.url, color=self.bot.embed_color, timestamp=datetime.datetime.now())

            if artist.bio is not None and artist.bio.summary:
                embed.set_description(re.sub(r"<a href=\"(.+)\">(.+)</a>", r"[\2](\1)", artist.bio.summary))

            embed.add_field(name="Liczba słuchaczy", value=artist.stats.listeners, inline=True)
            embed.add_field(name="Liczba odtworzeń", value=artist.stats.playcount, inline=True)
            embed.add_field(name="Liczba twoich odtworzeń", value=artist.stats.userplaycount, inline=True)
            embed.add_field(name="Gatunki", value="\n".join(["- " + genere.name.title() for genere in artist.tags]), inline=False)

            embed.set_thumbnail(url=artist.image[-1].url)
            embed.set_footer(text="hejka tu lenka", icon_url=ctx.author.avatar_url)

            await ctx.reply(embed=embed)

    @commands.hybrid_command(description="Informacje o obecnie grającej piosence", usage="[użytkownik]", aliases=["ti", "track", "trackstats"])
    async def trackinfo(
            self,
            ctx: Union["Context", "AppContext"],
            *,
            user: types.User = None # type: ignore
        ) -> None:
        is_app = isinstance(ctx, commands.AppContext)

        if is_app:
            await ctx.think()

        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)


        if lastfm is None:
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        async with Client(LASTFM_API_KEY) as client:
            try:
                recent_tracks = await client.recent_tracks(lastfm.username, limit=1)
            except exceptions.NotFound:
                await ctx.reply("Nie znaleziono takiego użytkownika")
                return

            track = recent_tracks.tracks[0]

            track_info = await client.track_info(track.artist.name, track.title, lastfm.username)
            track_info.image = track.image
            track_info.duration = track_info.duration
            preview_url = None

            async with DeezerClient() as deezer:
                deezer_search = await deezer.search(track.title + " " + track.artist.name)

                if deezer_search["total"] > 0:
                    deezer_track = await deezer.get_track(deezer_search["data"][0]["id"])

                    if deezer_track["preview"] is not None:
                        preview_url = deezer_track["preview"]
                        track_info.duration = deezer_track["duration"]

            components = femcord.Components()
            container = femcord.Container()

            container.add_component(femcord.MediaGallery().add_item(femcord.MediaItem(media=femcord.UnfurledMediaItem(url=track_info.image[-1].url))))
            container.add_component(femcord.Separator())

            content = f"## {track_info.artist.name} - {track_info.title}\n" + f"**Album:** {track.album.name}\n" + f"**Duration:** {track_info.duration // 60}:{track_info.duration % 60:02d}\n"

            if preview_url is not None:
                content += f"**BPM:** {deezer_track.get('bpm', 'N/A') or 'N/A'}\n" + f"**Release Date:** {deezer_track['release_date']}\n" # type: ignore

            content += f"**Genres:** {', '.join([genre.name.title() for genre in track_info.tags]) if track_info.tags else 'N/A'}\n" + f"**Listeners:** {track_info.listeners}\n" + f"**Global Scrobbles:** {track_info.playcount}\n" + f"**{'Your' if user.id == ctx.author.id else user.username + '\'s'} Scrobbles:** {track_info.scrobbles}"

            container.add_component(femcord.TextDisplay(content=content))
            container.add_component(femcord.Separator())
            action_row = femcord.ActionRow()

            if preview_url is not None:
                button = femcord.Button(
                    label="🎵 Preview",
                    style=femcord.ButtonStyles.PRIMARY,
                    custom_id="preview_button",
                )
                action_row.add_component(button).add_component(femcord.Button(label="🎧 Deezer", url=deezer_track["link"], style=femcord.ButtonStyles.LINK)) # type: ignore

            action_row.add_component(femcord.Button(label="📻 Last.fm", url=track_info.url, style=femcord.ButtonStyles.LINK))
            container.add_component(action_row)

            components.add_component(container)

            message = await ctx.send(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

            if not preview_url:
                return

            obj: commands.AppContext | femcord.types.Message = ctx if is_app else message # type: ignore

            def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
                if is_app:
                    return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id # type: ignore
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id # type: ignore

            try:
                interaction: femcord.types.Interaction
                interaction, = await ctx.bot.wait_for("interaction_create", check=check, timeout=60)
                button["disabled"] = True # type: ignore
                await obj.edit(components=components)
                await interaction.callback(femcord.InteractionCallbackTypes.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)

                async with ClientSession() as session:
                    async with session.get(preview_url) as response:
                        file_data = await response.read()

                waveform, duration = await generate_waveform_from_audio_bytes(file_data)

                await interaction.edit(
                    files = [
                        ("voice_message.mp3", file_data)
                    ],
                    flags = [
                        femcord.MessageFlags.IS_VOICE_MESSAGE
                    ],
                    other = {
                        "attachments": [
                            {
                                "id": 0,
                                "filename": "voice_message.mp3",
                                "duration_secs": duration,
                                "waveform": waveform
                            }
                        ]
                    }
                )
            except TimeoutError:
                button["disabled"] = True # type: ignore
                await obj.edit(components=components)

    # @commands.command(description="Informacje o użytkowniku LastFM", usage="[użytkownik]", aliases=["fui"])
    # async def fmuserinfo(self, ctx: "Context", *, user: types.User = None):
    #     user = user or ctx.author

    #     lastfm = self.lastfm_users.get(user.id)

    #     if lastfm is None:
    #         if ctx.author is user:
    #             return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

    #         return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

    #     async with femcord.Typing(ctx.channel):
    #         result = await run(
    #             lastfm.uiscript,
    #             modules = await get_modules(self.bot, ctx.guild, ctx=ctx, user=user),
    #             builtins = builtins,
    #             variables = convert(user=user)
    #         )

    #         if isinstance(result, femcord.Embed):
    #             return await ctx.reply(embed=result)

    #         await ctx.reply(result)

    @commands.hybrid_command(description="lastfm - now playing", usage="[user]", aliases=["fmstats", "fm"])
    async def lastfm(
            self,
            ctx: Union["Context", "AppContext"],
            *,
            user: types.User = None # type: ignore
        ) -> None:
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

        if lastfm is None:
            if ctx.author is user:
                await ctx.reply("You don't have a linked lastfm account, use `login` to link them")
                return

            await ctx.reply("This user doesn't have a linked lastfm account")
            return

        async with femcord.HybridTyping(ctx):
            async with Client(LASTFM_API_KEY) as client:
                try:
                    tracks = await client.recent_tracks(lastfm.username)
                except exceptions.NotFound:
                    await ctx.reply(f"Account {lastfm.username} doesn't exist")
                    return

                if not tracks.tracks:
                    await ctx.reply(f"{tracks.username} doesn't have any scrobbles")
                    return

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

                def merge(track: Track, track_info: Track, artist_info: Artist) -> Track:
                    merge_artist = "stats", "similar", "tags", "bio"
                    merge_track = "tags", "listeners", "playcount", "scrobbles", "tags", "streamable", "duration", "mbid", "loved", "userloved"

                    for item in merge_artist:
                        setattr(track.artist, item, getattr(artist_info, item))
                    for item in merge_track:
                        setattr(track, item, getattr(track_info, item))

                    return track

                async def append_track(index: int, track: Track) -> None:
                    track_info = await client.track_info(track.artist.name, track.title, lastfm.username)
                    artist_info = await client.artist_info(track.artist.name, lastfm.username)

                    data["tracks"].append((index, merge(track, track_info, artist_info)))

                for index, track in enumerate(tracks.tracks[:2]):
                    self.bot.loop.create_task(append_track(index, track))

                count = 0

                while len(data["tracks"]) < 2:
                    await asyncio.sleep(0.1)

                    count += 1

                    if count > 100:
                        await ctx.reply("Timed out")
                        return

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

                femscript = Femscript(lastfm.script, variables=variables, modules=self.bot.femscript_modules)

                femscript.wrap_function(request)

                wrap_builtins(femscript)

                result = await femscript.execute(debug=ctx.author.id in self.bot.owners)

                if hasattr(femscript, "is_components_v2"):
                    await ctx.reply(components=result, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])
                    return

                if isinstance(result, femcord.Embed):
                    await ctx.reply(embed=result)
                    return

                await ctx.reply(str(result))

    @commands.hybrid_command(description="Custom script for lastfm", usage="(script)", aliases=["fms", "fmset"])
    async def fmscript(self, ctx: Union["Context", "AppContext"], *, script) -> None:
        lastfm_user = self.lastfm_users.get(ctx.author.id)

        if lastfm_user is None:
            await ctx.reply("You don't have a linked lastfm account, use `login` to link them")
            return

        if re.match(r"get_code(\(\))?;?", script):
            await ctx.reply_paginator(highlight(lastfm_user.script), by_lines=True, base_embed=femcord.Embed(), prefix="```ansi\n", suffix="```")
            return

        script = f"# DATE: {datetime.datetime.now().strftime(r'%Y-%m-%d %H:%M:%S')}\n" \
                 f"# AUTHOR: {ctx.author.id}\n\n" \
               + script

        lastfm_user.script = script

        await lastfm_user.save()
        await ctx.reply("Script has been saved")

    @commands.hybrid_command(description="Wybieranie szablonu dla komendy lastfm", usage="(szablon)", aliases=["fmmode"], other={"embed": femcord.Embed(description="\nSzablony: `embedfull`, `embedsmall`, `embedmini`")})
    async def fmtemplate(self, ctx: Union["Context", "AppContext"], template: str) -> None:
        if not template in self.templates:
            await ctx.reply("Nie ma takiego szablonu, dostępne szablony to: " + ", ".join(self.templates.keys()))
            return

        await self.fmscript[0](ctx, script=self.templates[template]) # type: ignore

    @commands.command(description="Tempo do ilości scrobbli", usage="[użytkownik]", aliases=["pc"])
    async def pace(
            self,
            ctx: "Context",
            *,
            user: types.User = None # type: ignore
        ) -> None:
        user = user or ctx.author

        lastfm = self.lastfm_users.get(user.id)

        if lastfm is None:
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        async with femcord.Typing(ctx.channel): # type: ignore
            async with ClientSession() as session:
                async with session.get(LASTFM_API_URL + f"?method=user.getInfo&user={lastfm.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                    data = await response.json()

                    if "error" in data:
                        await ctx.reply("Nie znaleziono użytkownika LastFM")
                        return

                    account_age = (datetime.datetime.now(tz=datetime.timezone.utc)) - datetime.datetime.fromtimestamp(int(data["user"]["registered"]["unixtime"]))
                    scrobbles = int(data["user"]["playcount"])

                    if not scrobbles:
                        await ctx.reply("Ten użytkownik nie ma żadnych scrobbli")
                        return

                    milestone = self.milestones[0]

                    for _milestone in self.milestones:
                        if _milestone > scrobbles:
                            milestone = _milestone
                            break

                    scrobbles_per_day = scrobbles / account_age.days
                    days_to_milestone = (milestone - scrobbles) / scrobbles_per_day
                    pace = datetime.datetime.now() + datetime.timedelta(days=days_to_milestone)

                    await ctx.reply(f"{types.t['D'] @ pace} ({scrobbles_per_day:.2f} scrobbli dziennie | {scrobbles} w {account_age.days} dni)")

    @commands.command(description="Użytkownicy którzy znają artyste", aliases=["wk"])
    async def whoknows(
            self,
            ctx: "Context",
            *,
            user_or_track: types.User | str = None # type: ignore
        ) -> None:
        lastfm_users = self.lastfm_users.values()

        user = ctx.author

        if isinstance(user_or_track, types.User):
            user = user_or_track

        if not user.id in self.lastfm_users.keys():
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == user.id][0]
        lastfm_scrobbles = []

        async with femcord.Typing(ctx.channel): # type: ignore
            async with Client(LASTFM_API_KEY) as client:
                if isinstance(user_or_track, str):
                    try:
                        artist = await client.artist_info(user_or_track, lastfm_user.username)
                    except exceptions.NotFound:
                        await ctx.reply("Nie znaleziono artysty")
                        return
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
    async def whoknowstrack(
            self,
            ctx: "Context",
            *,
            user_or_track: types.User | str = None # type: ignore
        ) -> None:
        lastfm_users = self.lastfm_users.values()

        user = ctx.author

        if isinstance(user_or_track, types.User):
            user = user_or_track

        if not user.id in [lastfm_user.user_id for lastfm_user in lastfm_users]:
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        lastfm_users = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id in [member.user.id for member in ctx.guild.members]]
        lastfm_user = [lastfm_user for lastfm_user in lastfm_users if lastfm_user.user_id == user.id][0]
        lastfm_scrobbles = []

        async with femcord.Typing(ctx.channel): # type: ignore
            async with Client(LASTFM_API_KEY) as client:
                if isinstance(user_or_track, str):
                    try:
                        tracks = await client.track_search(user_or_track)
                    except exceptions.NotFound:
                        await ctx.reply("Nie znaleziono utworu")
                        return

                else:
                    recent_tracks = await client.recent_tracks(lastfm_user.username)
                    tracks = recent_tracks.tracks

                artist_name = tracks[0].artist.name
                track_name = tracks[0].title
                track_url = tracks[0].url

                artist_thumbnail = await get_artist_image(artist_name)

                async def get_scrobbles(lastfm_user: LastFMModel):
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

    @commands.command(description="Najczęściej słuchani artyści", usage="[użytkownik]")
    async def topartists(
            self,
            ctx: "Context",
            *,
            user: types.User = None # type: ignore
        ) -> None:
        user = user or ctx.author

        lastfm_user = self.lastfm_users.get(user.id)

        if lastfm_user is None:
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        async with femcord.Typing(ctx.channel):
            async with Client(LASTFM_API_KEY) as client:
                artists = await client.top_artists(lastfm_user.username, "overall", 100)

                if not artists:
                    await ctx.reply("Ten użytkownik nie słuchał żadnych artystów")
                    return

            pages = []

            for i in range(0, len(artists), 10):
                chunk = artists[i:i + 10]
                page_content = "\n".join([f"{i + index + 1}. {artist.name} - {artist.playcount} scrobbles" for index, artist in enumerate(chunk)])
                pages.append(page_content)

            base_embed = femcord.Embed(title=f"Najczęściej słuchani artyści {user.username}", color=self.bot.embed_color, timestamp=datetime.datetime.now())
            base_embed.set_thumbnail(url=await get_artist_image(artists[0].name))

        await ctx.reply_paginator(pages=pages, base_embed=base_embed)

    @commands.command(description="Najczęściej słuchane utwory", usage="[użytkownik]")
    async def toptracks(
            self,
            ctx: "Context",
            *,
            user: types.User = None # type: ignore
        ) -> None:
        user = user or ctx.author

        lastfm_user = self.lastfm_users.get(user.id)

        if lastfm_user is None:
            if ctx.author is user:
                await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                return

            await ctx.reply("Ta osoba nie ma połączonego konta LastFM")
            return

        async with femcord.Typing(ctx.channel):
            async with Client(LASTFM_API_KEY) as client:
                tracks = await client.top_tracks(lastfm_user.username, "overall", 100)

                if not tracks:
                    await ctx.reply("Ten użytkownik nie słuchał żadnych utworów")
                    return

            pages = []

            for i in range(0, len(tracks), 10):
                chunk = tracks[i:i + 10]
                page_content = "\n".join([f"{i + index + 1}. {track.title} by {track.artist.name} - {track.playcount} scrobbles" for index, track in enumerate(chunk)])
                pages.append(page_content)

            base_embed = femcord.Embed(title=f"Najczęściej słuchane utwory {user.username}", color=self.bot.embed_color, timestamp=datetime.datetime.now())
            base_embed.set_thumbnail(url=await get_artist_image(tracks[0].artist.name))

        await ctx.reply_paginator(pages=pages, base_embed=base_embed)

    @commands.hybrid_command(description="Judges your music taste")
    async def judge(
            self,
            ctx: Union["Context", "AppContext"],
            user: types.User = None # type: ignore
        ) -> None:
        user = user or ctx.author

        lastfm_user = self.lastfm_users.get(user.id)

        if lastfm_user is None:
            if ctx.author is user:
                 await ctx.reply("You don't have a linked lastfm account, use `login` to link them")
                 return

            await ctx.reply("This user doesn't have a linked lastfm account")
            return

        async with femcord.HybridTyping(ctx):
            async with Client(LASTFM_API_KEY) as client:
                artists = await client.top_artists(lastfm_user.username, "7day", 3)

                groq = Groq(GROQ_API_KEYS, "deepseek-r1-distill-llama-70b", "Generate a long-form, sarcastic, and humorous critique of someone's taste in a specific topic (e.g., music, movies, games, or fashion). " \
                    "The tone should be playful, exaggerated, and packed with witty metaphors, absurd comparisons, and creative insults. " \
                    "Avoid simple bullet points or structured lists—write in a flowing, rant-like format that builds on itself, " \
                    "making each point more ridiculous and entertaining than the last. Keep it engaging, fun, and slightly unhinged, " \
                    "while ensuring it remains lighthearted rather than mean-spirited. Maximum 800 characters. You can use some markdown too.")

                result = await groq.chat("\n".join([f"{index}. {artist.name} - rank {artist.rank}" for index, artist in enumerate(artists)]))

                await ctx.reply_paginator(result)

    @commands.hybrid_command(description="Pokazuje tekst piosenki", usage="[nazwa]")
    async def lyrics(self, ctx: Union["Context", "AppContext"], *, name = None) -> None:
        async with femcord.HybridTyping(ctx):
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
                        await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")
                        return

                    async with Client(LASTFM_API_KEY, session=session) as client:
                        recent_tracks = await client.recent_tracks(lastfm.username, limit=1)

                        if not recent_tracks.tracks:
                            await ctx.reply("Nie ma żadnych utworów")
                            return

                        if len(recent_tracks.tracks) == 2:
                            name = recent_tracks.tracks[0].title
                            artist = recent_tracks.tracks[0].artist.name

                if name is None:
                    await ctx.reply("Nie podałeś nazwy")
                    return

            async with ApiClient(self.bot.local_api_base_url) as client:
                lyrics = await client.lyrics(artist + " " + name)

                if lyrics is None or not lyrics["lyrics"]:
                    await ctx.reply("Nie ma tekstu dla tej piosenki")
                    return

            artist_image = await get_artist_image(lyrics["artist"])

        length = []
        x = lambda i: (length.append(len(i)), i)[-1]

        component_list = [
            femcord.Container(
                components = [
                    femcord.Section(
                        components = [
                            femcord.TextDisplay(
                                content = x(f"## Source: `{lyrics["source"]}`")
                            ),
                            femcord.TextDisplay(
                                content = x(f"## Artist name: `{lyrics["artist"]}`")
                            ),
                            femcord.TextDisplay(
                                content = x(f"## Track name: `{lyrics["title"]}`")
                            )
                        ],
                        accessory = femcord.Thumbnail(
                            media = femcord.UnfurledMediaItem(
                                url = artist_image
                            )
                        )
                    )
                ]
            ),
            *(
                femcord.Container(
                    components = [
                        femcord.TextDisplay(
                            content = chunk
                        )
                    ]
                ) for chunk in [lyrics["lyrics"][i:i + 4000] for i in range(0, len(lyrics["lyrics"]), 4000)]
            )
        ]

        #TODO: add paginator for components :3

        components = femcord.Components(
            components = component_list[:2]
        )

        await ctx.reply(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

        #         lyrics = f"# SOURCE: {lyrics.source}\n" \
        #                  f"# ARTIST NAME: {lyrics.artist}\n" \
        #                  f"# TRACK NAME: {lyrics.title}\n\n" \
        #                + lyrics.lyrics

        # await ctx.reply_paginator(lyrics, prefix="```md\n", suffix="```", buttons=True)

    @commands.hybrid_command(description="Shows Spotify playing song")
    async def spotify(self, ctx: Union["Context", "AppContext"]) -> None:
        if not ctx.member.presence.activities:
            await ctx.reply("You are not listening to anything")
            return

        activity = None

        for _activity in ctx.member.presence.activities:
            if _activity.type is femcord.ActivityTypes.LISTENING and _activity.name == "Spotify":
                activity = _activity
                break

        if activity is None:
            await ctx.reply("You are not listening to Spotify")
            return

        components = femcord.Components(
            components = [
                femcord.Container(
                    components = [
                        femcord.Section(
                            components = [
                                femcord.TextDisplay(
                                    content = f"## {activity.details}\n**by {activity.state}**\nAlbum: {activity.assets.large_text}\nDuration: {self.progress_bar(activity.timestamps.start // 1000, activity.timestamps.end // 1000)}"
                                )
                            ],
                            accessory = femcord.Thumbnail(
                                media = femcord.UnfurledMediaItem(
                                    url = activity.assets.large_image.replace("spotify:", "https://i.scdn.co/image/")
                                )
                            )
                        ),
                        femcord.Separator(),
                        femcord.ActionRow(
                            components = [
                                femcord.Button(
                                    label = "Listen on Spotify",
                                    url = f"https://open.spotify.com/track/{activity.sync_id}",
                                    style = femcord.ButtonStyles.LINK
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        await ctx.reply(components=components, flags=[femcord.MessageFlags.IS_COMPONENTS_V2])

def setup(bot: "Bot") -> None:
    bot.load_cog(LastFM(bot))
