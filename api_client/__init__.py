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

import aiohttp, base64, bs4
from typing import Dict, List, Literal, NotRequired, Optional, TypedDict, Union, Unpack, Any

class ScoreBreakdown(TypedDict):
    source: float
    artistMatch: float
    trackMatch: float
    confidence: float
    recencyPenalty: float
    freshnessBonus: float

class TrackInfo(TypedDict):
    id: int
    title: str
    normalizedTitle: str
    imageUrl: Optional[str]
    imageThumbnailUrl: Optional[str]

class ArtistInfo(TypedDict, total=False):
    id: int
    name: str
    normalizedName: str

class DecisionLogEntry(TypedDict, total=False):
    step: str
    source: NotRequired[Literal["MUSIXMATCH", "GENIUS"]]
    action: str
    score: NotRequired[float]
    candidateId: NotRequired[int]
    notes: NotRequired[str]
    extras: NotRequired[Union[ScoreBreakdown, Dict[str, Any]]]
    timestamp: str

class LyricSearchSuccessResponse(TypedDict):
    eventId: int
    versionId: int
    score: float
    breakdown: ScoreBreakdown
    source: Literal["MUSIXMATCH", "GENIUS"]
    track: TrackInfo
    artist: ArtistInfo
    lyrics: str
    snippet: NotRequired[str]
    fullLyricsUrl: str
    decisionLog: List[DecisionLogEntry]

class ErrorResponse(TypedDict):
    error: str

class ScreenshotSuccessResponse(TypedDict):
    image: bytes  # Image data as BytesIO
    content: str # HTML content as a prettified string

class ApiError(Exception):
    def __init__(self, message: str, url: str):
        super().__init__(message)
        self.url = url

class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.session = aiohttp.ClientSession(base_url=base_url)

    async def __aenter__(self) -> "ApiClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.session.close()

    async def _post(self, url: str, **kwargs: Unpack[aiohttp.client._RequestOptions]) -> dict:
        try:
            async with self.session.post(url, **kwargs) as response:
                if response.status not in (200, 400, 401):
                    raise ApiError(f"Unexpected status code: {response.status}", url)

                data = await response.json()

                if "error" in data:
                    raise ApiError(data["error"], url)

                return data
        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ClientConnectorError):
                raise ApiError("Api is down.", url)
            elif isinstance(e, aiohttp.ClientPayloadError):
                raise ApiError("Invalid payload.", url)

            raise ApiError("Unknown error occured.", url)

    async def _get(self, url: str, **kwargs: Unpack[aiohttp.client._RequestOptions]) -> dict:
        try:
            async with self.session.get(url, **kwargs) as response:
                if response.status not in (200, 400, 401):
                    raise ApiError(f"Unexpected status code: {response.status}", url)

                data = await response.json()

                if "error" in data:
                    raise ApiError(data["error"], url)

                return data
        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ClientConnectorError):
                raise ApiError("Api is down.", url)
            elif isinstance(e, aiohttp.ClientPayloadError):
                raise ApiError("Invalid payload.", url)

            raise ApiError("Unknown error occured.", url)

    async def screenshot(self, url: str, full_page: Optional[bool] = False) -> ScreenshotSuccessResponse:
        data = await self._post("/api/screenshot", json={"url": url, "full_page": full_page})
        return {
            "image": base64.b64decode(data["image"]),
            "content": bs4.BeautifulSoup(data["content"], "html.parser").prettify() # type: ignore
        }


    async def lyrics(self, track: str, artist: Optional[str] = None) -> LyricSearchSuccessResponse:
        params = {
            "track": track
        }

        if artist is not None:
            params["artist"] = artist

        return await self._get("/api/search", params=params) # type: ignore