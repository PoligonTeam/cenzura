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

from typing import List, Optional, Sequence, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from ..embed import Embed
    from ..components import Components
    from .guild import Guild
    from .channel import Channel
    from .message import Message, MessageComponents
    from .member import Member
    from .user import User

@dataclass
class InteractionDataOption:
    __client: "Client"
    name: str
    type: CommandOptionTypes
    value: Union[str, int, float] = None
    options: Sequence["InteractionDataOption"] = None
    focused: bool = None

    @classmethod
    async def from_raw(cls, client, dataoption):
        dataoption["type"] = CommandOptionTypes(dataoption["type"])

        if "options" in dataoption:
            dataoption["options"] = [await cls.from_raw(client, dataoption) for dataoption in dataoption["options"]]

        return cls(client, **dataoption)

@dataclass
class InteractionData:
    __client: "Client"
    id: str = None
    name: str = None
    type: CommandTypes = None
    options: Sequence[InteractionDataOption] = None
    custom_id: str = None
    component_type: ComponentTypes = None
    values: list = None
    target: Union["User", "Message"] = None
    components: Sequence["MessageComponents"] = None

    __CHANGE_KEYS__ = (
        (
            "target_id",
            "target"
        ),
    )

    @classmethod
    async def from_raw(cls, client, data):
        if "type" in data:
            data["type"] = CommandTypes(data["type"])
        if "options" in data:
            data["options"] = [await InteractionDataOption.from_raw(client, dataoption) for dataoption in data["options"]]
        if "component_type" in data:
            data["component_type"] = ComponentTypes(data["component_type"])
        if "target" in data:
            if data["type"] == CommandTypes.USER:
                data["target"] = await client.gateway.get_user(data["target"])

            elif data["type"] == CommandTypes.MESSAGE:
                index = get_index(client.gateway.messages, data["target"], key=lambda m: m.id)

                if index is not None:
                    data["target"] = client.gateway.messages[index]
        if "components" in data:
            data["components"] = [await MessageComponents.from_raw(client, component) for component in data["components"]]

        return cls(client, **data)

@dataclass
class Interaction:
    __client: "Client"
    id: str
    type: InteractionTypes = None
    application_id: str = None
    token: str = None
    version: int = None
    data: InteractionData = None
    guild: "Guild" = None
    channel: "Channel" = None
    member: "Member" = None
    name: str = None
    user: "User" = None
    message: "Message" = None

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
        return "<Interaction id={!r} type={!r}>".format(self.id, self.type)

    def __repr__(self):
        return "<Interaction id={!r} type={!r}>".format(self.id, self.type)

    @classmethod
    async def from_raw(cls, client, interaction):
        if "type" in interaction:
            interaction["type"] = InteractionTypes(interaction["type"])
        if "data" in interaction:
            interaction["data"] = await InteractionData.from_raw(client, interaction["data"])
        if "guild" in interaction:
            interaction["guild"] = client.gateway.get_guild(interaction["guild"])
        if "channel" in interaction and "guild" in interaction:
            interaction["channel"] = interaction["guild"].get_channel(interaction["channel"])
        if "member" in interaction and "guild" in interaction:
            interaction["member"] = await interaction["guild"].get_member(interaction["member"])
        if "user" in interaction:
            interaction["user"] = await client.gateway.get_user(interaction["user"])
        if "message" in interaction:
            index = get_index(client.gateway.messages, interaction["message"]["id"], key=lambda m: m.id)

            if index is not None:
                interaction["message"] = client.gateway.messages[index]

        return cls(client, **interaction)

    async def callback(self, interaction_type: InteractionCallbackTypes, content: Optional[str] = None, *, title: Optional[str] = None, custom_id: Optional[str] = None, embed: "Embed" = None, embeds: Sequence["Embed"] = None, components: Optional["Components"] = None, files: Optional[List[Union[str, bytes]]] = None, mentions: Optional[list] = [], other: Optional[dict] = {}):
        return await self.__client.http.interaction_callback(self.id, self.token, interaction_type, content, title=title, custom_id=custom_id, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)