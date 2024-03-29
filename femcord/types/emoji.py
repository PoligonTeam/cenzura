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
from datetime import datetime

@modified_dataclass
class Emoji:
    name: str
    id: str = None
    created_at: datetime = None
    animated: bool = None
    require_colons: bool = None
    managed: bool = None
    available: bool = None

    def __str__(self):
        return "<Emoji id={!r} name={!r} animated={!r}>".format(self.id, self.name, self.animated)

    def __repr__(self):
        return "<Emoji id={!r} name={!r} animated={!r}>".format(self.id, self.name, self.animated)

    @classmethod
    def from_raw(cls, emoji):
        if emoji.get("id", None) is not None:
            emoji["created_at"] = time_from_snowflake(emoji["id"])

        return cls(**emoji)