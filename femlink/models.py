"""
Copyright 2022-2025 PoligonTeam

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either exzess or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from dataclasses import dataclass
from typing import Union, TypedDict, Any, Literal
from .enums import LoadResultType



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
    position: Union[int, None] = None
    uri: Union[str, None] = None
    artwork_url: Union[str, None] = None
    isrc: Union[str, None] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TrackInfo":
        data["is_seekable"] = data.pop("isSeekable")
        data["artist"] = data.pop("author")
        data["is_stream"] = data.pop("isStream")
        data["source_name"] = data.pop("sourceName")
        data["artwork_url"] = data.pop("artworkUrl")
        data["isrc"] = data.pop("isrc")

        return cls(**data)

@dataclass
class Track:
    encoded: str
    info: TrackInfo
    plugin_info: Union[dict, None] = None
    user_data: Union[dict, None] = None

    @classmethod
    def from_dict(cls, data: "TrackDict") -> "Track":
        raw: dict[str, Any] = dict(data)

        raw["plugin_info"] = raw.pop("pluginInfo", None)
        raw["user_data"] = raw.pop("userData", None)
        raw["info"] = TrackInfo.from_dict(raw["info"])

        return cls(**raw)

    def to_dict(self) -> dict:
        return {
            "encoded": self.encoded,
            **({"userData": self.user_data} if self.user_data else {})
        }

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
    session_id: Union[str, None] = None
    event: Union[VoiceStateEvent, None] = None

    def __post_init__(self) -> None:
        if self.event:
            self.event = VoiceStateEvent(**self.event) # type: ignore

    def clear(self) -> None:
        self.__init__()

class TrackInfoDict(TypedDict):
    identifier: str
    isSeekable: bool
    author: str
    length: int
    isStream: bool
    title: str
    sourceName: str
    position: Union[int, None]
    uri: Union[str, None]
    artworkUrl: Union[str, None]
    isrc: Union[str, None]


class TrackDict(TypedDict):
    encoded: str
    info: TrackInfoDict
    pluginInfo: dict
    userData: dict

class LoadResultErrorData(TypedDict):
    message: Union[str, None]
    severity: Literal["common", "suspicious", "fault"]
    cause: str
    causeStackTrace: str

class LoadResultError(TypedDict):
    loadType: Literal[LoadResultType.ERROR]
    data: LoadResultErrorData

class LoadResultEmpty(TypedDict):
    loadType: Literal[LoadResultType.EMPTY]
    data: dict

class LoadResultSearch(TypedDict):
    loadType: Literal[LoadResultType.SEARCH]
    data: list[TrackDict]

class PlaylistInfo(TypedDict):
    name: str
    pluginInfo: dict
    selectedTrack: int

class LoadResultPlaylistData(TypedDict):
    info: PlaylistInfo
    tracks: list[TrackDict]

class LoadResultPlaylist(TypedDict):
    loadType: Literal[LoadResultType.PLAYLIST]
    data: LoadResultPlaylistData

class LoadResultTrack(TypedDict):
    loadType: Literal[LoadResultType.TRACK]
    data: TrackDict

LoadResult = Union[
    LoadResultError,
    LoadResultEmpty,
    LoadResultTrack,
    LoadResultSearch,
    LoadResultPlaylist,
]