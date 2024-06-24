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

from ..http import Route
from ..enums import *
from ..utils import *
from ..errors import InvalidArgument

from .channel import Channel
from .user import User
from .role import Role
from .emoji import Emoji
from .sticker import Sticker
from .member import Member

from datetime import datetime

from typing import Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client

CDN_URL = "https://cdn.discordapp.com"
EXTENSIONS = ("png", "jpg", "jpeg", "webp", "gif")

@dataclass
class WelcomeScreenChannel:
    __client: "Client"
    channel: Channel
    description: str
    emoji_id: str
    emoji_name: str

    @classmethod
    async def from_raw(cls, client, channels: List[Channel], channel: Dict):
        channel["channel"] = [_channel := [_channel for _channel in channels if _channel.id == channel["channel_id"]], _channel if len(_channel) >= 1 else None][1]

        return cls(client, **channel)

@dataclass
class WelcomeScreen:
    __client: "Client"
    description: str
    welcome_channels: List[WelcomeScreenChannel]

    @classmethod
    async def from_raw(cls, client, channels: List[Channel], welcomescreen: Dict):
        welcomescreen["welcome_channels"] = [await WelcomeScreenChannel.from_raw(client, channels, channel) for channel in welcomescreen["welcome_channels"]]

        return cls(client, **welcomescreen)

@dataclass
class Guild:
    __client: "Client"
    id: str
    name: str
    icon: str
    icon_url: str
    splash: str
    discovery_splash: str
    afk_timeout: int
    verification_level: VerificationLevel
    default_message_notifications: DefaultMessageNotification
    explicit_content_filter: ExplicitContentFilter
    roles: List[Role]
    features: List[str]
    mfa_level: MfaLevel
    joined_at: datetime
    large: bool
    member_count: int
    members: List[Member]
    channels: List[Channel]
    threads: List[Channel]
    description: str
    banner: str
    banner_url: str
    premium_tier: int
    premium_subscription_count: int
    preferred_locale: str
    nsfw_level: NSFWLevel
    stickers: List[Sticker]
    premium_progress_bar_enabled: bool
    created_at: datetime
    owner: Optional[Member] = None
    afk_channel: Optional[Channel] = None
    system_channel: Optional[Channel] = None
    rules_channel: Optional[Channel] = None
    vanity_url: Optional[str] = None
    public_updates_channel: Optional[Channel] = None
    emojis: Optional[List[Emoji]] = None
    icon_hash: Optional[str] = None
    widget_enabled: Optional[bool] = None
    widget_channel: Optional[Channel] = None
    approximate_member_count: Optional[int] = None
    welcome_screen: Optional[WelcomeScreen] = None
    me: Optional[Member] = None

    __CHANGE_KEYS__ = (
        (
            "rules_channel_id",
            "rules_channel"
        ),
        (
            "system_channel_id",
            "system_channel"
        ),
        (
            "vanity_url_code",
            "vanity_url"
        ),
        (
            "public_updates_channel_id",
            "public_updates_channel"
        ),
        (
            "afk_channel_id",
            "afk_channel"
        ),
        (
            "owner_id",
            "owner"
        )
    )

    def __str__(self) -> str:
        return "<Guild id={!r} name={!r} owner={!r}>".format(self.id, self.name, self.owner)

    def __repr__(self) -> str:
        return "<Guild id={!r} name={!r} owner={!r}>".format(self.id, self.name, self.owner)

    @classmethod
    async def from_raw(cls, client, guild: Dict) -> "Guild":
        icon_url = CDN_URL + "/icons/%s/%s.%s" % (guild["id"], guild["icon"], "gif" if guild["icon"] and guild["icon"][:2] == "a_" else "png")
        banner_url = CDN_URL + "/banners/%s/%s.%s" % (guild["id"], guild["banner"], "gif" if guild["banner"] and guild["banner"][:2] == "a_" else "png")

        if guild["icon"] is None:
            icon_url = CDN_URL + "/embed/avatars/%s.png" % (int(guild["id"]) % 5)

        if guild["banner"] is None:
            banner_url = None

        channels = [await Channel.from_raw(client, channel) for channel in guild["channels"]]

        guild["verification_level"] = VerificationLevel(guild["verification_level"])
        guild["default_message_notifications"] = DefaultMessageNotification(guild["default_message_notifications"])
        guild["explicit_content_filter"] = ExplicitContentFilter(guild["explicit_content_filter"])
        guild["roles"] = sorted([await Role.from_raw(client, role) for role in guild["roles"]], key=lambda role: role.position)
        guild["emojis"] = [await Emoji.from_raw(client, emoji) for emoji in guild["emojis"]]
        guild["mfa_level"] = MfaLevel(guild["mfa_level"])
        guild["joined_at"] = parse_time(guild["joined_at"])
        guild["members"] = []
        guild["channels"] = channels
        guild["threads"] = [await Channel.from_raw(client, thread) for thread in guild["threads"]]
        guild["nsfw_level"] = NSFWLevel(guild["nsfw_level"])
        guild["stickers"] = [await Sticker.from_raw(client, sticker) for sticker in guild["stickers"]]
        guild["created_at"] = time_from_snowflake(guild["id"])
        guild["icon_url"] = icon_url
        guild["banner_url"] = banner_url

        if "public_updates_channel" in guild:
            index = get_index(guild["channels"], guild["public_updates_channel"], key=lambda channel: channel.id)
            guild["public_updates_channel"] = guild["channels"][index] if index is not None else None
        if "afk_channel" in guild:
            index = get_index(guild["channels"], guild["afk_channel"], key=lambda channel: channel.id)
            guild["afk_channel"] = guild["channels"][index] if index is not None else None
        if "system_channel" in guild:
            index = get_index(guild["channels"], guild["system_channel"], key=lambda channel: channel.id)
            guild["system_channel"] = guild["channels"][index] if index is not None else None
        if "rules_channel" in guild:
            index = get_index(guild["channels"], guild["rules_channel"], key=lambda channel: channel.id)
            guild["rules_channel"] = guild["channels"][index] if index is not None else None
        if "widget_channel" in guild:
            index = get_index(guild["channels"], guild["widget_channel"], key=lambda channel: channel.id)
            guild["widget_channel"] = guild["channels"][index] if index is not None else None
        if "welcome_screen" in guild:
            guild["welcome_screen"] = await WelcomeScreen.from_raw(client, channels, guild["welcome_screen"])

        return cls(client, **guild)

    def get_channel(self, channel_id_or_name: str) -> Union[Channel, None]:
        if not channel_id_or_name:
            return

        for channel in self.channels + self.threads:
            if channel.name.lower() == channel_id_or_name.lower() or channel.id == channel_id_or_name:
                return channel

    def get_role(self, role_id_or_name: str) -> Union[Role, None]:
        if not role_id_or_name:
            return

        for role in self.roles:
            if role.name.lower() == role_id_or_name.lower() or role.id == role_id_or_name:
                return role

    def get_emoji(self, emoji_name_or_id: str) -> Union[Emoji, None]:
        if not emoji_name_or_id:
            return

        if self.emojis is None:
            return

        for emoji in self.emojis:
            if emoji.name.lower() == emoji_name_or_id.lower() or emoji.id == emoji_name_or_id:
                return emoji

    def get_sticker(self, sticker_name_or_id: str) -> Union[Sticker, None]:
        if not sticker_name_or_id:
            return

        for sticker in self.stickers:
            if sticker.name.lower() == sticker_name_or_id.lower() or sticker.id == sticker_name_or_id:
                return sticker

    def icon_as(self, extension: str) -> str:
        if not extension in EXTENSIONS:
            raise InvalidArgument("Invalid extension")

        return CDN_URL + "/icons/%s/%s.%s" % (self.id, self.icon, extension)

    def banner_as(self, extension: str) -> str:
        if not extension in EXTENSIONS:
            raise InvalidArgument("Invalid extension")

        return CDN_URL + "/banners/%s/%s.%s" % (self.id, self.banner, extension)

    async def fetch_member(self, member_id: str) -> Dict[str, str]:
        return await self.__client.http.request(Route("GET", "guilds", self.id, "members", member_id))

    async def get_member(self, member: Union[dict, str], user: Optional[Union[User, dict]] = None) -> Member:
        for cached_member in self.members:
            if isinstance(member, str):
                if member.lower() in (cached_member.user.username.lower(), (cached_member.nick or "").lower(), cached_member.user.id):
                    return cached_member
            elif isinstance(member, dict):
                if user is not None:
                    if isinstance(user, User):
                        if user.id == cached_member.user.id:
                            return cached_member
                    elif isinstance(user, dict):
                        if user["id"] == cached_member.user.id:
                            return cached_member
                elif "user" in member:
                    if member["user"]["id"] == cached_member.user.id:
                        return cached_member

        if isinstance(member, str):
            member = await self.fetch_member(member)

        if isinstance(user, dict):
            user = await self.__client.gateway.get_user(user)

        if not user and "user" in member:
            user = await self.__client.gateway.get_user(member["user"])

        member = await Member.from_raw(self.__client, self, member, user)
        self.members.append(member)

        return member

    async def ban(self, user: User, reason: Optional[str] = None, delete_message_seconds: Optional[int] = 0) -> Union[dict, str]:
        return await self.__client.http.ban_member(self.id, user.id, reason=reason, delete_message_seconds=delete_message_seconds)

    async def unban(self, member_id: str, reason: Optional[str] = None) -> Union[dict, str]:
        return await self.__client.http.unban_member(self.id, member_id, reason=reason)