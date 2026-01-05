"""
Copyright 2022-2026 PoligonTeam

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

from tortoise.models import Model
from tortoise.fields import Field, IntField, TextField, JSONField, BooleanField, DatetimeField, CharEnumField, ReverseRelation, ForeignKeyRelation, ForeignKeyField, Field
from enum import Enum
from typing import TypedDict
import json

class TicketConfig(TypedDict):
    enabled: bool
    log_channel_id: str
    category_id: str
    tickets_role_id: str
    tickets_message_id: str
    ticket_categories: list[str]

class TicketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"

class TextArray(Field):
    SQL_TYPE = "text[]"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_db_value(self, value, instance):
        return value

    def to_python_value(self, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

class JSONArray(Field):
    SQL_TYPE = "JSON[]"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_db_value(self, value, instance):
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def to_python_value(self, value):
        if isinstance(value, str):
            return json.loads(value)
        return value

class Guilds(Model):
    id = IntField(pk=True)
    guild_id = TextField()
    prefix = TextField()
    welcome_message = TextField()
    leave_message = TextField()
    autorole = TextField()
    custom_commands = TextArray()
    database = JSONField()
    permissions = JSONField()
    schedules = TextArray()
    language = TextField()
    verification_role = TextField()
    verification_message = TextField()
    verification_channel = TextField()
    eventhandlers = JSONField()
    interaction_callbacks = JSONField()
    # tickets_config = JSONField[TicketConfig]()
    # tickets: ReverseRelation["Tickets"]

class Users(Model):
    id = IntField(pk=True)
    user_id = TextField()
    avatars = JSONArray()

class LastFM(Model):
    id = IntField(pk=True)
    user_id = TextField()
    username = TextField()
    token = TextField()
    script = TextField()
    avatar = TextField()

class Artists(Model):
    id = IntField(pk=True)
    artist = TextField()
    image = TextField()

class Lyrics(Model):
    id = IntField(pk=True)
    artist = TextField()
    title = TextField()
    source = TextField()
    lyrics = TextField()

class Giveaways(Model):
    id = IntField(pk=True)
    message_id = TextField()
    channel_id = TextField()
    guild_id = TextField()
    prize = TextField()
    host_id = TextField()
    winner_count = IntField()
    end_time = DatetimeField()
    participants = TextArray()
    ended = BooleanField(default=False)

# class Tickets(Model):
#     id = IntField(pk=True)
#     guild_id: ForeignKeyRelation[Guilds] = ForeignKeyField("models.Guilds", related_name="tickets")
#     user_id = TextField()
#     channel_id = TextField()
#     status = CharEnumField(
#         enum_type=TicketStatus,
#         default="open"
#     )