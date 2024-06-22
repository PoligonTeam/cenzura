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

from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client
    from .user import User

@dataclass
class Sticker:
    __client: "Client"
    id: str
    name: str
    description: str
    type: StickerTypes
    format_type: StickerFormatTypes
    available: bool
    created_at: datetime
    pack_id: str = None
    user: "User" = None
    sort_value: int = None

    def __str__(self):
        return "<Sticker id={!r} name={!r} description={!r}>".format(self.id, self.name, self.description)

    def __repr__(self):
        return "<Sticker id={!r} name={!r} description={!r}>".format(self.id, self.name, self.description)

    @classmethod
    async def from_raw(cls, client, sticker):
        sticker["created_at"] = time_from_snowflake(sticker["id"])

        return cls(client, **sticker)