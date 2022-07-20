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

import aiohttp, asyncio, json, random
from .types import Player, Bug

URL = "wss://ws.korrumzthegame.wtf"

class Client:
    def __init__(self, username, x: int, y: int, pull_requests: int, image_number: int):
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()
        self.ws: aiohttp.client_ws.ClientWebSocketResponse = None

        self.username = username
        self.x = x
        self.y = y
        self.pull_requests = pull_requests
        self.image_number = image_number

        self.players = []
        self.bugs = []

    async def move(self, direction):
        directions = {
            "up": (0, -75),
            "down": (0, 75),
            "left": (-75, 0),
            "right": (75, 0),
            "left up": (-75, -75),
            "right up": (75, -75),
            "left down": (-75, 75),
            "right down": (75, 75)
        }

        self.x += directions[direction][0]
        self.y += directions[direction][1]

        if self.x < 0 or self.x > 1920:
            self.x = random.randint(0, 1920)
        if self.y < 0 or self.y > 1080:
            self.y = random.randint(0, 1080)

        data = {
            "event": "move",
            "data": {
                "username": self.username,
                "x": round(self.x),
                "y": round(self.y)
            }
        }

        await self.ws.send_json(data)

    async def identify(self):
        await self.ws.send_json({
            "event": "new player",
            "data": {
                "username": self.username,
                "x": round(self.x),
                "y": round(self.y),
                "canvasWidth": 5000,
                "canvasHeight": 5000,
                "imageNumber": self.image_number
            }
        })

    async def run(self):
        self.ws = await self.session.ws_connect(URL)

        await self.identify()

        async for message in self.ws:
            if message.type in (aiohttp.WSMsgType.error, aiohttp.WSMsgType.closed): break

            if message.type == aiohttp.WSMsgType.text:
                data = json.loads(message.data)
                event = data["event"]
                data = data["data"]

                player = None

                for p in self.players + [self]:
                    if "username" in data and p.username == data["username"]:
                        player = p

                match event:
                    case "new player":
                        self.players.append(Player(data["username"], data["x"], data["y"], data["pullRequests"], data["imageNumber"]))

                    case "new username":
                        self.username = data["username"]

                    case "new image":
                        self.image_number = data["imageNumber"]

                    case "move":
                        if player.username == self.username:
                            return

                        player.x = data["x"]
                        player.y = data["y"]

                    case "new bug":
                        self.bugs.append(Bug(data["x"], data["y"], data["imageNumber"]))

                    case "pull request":
                        bug = None

                        for b in self.bugs:
                            if (b.x, b.y, b.image_number) == (data["bug"]["x"], data["bug"]["y"], data["bug"]["imageNumber"]):
                                bug = b

                        self.bugs.remove(bug)
                        player.pull_requests = data["pullRequests"]

                    case "player disconnected":
                        self.players.remove(player)