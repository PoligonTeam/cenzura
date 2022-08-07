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
from .user import User
from .role import Role
from .presence import Presence
from .voice import VoiceState
from datetime import datetime

@modified_dataclass
class Member:
    user: User
    roles: Sequence[Role]
    permissions: Permissions
    joined_at: datetime
    guild_id: str
    deaf: bool = None
    mute: bool = None
    nick: str = None
    avatar: str = None
    premium_since: datetime = None
    pending: bool = None
    is_pending: bool = None
    hoisted_role: Role = None
    communication_disabled_until: datetime = None
    presence: Presence = None
    voice_state: VoiceState = None

    def __str__(self):
        return "<Member user={!r} roles={!r} presence={!r}>".format(self.user, self.roles, self.presence)

    def __repr__(self):
        return "<Member user={!r} roles={!r} presence={!r}>".format(self.user, self.roles, self.presence)

    @classmethod
    def from_raw(cls, guild, member, user):
        member["user"] = user
        member["guild_id"] = guild.id

        if member is not None:
            member["roles"] = [guild.roles[0]] + sorted((guild.get_role(role) for role in member["roles"]), key=lambda role: role.position if role else 0)
            member["permissions"] = Permissions(*set(permission for permissions in [role.permissions.permissions for role in member["roles"] if role] for permission in permissions))
            member["joined_at"] = parse_time(member["joined_at"])

            if "premium_since" in member:
                member["premium_since"] = parse_time(member["premium_since"])
            if "communication_disabled_until" in member:
                member["communication_disabled_until"] = parse_time(member["communication_disabled_until"])

            for role in member["roles"][::-1]:
                if role.hoist is True:
                    member["hoisted_role"] = role
                    break

        member["voice_state"] = VoiceState(*[None] * 7)

        return cls(**member)