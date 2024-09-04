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

import asyncio, aiohttp, json
from enum import Enum
from .models import *

class Opcodes(Enum):
    READY = "ready"
    PLAY = "play"
    STOP = "stop"
    PAUSE = "pause"
    SEEK = "seek"
    VOLUME = "volume"
    FILTERS = "filters"
    DESTROY = "destroy"
    VOICE_UPDATE = "voiceUpdate"
    PLAYER_UPDATE = "playerUpdate"
    STATS = "stats"
    EVENT = "event"

class Events(Enum):
    TRACK_START = "TrackStartEvent"
    TRACK_END = "TrackEndEvent"
    TRACK_EXCEPTION = "TrackExceptionEvent"
    TRACK_STUCK = "TrackStuckEvent"
    WEBSOCKET_CLOSED = "WebSocketClosedEvent"

class Player:
    def __init__(self, client: "Client", guild_id: str) -> None:
        self.client = client
        self.guild_id = guild_id
        self.track: Track = None
        self.queue: list[Track] = []
        self.position: int = 0
        self.paused: bool = False
        self.volume: int = 100
        self.loop: bool = False
        self.filters: dict = {}

    def play(self, track: Track) -> None:
        self.track = track
        return self.client.send(Opcodes.PLAY, guildId=self.guild_id, track=track.encoded)

    def add(self, track: Track) -> None:
        self.queue.append(track)

    def skip(self) -> None:
        if len(self.queue) > 0:
            return self.play(self.queue.pop(0))

        return self.stop()

    def stop(self) -> None:
        self.track = None
        return self.client.send(Opcodes.STOP, guildId=self.guild_id)

    def pause(self) -> None:
        self.paused = True
        return self.client.send(Opcodes.PAUSE, guildId=self.guild_id, pause=self.paused)

    def resume(self) -> None:
        self.paused = False
        return self.client.send(Opcodes.PAUSE, guildId=self.guild_id, pause=self.paused)

    def seek(self, position: int) -> None:
        if position < 0:
            raise ValueError("Position must be greater than 0")
        elif position > self.track.length:
            raise ValueError("Position must be less than track length")

        self.position = position

        return self.client.send(Opcodes.SEEK, guildId=self.guild_id, position=position)

    def set_volume(self, volume: int) -> None:
        if volume < 0 or volume > 1000:
            raise ValueError("Volume must be between 0 and 1000")

        self.volume = volume

        return self.client.send(Opcodes.VOLUME, guildId=self.guild_id, volume=volume)

    def set_loop(self, loop: bool) -> None:
        self.loop = loop

    def set_filters(self, **filters) -> None:
        self.filters = filters
        return self.client.send(Opcodes.FILTERS, guildId=self.guild_id, **filters)

class Client:
    async def __new__(cls, *args) -> "Client":
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, user_id: str, host: str, port: int, password: str, _ssl: bool = False) -> None:
        self.user_id = user_id
        self.host = host
        self.port = port
        self.password = password
        self._ssl = _ssl
        self.session_id = None
        self._voice_state = VoiceState()
        self.players: list[Player] = []

        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)

        self.headers = {
            "Authorization": password,
            "User-Id": user_id,
            "Client-Name": "femlink/1.0"
        }

        self.ws = await self.session.ws_connect("%s://%s:%d/v3/websocket" % ("wss" if self._ssl else "ws", host, port), headers=self.headers)

        self.receiver_task = self.loop.create_task(self.data_receiver())

    def send(self, op: Opcodes, **kwargs) -> None:
        return self.ws.send_json({"op": op.value, **kwargs})

    def get_player(self, guild_id: str) -> Player:
        for player in self.players:
            if player.guild_id == guild_id:
                return player

    async def data_receiver(self) -> None:
        async for message in self.ws:
            if message.type in (aiohttp.WSMsgType.error, aiohttp.WSMsgType.closed):
                break

            if message.type is aiohttp.WSMsgType.text:
                data = json.loads(message.data)

                op = Opcodes(data["op"])

                if op is Opcodes.READY:
                    self.session_id = data["sessionId"]

                elif op is Opcodes.PLAYER_UPDATE:
                    player = self.get_player(data["guildId"])
                    player.position = data["state"]["position"]

                elif op is Opcodes.EVENT:
                    player = self.get_player(data["guildId"])
                    event = Events(data["type"])

                    if event in (Events.TRACK_END, Events.TRACK_EXCEPTION):
                        if player.loop is True:
                            await player.play(player.track)
                            continue

                        if data["reason"] in ("FINISHED", "LOAD_FAILED"):
                            player.track = None
                            await player.skip()

                    elif event == Events.TRACK_STUCK:
                        await player.play(player.track)
                        await player.seek(player.position)

        self.ws = await self.session.ws_connect("ws://%s:%d/v3/websocket" % (self.host, self.port), headers=self.headers)

        self.receiver_task = self.loop.create_task(self.data_receiver())

    async def voice_server_update(self, data: dict) -> None:
        self._voice_state.event = VoiceStateEvent(**data)

        self.players.append(Player(self, data["guild_id"]))

        await self.voice_update()

    async def voice_state_update(self, data: dict) -> None:
        if data["user_id"] != self.user_id:
            return

        if data["channel_id"] is None:
            self._voice_state.clear()
            player = self.get_player(data["guild_id"])
            if player:
                del self.players[player]
            return

        if data["session_id"] == self._voice_state.session_id:
            return

        self._voice_state.session_id = data["session_id"]

        await self.voice_update()

    async def voice_update(self) -> None:
        if self._voice_state.event is not None:
            await self.send(Opcodes.VOICE_UPDATE, guildId=self._voice_state.event.guild_id, sessionId=self._voice_state.session_id, event=self._voice_state.event.to_dict())

    async def get_tracks(self, identifier: str) -> list[Track]:
        async with self.session.get("%s://%s:%d/v3/loadtracks?identifier=%s" % ("https" if self._ssl else "http", self.host, self.port, identifier), headers=self.headers) as response:
            data = await response.json()
            tracks = []

            for track in data["tracks"]:
                track_info = TrackInfo(
                    identifier = track["info"]["identifier"],
                    is_seekable = track["info"]["isSeekable"],
                    artist = track["info"]["author"],
                    length = track["info"]["length"],
                    is_stream = track["info"]["isStream"],
                    title = track["info"]["title"],
                    source_name = track["info"]["sourceName"],
                    uri = track["info"]["uri"]
                )

                track = Track(
                    encoded = track["encoded"],
                    info = track_info
                )

                tracks.append(track)

            return tracks