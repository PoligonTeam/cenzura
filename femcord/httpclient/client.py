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
from .types import Response
from .enums import HTTPStatus
from ..client import Client
from ..http import HTTP
from ..types import Interaction
from typing import Callable

class HTTPClient(Client):
    def __init__(self, webserver: Callable, *, client_id: str, client_secret: str, public_key: str, interaction_endpoint: str):
        self.loop = asyncio.get_event_loop()
        self.client_id = client_id
        self.client_secret = client_secret
        self.public_key = public_key
        self.interaction_endpoint = interaction_endpoint
        self.token: str = None

        self.http: HTTP = None
        self.web = webserver(self.on_interaction, public_key=self.public_key, interaction_endpoint=self.interaction_endpoint)

    def convert(self, data: dict = None) -> Interaction:
        ... # konwerter na interakcje

        return data

    async def on_interaction(self, data: dict = None) -> Response:
        data: Interaction = self.convert(data)

        print(data)

        return Response(status=HTTPStatus.OK, data={})

    def run(self, token: str = None, *, host: str, port: int):
        self.token = token

        self.loop.create_task(HTTP(self))
        self.loop.create_task(self.web.run(host=host, port=port))