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

from .dataclass import dataclass

from ..enums import *
from ..utils import *
from ..permissions import Permissions
from ..http import Route

from datetime import datetime

from typing import List, Optional, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from ..commands import Context
    from ..embed import Embed
    from ..components import Components
    from .message import Message
    from .sticker import Sticker

@dataclass
class PermissionOverwrite:
    __client: "Client"
    type: OverwriteTypes
    allow: Permissions
    deny: Permissions
    id: str = None
    user_id: str = None
    role_id: str = None

    @classmethod
    async def from_raw(cls, client, overwrite):
        overwrite["role_id" if overwrite["type"] == OverwriteTypes.ROLE else "user_id"] = overwrite["id"]
        overwrite["allow"] = Permissions.from_int(int(overwrite["allow"]))
        overwrite["deny"] = Permissions.from_int(int(overwrite["deny"]))

        return cls(client, **overwrite)

@dataclass
class ThreadMetadata:
    __client: "Client"
    archived: bool
    auto_archive_duration: int
    archive_timestamp: datetime
    create_timestamp: datetime
    locked: bool
    invitable: bool = None

    @classmethod
    async def from_raw(cls, client, metadata):
        metadata["archive_timestamp"] = parse_time(metadata["archive_timestamp"])
        metadata["create_timestamp"] = parse_time(metadata["create_timestamp"])

        return cls(client, **metadata)

@dataclass
class ThreadMember:
    __client: "Client"
    id: str = None
    user_id: str = None
    join_timestamp: datetime = None
    flags: int = None

    @classmethod
    async def from_raw(cls, client, member):
        if "datetime" in member:
            member["datetime"] = parse_time(member["datetime"])

        return cls(client, **member)

@dataclass
class Channel:
    __client: "Client"
    id: str
    type: ChannelTypes
    name: str = None
    position: int = None
    permission_overwrites: Sequence[PermissionOverwrite] = None
    topic: str = None
    nsfw: bool = None
    bitrate: int = None
    user_limit: int = None
    rate_limit_per_user: int = None
    application_id: str = None
    parent_id: str = None
    last_pin_timestamp: datetime = None
    message_count: int = None
    thread_metadata: ThreadMetadata = None
    member: ThreadMember = None
    default_auto_archive_duration: int = None
    rtc_region: str = None
    created_at: datetime = None

    def __str__(self):
        return "<Channel id={!r} name={!r} type={!r} position={!r}>".format(self.id, self.name, self.type, self.position)

    def __repr__(self):
        return "<Channel id={!r} name={!r} type={!r} position={!r}>".format(self.id, self.name, self.type, self.position)

    @classmethod
    async def from_raw(cls, client, channel):
        channel["type"] = ChannelTypes(channel["type"])
        channel["created_at"] = time_from_snowflake(channel["id"])

        if "permission_overwrites" in channel:
            channel["permission_overwrites"] = [await PermissionOverwrite.from_raw(client, overwrite) for overwrite in channel["permission_overwrites"]]
        if "last_pin_timestamp" in channel:
            channel["last_pin_timestamp"] = parse_time(channel["last_pin_timestamp"])
        if "thread_metadata" in channel:
            channel["thread_metadata"] = await ThreadMetadata.from_raw(client, channel["thread_metadata"]) if channel["thread_metadata"] else None
        if "member" in channel:
            channel["member"] = await ThreadMember.from_raw(client, channel["member"]) if channel["member"] else None
        if "nsfw" not in channel or channel["nsfw"] is None:
            channel["nsfw"] = False

        return cls(client, **channel)

    @classmethod
    def from_arg(cls, ctx: "Context", argument) -> Union["Channel", None]:
        result = ID_PATTERN.search(argument)

        if result is not None:
            argument = result.group()

        return ctx.guild.get_channel(argument)

    async def fetch_message(self, message_id: str) -> Union[dict, str]:
        return await self.__client.http.request(Route("GET", "channels", self.id, "messages", message_id))

    async def start_typing(self) -> Union[dict, str]:
        return await self.__client.http.start_typing(self.id)

    async def send(self, content: Optional[str] = None, *, embed: Optional["Embed"] = None, embeds: Optional[Sequence["Embed"]] = None, components: Optional["Components"] = None, files: Optional[List[Union[str, bytes]]] = [], mentions: Optional[list] = [], stickers: Optional[List["Sticker"]] = None, other: Optional[dict] = {}) -> "Message":
        response = await self.__client.http.send_message(self.id, content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

        if response is not None:
            return await Message.from_raw(self.__client, response)

    async def get_messages(self, *, around: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None, limit: Optional[int] = None) -> List["Message"]:
        response = await self.__client.http.get_messages(self.id, around=around, before=before, after=after, limit=limit)

        if response is not None:
            return [await Message.from_raw(self.__client, message) for message in response]

    async def purge(self, *, limit: Optional[int] = None, messages: Optional[Sequence[Union["Message", str]]] = [], key: Optional[Callable[["Message"], bool]] = None) -> List[dict]:
        if limit is not None:
            messages += [message for message in self.__client.gateway.messages if message.channel.id == self.id][-limit:]

            if len(messages) < limit:
                missing_messages = limit - len(messages)
                messages += await self.get_messages(limit=missing_messages)

        if key is not None:
            messages = [message for message in messages if isinstance(message, Message) and key(message) is True]

        messages = list(set([message.id if isinstance(message, Message) else message for message in messages]))

        chunks = [messages[x:x+100] for x in range(0, len(messages), 100)]

        responses = []

        for messages in chunks:
            responses.append(await self.__client.http.purge_channel(self.id, messages))

        return responses