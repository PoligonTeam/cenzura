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

import asyncio, sys, traceback
from .websocket import WebSocket
from .http import Route
from .enums import Opcodes
from .types import Guild, User, Presence
from . import eventhandlers
from types import CoroutineType
from typing import Union
import time

class Heartbeat:
    def __init__(self, gateway, heartbeat_interval):
        self.loop = asyncio.get_event_loop()
        self.gateway = gateway
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task = None
        self.time = None

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
        self.http = client.http
        self.intents = client.intents
        self.token = client.token
        self.bot = client.bot
        self.heartbeat: Heartbeat = None
        self.latency = None
        self.last_latencies = []
        self.last_latencies_limit = client.last_latencies_limit
        self.session_id = None
        self.sequence_number = None
        self.listeners = client.listeners
        self.waiting_for = client.waiting_for

        self.resuming = False
        self.last_sequence_number = None

        self.bot_user: User = None

        self.guilds = []
        self.unavailable_guilds = []
        self.requested_guilds = []
        self.users = []
        self.request_members = []

        self.messages_limit = client.messages_limit
        self.messages = []

        self.dispatched_ready = False
        self.presence = None

        await WebSocket(self, client)

    async def dispatch(self, event, *args, **kwargs):
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
                "$os": sys.platform,
                "$browser": "cenzuralib",
                "$device": "cenzuralib"
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

    async def on_message(self, op, data, sequence_number, event_name):
        self.sequence_number = sequence_number

        if op is Opcodes.HELLO:
            self.heartbeat = Heartbeat(self, data["heartbeat_interval"])
            self.heartbeat.start()

            if self.resuming is True:
                return await self.resume()

            await self.identify()

        elif op is Opcodes.INVALID_SESSION:
            await asyncio.sleep(5)
            await self.identify()

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
            if not self.dispatched_ready and event_name == "GUILD_CREATE":
                await eventhandlers.guild_create(self, data)

                if len(self.unavailable_guilds) <= len(self.guilds):
                    self.dispatched_ready = True

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

    def get_guild(self, guild_id):
        for guild in self.guilds:
            if guild.id == guild_id:
                return guild

    async def fetch_user(self, user_id):
        return await self.http.request(Route("GET", "users", user_id))

    async def get_user(self, user: Union[dict, str]):
        for cached_user in self.users:
            if isinstance(user, str):
                if user.lower() == cached_user.username.lower() or user == cached_user.id:
                    return cached_user
            elif isinstance(user, dict):
                if user["id"] == cached_user.id:
                    return cached_user

        if isinstance(user, str):
            user = await self.fetch_user(user)

        user = User.from_raw(user)
        self.users.append(user)

        return user