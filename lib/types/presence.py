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
from typing import List, Sequence, Union, Optional
from .emoji import Emoji
from ..enums import *
from datetime import datetime

@modified_dataclass
class ActivityTimestamps:
    start: datetime = None
    end: datetime = None

    @classmethod
    def from_raw(cls, timestamps):
        if "start" in timestamps:
            timestamps["start"] = datetime.fromtimestamp(timestamps["start"] / 1000)
        if "end" in timestamps:
            timestamps["end"] = datetime.fromtimestamp(timestamps["end"] / 1000)

        return cls(**timestamps)

@modified_dataclass
class ActivityParty:
    id: str = None
    size: List[int] = None

@modified_dataclass
class ActivityAssets:
    large_image: str = None
    large_text: str = None
    small_image: str = None
    small_text: str = None

@modified_dataclass
class ActivitySecrets:
    join: str = None
    spectate: str = None
    match: str = None

@modified_dataclass
class ActivityButton:
    label: str
    url: str

@modified_dataclass
class Activity:
    name: str
    type: ActivityTypes
    created_at: datetime = None
    url: str = None
    timestamps: ActivityTimestamps = None
    application_id: str = None
    details: str = None
    state: str = None
    emoji: Emoji = None
    party: ActivityParty = None
    assets: ActivityAssets = None
    secrets: ActivitySecrets = None
    instance: bool = None
    flags: Sequence[ActivityFlags] = None
    buttons: Union[List[ActivityButton], List[str]] = None

    def __str__(self):
        return "<Activity name={!r} type={!r} details={!r} state={!r}>".format(self.name, self.type, self.details, self.state)

    def __repr__(self):
        return "<Activity name={!r} type={!r} details={!r} state={!r}>".format(self.name, self.type, self.details, self.state)

    @classmethod
    def from_raw(cls, activity):
        activity["type"] = ActivityTypes(activity["type"])
        activity["created_at"] = datetime.fromtimestamp(activity["created_at"] / 1000)

        if "timestamps" in activity:
            activity["timestamps"] = ActivityTimestamps.from_raw(activity["timestamps"])
        if "emoji" in activity:
            activity["emoji"] = Emoji.from_raw(activity["emoji"])
        if "party" in activity:
            activity["party"] = ActivityParty(**activity["party"])
        if "assets" in activity:
            activity["assets"] = ActivityAssets(**activity["assets"])
        if "secrets" in activity:
            activity["secrets"] = ActivitySecrets(**activity["secrets"])
        if "flags" in activity:
            activity["flags"] = [flag for flag in ActivityFlags if activity["flags"] & flag.value == flag.value]
        if "buttons" in activity:
            if isinstance(activity["buttons"], dict) is True:
                activity["buttons"] = [ActivityButton(**button) for button in activity["buttons"]]

        return cls(**activity)

@modified_dataclass
class ClientStatus:
    desktop: Optional[StatusTypes] = None
    mobile: Optional[StatusTypes] = None
    web: Optional[StatusTypes] = None

    def __str__(self):
        return "<ClientStatus desktop={!r} mobile={!r} web={!r}>".format(self.desktop, self.mobile, self.web)

    def __repr__(self):
        return "<ClientStatus desktop={!r} mobile={!r} web={!r}>".format(self.desktop, self.mobile, self.web)

    @classmethod
    def from_raw(cls, client_status):
        for key in client_status:
            client_status[key] = StatusTypes(client_status[key])

        return cls(**client_status)

@modified_dataclass
class Presence:
    status: StatusTypes
    activities: Sequence[Activity]
    client_status: ClientStatus = None

    def __str__(self):
        return "<Presence status={!r} client_status={!r} activities={!r}>".format(self.status, self.client_status, self.activities)

    def __repr__(self):
        return "<Presence status={!r} client_status={!r} activities={!r}>".format(self.status, self.client_status, self.activities)

    def to_dict(self):
        presence = {key: value for key, value in self.__dict__.items() if value is not None}

        for key, value in presence.items():
            if isinstance(value, Enum):
                presence[key] = value.value

        activities = []

        for activity in presence["activities"]:
            activity = {key: value for key, value in activity.__dict__.items() if value is not None}

            for key, value in activity.items():
                if isinstance(value, Enum):
                    activity[key] = value.value

            activities.append(activity)

        presence["activities"] = activities
        presence["since"] = None
        presence["afk"] = False

        return presence

    @classmethod
    def from_raw(cls, presence):
        presence["status"] = StatusTypes(presence["status"])
        presence["client_status"] = ClientStatus.from_raw(presence["client_status"])
        presence["activities"] = [Activity.from_raw(activity) for activity in presence["activities"]]

        return cls(**presence)