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
from ..errors import InvalidArgument
from .channel import Channel
from datetime import datetime

CDN_URL = "https://cdn.discordapp.com"

@modified_dataclass
class User:
    id: str
    username: str
    avatar: str
    avatar_url: str
    created_at: datetime
    global_name: str = None
    display_name: str = None
    public_flags: Sequence[PublicFlags] = None
    bot: bool = None
    system: bool = None
    banner: str = None
    accent_color: int = None
    avatar_decoration: None = None
    verified: bool = None
    mfa_enabled: bool = None
    locale: str = None
    email: str = None
    flags: UserFlags = None
    premium_type: PremiumTypes = None
    banner_color: int = None
    purchased_flags: int = None
    premium_usage_flags: int = None
    premium: bool = None
    phone: str = None
    nsfw_allowed: bool = None
    mobile: bool = None
    desktop: bool = None
    bio: str = None
    dm: Channel = None

    def __str__(self):
        return self.username

    def __repr__(self):
        return "<User id={!r} username={!r} public_flags={!r}>".format(self.id, self.username, self.public_flags)

    def avatar_as(self, extension):
        if not extension in ("png", "jpg", "jpeg", "webp", "gif"):
            raise InvalidArgument("Invalid extension")

        if self.avatar is None:
            return self.avatar_url

        return CDN_URL + "/avatars/%s/%s.%s" % (self.id, self.avatar, extension)

    @classmethod
    def from_raw(cls, user):
        avatar_url = CDN_URL + "/avatars/%s/%s.%s" % (user["id"], user["avatar"], "gif" if user["avatar"] and user["avatar"][:2] == "a_" else "png")

        if user["avatar"] is None:
            avatar_url = CDN_URL + "/embed/avatars/%s.png" % ((int(user["id"]) >> 22) % 5)

        user["avatar_url"] = avatar_url
        user["created_at"] = time_from_snowflake(user["id"])

        if "public_flags" in user:
            user["public_flags"] = [flag for flag in PublicFlags if user["public_flags"] & flag.value == flag.value]
        if "flags" in user:
            user["flags"] = [flag for flag in UserFlags if user["flags"] & flag.value == flag.value]
        if "premium_type" in user:
            user["premium_type"] = PremiumTypes(user["premium_type"])
        if "banner_color" in user and user["banner_color"] is not None:
            user["banner_color"] = int(user["banner_color"][1:], 16)

        return cls(**user)