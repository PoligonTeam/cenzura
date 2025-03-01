"""
Copyright 2022-2025 Smugaski

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

import aiohttp, bs4
from typing import Optional, Type
from types import TracebackType
from dataclasses import dataclass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Safari/605.1.15 Epiphany/605.1.15"
}


@dataclass
class Lyrics:
    artist: str
    title: str
    url: str = None
    lyrics: str = None


class TrackNotFound(Exception):
    pass


class LyricsNotFound(Exception):
    pass


class LyricsClient:
    def __init__(self, api_key: str, session: aiohttp.ClientSession = None):
        self.api_key = api_key
        self.own_session = session is None
        self.session = session or aiohttp.ClientSession()

    async def __aenter__(self) -> "LyricsClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        if self.own_session is True:
            await self.session.close()

    async def search_track(self, name: str) -> Lyrics:
        raise NotImplementedError()

    async def get_lyrics(self, name: str) -> Lyrics:
        raise NotImplementedError()


class MusixmatchClient(LyricsClient):
    def __init__(self, api_key: str, session: aiohttp.ClientSession = None):
        super().__init__(api_key, session)

    async def search_track(self, name: str) -> Lyrics:
        async with self.session.get(
            "https://api.musixmatch.com/ws/1.1/track.search",
            params={
                "q_track_artist": name,
                "page_size": 1,
                "page": 1,
                "s_track_rating": "desc",
                "q_artist_rating": "desc",
                "country": "us",
                "apikey": self.api_key,
            },
        ) as response:
            data = await response.json(content_type=None)
            track_list = data["message"]["body"]["track_list"]

            if not track_list:
                raise TrackNotFound()

            track = track_list[0]["track"]

            return Lyrics(
                track["artist_name"],
                track["track_name"],
                track["track_share_url"].split("?")[0],
            )

    async def get_lyrics(self, name: str) -> Lyrics:
        track = await self.search_track(name)

        async with self.session.get(track.url, headers=HEADERS) as response:
            soup = bs4.BeautifulSoup(await response.text(), "html.parser")
            element = soup.find(
                lambda tag: tag.name == "h2" and "Lyrics of" in tag.text
            )

            if element is None:
                raise LyricsNotFound()

            elements = "\n\n".join(
                [
                    "\n".join(
                        [second_child.text for second_child in list(child.children)[1:]]
                    )
                    for child in list(element.parent.children)[1:-3]
                ]
            )

            track.lyrics = elements
            return track


class GeniusClient(LyricsClient):
    def __init__(self, api_key: str, session: aiohttp.ClientSession = None):
        super().__init__(api_key, session)

    async def search_track(self, name: str) -> Lyrics:
        async with self.session.get(
            "https://api.genius.com/search",
            params={"q": name, "access_token": self.api_key},
        ) as response:
            data = await response.json()
            hits = data["response"].get("hits")

            if hits is None:
                raise TrackNotFound()

            track = hits[0]["result"]

            return Lyrics(track["artist_names"], track["title"], track["url"])

    async def get_lyrics(self, name: str) -> Lyrics:
        track = await self.search_track(name)

        async with self.session.get(track.url, headers=HEADERS) as response:
            html = await response.content.read()

            soup = bs4.BeautifulSoup(html, "html.parser")
            lyrics = soup.find("div", {"data-lyrics-container": True})

            if lyrics is None:
                raise LyricsNotFound()

            track.lyrics = lyrics.get_text("\n")

            return track