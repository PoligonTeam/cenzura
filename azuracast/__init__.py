"""
Copyright 2022-2025 PoligonTeam

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

from typing import Optional, Any

@dataclass
class Listeners:
    total: int
    unique: int
    current: int

    @classmethod
    def from_dict(cls, data: dict) -> "Listeners":
        return cls(**data)

@dataclass
class Mount:
    id: int
    name: str
    url: str
    bitrate: int
    format: str
    listeners: Listeners
    path: str
    is_default: bool

    @classmethod
    def from_dict(cls, data: dict) -> "Mount":
        data["listeners"] = Listeners.from_dict(data["listeners"])

        return cls(**data)

@dataclass
class Remote:
    id: int
    name: str
    url: str
    bitrate: int
    format: str
    listeners: Listeners

    @classmethod
    def from_dict(cls, data: dict) -> "Remote":
        data["listeners"] = Listeners.from_dict(data["listeners"])

        return cls(**data)

@dataclass
class Station:
    id: int
    name: str
    shortcode: str
    description: str
    frontend: str
    backend: str
    listen_url: str
    url: str
    public_player_url: str
    playlist_pls_url: str
    playlist_m3u_url: str
    is_public: bool
    mounts: list[Mount]
    remotes: list[Remote]
    hls_enabled: bool
    hls_url: str
    hls_listeners: int
    hls_is_default: Any
    timezone: Any

    @classmethod
    def from_dict(cls, data: dict) -> "Station":
        data["mounts"] = [Mount.from_dict(mount) for mount in data["mounts"]]
        data["remotes"] = [Remote.from_dict(remote) for remote in data["remotes"]]

        return cls(**data)

@dataclass
class Live:
    is_live: bool
    streamer_name: str
    broadcast_start: str
    art: str

@dataclass
class Song:
    id: str
    text: str
    artist: str
    title: str
    album: str
    genre: str
    isrc: str
    lyrics: str
    art: str
    custom_fields: list[dict]
    bottom_text: str = None
    formatted_text: str = None

    def __post_init__(self) -> None:
        if self.artist and self.album:
            self.bottom_text = f"{self.artist} • {self.album}"
        elif self.artist:
            self.bottom_text = self.artist

        self.formatted_text = f"**{self.title}**\n" + (f"{self.bottom_text}\n" if self.bottom_text is not None else "")

@dataclass
class NowPlayingSong:
    sh_id: int
    played_at: int
    duration: int
    playlist: str
    streamer: str
    is_request: bool
    song: Song
    elapsed: int
    remaining: int

    @classmethod
    def from_dict(cls, data: dict):
        data["song"] = Song(**data["song"])

        return cls(**data)

@dataclass
class PlayingNextSong:
    cued_at: int
    played_at: int
    duration: int
    playlist: str
    is_request: bool
    song: Song

    @classmethod
    def from_dict(cls, data: dict):
        data["song"] = Song(**data["song"])

        return cls(**data)

@dataclass
class SongHistory:
    sh_id: int
    played_at: int
    duration: int
    playlist: str
    streamer: str
    is_request: bool
    song: Song

    @classmethod
    def from_dict(cls, data: dict) -> "SongHistory":
        data["song"] = Song(**data["song"])

        return cls(**data)

@dataclass
class NowPlaying:
    station: Station
    listeners: Listeners
    live: Live
    now_playing: NowPlayingSong
    playing_next: PlayingNextSong
    song_history: list[SongHistory]
    is_online: bool
    cache: Optional[bool]

    @classmethod
    def from_dict(cls, data: dict):
        data["station"] = Station.from_dict(data["station"])
        data["listeners"] = Listeners.from_dict(data["listeners"])
        data["live"] = Live(**data["live"])
        data["now_playing"] = NowPlayingSong.from_dict(data["now_playing"])
        data["playing_next"] = PlayingNextSong.from_dict(data["playing_next"])
        data["song_history"] = [SongHistory.from_dict(song) for song in data["song_history"]]

        return cls(**data)