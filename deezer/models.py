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

from typing import TypedDict, List, Literal, Optional

class ArtistBase(TypedDict):
    id: int
    name: str
    link: str
    picture: str
    picture_small: str
    picture_medium: str
    picture_big: str
    picture_xl: str
    tracklist: str
    type: Literal["artist"]

class Artist(ArtistBase):
    radio: Optional[bool]
    share: Optional[str]

class Contributor(Artist):
    role: Optional[str]

class Album(TypedDict):
    id: int
    title: str
    cover: str
    cover_small: str
    cover_medium: str
    cover_big: str
    cover_xl: str
    md5_image: str
    tracklist: str
    type: Literal["album"]
    link: Optional[str]
    release_date: Optional[str]

class TrackBase(TypedDict):
    id: int
    readable: bool
    title: str
    title_short: str
    title_version: str
    link: str
    duration: int
    rank: int
    explicit_lyrics: bool
    explicit_content_lyrics: int
    explicit_content_cover: int
    preview: str
    md5_image: str
    type: Literal["track"]

class TrackSearch(TrackBase):
    artist: Artist
    album: Album

class SearchResponse(TypedDict):
    data: List[TrackSearch]
    total: int

class TrackDetail(TrackBase):
    isrc: str
    share: str
    track_position: int
    disk_number: int
    release_date: str
    bpm: float
    gain: float
    available_countries: List[str]
    contributors: List[Contributor]
    artist: Artist
    album: Album
    track_token: str