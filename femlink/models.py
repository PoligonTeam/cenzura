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

from dataclasses import dataclass

@dataclass
class NodeStatsMemory:
    free: int
    used: int
    allocated: int
    reservable: int

@dataclass
class NodeStatsCPU:
    cores: int
    system_load: float
    lavalink_load: float

@dataclass
class NodeStatsFrameStats:
    sent: int
    nulled: int
    deficit: int

@dataclass
class NodeStats:
    players: int
    playing_players: int
    uptime: int
    memory: NodeStatsMemory
    cpu: NodeStatsCPU
    frame_stats: NodeStatsFrameStats

@dataclass
class PlayerState:
    time: int
    postion: int
    connected: bool
    ping: int

@dataclass
class TrackInfo:
    identifier: str
    is_seekable: bool
    artist: str
    length: int
    is_stream: bool
    title: str
    source_name: str
    position: int = None
    uri: str = None

    @classmethod
    def from_dict(cls, data: dict) -> "TrackInfo":
        data["is_seekable"] = data.pop("isSeekable"),
        data["artist"] = data.pop("author"),
        data["is_stream"] = data.pop("isStream"),
        data["source_name"] = data.pop("sourceName"),

        return cls(**data)

@dataclass
class Track:
    encoded: str
    info: TrackInfo

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        data["info"] = TrackInfo.from_dict(data["info"])
        del data["track"]

        return cls(**data)

@dataclass
class VoiceStateEvent:
    token: str
    guild_id: str
    endpoint: str

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "guildId": self.guild_id,
            "endpoint": self.endpoint
        }

@dataclass
class VoiceState:
    session_id: str = None
    event: VoiceStateEvent = None

    def __post_init__(self) -> None:
        if self.event:
            self.event = VoiceStateEvent(**self.event)

    def clear(self) -> None:
        self.__init__()