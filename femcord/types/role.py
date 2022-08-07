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
from ..enums import *
from ..utils import *
from ..permissions import Permissions
from datetime import datetime

@modified_dataclass
class Role:
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
    def from_raw(cls, role):
        role["permissions"] = Permissions.from_int(int(role["permissions"]))
        role["created_at"] = time_from_snowflake(role["id"])

        return cls(**role)