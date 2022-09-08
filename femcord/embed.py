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

from datetime import datetime, timedelta
from typing import TypeVar, Optional

Embed = TypeVar("Embed")

class Embed:
    def __init__(self, *, title: Optional[str] = None, url: Optional[str] = None, description: Optional[str] = None, color: Optional[int] = None, timestamp: Optional[datetime] = None):
        if title is not None:
            self.title: str = title
        if url is not None:
            self.url: str = url
        if description is not None:
            self.description: str = description
        if color is not None:
            self.color: str = color
        if timestamp is not None:
            if isinstance(timestamp, int):
                timestamp = datetime.fromtimestamp(timestamp)
            self.timestamp: str = (timestamp - timedelta(hours=2)).isoformat()

    def __add__(self, embed: Embed) -> Embed:
        new_embed: Embed = Embed()
        new_embed.__dict__ = self.__dict__

        for key, new_value in embed.__dict__.items():
            value: str = getattr(self, key, "")

            if isinstance(new_value, str) is True:
                setattr(new_embed, key, value + new_value)
            elif isinstance(new_value, list) is True:
                getattr(self, key).extend(new_value)
                setattr(new_embed, key, getattr(self, key))
            else:
                setattr(new_embed, key, new_value)

        return new_embed

    def set_image(self, *, url: str) -> Embed:
        self.image = {"url": url}

        return self

    def set_thumbnail(self, *, url: str) -> Embed:
        self.thumbnail = {"url": url}

        return self

    def set_footer(self, *, text: str, icon_url: Optional[str] = None) -> Embed:
        self.footer = {"text": text}

        if icon_url:
            self.footer["icon_url"] = icon_url

        return self

    def set_author(self, *, name: str, url: Optional[str] = None, icon_url: Optional[str] = None) -> Embed:
        self.author = {"name": name}

        if url:
            self.author["url"] = url
        if icon_url:
            self.author["icon_url"] = icon_url

        return self

    def add_field(self, *, name: str, value: str, inline: Optional[bool] = False) -> Embed:
        if not hasattr(self, "fields"):
            self.fields = []

        self.fields.append({
            "name": name,
            "value": value,
            "inline": inline
        })

        return self

    def add_blank_field(self, *, inline: Optional[bool] = True) -> Embed:
        return self.add_field(name="\u200b", value="\u200b", inline=inline)