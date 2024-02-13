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
from typing import TypeVar
from .channel import Channel
from datetime import datetime

Guild = TypeVar("Guild")

@modified_dataclass
class VoiceState:
    session_id: str
    deaf: bool
    mute: bool
    self_deaf: bool
    self_mute: bool
    self_video: bool
    suppress: bool
    guild: Guild = None
    channel: Channel = None
    self_stream: bool = None
    request_timestamp: datetime = None

    __CHANGE_KEYS__ = (
        (
            "request_to_speak_timestamp",
            "request_timestamp"
        ),
    )

    def __str__(self):
        return "<VoiceState guild={!r} channel={!r} deaf={!r} mute={!r} self_deaf={!r} self_mute={!r} self_stream={!r} self_video={!r} suppress={!r} request_timestamp={!r}>".format(self.guild, self.channel, self.deaf, self.mute, self.self_deaf, self.self_mute, self.self_stream, self.self_video, self.suppress, self.request_timestamp)

    def __repr__(self):
        return "<VoiceState guild={!r} channel={!r} deaf={!r} mute={!r} self_deaf={!r} self_mute={!r} self_stream={!r} self_video={!r} suppress={!r} request_timestamp={!r}>".format(self.guild, self.channel, self.deaf, self.mute, self.self_deaf, self.self_mute, self.self_stream, self.self_video, self.suppress, self.request_timestamp)

    @classmethod
    def from_raw(cls, gateway, voice_state):
        if voice_state["request_timestamp"] is not None:
            voice_state["request_timestamp"] = datetime.fromisoformat(voice_state["request_timestamp"])

        return cls(**voice_state)