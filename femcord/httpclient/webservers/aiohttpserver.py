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

from aiohttp import web
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from ..types import *
from ..enums import *
from ...enums import InteractionCallbackTypes
from typing import Callable

class WebServer(web.Application):
    def __init__(self, on_interaction: Callable, *, public_key: str, interaction_endpoint: str):
        super().__init__()

        self.on_interaction = on_interaction

        self.public_key = public_key
        self.interaction_endpoint = interaction_endpoint

        self.router.add_post(self.interaction_endpoint, self.interaction_handler)

    async def interaction_handler(self, request: web.Request):
        if not "X-Signature-Ed25519" in request.headers:
            raise web.HTTPUnauthorized(text="missing X-Signature-Ed25519")

        if not "X-Signature-Timestamp" in request.headers:
            raise web.HTTPUnauthorized(text="missing X-Signature-Timestamp")

        verify_key = VerifyKey(bytes.fromhex(self.public_key))

        signature = request.headers["X-Signature-Ed25519"]
        timestamp = request.headers["X-Signature-Timestamp"]

        if request.body_exists is False:
            raise web.HTTPBadRequest(text="missing request body")

        body = await request.read()

        try:
            verify_key.verify(timestamp.encode() + body, bytes.fromhex(signature))
        except BadSignatureError:
            raise web.HTTPUnauthorized(text="invalid signature")

        result: Response = await self.on_interaction(await request.json())

        return web.json_response(result.data, status=result.status, headers=result.headers)

    def run(self, *, host: str, port: int):
        web.run_app(self, host=host, port=port)