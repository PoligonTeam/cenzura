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

import jwt
import config

from aiohttp import web

from dataclasses import dataclass
from enum import Enum

from typing import Callable, Awaitable, Optional, TypedDict, Any

router = web.RouteTableDef()

RouteFunction = Callable[[web.Request], Awaitable[web.Response]]

def logged_in(func: RouteFunction) -> RouteFunction:
    def wrapper(request: web.Request) -> Awaitable[web.Response]:
        token = request.headers.get("authorization")

        if not token:
            return web.json_response({"error": "Missing token"}, status=401)

        try:
            payload = jwt.decode(token, config.JWT_SECRET, ["HS256"])
            request["user_id"] = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return web.json_response({"error": "Token has expired"}, status=401)
        except jwt.InvalidTokenError as e:
            return web.json_response({"error": "Invalid token"}, status=401)

        return func(request)
    return wrapper

class ChannelDict(TypedDict):
    id: str
    name: str

class RoleDict(TypedDict):
    id: str
    name: str

class GuildDict(TypedDict):
    id: str
    name: str
    icon: str
    channels: list[ChannelDict]
    roles: list[RoleDict]

class EndpointTypes(Enum):
    STRING = 0
    LIST = 1
    DICT = 2
    SELECT = 3
    CHANNEL = 4
    ROLE = 5
    FEMSCRIPT = 6
    CUSTOM_COMMANDS = 7

@dataclass
class Endpoint:
    category: str
    type: EndpointTypes
    subcategory: Optional[str] = None
    min: Optional[int] = None
    max: Optional[int] = None
    options: Optional[list[Any]] = None
    functions: Optional[dict[str, Callable[..., None]]] = None
    disabled: bool = False

    def check(self, guild: GuildDict, item: str | list[str] | dict[str, str | float]) -> bool:
        if self.type in (EndpointTypes.STRING, EndpointTypes.LIST, EndpointTypes.DICT):
            return self.max >= len(item) >= self.min
        elif self.type is EndpointTypes.SELECT:
            return item in self.options
        elif self.type is EndpointTypes.CHANNEL:
            return item in (channel["id"] for channel in guild["channels"])
        elif self.type is EndpointTypes.ROLE:
            return item in (role["id"] for role in guild["roles"])
        elif self.type is EndpointTypes.FEMSCRIPT:
            if not self.max >= len(item) >= self.min:
                return False
            return True # TODO: zrobic na to checka
        elif self.type is EndpointTypes.CUSTOM_COMMANDS:
            for custom_command in item:
                if not self.max >= len(custom_command) >= self.min:
                    return False
            return True # TODO: zrobic na to checka

endpoints = dict(
    prefix = Endpoint(
        category = "General",
        type = EndpointTypes.STRING,
        min = 1,
        max = 5
    ),
    language = Endpoint(
        category = "General",
        type = EndpointTypes.SELECT,
        options = ["en", "pl"]
    ),
    autorole = Endpoint(
        category = "Roles",
        type = EndpointTypes.ROLE
    ),
    verification_channel = Endpoint(
        category = "Roles",
        type = EndpointTypes.CHANNEL,
        disabled = True
    ),
    verification_message = Endpoint(
        category = "Roles",
        type = EndpointTypes.STRING,
        disabled = True
    ),
    verification_role = Endpoint(
        category = "Roles",
        type = EndpointTypes.ROLE,
        disabled = True
    ),
    database = Endpoint(
        category = "Database",
        type = EndpointTypes.DICT,
        max = 100
    ),
    welcome_message = Endpoint(
        category = "Scripts",
        subcategory = "Messages",
        type = EndpointTypes.FEMSCRIPT,
        max = 200
    ),
    leave_message = Endpoint(
        category = "Scripts",
        subcategory = "Messages",
        type = EndpointTypes.FEMSCRIPT,
        max = 4000
    ),
    custom_commands = Endpoint(
        category = "Scripts",
        subcategory = "Custom commands",
        type = EndpointTypes.CUSTOM_COMMANDS,
        max = 4000
    )
)

class User:
    prefix = "/user"

    def __init__(self, root: web.Application) -> None:
        self.app = web.Application()
        self.app.root = root

        self.app.add_routes(router)

    @router.get("")
    @logged_in
    async def me(request: web.Request) -> web.Response:
        user = await request.app.root.ipc.emit("get_user", request["user_id"])
        return web.json_response(user)

    @router.get("/guilds")
    @logged_in
    async def guilds(request: web.Request) -> web.Response:
        guilds = await request.app.root.ipc.emit("get_guilds_for", request["user_id"])
        return web.json_response(guilds)

    @router.get("/guilds/{guild_id}")
    @logged_in
    async def guild(request: web.Request) -> web.Response:
        guild_db = await request.app.root.ipc.emit("get_guild_db", request.match_info.get("guild_id"), request["user_id"])

        if isinstance(guild_db, int):
            return web.Response(status=guild_db)

        return web.json_response(guild_db)

    @router.post("/guilds/{guild_id}/{endpoint}")
    @router.get("/guilds/{guild_id}/options")
    @logged_in
    async def modify_guild(request: web.Request) -> web.Response:
        if request.method == "GET":
            return web.json_response({key: value.__dict__ | {"type": value.type.value} for key, value in endpoints.items()})

        endpoint = request.match_info.get("endpoint")

        if endpoint not in endpoints:
            return web.HTTPNotFound()

        data = await request.json()

        if not data or "value" not in data:
            return web.HTTPBadRequest()

        guild_db = await request.app.root.ipc.emit("get_guild_db", request.match_info.get("guild_id"), request["user_id"])

        if isinstance(guild_db, int):
            return web.Response(status=guild_db)

        if not endpoints[endpoint].check(guild_db["guild"], data.get("value")):
            return web.HTTPBadRequest()

        return web.HTTPOk()

def get_app(root: web.Application) -> User:
    return User(root)