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

from .enums import Intents as IntentsEnum
from .errors import IntentNotExist
from functools import reduce

__all__ = ("Intents",)

class Intents:
    def __init__(self, *intents):
        for intent in intents:
            self.check(intent)

        self.intents = list(intents)

    def __str__(self):
        return "<Intents intents={!r} value={!r}>".format(self.intents, self.get_int())

    def __repr__(self):
        return "<Intents intents={!r} value={!r}>".format(self.intents, self.get_int())

    def check(self, intent):
        if not isinstance(intent, IntentsEnum) and intent in (i.name for i in IntentsEnum):
            intent = IntentsEnum[intent]

        if not intent in IntentsEnum:
            raise IntentNotExist(f"{intent} doesn't exist")

        return intent

    def add(self, intent):
        intent = self.check(intent)
        self.intents.append(intent)

        return self

    def remove(self, intent):
        intent = self.check(intent)
        self.intents.remove(intent)

        return self

    def get_int(self):
        return reduce(lambda a, b: a | b, [intent.value for intent in IntentsEnum if intent in self.intents])

    def has(self, intent):
        intent = self.check(intent)

        return intent in self.intents

    @classmethod
    def all(cls):
        return cls(*(intent for intent in IntentsEnum))

    @classmethod
    def default(cls):
        return cls(*(intent for intent in IntentsEnum if not intent in (IntentsEnum.GUILD_MEMBERS, IntentsEnum.GUILD_PRESENCES, IntentsEnum.GUILD_MESSAGES)))

    @classmethod
    def from_int(cls, intents):
        return cls(*(intent for intent in IntentsEnum if intents & intent.value == intent.value))