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

from dataclasses import modified_dataclass
from typing import TypeVar, Sequence
from ..enums import *
from ..utils import *
from .channel import Channel
from .guild import Guild
from .user import User
from .emoji import Emoji
from .member import Member
from .role import Role
from .embed import Embed
from .sticker import Sticker
from .interaction import Interaction
from datetime import datetime

MessageComponents = TypeVar("MessageComponents")

@modified_dataclass
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

@modified_dataclass
class MessageReference:
    message_id: str = None
    channel_id: str = None
    guild_id: str = None
    fail_if_not_exists: bool = None

@modified_dataclass
class MessageSticker:
    id: str
    name: str
    format_type: StickerFormatTypes

    @classmethod
    def from_raw(cls, sticker):
        sticker["format_type"] = StickerFormatTypes(sticker["format_type"])

        return cls(**sticker)

@modified_dataclass
class SelectOptions:
    label: str
    value: str
    description: str = None
    emoji: Emoji = None
    default: bool = None

    @classmethod
    def from_raw(cls, option):
        if "emoji" in option:
            option["emoji"] = Emoji(**option["emoji"])

        return cls(**option)

@modified_dataclass
class MessageComponents:
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
    components: Sequence[MessageComponents] = None
    value: str = None

    @classmethod
    def from_raw(cls, component):
        if "hash" in component: del component["hash"]

        component["type"] = ComponentTypes(component["type"])

        if "components" in component:
            component["components"] = [cls.from_raw(components) for components in component["components"]]
        if "style" in component:
            component["style"] = ButtonStyles(component["style"])
        if "emoji" in component:
            component["emoji"] = Emoji(**component["emoji"])
        if "options" in component:
            component["options"] = [SelectOptions.from_raw(option) for option in component["options"]]

        return cls(**component)

@modified_dataclass
class MessageReaction:
    count: int
    me: bool
    emoji: Emoji

    @classmethod
    def from_raw(cls, reaction):
        reaction["emoji"] = Emoji.from_raw(reaction["emoji"])

        return cls(**reaction)

@modified_dataclass
class Message:
    id: str
    channel: Channel = None
    author: User = None
    content: str = None
    mention_everyone: bool = None
    pinned: bool = None
    tts: bool = None
    type: MessageTypes = None
    flags: int = None
    mentions: Sequence[User] = None
    attachments: Sequence[Attachment] = None
    mention_roles: Sequence[Role] = None
    embeds: Sequence[Embed] = None
    components: Sequence[MessageComponents] = None
    guild: Guild = None
    member: Member = None
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
    async def from_raw(cls, gateway, message):
        for guild in gateway.guilds:
            if isinstance(message["channel"], Channel) is False:
                channel = guild.get_channel(message["channel"])
                if channel is not None:
                    message["channel"] = channel

        if "guild" in message:
            message["guild"] = gateway.get_guild(message["guild"])

            if "member" in message:
                message["member"] = await message["guild"].get_member(message["member"], message["author"])
                message["author"] = message["member"].user
            if "interaction" in message:
                message["interaction"] = await Interaction.from_raw(gateway, message["interaction"])
            if "thread" in message:
                message["thread"] = message["guild"].get_channel(message["thread"])
            if "mentions" in message:
                message["mentions"] = [await gateway.get_user(mention["id"]) for mention in message["mentions"]]
            if "mention_channels" in message:
                message["mention_channels"] = [message["guild"].get_channel(channel["id"]) for channel in message["mention_channels"]]
            if "mention_roles" in message:
                message["mention_roles"] = [message["guild"].get_role(role_id) for role_id in message["mention_roles"]]

        if "author" in message and "member" not in message:
            message["author"] = await gateway.get_user(message["author"])
        if "timestamp" in message:
            message["timestamp"] = parse_time(message["timestamp"])
        if "edited_timestamp" in message:
            message["edited_timestamp"] = parse_time(message["edited_timestamp"])
        if "sticker_items" in message:
            message["sticker_items"] = [MessageSticker.from_raw(sticker) for sticker in message["sticker_items"]]
        if "reactions" in message:
            message["reactions"] = [MessageReaction.from_raw(reaction) for reaction in message["reactions"]]
        if "message_reference" in message:
            message["message_reference"] = MessageReference(**message["message_reference"])
        if "attachments" in message:
            message["attachments"] = [Attachment(**attachment) for attachment in message["attachments"]]
        if "type" in message:
            message["type"] = MessageTypes(message["type"])
        if "components" in message:
            message["components"] = [MessageComponents.from_raw(component) for component in message["components"]]
        if "embeds" in message:
            message["embeds"] = [Embed.from_raw(embed) for embed in message["embeds"]]
        if "flags" in message:
            message["flags"] = [flag for flag in MessageFlags if message["flags"] & flag.value == flag.value]

        return cls(**message)