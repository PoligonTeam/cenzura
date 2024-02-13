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

from dataclasses import dataclass
from typing import Union, List, Dict
from datetime import datetime
from urllib.parse import quote_plus

@dataclass
class TrackImage:
    size: str
    url: str

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data["size"], data["#text"])

@dataclass
class TrackTag:
    name: str
    url: str

@dataclass
class ArtistStats:
    listeners: str
    playcount: str
    userplaycount: str

    @classmethod
    def from_dict(cls, data: Dict):
        data["userplaycount"] = data.pop("userplaycount", None)

        return cls(**data)

@dataclass
class ArtistBioLinks:
    name: str
    rel: str
    url: str

    @classmethod
    def from_dict(cls, data: Dict):
        data["name"] = data.pop("#text")
        data["url"] = data.pop("href")

        return cls(**data)

@dataclass
class ArtistBio:
    published: str
    summary: str
    content: str
    links: List[ArtistBioLinks] = None

    @classmethod
    def from_dict(cls, data: Dict):
        if "links" in data:
            data["links"] = ArtistBioLinks.from_dict(data["links"]["link"])

        return cls(**data)

@dataclass
class Artist:
    name: str
    url: str
    streamable: str = None
    on_tour: str = None
    mbid: str = None
    similar: List["Artist"] = None
    stats: ArtistStats = None
    image: List[TrackImage] = None
    tags: List[TrackTag] = None
    bio: str = None

    @classmethod
    def from_dict(cls, data: Union[Dict, str]):
        if isinstance(data, str):
            data = {
                "name": data,
                "url": "https://www.last.fm/music/" + quote_plus(data),
            }

            return cls(**data)

        if "image" in data:
            data["image"] = [TrackImage.from_dict(image) for image in data["image"]]
        if "stats" in data:
            data["stats"] = ArtistStats.from_dict(data["stats"])
        if "similar" in data:
            data["similar"] = [Artist.from_dict(artist) for artist in data["similar"]["artist"]]
        if "tags" in data:
            data["tags"] = [TrackTag(**tag) for tag in data["tags"]["tag"]]
        if "bio" in data:
            data["bio"] = ArtistBio.from_dict(data["bio"])

        data["streamable"] = data.get("streamable")
        data["on_tour"] = data.pop("ontour", None)

        return cls(**data)

@dataclass
class TrackAlbum:
    name: str
    artist: str = None
    mbid: str = None
    image: List[TrackImage] = None
    url: str = None
    position: str = None

    @classmethod
    def from_dict(cls, data: Dict):
        if "artist" in data:
            data["artist"] = data["artist"]
        if "mbid" not in data:
            data["mbid"] = ""
        if "image" in data:
            data["image"] = [TrackImage.from_dict(image) for image in data["image"]]
        if "#text" in data:
            data["title"] = data.pop("#text")
        if "@attr" in data:
            data["position"] = data.pop("@attr")["position"]

        data["name"] = data.pop("title")

        return cls(**data)

@dataclass
class TrackDate:
    uts: int
    text: str
    date: datetime

    @classmethod
    def from_dict(cls, data: Dict):
        data["uts"] = int(data.pop("uts"))
        data["text"] = data.pop("#text")
        data["date"] = datetime.fromtimestamp(int(data["uts"]))

        return cls(**data)

@dataclass
class TrackWiki:
    published: str
    summary: str
    content: str

@dataclass
class Track:
    artist: Artist
    title: str
    url: str
    streamable: str
    listeners: str
    playcount: str
    duration: str
    album: TrackAlbum = None
    scrobbles: str = None
    mbid: str = None
    loved: bool = None
    userloved: bool = None
    image: List[TrackImage] = None
    tags: List[TrackTag] = None
    date: TrackDate = None
    wiki: TrackWiki = None

    @classmethod
    def from_dict(cls, data: Dict):
        if "album" in data:
            data["album"] = TrackAlbum.from_dict(data["album"])
        if "userplaycount" in data:
            data["scrobbles"] = data.pop("userplaycount")
        if "loved" in data:
            data["loved"] = data["loved"] == "1"
        if "userloved" in data:
            data["userloved"] = data["userloved"] == "1"
        if "image" in data:
            data["image"] = [TrackImage.from_dict(image) for image in data["image"]]
        if "toptags" in data:
            data["tags"] = [TrackTag(**tag) for tag in data.pop("toptags")["tag"]]
        if "wiki" in data:
            data["wiki"] = TrackWiki(**data["wiki"])

        date = data.pop("date", datetime.now())

        data["date"] = TrackDate.from_dict(date if isinstance(date, dict) else {"uts": date.timestamp(), "#text": date.strftime(r"%d %b %Y, %H:%M")})
        data["title"] = data.pop("name")
        data["listeners"] = data.get("listeners")
        data["playcount"] = data.get("playcount")
        data["duration"] = data.get("duration")
        data["artist"] = Artist.from_dict(data["artist"])

        data.pop("@attr", None)

        return cls(**data)

@dataclass
class RecentTracks:
    tracks: List[Track]
    username: str
    scrobbles: str

    @classmethod
    def from_dict(cls, data: Dict):
        data = data["recenttracks"]
        data["tracks"] = [Track.from_dict(track) for track in data.pop("track")]

        attributes = data.pop("@attr")

        data["username"] = attributes["user"]
        data["scrobbles"] = attributes["total"]

        return cls(**data)