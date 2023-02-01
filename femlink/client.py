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

import asyncio, aiohttp, json
from .models import *
from typing import List

class Player:
    def __init__(self, client: "Client", guild_id: str):
        self.client = client
        self.guild_id = guild_id
        self.track: Track = None
        self.queue: List[Track] = []
        self.position: int = 0
        self.paused: bool = False
        self.volume: int = 100
        self.loop: bool = False
        self.filters: dict = {}

    def play(self, track: Track):
        self.track = track
        return self.client.send("play", guildId=self.guild_id, track=track.encoded)

    def add(self, track: Track):
        self.queue.append(track)

    def skip(self):
        if len(self.queue) > 0:
            return self.play(self.queue.pop(0))

        return self.stop()

    def stop(self):
        self.track = None
        return self.client.send("stop", guildId=self.guild_id)

    def pause(self):
        self.paused = True
        return self.client.send("pause", guildId=self.guild_id, pause=self.paused)

    def resume(self):
        self.paused = False
        return self.client.send("pause", guildId=self.guild_id, pause=self.paused)

    def seek(self, position: int):
        return self.client.send("seek", guildId=self.guild_id, position=position)

    def set_volume(self, volume: int):
        if volume < 0 or volume > 1000:
            raise ValueError("Volume must be between 0 and 1000")

        self.volume = volume

        return self.client.send("volume", guildId=self.guild_id, volume=volume)

    def set_loop(self, loop: bool):
        self.loop = loop

    def set_filters(self, **filters):
        self.filters = filters
        return self.client.send("filters", guildId=self.guild_id, **filters)

class Client:
    async def __new__(cls, *args):
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, user_id: str, host: str, port: int, password: str):
        self.user_id = user_id
        self.host = host
        self.port = port
        self.password = password
        self.session_id = None
        self._voice_state = {}
        self.players: List[Player] = []

        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)

        self.headers = {
            "Authorization": password,
            "User-Id": user_id,
            "Client-Name": "cenzura/1.0"
        }

        self.ws = await self.session.ws_connect("ws://%s:%d/v3/websocket" % (host, port), headers=self.headers)

        self.receiver_task = self.loop.create_task(self.data_receiver())

    def send(self, op: str, **kwargs):
        return self.ws.send_json({"op": op, **kwargs})

    def get_player(self, guild_id: str) -> Player:
        for player in self.players:
            if player.guild_id == guild_id:
                return player

    async def data_receiver(self):
        async for message in self.ws:
            if message.type in (aiohttp.WSMsgType.error, aiohttp.WSMsgType.closed):
                break

            if message.type is aiohttp.WSMsgType.text:
                data = json.loads(message.data)

                if data["op"] == "ready":
                    self.session_id = data["sessionId"]

                elif data["op"] == "playerUpdate":
                    player = self.get_player(data["guildId"])
                    player.position = data["state"]["position"]

                elif data["op"] == "event":
                    player = self.get_player(data["guildId"])

                    if data["type"] in ("TrackEndEvent", "TrackExceptionEvent"):
                        if player.loop is True:
                            await player.play(player.track)
                            continue

                        if data["reason"] in ("FINISHED", "LOAD_FAILED"):
                            player.track = None
                            await player.skip()

                    elif data["type"] == "TrackStuckEvent":
                        await player.play(player.track)
                        await player.seek(player.position)

        self.ws = await self.session.ws_connect("ws://%s:%d/v3/websocket" % (self.host, self.port), headers=self.headers)

        self.receiver_task = self.loop.create_task(self.data_receiver())

    async def voice_server_update(self, data):
        self._voice_state.update({"event": data})

        self.players.append(Player(self, data["guild_id"]))

        await self.voice_update()

    async def voice_state_update(self, data):
        if data["user_id"] != self.user_id:
            return

        if data["channel_id"] is None:
            self._voice_state.clear()
            del self.players[self.get_player(data["guild_id"])]
            return

        if data["session_id"] == self._voice_state.get("sessionId"):
            return

        self._voice_state.update({"sessionId": data["session_id"]})

        await self.voice_update()

    async def voice_update(self):
        if "sessionId" in self._voice_state and "event" in self._voice_state:
            await self.send("voiceUpdate", guildId=self._voice_state["event"]["guild_id"], sessionId=self._voice_state["sessionId"], event=self._voice_state["event"])

    async def get_tracks(self, identifier: str) -> List[Track]:
        async with self.session.get("http://%s:%d/v3/loadtracks?identifier=%s" % (self.host, self.port, identifier), headers=self.headers) as response:
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