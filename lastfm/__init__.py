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
from typing import List
from datetime import datetime

@modified_dataclass
class TrackTag:
    name: str
    url: str

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class TrackImage:
    size: str
    url: str

    __CHANGE_KEYS__ = (
        (
            "#text",
            "url"
        ),
    )

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class TrackArtistStats:
    listeners: str
    playcount: str
    userplaycount: str

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class TrackArtistSimilar:
    name: str
    url: str
    image: List[TrackImage]

    @classmethod
    def from_raw(cls, data):
        if "image" in data:
            data["image"] = [TrackImage.from_raw(image) for image in data["image"]]

        return cls(**data)

@modified_dataclass
class TrackArtistBioLink:
    name: str
    rel: str
    url: str

    __CHANGE_KEYS__ = (
        (
            "#text",
            "name"
        ),
        (
            "href",
            "url"
        )
    )

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class TrackArtistBio:
    links: TrackArtistBioLink
    published: str
    summary: str
    content: str

    @classmethod
    def from_raw(cls, data):
        if "links" in data:
            data["links"] = TrackArtistBioLink.from_raw(data["links"]["link"])

        return cls(**data)

@modified_dataclass
class TrackArtist:
    name: str
    url: str
    image: List[TrackImage] = None
    streamable: str = None
    stats: TrackArtistStats = None
    similar: List[TrackArtistSimilar] = None
    tags: List[TrackTag] = None
    ontour: str = None
    mbid: str = None
    bio: TrackArtistBio = None

    @classmethod
    def from_raw(cls, data):
        if "image" in data:
            data["image"] = [TrackImage.from_raw(image) for image in data["image"]]
        if "stats" in data:
            data["stats"] = TrackArtistStats.from_raw(data["stats"])
        if "similar" in data:
            data["similar"] = [TrackArtistSimilar.from_raw(similar) for similar in data["similar"]["artist"]]
        if "tags" in data:
            data["tags"] = [TrackTag.from_raw(tag) for tag in data["tags"]["tag"]]
        if "bio" in data:
            data["bio"] = TrackArtistBio.from_raw(data["bio"])

        return cls(**data)

@modified_dataclass
class TrackAlbum:
    mbid: str
    name: str

    __CHANGE_KEYS__ = (
        (
            "#text",
            "name"
        ),
    )

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class TrackDate:
    uts: int
    text: str
    date: datetime

    __CHANGE_KEYS__ = (
        (
            "#text",
            "text"
        ),
    )

    @classmethod
    def from_raw(cls, data):
        data["uts"] = int(data["uts"])
        data["date"] = datetime.fromtimestamp(data["uts"])
        return cls(**data)

@modified_dataclass
class Track:
    artist: TrackArtist
    image: List[TrackImage] = None
    album: TrackAlbum = None
    title: str = None
    url: str = None
    date: TrackDate = None
    listeners: str = None
    playcount: str = None
    scrobbles: str = None
    tags: List[TrackTag] = None

    @classmethod
    def from_raw(cls, data):
        if "artist" in data:
            data["artist"] = TrackArtist.from_raw(data["artist"])
        if "image" in data:
            data["image"] = [TrackImage.from_raw(image) for image in data["image"]]
        if "album" in data:
            data["album"] = TrackAlbum.from_raw(data["album"])
        if "date" in data:
            data["date"] = TrackDate.from_raw(data["date"])
        if "tags" in data:
            data["tags"] = [TrackTag.from_raw(tag) for tag in data["tags"]]

        return cls(**data)

@modified_dataclass
class PartialTrackStreamable:
    text: str
    fulltrack: str

    __CHANGE_KEYS__ = (
        (
            "#text",
            "text"
        ),
    )

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class PartialTrackArtist:
    name: str
    url: str

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class PartialTrackWiki:
    published: str
    summary: str
    content: str

    @classmethod
    def from_raw(cls, data):
        return cls(**data)

@modified_dataclass
class PartialTrack:
    title: str
    url: str
    images: List[TrackImage]
    duration: str
    streamable: PartialTrackStreamable
    listeners: str
    playcount: str
    artist: PartialTrackArtist
    userplaycount: str
    userloved: str
    tags: List[TrackTag]
    wiki: PartialTrackWiki = None

    __CHANGE_KEYS__ = (
        (
            "name",
            "title"
        ),
        (
            "toptags",
            "tags"
        ),
    )

    @classmethod
    def from_raw(cls, data):
        if "images" in data:
            data["images"] = [TrackImage.from_raw(image) for image in data["images"]]
        if "streamable" in data:
            data["streamable"] = PartialTrackStreamable.from_raw(data["streamable"])
        if "artist" in data:
            data["artist"] = PartialTrackArtist.from_raw(data["artist"])
        if "tags" in data:
            data["tags"] = [TrackTag.from_raw(tag) for tag in data["tags"]["tag"]]
        return cls(**data)