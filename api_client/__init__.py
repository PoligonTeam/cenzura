"""
Copyright 2023-2025 PoligonTeam

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

import aiohttp, base64, bs4, io
from dataclasses import dataclass
from types import TracebackType
from typing import Optional, Type, TypedDict

ERROR_MAP = {
    "api_down": "API is down",
    "unexpected_status": "Unexpected status code",
    "invalid_payload": "Invalid payload",
    "invalid_apikey": "Invalid API key",
    "invalid_url": "Invalid URL",
    "live_unsupported": "Live videos are not supported",
    "too_long": "Videos longer than 5 minutes are not supported",
    "no_formats": "No formats found",
    "too_large": "File too large",
    "load_failed": "Failed to fetch URL"
}

class ResponseDict(TypedDict):
    error: str

class ScreenshotResponseDict(ResponseDict):
    image: str
    content: str

class YoutubeInfoDict(TypedDict):
    title: str
    likes: str
    dislikes: str
    views: str
    length: str
    thumbnail: str

class YoutubeResponseDict(ResponseDict):
    video: str
    info: YoutubeInfoDict

@dataclass
class ScreenshotResponse:
    image: io.BytesIO
    content: str

    @classmethod
    def from_dict(cls, data: ScreenshotResponseDict) -> "ScreenshotResponse":
        return cls(io.BytesIO(base64.b64decode(data["image"])), bs4.BeautifulSoup(data["content"], "html.parser").prettify())

@dataclass
class YoutubeInfo:
    title: str
    likes: str
    dislikes: str
    views: str
    length: str
    thumbnail: str

@dataclass
class YoutubeResponse:
    video: io.BytesIO
    info: YoutubeInfo

    @classmethod
    def from_dict(cls, data: YoutubeResponseDict) -> "YoutubeResponse":
        return cls(io.BytesIO(base64.b64decode(data["video"])), YoutubeInfo(**data["info"]))

class LyricsResponse(TypedDict):
    status: int
    lyrics: str
    artist: str
    title: str
    source: str
    cached: bool

class ApiError(Exception):
    def __init__(self, message: str, url: str):
        super().__init__(message)
        self.url = url

class ApiClient:
    def __init__(self, base_url: str, error_map: dict[str, str] = ERROR_MAP) -> None:
        self.session = aiohttp.ClientSession(base_url=base_url)
        self.error_map = error_map

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]) -> None:
        await self.session.close()

    async def _post(self, url: str, **kwargs) -> dict:
        try:
            async with self.session.post(url, **kwargs) as response:
                if response.status not in (200, 400, 401):
                    raise ApiError(f"Unexpected status code: {response.status}", url)

                data = await response.json()

                if "error" in data:
                    raise ApiError(self.error_map.get(data["error"], "Unknown error"), url)

                return data
        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ClientConnectorError):
                raise ApiError(self.error_map["api_down"], url)
            elif isinstance(e, aiohttp.ClientPayloadError):
                raise ApiError(self.error_map["invalid_payload"], url)

            raise ApiError(self.error_map["unexpected_status"], url)

    async def screenshot(self, url: str, full_page: Optional[bool] = False) -> ScreenshotResponse:
        data = await self._post("/screenshot", json={"url": url, "full_page": full_page})
        return ScreenshotResponse.from_dict(data)

    async def ytdl(self, url: str) -> YoutubeResponse:
        data = await self._post("/ytdl", json={"url": url})
        return YoutubeResponse.from_dict(data)

    async def lyrics(self, name: str) -> LyricsResponse:
        data: LyricsResponse = await self._post("/lyrics", json={"name": name}) # type: ignore
        return data