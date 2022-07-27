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

import asyncio, aiohttp, zlib, json, logging
from .enums import Opcodes

class WebSocket:
    URL = "wss://gateway.discord.gg/?v=9&encoding=json&compress=zlib-stream"

    async def __new__(cls, *args):
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, gateway, client):
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.gateway = gateway
        self.client = client

        self.ws = await self.session.ws_connect(self.URL)
        self.gateway.ws = self
        self.client.gateway = self.gateway

        self.buffer = bytearray()
        self.inflator = zlib.decompressobj()

        async for message in self.ws:
            if message.type in (aiohttp.WSMsgType.error, aiohttp.WSMsgType.closed): break

            if message.type is aiohttp.WSMsgType.binary:
                self.buffer.extend(message.data)

                if len(message.data) < 4 or not message.data[-4:] == b"\x00\x00\xff\xff":
                    continue

                data = self.inflator.decompress(self.buffer)
                self.buffer = bytearray()

                data = json.loads(data)
                op = data.get("op")
                d = data.get("d")
                s = data.get("s")
                t = data.get("t")

                logging.debug(f"op: {Opcodes(op).name}, data: {None if not isinstance(data, dict) else data}, sequence number: {s}, event name: {t}")

                await self.gateway.on_message(Opcodes(op), d, s, t)

        self.gateway.heartbeat.stop()
        await self.session.close()
        self.gateway.resuming = True
        self.gateway.last_sequence_number = self.gateway.sequence_number
        await WebSocket.__init__(self, self.gateway, self.client)

    async def send(self, op, data, *, sequences = None):
        logging.debug(f"sent op: {op.name}, data: {data}, sequences: {sequences}".replace("'" + self.gateway.token + "'", "TOKEN"))

        ready_data = {
            "op": op.value,
            "d": data
        }

        if sequences is not None:
            ready_data["s"] = sequences

        await self.ws.send_json(ready_data)