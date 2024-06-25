"""
Copyright 2022-2024 PoligonTeam

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

import aiohttp
from datetime import datetime
from femcord.femcord.commands import Context
from femcord.femcord.types import Guild
from scheduler.scheduler import Scheduler
from typing import List, Optional

class LokiException(Exception):
    pass

class LokiLog:
    def __init__(self, type: str, labels: dict, message: str, timestamp: datetime) -> None:
        self.type = type
        self.labels = {
            "type": type,
            **labels
        }
        self.message = message
        self.timestamp = int(timestamp.timestamp() * 1000 * 1000 * 1000)

    def __str__(self) -> str:
        return "<LokiLog type={!r} labels={!r} message={!r} timestamp={!r}>".format(self.type, self.labels, self.message, self.timestamp)

    def __repr__(self) -> str:
        return "<LokiLog type={!r} labels={!r} message={!r} timestamp={!r}>".format(self.type, self.labels, self.message, self.timestamp)

    def to_dict(self) -> dict:
        return {
            "stream": self.labels,
            "values": [[str(self.timestamp), self.message]]
        }

class LokiClient:
    def __init__(self, base_url: str, scheduler: Scheduler, interval: str = "5m") -> None:
        self.base_url = base_url
        self.logs: List[LokiLog] = []

        scheduler.create_schedule(self.send, interval)

    def add_command_log(self, ctx: Context) -> None:
        self.logs.append(LokiLog(
            "command",
            {
                "channel": str(ctx.channel.id),
                "guild": str(ctx.guild.id),
                "user": str(ctx.author.id),
                "command": ctx.command.name,
                "arguments": ", ".join([str(argument) for argument in ctx.arguments]) if ctx.arguments else ""
            },
            ctx.message.content,
            ctx.message.timestamp
        ))

    def add_command_exception_log(self, ctx: Context, exception: Exception, formatted_exception: str) -> None:
        self.logs.append(LokiLog(
            "command.exception",
            {
                "channel": str(ctx.channel.id),
                "guild": str(ctx.guild.id),
                "user": str(ctx.author.id),
                "command": ctx.command.name,
                "arguments": ", ".join([str(argument) for argument in ctx.arguments]) if ctx.arguments else "",
                "exception": type(exception).__name__,
                "exception_message": formatted_exception
            },
            ctx.message.content,
            ctx.message.timestamp
        ))

    def add_guild_log(self, guild: Guild, leave: bool = False) -> None:
        self.logs.append(LokiLog(
            "guild.create" if not leave else "guild.leave",
            {
                "type": "guild.create" if not leave else "guild.delete",
                "guild": guild.id,
                "name": guild.name,
                "owner": guild.owner_id,
                "members": len(guild.members)
            },
            "",
            datetime.utcnow()
        ))

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        async with aiohttp.ClientSession(base_url=self.base_url) as session:
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 204:
                        return

                    if response.content_type == "application/json":
                        return await response.json()

                    return await response.text()
            except Exception as e:
                raise LokiException(e)

    async def get_logs(self, query: str, *, start: Optional[int] = None, end: Optional[int] = None, limit: Optional[int] = None) -> dict:
        return await self._request("GET", "/loki/api/v1/query_range", params={
            "query": query,
            **({"start": start} if start else {}),
            **({"end": end} if end else {}),
            **({"limit": limit} if limit else {})
        })

    async def send(self) -> None:
        await self._request("POST", "/loki/api/v1/push", json={"streams": [log.to_dict() for log in self.logs]})
        self.logs = []