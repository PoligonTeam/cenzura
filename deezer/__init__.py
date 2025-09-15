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

from aiohttp import ClientSession
from typing import Optional, Type
from types import TracebackType
from .models import SearchResponse, TrackDetail

class DeezerApiError(Exception):
    pass

class DeezerClient:
    api_url = "https://api.deezer.com"

    def __init__(self, session: Optional[ClientSession] = None) -> None:
        self.own_session = session is None
        self.session = session or ClientSession()

    async def __aenter__(self) -> "DeezerClient":
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_val: Optional[BaseException],
            exc_tb: Optional[TracebackType],
    ):
        if self.own_session is True:
            await self.session.close()

    async def search(self, query: str) -> SearchResponse:
        async with self.session.get(self.api_url + "/search/track", params={
            "q": query
        }) as response:
            if response.status != 200:
                raise DeezerApiError()

            return await response.json()

    async def get_track(self, track_id: str | int) -> TrackDetail:
        async with self.session.get(self.api_url + f"/track/{track_id}") as response:
            if response.status != 200:
                raise DeezerApiError()

            return await response.json()