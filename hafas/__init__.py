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

import aiohttp, bs4, enum, json
from typing import Optional, Type, List
from types import TracebackType
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:108.0) Gecko/20100101 Firefox/108.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
}

COOKIES = {"app_version": "3.0.4.1"}


class ApiError(Exception):
    pass


class NotFound(Exception):
    pass


class TransportTypes(enum.Enum):
    TRAIN = "TRAIN"
    HafasNoTrain = "HAFAS_NO_TRAIN"


def _operator_image(operator: str) -> str:
    return f"https://bilkom.pl/img/carriers/{operator.lower()}.png"


@dataclass
class StationGeolocation:
    lat: float
    lon: float


@dataclass
class Station:
    name: str
    station_id: str
    id_string: str
    geolocation: StationGeolocation
    arrival_date: int = None
    real_arrival_date: int = None
    departure_date: int = None
    real_departure_date: int = None
    stop_time: int = None
    platform: str = None
    track: str = None
    platform_and_track_string: str = None

    def __post_init__(self):
        self.geolocation = StationGeolocation(**self.geolocation)
        self.stop_time = (
            self.real_departure_date - self.real_arrival_date
            if self.real_departure_date and self.real_arrival_date
            else None
        )


@dataclass
class MeansOfTransport:
    operator_id: str
    name: str
    transport_type: TransportTypes
    detailed_name: str = None
    operator_image: str = None

    def __post_init__(self):
        self.transport_type = TransportTypes(self.transport_type)
        self.operator_image = _operator_image(self.operator_id)


@dataclass
class JourneyTimes:
    departure: int
    real_departure: int
    arrival: int
    real_arrival: int
    duration: int
    delay: int = None

    def __post_init__(self): ...


@dataclass
class Journey:
    times: JourneyTimes
    route_type: TransportTypes
    departure_station: Station
    arrival_station: Station
    stops: List[Station]
    means_of_transport: MeansOfTransport

    def __post_init__(self):
        self.times = JourneyTimes(*self.times)
        self.route_type = TransportTypes(self.route_type)
        self.means_of_transport = MeansOfTransport(*self.means_of_transport)


@dataclass
class BoardRow:
    time: datetime
    delay: int
    destination: str
    number: str
    track: str
    url: str
    time_with_delay: Optional[datetime] = None
    operator: Optional[str] = None
    operator_image: Optional[str] = None

    def __post_init__(self):
        self.time = datetime.fromtimestamp(int(self.time) / 1000)
        self.delay = int(self.delay)
        self.time_with_delay = self.time + timedelta(minutes=self.delay)
        self.operator = parse_qs(urlparse(self.url).query)["tc"][0]
        self.operator_image = _operator_image(self.operator)


class HafasClient:
    def __init__(self, session: aiohttp.ClientSession = None):
        self.own_session = True if session is None else False
        self.session = session or aiohttp.ClientSession()

    async def __aenter__(self) -> "HafasClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        if self.own_session is True:
            await self.session.close()

    async def search_station(self, name: str) -> List[Station]:
        async with self.session.get(
            "https://bilkom.pl/stacje/szukaj", headers=HEADERS, params={"q": name}
        ) as response:
            if not response.status == 200:
                raise ApiError()

            data = await response.json()

            if not data["stations"]:
                raise NotFound()

            return [
                Station(
                    station["name"],
                    station["extId"],
                    station["id"],
                    station["geoPoint"],
                )
                for station in data["stations"]
            ]

    async def get_journey(
        self,
        departure_station: Station,
        arrival_station: Station,
        date: datetime,
        limit: int = 1,
    ) -> List[Journey]:
        async with self.session.get(
            "https://bilkom.pl/podroz",
            headers=HEADERS,
            cookies=COOKIES,
            params={
                "carrierKeys": "P2,P5,P7,O1,PZ,P0,P9,P4,P1,P3,P6,P8",
                "fromStation": departure_station.name,
                "poczatkowa": departure_station.id_string,
                "toStation": arrival_station.name,
                "docelowa": arrival_station.id_string,
                "data": date.strftime("%d%m%Y%H%M"),
                "date": date.strftime("%d/%m/%Y"),
                "time": date.strftime("%H:%M"),
                "przyjazd": "false",
                "minChangeTime": "10",
                "_csrf": "",
            },
        ) as response:
            if not response.status == 200:
                raise ApiError()

            content = await response.content.read()

            soup = bs4.BeautifulSoup(content, "html.parser")
            jsonPaths = soup.find_all("input", {"class": "jsonPath"})

            if not jsonPaths:
                raise NotFound()

            completeJourneys = []

            for jsonPath in jsonPaths[:limit]:
                partialJourneys = json.loads(jsonPath["value"])

                for journey in partialJourneys:
                    if journey["routeType"] == TransportTypes.HafasNoTrain.value:
                        continue

                    stops = [
                        Station(
                            station["name"],
                            station["extId"],
                            station["id"],
                            station["geoPoint"],
                            station["arrivalDate"],
                            station["realArrivalDate"],
                            station["departureDate"],
                            station["realDepartureDate"],
                            station["duration"],
                            station["platform"],
                            station["track"],
                            station["platformAndTrack"],
                        )
                        for station in journey["stops"]
                    ]

                    completeJourneys.append(
                        Journey(
                            (
                                journey["startDate"],
                                journey["realStartDate"],
                                journey["stopDate"],
                                journey["realStopDate"],
                                journey["duration"],
                            ),
                            journey["routeType"],
                            stops[0],
                            stops[-1],
                            stops,
                            (
                                journey["meansOfTransport"]["id"],
                                journey["meansOfTransport"]["name"],
                                journey["meansOfTransport"]["type"],
                                journey["meansOfTransport"]["detailedName"],
                            ),
                        )
                    )

                if not completeJourneys:
                    raise NotFound()

                return completeJourneys

    async def _get_board(self, station: Station, _type: str, date: datetime):
        async with self.session.get(
            "https://bilkom.pl/stacje/tablica",
            headers=HEADERS,
            cookies=COOKIES,
            params={
                "stacja": station.station_id,
                "przyjazd": str(_type == "arrivals"),
                "data": date.strftime("%d%m%Y%H%M"),
                "time": date.strftime("%H:%M"),
            },
        ) as response:
            if not response.status == 200:
                raise ApiError()

            content = await response.content.read()

            soup = bs4.BeautifulSoup(content, "html.parser")
            timetable_rows = soup.find_all("div", {"class": "timeTableRow"})

            if not timetable_rows:
                raise NotFound()

            return [
                BoardRow(
                    (time := row.find("div", {"class": "date-time-hidden"})).text,
                    time.get("data-difference", 0),
                    row.find("div", {"class": "direction"}).text,
                    row.find("div", {"class": "mobile-carrier"}).text,
                    (
                        track.text
                        if (track := row.find("div", {"class": "track"})) is not None
                        else ""
                    ),
                    row.find("div", {"class": "btnWrapper"})
                    .find("a", {"btn"})
                    .get("href"),
                )
                for row in timetable_rows
            ]

    async def get_arrivals(self, station: Station, date: datetime) -> List[BoardRow]:
        return await self._get_board(station, "arrivals", date)

    async def get_departures(self, station: Station, date: datetime) -> List[BoardRow]:
        return await self._get_board(station, "departures", date)