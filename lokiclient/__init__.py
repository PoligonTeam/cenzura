"""
Copyright 2022-2026 PoligonTeam

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
from datetime import datetime, timezone
from femcord.femcord.commands import Context, AppContext
from femcord.femcord.types import Guild
from scheduler.scheduler import Scheduler
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ipc import Event

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
        self.logs: list[LokiLog] = []

        scheduler.create_schedule(self.send, interval)

    def add_command_log(self, ctx: Context | AppContext) -> None:
        if isinstance(ctx, Context):
            self.logs.append(LokiLog(
                "command",
                {
                    "channel": ctx.channel.id,
                    "guild": ctx.guild.id,
                    "user": ctx.author.id,
                    "command": ctx.command.name,
                    "arguments": ", ".join([str(argument) for argument in ctx.arguments]) if ctx.arguments else ""
                },
                ctx.message.content,
                ctx.message.timestamp
            ))
        elif isinstance(ctx, AppContext):
            options = {item.name: item.value for item in ctx.interaction.data.options or []}
            self.logs.append(LokiLog(
                "app_command",
                {
                    "channel": ctx.interaction.channel.id,
                    "user": ctx.interaction.user.id,
                    "command": ctx.interaction.data.name,
                    "arguments": ", ".join([f"{key}={value}" for key, value in options.items()]) if options else "",
                    **({"guild": ctx.interaction.guild.id} if ctx.interaction.guild else {})
                },
                f"/{ctx.interaction.data.name} {' '.join([f'{key}={value}' for key, value in options.items()])}",
                datetime.now(tz=timezone.utc)
            ))

    def add_command_exception_log(self, ctx: Context | AppContext, exception: Exception, formatted_exception: str) -> None:
        if isinstance(ctx, Context):
            self.logs.append(LokiLog(
                "command.exception",
                {
                    "channel": ctx.channel.id,
                    "guild": ctx.guild.id,
                    "user": ctx.author.id,
                    "command": ctx.command.name,
                    "arguments": ", ".join([str(argument) for argument in ctx.arguments]) if ctx.arguments else "",
                    "exception": type(exception).__name__,
                    "exception_message": formatted_exception
                },
                ctx.message.content,
                ctx.message.timestamp
            ))
        elif isinstance(ctx, AppContext):
            options = {item.name: item.value for item in ctx.interaction.data.options or []}
            self.logs.append(LokiLog(
                "app_command.exception",
                {
                    "channel": ctx.interaction.channel.id,
                    "user": ctx.interaction.user.id,
                    "command": ctx.interaction.data.name,
                    "arguments": ", ".join([f"{key}={value}" for key, value in options.items()]) if options else "",
                    "exception": type(exception).__name__,
                    "exception_message": formatted_exception,
                    **({"guild": ctx.interaction.guild.id} if ctx.interaction.guild else {})
                },
                f"/{ctx.interaction.data.name} {' '.join([f'{key}={value}' for key, value in options.items()])}",
                datetime.now(tz=timezone.utc)
            ))

    def add_guild_log(self, guild: Guild, leave: bool = False) -> None:
        description = "Guild joined" if not leave else "Guild left"
        self.logs.append(LokiLog(
            "guild.create" if not leave else "guild.leave",
            {
                "guild": guild.id,
                "name": guild.name,
                "members": len(guild.members),
                **({"owner": guild.owner.user.id} if guild.owner else {})
            },
            description,
            datetime.now(tz=timezone.utc)
        ))

    def add_webhook_event_log(self, event: "Event") -> None:
        description = "User installed app" if event["integration_type"] == 1 else "Guild installed app"
        self.logs.append(LokiLog(
            "webhook.event",
            {
                "integration_type": event["integration_type"],
                "user": event["user"]["id"],
                **({"guild": event["guild"]["id"]} if "guild" in event else {})
            },
            description,
            datetime.now(tz=timezone.utc)
        ))

    async def _request(self, method: str, url: str, **kwargs) -> dict | None:
        async with aiohttp.ClientSession(base_url=self.base_url) as session:
            try:
                async with session.request(method, url, **kwargs) as response:
                    if response.status == 204:
                        return

                    if response.content_type == "application/json":
                        return await response.json()
            except Exception as e:
                raise LokiException(e)

    async def get_logs(self, query: str, *, start: Optional[int] = None, end: Optional[int] = None, limit: Optional[int] = None) -> dict | None:
        return await self._request("GET", "/loki/api/v1/query_range", params={
            "query": query,
            **({"start": start} if start else {}),
            **({"end": end} if end else {}),
            **({"limit": limit} if limit else {})
        })

    async def send(self) -> None:
        if self.logs:
            await self._request("POST", "/loki/api/v1/push", json={"streams": [log.to_dict() for log in self.logs]})
            self.logs = []