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
    uri: str = None

@dataclass
class Track:
    encoded: str
    info: TrackInfo

@dataclass
class VoiceState:
    token: str
    endpoint: str
    session_id: str
    connected: bool
    ping: int