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
from typing import Sequence
from ..enums import *
from ..utils import *
from ..errors import InvalidArgument
from .channel import Channel
from .role import Role
from .emoji import Emoji
from .sticker import Sticker
from .member import Member
from datetime import datetime

CDN_URL = "https://cdn.discordapp.com"

@modified_dataclass
class WelcomeScreenChannel:
    channel: Channel
    description: str
    emoji_id: str
    emoji_name: str

    @classmethod
    def from_raw(cls, channels, channel):
        channel["channel"] = [channel := [channel for channel in channels if channel.id == channel["channel_id"]], channel if len(channel) >= 1 else None][1]

        return cls(**channel)

@modified_dataclass
class WelcomeScreen:
    description: str
    welcome_channels: Sequence[WelcomeScreenChannel]

    @classmethod
    def from_raw(cls, channels, welcomescreen):
        welcomescreen["welcome_channels"] = [WelcomeScreenChannel.from_raw(channels, channel) for channel in welcomescreen["welcome_channels"]]

        return cls(**welcomescreen)

@modified_dataclass
class Guild:
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
    roles: Sequence[Role]
    features: Sequence[str]
    mfa_level: MfaLevel
    joined_at: datetime
    large: bool
    member_count: int
    members: Sequence[Member]
    channels: Sequence[Channel]
    threads: Sequence[Channel]
    description: str
    banner: str
    banner_url: str
    premium_tier: int
    premium_subscription_count: int
    preferred_locale: str
    nsfw_level: NSFWLevel
    stickers: Sequence[Sticker]
    premium_progress_bar_enabled: bool
    created_at: datetime
    owner: Member = None
    afk_channel: Channel = None
    system_channel: Channel = None
    rules_channel: Channel = None
    vanity_url: str = None
    public_updates_channel: Channel = None
    emojis: Sequence[Emoji] = None
    icon_hash: str = None
    widget_enabled: bool = None
    widget_channel: Channel = None
    approximate_member_count: int = None
    welcome_screen: WelcomeScreen = None
    me: Member = None

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

    def __str__(self):
        return "<Guild id={!r} name={!r} owner={!r}>".format(self.id, self.name, self.owner)

    def __repr__(self):
        return "<Guild id={!r} name={!r} owner={!r}>".format(self.id, self.name, self.owner)

    def get_channel(self, channel_id_or_name):
        if not channel_id_or_name:
            return

        for channel in self.channels:
            if channel.name.lower() == channel_id_or_name.lower() or channel.id == channel_id_or_name:
                return channel

    def get_role(self, role_id_or_name):
        if not role_id_or_name:
            return

        for role in self.roles:
            if role.name.lower() == role_id_or_name.lower() or role.id == role_id_or_name:
                return role

    def get_emoji(self, emoji_name_or_id):
        if not emoji_name_or_id:
            return

        for emoji in self.emojis:
            if emoji.name.lower() == emoji_name_or_id.lower() or emoji.id == emoji_name_or_id:
                return emoji

    def get_sticker(self, sticker_name_or_id):
        if not sticker_name_or_id:
            return

        for sticker in self.stickers:
            if sticker.name.lower() == sticker_name_or_id.lower() or sticker.id == sticker_name_or_id:
                return sticker

    def icon_as(self, extension):
        if not extension in ("png", "jpg", "jpeg", "webp", "gif"):
            raise InvalidArgument("Invalid extension")

        return CDN_URL + "/icons/%s/%s.%s" % (self.id, self.icon, extension)

    def banner_as(self, extension):
        if not extension in ("png", "jpg", "jpeg", "webp", "gif"):
            raise InvalidArgument("Invalid extension")

        return CDN_URL + "/banners/%s/%s.%s" % (self.id, self.banner, extension)

    @classmethod
    def from_raw(cls, guild):
        icon_url = CDN_URL + "/icons/%s/%s.%s" % (guild["id"], guild["icon"], "gif" if guild["icon"] and guild["icon"][:2] == "a_" else "png")
        banner_url = CDN_URL + "/banners/%s/%s.%s" % (guild["id"], guild["banner"], "gif" if guild["banner"] and guild["banner"][:2] == "a_" else "png")

        if guild["icon"] is None:
            icon_url = CDN_URL + "/embed/avatars/%s.png" % (int(guild["id"]) % 5)

        if guild["banner"] is None:
            banner_url = None

        channels = [Channel.from_raw(channel) for channel in guild["channels"]]

        guild["verification_level"] = VerificationLevel(guild["verification_level"])
        guild["default_message_notifications"] = DefaultMessageNotification(guild["default_message_notifications"])
        guild["explicit_content_filter"] = ExplicitContentFilter(guild["explicit_content_filter"])
        guild["roles"] = sorted((Role.from_raw(role) for role in guild["roles"]), key=lambda role: role.position)
        guild["emojis"] = [Emoji.from_raw(emoji) for emoji in guild["emojis"]]
        guild["mfa_level"] = MfaLevel(guild["mfa_level"])
        guild["joined_at"] = parse_time(guild["joined_at"])
        guild["members"] = []
        guild["channels"] = channels
        guild["threads"] = [Channel.from_raw(thread) for thread in guild["threads"]]
        guild["nsfw_level"] = NSFWLevel(guild["nsfw_level"])
        guild["stickers"] = [Sticker.from_raw(sticker) for sticker in guild["stickers"]]
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
            guild["welcome_screen"] = WelcomeScreen.from_raw(channels, guild["welcome_screen"])

        return cls(**guild)