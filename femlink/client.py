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

import asyncio, aiohttp, json
from typing import Optional, Any
from .models import *
from .enums import *

MISSING: Any = object()

class Player:
    def __init__(self, client: "Client", guild_id: str, user_data: dict = {}) -> None:
        self.client = client
        self.guild_id = guild_id
        self.user_data: dict[str, Any] = user_data
        self.channel_id: str | None = None
        self.track: Track | None = None
        self.queue: list[Track] = []
        self.position: int = 0
        self.paused: bool = False
        self.volume: int = 100
        self.loop: bool = False
        self.filters: dict = {}

    async def play(self, track: Track) -> None:
        self.track = track
        return await self.client.update_player(self.guild_id, encoded_track=track.encoded)

    def add(self, track: Track) -> None:
        self.queue.append(track)

    def add_playlist(self, tracks: list[Track]) -> None:
        for track in tracks:
            self.queue.append(track)

    async def skip(self) -> None:
        await self.on_skip(self)

        if len(self.queue) > 0:
            return await self.play(self.queue.pop(0))

        return await self.stop()

    async def stop(self) -> None:
        await self.client.update_player(self.guild_id, encoded_track=None)
        self.track = None

    async def pause(self) -> None:
        self.paused = True
        await self.client.update_player(self.guild_id, paused=True)

    async def resume(self) -> None:
        self.paused = False
        await self.client.update_player(self.guild_id, paused=False)

    async def seek(self, position: int) -> None:
        if not self.track:
            raise ValueError("No track is currently playing")

        if position < 0:
            raise ValueError("Position must be greater than 0")
        elif position > self.track.info.length:
            raise ValueError("Position must be less than track length")

        self.position = position

        await self.client.update_player(
            self.guild_id,
            position=position,
        )

    async def set_volume(self, volume: int | float) -> None:
        if volume < 0 or volume > 500:
            raise ValueError("Volume must be between 0 and 500")

        self.filters["volume"] = volume / 100.0

        await self.set_filters(**self.filters)

    def set_loop(self, loop: bool) -> None:
        self.loop = loop

    async def set_filters(self, **filters) -> None:
        self.filters = filters
        await self.client.update_player(self.guild_id, filters=filters)

    async def on_skip(self, player: "Player") -> None:
        """This method is called when a track is skipped. Override this method to handle the event."""
        pass

class Client:
    async def __new__(cls, *args) -> "Client":
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, user_id: str, host: str, port: int, password: str, _ssl: bool = False, session_id: Optional[str] = None) -> None:
        self.user_id = user_id
        self.host = host
        self.port = port
        self.password = password
        self._ssl = _ssl
        self.session_id = session_id
        self._voice_state = VoiceState()
        self.players: list[Player] = []

        self.loop = asyncio.get_event_loop()
        self._base_url = "%s://%s:%d" % ("https" if self._ssl else "http", host, port)
        self.session = aiohttp.ClientSession(loop=self.loop)

        self.headers = {
            "Authorization": password,
            "User-Id": user_id,
            "Client-Name": "femlink/1.0"
        }

        if self.session_id is not None:
            self.headers["Session-Id"] = self.session_id

        self.ws = await self.session.ws_connect("%s://%s:%d/v4/websocket" % ("wss" if self._ssl else "ws", host, port), headers=self.headers)

        self.receiver_task = self.loop.create_task(self.data_receiver())

    def get_player(self, guild_id: str) -> Player | None:
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

                    # if data["resumed"] is True:
                    #     for player in await self.get_players():
                    #         self._voice_state.session_id = player["voice"]["sessionId"]
                    #         await self.voice_server_update({
                    #             "guild_id": player["guildId"],
                    #             "token": player["voice"]["token"],
                    #             "endpoint": player["voice"]["endpoint"],
                    #         })

                elif op is Opcodes.PLAYER_UPDATE:
                    player = self.get_player(data["guildId"])

                    if not player:
                        self.players.append(Player(self, data["guildId"]))
                        continue

                    player.position = data["state"]["position"]

                elif op is Opcodes.EVENT:
                    player = self.get_player(data["guildId"])

                    if not player:
                        continue

                    event = Events(data["type"])

                    if event in (Events.TRACK_END, Events.TRACK_EXCEPTION):
                        if player.loop is True:
                            await player.play(player.track)
                            continue

                        if "reason" not in data:
                            print("Received event without reason:", data)

                        if data["reason"] in ("finished", "loadFailed"):
                            player.track = None
                            await player.skip()

                    elif event == Events.TRACK_STUCK:
                        await player.play(player.track)
                        await player.seek(player.position)

        self.ws = await self.session.ws_connect("ws://%s:%d/v4/websocket" % (self.host, self.port), headers=self.headers)
        self.receiver_task = self.loop.create_task(self.data_receiver())

    async def voice_server_update(self, data: dict) -> None:
        self._voice_state.event = VoiceStateEvent(**data)

        self.players.append(Player(self, data["guild_id"]))

        await self.voice_update()

    async def voice_state_update(self, data: dict) -> None:
        if data["user_id"] != self.user_id:
            return

        player = self.get_player(data["guild_id"])

        if data["channel_id"] is None:
            self._voice_state.clear()

            if player:
                await self.destroy_player(data["guild_id"])
                self.players.remove(player)
            return

        if player is not None and player.channel_id != data["channel_id"] and data["channel_id"] is not None:
            player.channel_id = data["channel_id"]

        if data["session_id"] == self._voice_state.session_id:
            return

        self._voice_state.session_id = data["session_id"]

        await self.voice_update()

    async def voice_update(self) -> None:
        if self._voice_state.event is not None:
            await self.update_player(self._voice_state.event.guild_id, voice_state=self._voice_state, no_replace=True)

    async def update_player(
            self,
            guild_id: str,
            identifier: Optional[str] = MISSING,
            encoded_track: Optional[str] = MISSING,
            position: Optional[int] = MISSING,
            end_time: Optional[int] = MISSING,
            volume: Optional[int] = MISSING,
            paused: Optional[bool] = MISSING,
            filters: Optional[dict[str, Any]] = MISSING,
            voice_state: Optional[VoiceState] = MISSING,
            no_replace: bool = MISSING
        ) -> None:
        data = {}
        params = {}

        if encoded_track is not MISSING or identifier is not MISSING:
            track = {}

            if identifier is not MISSING:
                track["identifier"] = identifier
            elif encoded_track is not MISSING:
                track["encoded"] = encoded_track

            if no_replace is not MISSING:
                params["noReplace"] = no_replace

            data["track"] = track

        if position is not MISSING:
            data["position"] = position
        if end_time is not MISSING:
            data["endTime"] = end_time
        if volume is not MISSING:
            data["volume"] = volume
        if paused is not MISSING:
            data["paused"] = paused
        if filters is not MISSING:
            data["filters"] = filters
        if voice_state is not MISSING and voice_state is not None and voice_state.event is not None:
            data["voice"] = {
                "token": voice_state.event.token,
                "endpoint": voice_state.event.endpoint,
                "sessionId": voice_state.session_id,
            }

        async with self.session.patch(f"{self._base_url}/v4/sessions/{self.session_id}/players/{guild_id}", headers=self.headers, json=data, params=params) as response:
            if response.status != 200:
                raise Exception(f"Failed to update player: {response.status} {response.reason}")

    async def destroy_player(self, guild_id: str) -> None:
        async with self.session.delete(f"{self._base_url}/v4/sessions/{self.session_id}/players/{guild_id}", headers=self.headers) as response:
            if response.status != 204:
                raise Exception(f"Failed to destroy player: {response.status} {response.reason}")

        player = self.get_player(guild_id)

        if player is not None:
            self.players.remove(player)

    async def get_tracks(self, identifier: str) -> LoadResult:
        async with self.session.get(f"{self._base_url}/v4/loadtracks?identifier={identifier}", headers=self.headers) as response:
            data = await response.json()
            data["loadType"] = LoadResultType(data["loadType"])
            return data

    async def get_players(self) -> list[dict]:
        async with self.session.get(f"{self._base_url}/v4/sessions/{self.session_id}/players", headers=self.headers) as response:
            if response.status != 200:
                raise Exception(f"Failed to get players: {response.status} {response.reason}")

            return await response.json()

    async def update_session(self, resuming: bool, timeout: int = 60) -> None:
        async with self.session.patch(
            f"{self._base_url}/v4/sessions/{self.session_id}",
            headers=self.headers,
            json={"resuming": resuming, "timeout": timeout}
        ) as response:
            if response.status != 200:
                raise Exception(f"Failed to update session: {response.status} {response.reason}")