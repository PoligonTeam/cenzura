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
from ..permissions import Permissions
from datetime import datetime

@modified_dataclass
class PermissionOverwrite:
    type: OverwriteTypes
    allow: Permissions
    deny: Permissions
    id: str = None
    user_id: str = None
    role_id: str = None

    @classmethod
    def from_raw(cls, overwrite):
        overwrite["role_id" if overwrite["type"] == OverwriteTypes.ROLE else "user_id"] = overwrite["id"]
        overwrite["allow"] = Permissions.from_int(int(overwrite["allow"]))
        overwrite["deny"] = Permissions.from_int(int(overwrite["deny"]))

        return cls(**overwrite)

@modified_dataclass
class ThreadMetadata:
    archived: bool
    auto_archive_duration: int
    archive_timestamp: datetime
    create_timestamp: datetime
    locked: bool
    invitable: bool = None

    @classmethod
    def from_raw(cls, metadata):
        metadata["archive_timestamp"] = parse_time(metadata["archive_timestamp"])
        metadata["create_timestamp"] = parse_time(metadata["create_timestamp"])

        return cls(**metadata)

@modified_dataclass
class ThreadMember:
    id: str = None
    user_id: str = None
    join_timestamp: datetime = None
    flags: int = None

    @classmethod
    def from_raw(cls, member):
        if "datetime" in member:
            member["datetime"] = parse_time(member["datetime"])

        return cls(**member)

@modified_dataclass
class Channel:
    id: str
    type: ChannelTypes
    name: str = None
    position: int = None
    permission_overwrites: Sequence[PermissionOverwrite] = None
    topic: str = None
    nsfw: bool = None
    bitrate: int = None
    user_limit: int = None
    rate_limit_per_user: int = None
    application_id: str = None
    parent_id: str = None
    last_pin_timestamp: datetime = None
    message_count: int = None
    thread_metadata: ThreadMetadata = None
    member: ThreadMember = None
    default_auto_archive_duration: int = None
    rtc_region: str = None
    created_at: datetime = None

    def __str__(self):
        return "<Channel id={!r} name={!r} type={!r} position={!r}>".format(self.id, self.name, self.type, self.position)

    def __repr__(self):
        return "<Channel id={!r} name={!r} type={!r} position={!r}>".format(self.id, self.name, self.type, self.position)

    @classmethod
    def from_raw(cls, channel):
        channel["type"] = ChannelTypes(channel["type"])
        channel["created_at"] = time_from_snowflake(channel["id"])

        if "permission_overwrites" in channel:
            channel["permission_overwrites"] = [PermissionOverwrite.from_raw(overwrite) for overwrite in channel["permission_overwrites"]]
        if "last_pin_timestamp" in channel:
            channel["last_pin_timestamp"] = parse_time(channel["last_pin_timestamp"])
        if "thread_metadata" in channel:
            channel["thread_metadata"] = ThreadMetadata.from_raw(channel["thread_metadata"]) if channel["thread_metadata"] else None
        if "member" in channel:
            channel["member"] = ThreadMember.from_raw(channel["member"]) if channel["member"] else None
        if "nsfw" not in channel or channel["nsfw"] is None:
            channel["nsfw"] = False

        return cls(**channel)