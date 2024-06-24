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

from .channel import Channel
from .emoji import Emoji
from .embed import Embed
from .interaction import Interaction

from datetime import datetime

from typing import List, Optional, Sequence, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from ..embed import Embed as UserEmbed
    from ..components import Components
    from .guild import Guild
    from .user import User
    from .member import Member
    from .role import Role
    from .sticker import Sticker

@dataclass
class Attachment:
    id: str
    filename: str
    size: int
    url: str
    proxy_url: str
    height: int = None
    width: int = None
    description: str = None
    ephemeral: bool = None
    content_type: str = None
    waveform: str = None
    duration_secs: float = None
    flags: Any = None
    placeholder_version: Any = None
    placeholder: Any = None
    content_scan_version: Any = None

@dataclass
class MessageReference:
    type: int = None
    message_id: str = None
    channel_id: str = None
    guild_id: str = None
    fail_if_not_exists: bool = None

@dataclass
class MessageSticker:
    __client: "Client"
    id: str
    name: str
    format_type: StickerFormatTypes

    @classmethod
    async def from_raw(cls, client, sticker):
        sticker["format_type"] = StickerFormatTypes(sticker["format_type"])

        return cls(client, **sticker)

@dataclass
class SelectOptions:
    __client: "Client"
    label: str
    value: str
    description: str = None
    emoji: Emoji = None
    default: bool = None

    @classmethod
    async def from_raw(cls, client, option):
        if "emoji" in option:
            option["emoji"] = Emoji(**option["emoji"])

        return cls(client, **option)

@dataclass
class MessageComponents:
    __client: "Client"
    type: ComponentTypes
    custom_id: str = None
    disabled: bool = None
    style: ButtonStyles = None
    label: str = None
    emoji: Emoji = None
    url: str = None
    options: Sequence[SelectOptions] = None
    placeholder: str = None
    min_values: int = None
    max_values: int = None
    components: Sequence["MessageComponents"] = None
    value: str = None

    @classmethod
    async def from_raw(cls, client, component):
        if "hash" in component: del component["hash"]

        component["type"] = ComponentTypes(component["type"])

        if "components" in component:
            component["components"] = [await cls.from_raw(client, components) for components in component["components"]]
        if "style" in component:
            component["style"] = ButtonStyles(component["style"])
        if "emoji" in component:
            component["emoji"] = Emoji(client, **component["emoji"])
        if "options" in component:
            component["options"] = [await SelectOptions.from_raw(client, option) for option in component["options"]]

        return cls(client, **component)

@dataclass
class MessageReaction:
    __client: "Client"
    count: int
    me: bool
    emoji: Emoji

    @classmethod
    async def from_raw(cls, client, reaction):
        reaction["emoji"] = await Emoji.from_raw(client, reaction["emoji"])

        return cls(client, **reaction)

@dataclass
class Message:
    __client: "Client"
    id: str
    channel: Channel = None
    author: "User" = None
    content: str = None
    mention_everyone: bool = None
    pinned: bool = None
    tts: bool = None
    type: MessageTypes = None
    flags: int = None
    mentions: Sequence["User"] = None
    attachments: Sequence[Attachment] = None
    mention_roles: Sequence["Role"] = None
    embeds: Sequence[Embed] = None
    components: Sequence[MessageComponents] = None
    guild: "Guild" = None
    member: "Member" = None
    timestamp: datetime = None
    edited_timestamp: datetime = None
    sticker_items: Sequence[MessageSticker] = None
    reactions: Sequence[MessageReaction] = None
    mention_channels: Sequence[Channel] = None
    webhook_id: str = None
    message_reference: MessageReference = None
    interaction: Interaction = None
    thread: Channel = None
    application_id: str = None

    __CHANGE_KEYS__ = (
        (
            "channel_id",
            "channel"
        ),
        (
            "guild_id",
            "guild"
        )
    )

    def __str__(self):
        return "<Message id={!r} channel={!r} author={!r} content={!r}>".format(self.id, self.channel, self.author, self.content)

    def __repr__(self):
        return "<Message id={!r} channel={!r} author={!r} content={!r}>".format(self.id, self.channel, self.author, self.content)

    @classmethod
    async def from_raw(cls, client, message):
        for guild in client.gateway.guilds:
            if isinstance(message["channel"], Channel) is False:
                channel = guild.get_channel(message["channel"])
                if channel is not None:
                    message["channel"] = channel

        if "guild" in message:
            message["guild"] = client.gateway.get_guild(message["guild"])

            if "member" in message:
                message["member"] = await message["guild"].get_member(message["member"], message["author"])
                message["author"] = message["member"].user
            if "interaction" in message:
                message["interaction"] = await Interaction.from_raw(client, message["interaction"])
            if "thread" in message:
                message["thread"] = message["guild"].get_channel(message["thread"])
            if "mentions" in message:
                message["mentions"] = [await client.gateway.get_user(mention["id"]) for mention in message["mentions"]]
            if "mention_channels" in message:
                message["mention_channels"] = [message["guild"].get_channel(channel["id"]) for channel in message["mention_channels"]]
            if "mention_roles" in message:
                message["mention_roles"] = [message["guild"].get_role(role_id) for role_id in message["mention_roles"]]

        if "author" in message and "member" not in message:
            message["author"] = await client.gateway.get_user(message["author"])
        if "timestamp" in message:
            message["timestamp"] = parse_time(message["timestamp"])
        if "edited_timestamp" in message:
            message["edited_timestamp"] = parse_time(message["edited_timestamp"])
        if "sticker_items" in message:
            message["sticker_items"] = [await MessageSticker.from_raw(client, sticker) for sticker in message["sticker_items"]]
        if "reactions" in message:
            message["reactions"] = [await MessageReaction.from_raw(client, reaction) for reaction in message["reactions"]]
        if "message_reference" in message:
            message["message_reference"] = MessageReference(**message["message_reference"])
        if "attachments" in message:
            message["attachments"] = [Attachment(**attachment) for attachment in message["attachments"]]
        if "type" in message:
            message["type"] = MessageTypes(message["type"])
        if "components" in message:
            message["components"] = [await MessageComponents.from_raw(client, component) for component in message["components"]]
        if "embeds" in message:
            message["embeds"] = [await Embed.from_raw(client, embed) for embed in message["embeds"]]
        if "flags" in message:
            message["flags"] = [flag for flag in MessageFlags if message["flags"] & flag.value == flag.value]

        return cls(client, **message)

    async def reply(self, content: Optional[str] = None, *, embed: Optional["UserEmbed"] = None, embeds: Optional[Sequence["UserEmbed"]] = None, components: Optional["Components"] = None, files: Optional[List[Union[str, bytes]]] = None, mentions: Optional[list] = [], stickers: Optional[List["Sticker"]] = None, other: Optional[dict] = {}) -> "Message":
        other["message_reference"] = {"guild_id": self.guild.id, "channel_id": self.channel.id, "message_id": self.id}
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

    async def edit(self, content: Optional[str] = None, *, embed: Optional["UserEmbed"] = None, embeds: Optional[Sequence["UserEmbed"]] = None, components: Optional["Components"] = None, files: Optional[List[Union[str, bytes]]] = None, mentions: Optional[list] = [], stickers: Optional[List["Sticker"]] = None, other: Optional[dict] = {}) -> "Message":
        channel_id = self.channel

        if isinstance(self.channel, Channel):
            channel_id = self.channel.id

        response = await self.__client.http.edit_message(channel_id, self.id, content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

        if response is not None:
            return await Message.from_raw(self.__client, response)

    async def delete(self) -> Union[dict, str]:
        return await self.__client.http.delete_message(self.channel.id, self.id)