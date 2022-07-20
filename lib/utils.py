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

from datetime import datetime
from .errors import InvalidArgument

DISCORD_EPOCH = 1420070400000

def parse_time(timestamp):
    if isinstance(timestamp, str):
        timestamp = timestamp.replace(" ", "T")
        return datetime.fromisoformat(timestamp)

def time_from_snowflake(snowflake):
    snowflake = int(snowflake)
    timestamp = ((snowflake >> 22) + DISCORD_EPOCH) / 1000

    return datetime.fromtimestamp(timestamp)

def get_mime(data: bytes):
    if data[0:8] == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
        return "image/png"
    elif data[0:3] == b"\xff\xd8\xff" or data[6:10] in (b"JFIF", b"Exif"):
        return "image/jpeg"
    elif data[0:6] in (b"\x47\x49\x46\x38\x37\x61", b"\x47\x49\x46\x38\x39\x61"):
        return "image/gif"
    elif (data[0:4], data[8:12]) == (b"RIFF", b"WEBP"):
        return "image/webp"

    raise InvalidArgument("Unsupported image type given")

def get_index(iterable, value, *, key = None):
    for i, v in enumerate(iterable):
        if key and key(v) == value:
            return i
        if not key and value == v:
            return i