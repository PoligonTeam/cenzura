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
from .http import Http
from .intents import Intents
from .types import *
from .typesfunctions import set_functions
from datetime import datetime

class Client:
    def __init__(self, *, intents: Intents = Intents.default(), messages_limit: int = 1000, last_latencies_limit: int = 100):
        self.loop = asyncio.get_event_loop()
        self.token = None
        self.intents = intents
        self.http: Http = None
        self.gateway: Gateway = None
        self.listeners = []
        self.waiting_for = []
        self.messages_limit = messages_limit
        self.last_latencies_limit = last_latencies_limit
        self.started_at = datetime.now()

    def event(self, func):
        self.listeners.append(func)

    def wait_for(self, name, func, key):
        self.waiting_for.append((name, func, key))

    def run(self, token, *, bot: bool = True):
        self.token = token
        self.bot = bot

        self.loop.create_task(Http(self))
        self.loop.create_task(Gateway(self))

        set_functions(self)

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.gateway.heartbeat.stop()

    @classmethod
    def func_for(cls, _type):
        return lambda func: setattr(_type, func.__name__, func)