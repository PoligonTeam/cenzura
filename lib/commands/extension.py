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

from .enums import CommandTypes
from ..utils import get_index

class Command:
    def __init__(self, **kwargs):
        self.type = kwargs.get("type")
        self.parent = kwargs.get("parent", None)
        self.cog = kwargs.get("cog", None)

        self.name = kwargs.get("name") or kwargs.get("callback").__name__
        self.description = kwargs.get("description")
        self.usage = kwargs.get("usage")
        self.enabled = kwargs.get("enabled", True)
        self.hidden = kwargs.get("hidden", False)
        self.aliases = kwargs.get("aliases", [])
        self.guild = kwargs.get("guild", None)
        self.other = kwargs.get("other", {})
        self.callback = kwargs.get("callback")

    async def __call__(self, context, *args, **kwargs):
        if self.cog is not None:
            return await self.callback(self.cog, context, *args, **kwargs)

        return await self.callback(context, *args, **kwargs)

class Group(Command):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.subcommands = []

    def command(self, **kwargs):
        def decorator(func):
            kwargs["type"] = CommandTypes.SUBCOMMAND
            kwargs["parent"] = self.name
            kwargs["callback"] = func

            subcommand = Command(**kwargs)
            self.subcommands.append(subcommand)

            return subcommand

        return decorator

    def group(self, **kwargs):
        def decorator(func):
            kwargs["type"] = CommandTypes.GROUP
            kwargs["callback"] = func

            group = Group(**kwargs)
            self.subcommands.append(group)

            return group

        return decorator

    def get_subcommand(self, command):
        index = get_index(self.subcommands, command, key=lambda c: c.name)

        if index is None:
            for command_object_index, command_object in enumerate(self.subcommands):
                if command in command_object.aliases:
                    index = command_object_index

        if index is None:
            return

        return self.subcommands[index]

class Listener:
    def __init__(self, callback):
        self.callback = callback
        self.cog = None
        self.__name__ = callback.__name__

    def __str__(self):
        return f"{self.callback!r}"

    def __repr__(self):
        return f"{self.callback!r}"

    async def __call__(self, *args, **kwargs):
        if self.cog is not None:
            return await self.callback(self.cog, *args, **kwargs)

        return await self.callback(*args, **kwargs)

class Cog:
    def __init__(self):
        self.listeners = []
        self.commands = []

    def on_cog_unload(self):
        pass