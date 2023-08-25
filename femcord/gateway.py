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

import asyncio
from .websocket import WebSocket
from .http import Route, HTTP
from .intents import Intents
from .enums import Opcodes, Intents as IntentsEnum
from .types import Guild, Channel, User, Message, Presence
from . import eventhandlers
from types import CoroutineType
from typing import TypeVar, Callable, Union, List
import sys, traceback, time, copy

Gateway = TypeVar("Gateway")

class Heartbeat:
    def __init__(self, gateway: Gateway, heartbeat_interval: float):
        self.loop = asyncio.get_event_loop()
        self.gateway: Gateway = gateway
        self.heartbeat_interval: float = heartbeat_interval
        self.heartbeat_task: Callable = None
        self.time: float = None

    def send(self):
        return self.gateway.ws.send(Opcodes.HEARTBEAT, self.gateway.sequence_number)

    async def heartbeat_loop(self):
        await self.send()

        while True:
            self.time = time.time()
            await asyncio.sleep(self.heartbeat_interval / 1000)
            await self.send()

    def start(self):
        self.heartbeat_task = self.loop.create_task(self.heartbeat_loop())

    def stop(self):
        self.heartbeat_task.cancel()

class Gateway:
    async def __new__(cls, *args):
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, client):
        client.gateway = self
        self.loop = asyncio.get_event_loop()
        self.http: HTTP = client.http
        self.intents: Intents = client.intents
        self.token: str = client.token
        self.bot: bool = client.bot
        self.ws: "WebSocket" =  None
        self.heartbeat: Heartbeat = None
        self.latency: int = None
        self.last_latencies: List[int] = []
        self.last_latencies_limit: int = client.last_latencies_limit
        self.session_id: str = None
        self.sequence_number: int = None
        self.listeners: List[Callable] = client.listeners
        self.waiting_for: List[Callable] = client.waiting_for

        self.resuming: bool = False
        self.last_sequence_number: int = None

        self.bot_user: User = None

        self.guilds: List[Guild] = []
        self.unavailable_guilds: List[dict] = []
        self.requested_guilds: List[str] = []
        self.users: List[User] = []
        self.request_members: List[str] = []
        self.member_chunks: List[dict] = []

        self.messages_limit: int = client.messages_limit
        self.messages: List[Message] = []

        self.dispatched_ready: bool = False
        self.presence: Presence = None

        self.copied_objects: List[object] = []

        await WebSocket(self, client)

    async def dispatch(self, event: str, *args, **kwargs):
        for listener in self.waiting_for:
            if listener[0] == event:
                if listener[2](*args, **kwargs) is True:
                    try:
                        self.loop.create_task(listener[1](*args, **kwargs))
                    except Exception:
                        traceback.print_exc()

                    return self.waiting_for.remove(listener)

        for listener in self.listeners:
            if listener.__name__ == "on_" + event:
                try:
                    self.loop.create_task(listener(*args, **kwargs))
                except Exception:
                    traceback.print_exc()

    def reset(self):
        self.guilds = []
        self.unavailable_guilds = []
        self.requested_guilds = []
        self.users = []
        self.request_members = []

    async def identify(self):
        self.reset()

        identify_data = {
            "token": self.token,
            "properties": {
                "os": sys.platform,
                "browser": "femcord",
                "device": "femcord"
            }
        }

        if self.bot is True:
            identify_data["intents"] = self.intents.get_int()

        if self.presence is not None:
            identify_data["presence"] = self.presence.to_dict()

        await self.ws.send(Opcodes.IDENTIFY, identify_data)

    async def resume(self):
        await self.ws.send(Opcodes.RESUME, {
            "token": self.token,
            "session_id": self.session_id,
            "seq": self.last_sequence_number
        })

        self.resuming = False
        self.last_sequence_number = None

    async def on_message(self, op: Opcodes, data: dict, sequence_number: int, event_name: str):
        self.sequence_number = sequence_number

        if op is Opcodes.HELLO:
            self.heartbeat = Heartbeat(self, data["heartbeat_interval"])
            self.heartbeat.start()

            if self.resuming is True:
                while (index := len(self.copied_objects)) > 0:
                    del self.copied_objects[index - 1]
                    index -= 1

                await self.dispatch("reconnect")
                return await self.resume()

            await self.identify()

        elif op is Opcodes.INVALID_SESSION:
            while (index := len(self.copied_objects)) > 0:
                del self.copied_objects[index - 1]
                index -= 1

            await asyncio.sleep(5)
            await self.identify()
            await asyncio.sleep(1)
            await self.dispatch("reconnect")

        elif op is Opcodes.HEARTBEAT_ACK:
            if len(self.last_latencies) > self.last_latencies_limit:
                self.last_latencies.pop(0)

            if self.latency is not None:
                self.last_latencies.append(self.latency)

            self.latency = round((time.time() - self.heartbeat.time) * 1000)

        if event_name == "READY":
            self.session_id = data["session_id"]
            self.bot_user = User.from_raw(data["user"])
            self.unavailable_guilds = data["guilds"]

            if self.bot is False:
                self.unavailable_guilds = []
                self.guilds = [Guild.from_raw(guild) for guild in data["guilds"]]

                if not self.dispatched_ready:
                    self.dispatched_ready = True
                    await self.dispatch("ready")

        elif isinstance(event_name, str) and isinstance(data, dict):
            if self.dispatched_ready:
                await self.dispatch("raw_" + event_name.lower(), copied_data := copy.copy(data))
                del copied_data

            if not self.dispatched_ready and event_name == "GUILD_CREATE":
                await eventhandlers.guild_create(self, data)

                if len(self.unavailable_guilds) <= len(self.guilds):
                    self.dispatched_ready = True

                    # for guild in self.guilds[:50]:
                    #     await self.ws.send(Opcodes.REQUEST_GUILD_MEMBERS, {"guild_id": guild.id, "query": "", "limit": 0, "presences": self.intents.has(IntentsEnum.GUILD_PRESENCES)})

                    return await self.dispatch("ready")

            if not self.dispatched_ready:
                return

            parsed_data = getattr(eventhandlers, event_name.lower(), lambda *_: ...)(self, data)

            if isinstance(parsed_data, CoroutineType):
                parsed_data = await parsed_data
            else:
                parsed_data = data,

            if parsed_data == None or parsed_data == (None,):
                parsed_data = ()

            if self.dispatched_ready:
                await self.dispatch(event_name.lower(), *parsed_data)

    async def set_presence(self, presence: Presence):
        self.presence = presence
        await self.ws.send(Opcodes.PRESENCE_UPDATE, self.presence.to_dict())

    def get_guild(self, guild_id: str) -> Guild:
        for guild in self.guilds:
            if guild.id == guild_id:
                return guild

    def get_channel(self, channel_id: str) -> Channel:
        for guild in self.guilds:
            for channel in guild.channels + guild.threads:
                if channel.id == channel_id:
                    return channel

    def get_guild_by_channel_id(self, channel_id: str) -> Guild:
        for guild in self.guilds:
            for channel in guild.channels:
                if channel.id == channel_id:
                    return guild

    async def fetch_user(self, user_id: str) -> dict:
        return await self.http.request(Route("GET", "users", user_id))

    async def get_user(self, user: Union[dict, str]) -> User:
        for cached_user in self.users:
            if isinstance(user, str):
                if user.lower() in (cached_user.username.lower(), cached_user.id):
                    return cached_user
            elif isinstance(user, dict):
                if user["id"] == cached_user.id:
                    return cached_user

        if isinstance(user, str):
            user = await self.fetch_user(user)

        user = User.from_raw(user)
        self.users.append(user)

        return user

    def copy(self, _object, deep: bool = False):
        if deep is True:
            copied_object = copy.deepcopy(_object)
        elif deep is False:
            copied_object = copy.copy(_object)

        self.copied_objects.append(copied_object)

        return copied_object