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

from dataclasses import dataclass
from html import unescape

@dataclass
class Station:
    """
    Station object.
    """
    name: str
    value: str
    stops_number: str
    id: str

    def __post_init__(self):
        self.name = unescape(self.name)

@dataclass
class Journey:
    """
    Journey object.
    """
    id: str
    time: str
    timeId: str
    product: str
    dest: str
    delay: str = ""

    def __post_init__(self):
        self.dest = unescape(self.dest)

        if self.delay is not None:
            self.delay = unescape(self.delay)