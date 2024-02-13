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
from typing import Sequence
from ..enums import *
from ..utils import *
from datetime import datetime

@modified_dataclass
class EmbedFooter:
    text: str
    icon_url: str = None
    proxy_icon_url: str = None

@modified_dataclass
class EmbedImage:
    url: str
    height: int
    width: int
    proxy_url: str = None
    placeholder_version: object = None
    placeholder: object = None

@modified_dataclass
class EmbedThumbnail:
    url: str
    height: int
    width: int
    proxy_url: str = None
    placeholder_version: object = None
    placeholder: object = None

@modified_dataclass
class EmbedVideo:
    url: str
    height: int
    width: int
    proxy_url: str = None
    placeholder_version: object = None
    placeholder: object = None

@modified_dataclass
class EmbedProvider:
    name: str
    url: str = None

@modified_dataclass
class EmbedAuthor:
    name: str
    icon_url: str = None
    proxy_icon_url: str = None
    url: str = None

@modified_dataclass
class EmbedField:
    name: str
    value: str
    inline: bool

@modified_dataclass
class Embed:
    type: str
    title: str = None
    description: str = None
    url: str = None
    timestamp: datetime = None
    color: int = None
    footer: EmbedFooter = None
    image: EmbedImage = None
    thumbnail: EmbedThumbnail = None
    video: EmbedVideo = None
    provider: EmbedProvider = None
    author: EmbedAuthor = None
    fields: Sequence[EmbedField] = None
    reference_id: str = None
    placeholder_version: object = None

    @classmethod
    def from_raw(cls, embed):
        if "timestamp" in embed:
            embed["timestamp"] = parse_time(embed["timestamp"])
        if "footer" in embed:
            embed["footer"] = EmbedFooter(**embed["footer"])
        if "image" in embed:
            embed["image"] = EmbedImage(**embed["image"])
        if "thumbnail" in embed:
            embed["thumbnail"] = EmbedThumbnail(**embed["thumbnail"])
        if "video" in embed:
            embed["video"] = EmbedVideo(**embed["video"])
        if "provider" in embed:
            embed["provider"] = EmbedProvider(**embed["provider"])
        if "author" in embed:
            embed["author"] = EmbedAuthor(**embed["author"])
        if "fields" in embed:
            embed["fields"] = [EmbedField(**field) for field in embed["fields"]]

        return cls(**embed)