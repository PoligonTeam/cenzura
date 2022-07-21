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

import asyncio, aiohttp, json, logging
from .errors import *
from .embed import Embed
from .components import Components
from .enums import *
from typing import Sequence

URL = "https://discord.com/api/v10"

class Route:
    def __init__(self, method, *endpoint):
        self.method = method
        self.endpoint = "/" + "/".join(endpoint)

    def __eq__(self, route):
        return self.method == route.method and self.endpoint == route.endpoint

    def __ne__(self, route):
        return self.method != route.method and self.endpoint != route.endpoint

class Http:
    async def __new__(cls, *args):
        instance = super().__new__(cls)
        await instance.__init__(*args)
        return instance

    async def __init__(self, client):
        client.http = self
        self.loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.token = client.token
        self.bot = client.bot
        self.ratelimits = {}

    async def call_later(self, callback, *args, delay: int):
        await asyncio.sleep(delay)
        await callback(*args)

    async def remove_ratelimit(self, endpoint):
        requests = self.ratelimits.pop(endpoint)

        for route, headers, data, params, files in requests:
            await self.request(route, headers=headers, data=data, params=params, files=files)

    async def request(self, route: Route, *, headers: dict = {}, data: dict = None, params: dict = None, files: list = None):
        headers.update({"authorization": ("Bot " if self.bot is True else "") + self.token, "user-agent": "cenzuralib"})

        for route.endpoint in self.ratelimits:
            self.ratelimits[route.endpoint].append((route, data, files))
            return

        kwargs = dict(json=data)

        if params is not None:
            kwargs["params"] = params

        if files is not None:
            form = aiohttp.FormData()
            form.add_field("payload_json", json.dumps(data))

            for index, file in enumerate(files):
                form.add_field("file[%s]" % index, file[1], content_type="application/octet-stream", filename=file[0])

            kwargs = dict(data=form)

        async with self.session.request(route.method, URL + route.endpoint, headers=headers, **kwargs) as response:
            logging.debug(f"{route.method} {route.endpoint}, data: {data}, params: {params}, files: {[file[0] for file in files] if files is not None else None}; status: {response.status}, text: {await response.text()}")

            try:
                response_data = await response.json()
            except aiohttp.ContentTypeError:
                response_data = await response.text()

            if 300 > response.status >= 200:
                return response_data

            if response.status in (400, 401, 403, 404, 405):
                message = response_data

                if isinstance(response_data, dict):
                    message = response_data["message"]

                raise HTTPException(message, response.status, response_data)

            elif response.status == 429:
                if not route.endpoint in self.ratelimits:
                    self.ratelimits[route.endpoint] = []

                self.ratelimits[route.endpoint].append((route, headers, data, params, files))
                self.loop.create_task(self.call_later(self.remove_ratelimit, route.endpoint, delay=response_data["retry_after"]))

    def start_typing(self, channel_id):
        return self.request(Route("POST", "channels", channel_id, "typing"))

    def send_message(self, channel_id, content = None, *, embed: Embed = None, embeds: Sequence[Embed] = None, components: Components = None, files: list = [], mentions: list = [], other: dict = {}):
        data = {"allowed_mentions": {"parse": mentions, "users": [], "replied_user": False}}
        data.update(other)

        if content is not None:
            data["content"] = str(content)

        if embed is not None and isinstance(embed, Embed):
            data["embeds"] = []

            if embed.__dict__:
                data["embeds"].append(embed.__dict__)

        if embeds is not None:
            data["embeds"] = []

            for embed in embeds:
                if embed.__dict__:
                    data["embeds"].append(embed.__dict__)

        if components is not None:
            data["components"] = getattr(components, "components", components)

        return self.request(Route("POST", "channels", channel_id, "messages"), data=data, files=files)

    def edit_message(self, channel_id, message_id, content = None, *, embed: Embed = None, embeds: Sequence[Embed] = None, components: Components = None, files: list = [], other: dict = {}):
        data = other

        if content is not None:
            data["content"] = str(content)

        if embed is not None and isinstance(embed, Embed):
            data["embeds"] = []

            if embed.__dict__:
                data["embeds"].append(embed.__dict__)

        if embeds is not None:
            data["embeds"] = []

            for embed in embeds:
                if embed.__dict__:
                    data["embeds"].append(embed.__dict__)

        if components is not None:
            data["components"] = getattr(components, "components", components)

        return self.request(Route("PATCH", "channels", channel_id, "messages", message_id), data=data, files=files)

    def delete_message(self, channel_id, message_id):
        return self.request(Route("DELETE", "channels", channel_id, "messages", message_id))

    def interaction_callback(self, interaction_id, interaction_token, interaction_type: InteractionCallbackTypes, content = None, *, title: str = None, custom_id: str = None, embed: Embed = None, embeds: Sequence[Embed] = None, components: Components = None, files: list = [], mentions: list = [], other: dict = {}):
        data = {"type": interaction_type.value, "data": {}}
        data["data"].update(other)

        if content is not None:
            data["data"]["content"] = str(content)

        if title is not None:
            data["data"]["title"] = title

        if custom_id is not None:
            data["data"]["custom_id"] = custom_id

        if embed is not None and isinstance(embed, Embed):
            data["data"]["embeds"] = []

            if embed.__dict__:
                data["data"]["embeds"].append(embed.__dict__)

        if embeds is not None:
            data["data"]["embeds"] = []

            for embed in embeds:
                if embed.__dict__:
                    data["data"]["embeds"].append(embed.__dict__)

        if components is not None:
            data["data"]["components"] = getattr(components, "components", components)

        return self.request(Route("POST", "interactions", interaction_id, interaction_token, "callback"), data=data, files=files)

    def kick_member(self, guild_id, member_id, reason = None):
        headers = {}

        if reason is not None:
            headers["X-Audit-Log-Reason"] = reason

        return self.request(Route("DELETE", "guilds", guild_id, "members", member_id), headers=headers)

    def ban_member(self, guild_id, member_id, reason = None, delete_message_days = 0):
        headers = {}

        if reason is not None:
            headers["X-Audit-Log-Reason"] = reason

        return self.request(Route("PUT", "guilds", guild_id, "bans", member_id), headers=headers, data={"delete_message_days": delete_message_days})

    def unban_member(self, guild_id, member_id, reason = None):
        headers = {}

        if reason is not None:
            headers["X-Audit-Log-Reason"] = reason

        return self.request(Route("DELETE", "guilds", guild_id, "bans", member_id), headers=headers)

    def add_role(self, guild_id, member_id, role_id):
        return self.request(Route("PUT", "guilds", guild_id, "members", member_id, "roles", role_id))

    def remove_role(self, guild_id, member_id, role_id):
        return self.request(Route("DELETE", "guilds", guild_id, "members", member_id, "roles", role_id))

    def get_messages(self, channel_id, *, around = None, before = None, after = None, limit = None):
        params = {}

        if around is not None:
            params["around"] = around
        if before is not None:
            params["before"] = before
        if after is not None:
            params["after"] = after
        if limit is not None:
            params["limit"] = limit

        return self.request(Route("GET", "channels", channel_id, "messages"), params=params)

    def purge_channel(self, channel_id, messages):
        return self.request(Route("POST", "channels", channel_id, "messages", "bulk-delete"), data={"messages": messages})

    def open_dm(self, user_id):
        return self.request(Route("POST", "users", "@me", "channels"), data={"recipient_id": user_id})