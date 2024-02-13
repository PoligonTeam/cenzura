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

from dataclasses import modified_dataclass
from ..enums import *
from ..utils import *
from .guild import Guild
from .channel import Channel
from .role import Role
from .member import Member
from .user import User
from typing import TypeVar, Sequence, Union

Message = TypeVar("Message")
MessageComponents = TypeVar("MessageComponents")
InteractionDataOption = TypeVar("InteractionDataOption")

@modified_dataclass
class InteractionDataOption:
    name: str
    type: CommandOptionTypes
    value: Union[str, int, float] = None
    options: Sequence[InteractionDataOption] = None
    focused: bool = None

    @classmethod
    def from_raw(cls, dataoption):
        dataoption["type"] = CommandOptionTypes(dataoption["type"])

        if "options" in dataoption:
            dataoption["options"] = [cls.from_raw(dataoption) for dataoption in dataoption["options"]]

        return cls(**dataoption)

@modified_dataclass
class InteractionData:
    id: str = None
    name: str = None
    type: CommandTypes = None
    options: Sequence[InteractionDataOption] = None
    custom_id: str = None
    component_type: ComponentTypes = None
    values: list = None
    target: Union[User, Message] = None
    components: Sequence[MessageComponents] = None

    __CHANGE_KEYS__ = (
        (
            "target_id",
            "target"
        ),
    )

    @classmethod
    async def from_raw(cls, gateway, data):
        if "type" in data:
            data["type"] = CommandTypes(data["type"])
        if "options" in data:
            data["options"] = [InteractionDataOption.from_raw(dataoption) for dataoption in data["options"]]
        if "component_type" in data:
            data["component_type"] = ComponentTypes(data["component_type"])
        if "target" in data:
            if data["type"] == CommandTypes.USER:
                data["target"] = await gateway.get_user(data["target"])

            elif data["type"] == CommandTypes.MESSAGE:
                index = get_index(gateway.messages, data["target"], key=lambda m: m.id)

                if index is not None:
                    data["target"] = gateway.messages[index]
        if "components" in data:
            data["components"] = [MessageComponents.from_raw(component) for component in data["components"]]

        return cls(**data)

@modified_dataclass
class Interaction:
    id: str
    type: InteractionTypes = None
    application_id: str = None
    token: str = None
    version: int = None
    data: InteractionData = None
    guild: Guild = None
    channel: Channel = None
    member: Member = None
    name: str = None
    user: User = None
    message: Message = None

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
    async def from_raw(cls, gateway, interaction):
        if "type" in interaction:
            interaction["type"] = InteractionTypes(interaction["type"])
        if "data" in interaction:
            interaction["data"] = await InteractionData.from_raw(gateway, interaction["data"])
        if "guild" in interaction:
            interaction["guild"] = gateway.get_guild(interaction["guild"])
        if "channel" in interaction and "guild" in interaction:
            interaction["channel"] = interaction["guild"].get_channel(interaction["channel"])
        if "member" in interaction and "guild" in interaction:
            interaction["member"] = await interaction["guild"].get_member(interaction["member"])
        if "user" in interaction:
            interaction["user"] = await gateway.get_user(interaction["user"])
        if "message" in interaction:
            index = get_index(gateway.messages, interaction["message"]["id"], key=lambda m: m.id)

            if index is not None:
                interaction["message"] = gateway.messages[index]

        return cls(**interaction)