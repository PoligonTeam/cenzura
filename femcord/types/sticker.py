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
from .user import User
from datetime import date, datetime

@modified_dataclass
class Sticker:
    id: str
    name: str
    description: str
    type: StickerTypes
    format_type: StickerFormatTypes
    available: bool
    created_at: datetime
    pack_id: str = None
    user: User = None
    sort_value: int = None

    def __str__(self):
        return "<Sticker id={!r} name={!r} description={!r}>".format(self.id, self.name, self.description)

    def __repr__(self):
        return "<Sticker id={!r} name={!r} description={!r}>".format(self.id, self.name, self.description)

    @classmethod
    def from_raw(cls, sticker):
        sticker["created_at"] = time_from_snowflake(sticker["id"])

        return cls(**sticker)