"""
Copyright 2022 Smugaski

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
from .errors import InvalidBoardType, InvalidStation
from .models import Journey, Station
import time

class Client:
    def __init__(self):
        self.headers = {
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = ClientSession(headers=self.headers)

    async def search_station(self, name: str) -> list[Station]:
        """
        Search for station by name.
        """
        async with self.session.get(f"https://rozklad-pkp.pl/station/search?term={name}&short=0") as response:
            data = await response.json(content_type=None)

            if not data:
                raise InvalidStation()

            return [Station(*list(station.values())) for station in data]

    async def list_journeys(self, station: Station, type: str = "dep", amount: int = 5, start_time: int = None) -> list[Journey]:
        """
        List arrivals/departures for station.
        """
        if not type in ["dep", "arr"]:
            raise InvalidBoardType()

        start_time = start_time or int(time.time())

        async with self.session.get(f"https://rozklad-pkp.pl/pl/sq?input={station.value}&boardType={type}&disableEquivs=yes&maxJourneys={amount}&start={start_time}&ajax=yes&") as response:
            data = await response.json(content_type=None)
            journeys = data["stBoard"]["journey"]

            return [Journey(*list(journey.values())) for journey in journeys]