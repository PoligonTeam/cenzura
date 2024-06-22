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

from datetime import datetime

from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from ..commands import Context

@dataclass
class Role:
    __client: "Client"
    id: str
    name: str
    color: int
    hoist: bool
    icon: str
    unicode_emoji: str
    position: int
    permissions: Permissions
    managed: bool
    mentionable: bool
    created_at: datetime

    def __str__(self):
        return "<Role id={!r} name={!r} color={!r} position={!r}>".format(self.id, self.name, self.color, self.position)

    def __repr__(self):
        return "<Role id={!r} name={!r} color={!r} position={!r}>".format(self.id, self.name, self.color, self.position)

    @classmethod
    async def from_raw(cls, client, role):
        role["permissions"] = Permissions.from_int(int(role["permissions"]))
        role["created_at"] = time_from_snowflake(role["id"])

        return cls(client, **role)

    @classmethod
    def from_arg(cls, ctx: "Context", argument) -> Union["Role", None]:
        result = ID_PATTERN.search(argument)

        if result is not None:
            argument = result.group()

        return ctx.guild.get_role(argument)