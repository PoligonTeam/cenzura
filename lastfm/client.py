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

import aiohttp, re, hashlib
from typing import Optional, Type, Sequence, Literal
from types import TracebackType
from urllib.parse import quote_plus
from .models import RecentTracks, Track, Artist, TopArtist
from .exceptions import *

IMAGE_REGEX = re.compile(r"<meta property=\"og:image\"[ ]+content=\"([\w/:.]+)\" data-replaceable-head-tag>")

def check_api_key(func):
    async def wrapper(self, *args, **kwargs):
        if self.api_key is None:
            raise InvalidApiKey()

        return await func(self, *args, **kwargs)

    return wrapper

def check_api_secret(func):
    async def wrapper(self, *args, **kwargs):
        if self.api_secret is None:
            raise InvalidApiKey()

        return await func(self, *args, **kwargs)

    return wrapper

class Client:
    def __init__(self, api_key: str = None, api_secret: str = None, session: aiohttp.ClientSession = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.own_session = session is None
        self.session = session or aiohttp.ClientSession()

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]):
        if self.own_session is True:
            await self.session.close()

    def _sign(self, params: dict):
        keys = list(params.keys())

        keys.sort()

        string = "api_key" + self.api_key

        for name in keys:
            string += name
            string += params[name]

        string += self.api_secret

        return hashlib.md5(string.encode("utf-8"))

    async def _signed_request(self, method: str, params: dict) -> dict:
        params["api_sig"] = self._sign(params).hexdigest()

        return await self._request(method, params)

    async def _request(self, method: str, params: dict) -> dict:
        async with self.session.request(method, "http://ws.audioscrobbler.com/2.0/", params={
            **params,
            "api_key": self.api_key,
            "format": "json"
        }) as response:
            if response.status == 403:
                raise InvalidApiKey()

            elif response.status == 502:
                raise BadGateway()

            data = await response.json()
            error = data.get("error")

            if error is None:
                return data
            elif error == 4:
                raise InvalidToken()
            elif error == 6:
                raise NotFound()
            elif error == 10:
                raise InvalidApiKey()
            elif error == 13:
                raise InvalidSignature()
            elif error == 14:
                raise UnauthorizedToken()
            elif error == 15:
                raise ExpiredToken()
            elif error == 16:
                raise TemporaryError()
            elif error == 26:
                raise SuspendedApiKey()
            elif error == 29:
                raise RateLimitExceeded()

    @check_api_key
    async def recent_tracks(self, username: str, limit: int = 2, **kwargs: dict) -> RecentTracks:
        response = await self._request("GET", {
            "method": "user.getrecenttracks",
            "user": username,
            "extended": 1,
            "limit": limit,
            **kwargs
        })

        return RecentTracks.from_dict(response)

    @check_api_key
    async def top_artists(self, username: str, period: Literal["overall", "7day", "1month", "3month", "6month", "12month"] = "overall", limit: int = 1, **kwargs: dict) -> list[TopArtist]:
        response = await self._request("GET", {
            "method": "user.getTopArtists",
            "user": username,
            "period": period,
            "limit": limit,
            **kwargs
        })

        return [TopArtist.from_dict(artist) for artist in response["topartists"]["artist"]]

    @check_api_key
    async def track_info(self, artist: str, track: str, username: str = None, **kwargs: dict) -> Track:
        response = await self._request("GET", {
            "method": "track.getInfo",
            **({"username": username} if username is not None else {}),
            "artist": artist,
            "track": track,
            **kwargs
        })

        return Track.from_dict(response["track"])

    @check_api_key
    async def track_search(self, track: str, artist: str = None, limit: int = 1) -> Sequence[Track]:
        response = await self._request("GET", {
            "method": "track.search",
            "track": track,
            **({"artist": artist} if artist is not None else {}),
            "limit": limit
        })

        return [Track.from_dict(track) for track in response["results"]["trackmatches"]["track"]]

    @check_api_key
    async def artist_info(self, artist: str, username: str = None, **kwargs: dict) -> Artist:
        response = await self._request("GET", {
            "method": "artist.getInfo",
            **({"username": username} if username is not None else {}),
            "artist": artist,
            **kwargs
        })

        return Artist.from_dict(response["artist"])

    @check_api_key
    async def get_token(self) -> str:
        response = await self._request("GET", {
            "method": "auth.getToken"
        })

        return response["token"]

    @check_api_secret
    async def get_session(self, token: str):
        response = await self._signed_request("GET", {
            "method": "auth.getSession",
            "token": token
        })

        return response["session"]

    async def artist_image(self, artist: str):
        async with self.session.get("https://www.last.fm/music/" + quote_plus(artist)) as response:
            if not response.status == 200:
                raise NotFound()

            data = await response.text()

            return IMAGE_REGEX.search(data).group(1)