from femcord.femcord import commands, types, enums
from typing import TYPE_CHECKING, Awaitable
from aiohttp import ClientSession
from azuracast import NowPlaying
import femlink
import asyncio
import re

from config import CLIENT_ID, LAVALINK_IP, LAVALINK_PORT, LAVALINK_PASSWORD

if TYPE_CHECKING:
    from ..bot import Bot, Context

soundcloud_pattern = re.compile(r"(https?:\/\/)?(www.)?(m\.)?soundcloud\.com/.+/.+")

class Music(commands.Cog):
    client: femlink.Client

    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    async def _on_load(self) -> None:
        await self.connect_to_lavalink()

    def on_load(self) -> None:
        self.bot.loop.create_task(self._on_load())

    async def connect_to_lavalink(self) -> None:
        self.client = await femlink.Client(CLIENT_ID, LAVALINK_IP, LAVALINK_PORT, LAVALINK_PASSWORD, False)
        print("created lavalink client")

    def connect(self, guild, channel = None, *, mute = False, deaf = False) -> Awaitable[None]:
        return self.bot.gateway.ws.send(enums.Opcodes.VOICE_STATE_UPDATE, {
            "guild_id": guild.id if isinstance(guild, types.Guild) else guild,
            "channel_id": channel.id if isinstance(channel, types.Channel) else channel,
            "self_mute": mute,
            "self_deaf": deaf
        })

    def progress_bar(self, progress: int, length: int) -> str:
        return "[" + "=" * int(progress / length * 20) + "-" * (20 - int(progress / length * 20)) + "] " + \
               f"{(progress % 3600) // 60}:{progress % 60:02d}/{(length % 3600) // 60}:{length % 60:02d}"

    async def on_skip(self, player: femlink.Player) -> None:
        guild = self.bot.gateway.get_guild(player.guild_id)

        if guild is None:
            await self.connect(player.guild_id, None)
            await player.client.destroy_player(player.guild_id)
            return

        channel = guild.get_channel(player.channel_id) if player.channel_id is not None else None
        voice_status = ""

        if len(player.queue) > 0:
            track = player.queue[0]
            voice_status = f"{track.info.title} by {track.info.artist}"

        if channel is not None:
            await self.bot.http.set_channel_voice_status(channel.id, voice_status)

        if not voice_status:
            await player.client.destroy_player(player.guild_id)
            await self.connect(player.guild_id, None)

    @commands.Listener
    async def on_voice_server_update(self, data: dict) -> None:
        await self.client.voice_server_update(data)

    @commands.Listener
    async def on_raw_voice_state_update(self, data: dict) -> None:
        await self.client.voice_state_update(data)

    @commands.command(description="Łączy z kanałem głosowym", usage="[wyciszony_mikrofon] [wyciszone_słuchawki]")
    async def join(self, ctx: "Context", mute: int = 0, deaf: int = 0) -> None:
        channel = ctx.member.voice_state.channel

        if channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        await self.connect(ctx.guild, channel, mute=bool(mute), deaf=bool(deaf))

        for _ in range(5):
            player = self.client.get_player(ctx.guild.id)

            if player is not None:
                player.on_skip = self.on_skip
                player.channel_id = channel.id
                break

            await asyncio.sleep(0.5)

        await ctx.reply("Dołączyłem na kanał głosowy")

    @commands.command(description="Rozłącza z kanału głosowego")
    async def leave(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if player is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return

        if player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        await self.connect(ctx.guild, None)
        await ctx.reply("Wyszedłem z kanału głosowego")

    @commands.command(description="Odtwarza muzykę", usage="(tytuł)")
    async def play(self, ctx: "Context", *, query: str) -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None:
            await self.join(ctx)
            player = self.client.get_player(ctx.guild.id)
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        assert player

        if query == r"%radio":
            query = "https://radio.poligon.lgbt/listen/station_1/radio.mp3"
        elif ctx.author.id in self.bot.owners or ctx.guild.id == "704439884340920441":
            pass
        elif not soundcloud_pattern.match(query):
            query = "scsearch:" + query

        result = await self.client.get_tracks(query)

        if result["loadType"] in (femlink.LoadResultType.ERROR, femlink.LoadResultType.EMPTY) or not result["data"]:
            print(result["data"])
            await ctx.reply("Nie znaleziono żadnych utworów")
            return

        tracks: list[femlink.Track] = []

        if result["loadType"] == femlink.LoadResultType.TRACK:
            tracks.append(femlink.Track.from_dict(result["data"]))
        elif result["loadType"] == femlink.LoadResultType.PLAYLIST:
            tracks = [femlink.Track.from_dict(track) for track in result["data"]["tracks"]]
        elif result["loadType"] == femlink.LoadResultType.SEARCH:
            tracks.append([femlink.Track.from_dict(track) for track in result["data"]][0])

        player.add_playlist(tracks)

        if player.track is None:
            track = player.queue[0]
            await player.skip()
            await ctx.reply("Zaczynam grać `" + track.info.title + " - " + track.info.artist + "`")
            return

        await ctx.reply(
            f"Dodano do kolejki `{tracks[0].info.title} - {tracks[0].info.artist}`" if len(tracks) < 2 else f"Dodano {len(tracks)} utworów do kolejki"
        )

    @commands.command(description="Skips a track")
    async def skip(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        await player.skip()
        await ctx.reply("Skipped")

    @commands.command(description="Stops playback")
    async def stop(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None or player.track is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        await player.stop()
        await ctx.reply("Stopped playback")

    @commands.command(description="Pauses playback")
    async def pause(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None or player.track is None:
            await ctx.reply("No audio playing")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        await player.pause()
        await ctx.reply("Paused playback")

    @commands.command(description="Resumes playback")
    async def resume(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None or player.track is None:
            await ctx.reply("No audio playing")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        await player.resume()
        await ctx.reply("Resumed playback")

    @commands.command(description="Changes volume of audio", usage="[głośność]")
    async def volume(self, ctx: "Context", volume: float) -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        if volume < 0 or volume > 500:
            await ctx.reply("Głośność musi być pomiędzy 0 a 1000")
            return

        await player.set_volume(volume)

        await ctx.reply(f"Ustawiono głośność na {volume:.1f}%")

    @commands.command(description="Toggles bassboost")
    async def bassboost(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            await ctx.reply("Nie jesteś na żadnym kanale głosowym")
            return

        if player is None:
            await ctx.reply("No audio playing")
            return
        elif player.channel_id != ctx.member.voice_state.channel.id:
            await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")
            return

        if player.filters.get("equalizer"):
            await player.set_filters(equalizer=[])
            await ctx.reply("Turned off bassboost")
            return

        await player.set_filters(equalizer=[{"band": 0, "gain": 0.15}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.2}, {"band": 3, "gain": 0.2}, {"band": 4, "gain": 0.15}, {"band": 5, "gain": 0.0}, {"band": 6, "gain": 0.0}, {"band": 7, "gain": 0.0}, {"band": 8, "gain": 0.0}, {"band": 9, "gain": 0.0}, {"band": 10, "gain": 0.0}, {"band": 11, "gain": 0.0}, {"band": 12, "gain": 0.0}, {"band": 13, "gain": 0.0}, {"band": 14, "gain": 0.0}])
        await ctx.reply("Turned on bassboost")

    @commands.command(description="Włącza/wyłącza pętlę utworu")
    async def loop(self, ctx) -> None:
        player = self.client.get_player(ctx.guild.id)

        if ctx.member.voice_state.channel is None:
            return await ctx.reply("Nie jesteś na żadnym kanale głosowym")

        if player is None:
            return await ctx.reply("Nie gram na żadnym kanale głosowym")
        elif player.channel_id != ctx.member.voice_state.channel.id:
            return await ctx.reply("Nie jesteś na tym samym kanale głosowym co bot")

        player.set_loop(not player.loop)
        await ctx.reply("Włączono pętlę" if player.loop is True else "Wyłączono pętlę")

    @commands.command(description="Pokazuje kolejkę utworów")
    async def queue(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if player is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return

        if not player.queue:
            await ctx.reply("Kolejka jest pusta")
            return

        await ctx.reply_paginator("\n".join([f"`{track.info.artist} - {track.info.title} `" for track in player.queue]), replace=False)

    @commands.command(description="Pokazuje informacje o odtwarzanym utworze", aliases=["np"])
    async def nowplaying(self, ctx: "Context") -> None:
        player = self.client.get_player(ctx.guild.id)

        if player is None:
            await ctx.reply("Nie gram na żadnym kanale głosowym")
            return

        if player.track is None:
            await ctx.reply("Nie gram żadnego utworu")
            return

        elif player.track.info.title == "radio poligon":
            return await self.nowplayingradio(ctx)

        await ctx.reply(f"Gram teraz `{player.track.info.artist} - {player.track.info.title}`\n {self.progress_bar(player.position // 1000, player.track.info.length // 1000)}")

    @commands.command(description="Pokazuje informacje o odtwarzanym utworze w radiu poligon", aliases=["npr", "radiopoligon", "poligon"])
    async def nowplayingradio(self, ctx: "Context") -> None:
        async with ClientSession() as session:
            async with session.get("https://radio.poligon.lgbt/api/nowplaying/1") as response:
                data = await response.json()
                now_playing = NowPlaying.from_dict(data)
                song = now_playing.now_playing

                if now_playing.live.is_live is True:
                    streamer = now_playing.live.streamer_name

                    await ctx.reply(
                        "Live" + (" by **" + streamer + "**" if streamer is not None else "") + ":\n" +
                        song.song.formatted_text
                    )

                    return

                next_song = now_playing.playing_next.song

                await ctx.reply(
                    "Gram teraz:\n" +
                    song.song.formatted_text +
                    (self.progress_bar(song.elapsed, song.duration) + "\n" if now_playing.live.is_live is False else "") +
                    "\nNastępnie:\n" +
                    next_song.formatted_text
                )

def setup(bot: "Bot") -> None:
    bot.load_cog(Music(bot))