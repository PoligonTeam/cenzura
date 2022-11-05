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

import asyncio
from .gateway import Gateway
from .http import HTTP
from .intents import Intents
from .types import *
from .typefunctions import set_functions
from datetime import datetime
from typing import Callable, List, Type

class Client:
    def __init__(self, *, intents: Intents = Intents.default(), messages_limit: int = 1000, last_latencies_limit: int = 100):
        self.loop = asyncio.get_event_loop()
        self.token: str = None
        self.intents: Intents = intents
        self.http: HTTP = None
        self.gateway: Gateway = None
        self.listeners: List[Callable] = []
        self.waiting_for: List[Callable] = []
        self.messages_limit: int = messages_limit
        self.last_latencies_limit: List[int] = last_latencies_limit
        self.started_at: datetime = datetime.now()

    def event(self, function: Callable):
        self.listeners.append(function)

    async def wait_for(self, name: str, function: Callable, key: int, *, timeout: int = None, on_timeout: Callable = None):
        self.waiting_for.append((name, function, key))

        if timeout is not None:
            await asyncio.sleep(timeout)

            if (name, function, key) in self.waiting_for:
                self.waiting_for.remove((name, function, key))

                if on_timeout is not None:
                    await on_timeout()

    def run(self, token: str, *, bot: bool = True):
        self.token: str = token
        self.bot: bool = bot

        self.loop.create_task(HTTP(self))
        self.loop.create_task(Gateway(self))

        set_functions(self)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            on_closes = [listener() for listener in self.listeners if listener.__name__ == "on_close"]

            for on_close in on_closes:
                self.loop.run_until_complete(on_close)

            self.gateway.heartbeat.stop()

    @classmethod
    def func_for(cls, _type: Type):
        return lambda function: setattr(_type, function.__name__, function)