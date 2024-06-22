"""
Copyright 2022-2024 PoligonTeam

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

from typing import Callable, Union, List, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Context

class Command:
    def __init__(self, **kwargs):
        self.type: CommandTypes = kwargs["type"]
        self.parent: Union[str, None] = kwargs.get("parent", None)
        self.cog: Union[Cog, None] = kwargs.get("cog", None)

        self.callback: Callable = kwargs["callback"]
        self.name: str = kwargs.get("name") or self.callback.__name__
        self.description: Union[str, None] = kwargs.get("description")
        self.usage: Union[str, None] = kwargs.get("usage")
        self.enabled: bool = kwargs.get("enabled", True)
        self.hidden: bool = kwargs.get("hidden", False)
        self.aliases: List[str] = kwargs.get("aliases", [])
        self.guild_id: Union[str, None] = kwargs.get("guild_id", None)
        self.other: dict = kwargs.get("other", {})

    async def __call__(self, context: "Context", *args, **kwargs) -> None:
        if self.cog is not None:
            return await self.callback(self.cog, context, *args, **kwargs)

        return await self.callback(context, *args, **kwargs)

class Group(Command):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.subcommands: List[Command] = []

    def command(self, **kwargs) -> Callable[..., Command]:
        def decorator(func: Callable) -> Command:
            kwargs["type"] = CommandTypes.SUBCOMMAND
            kwargs["parent"] = self.name
            kwargs["callback"] = func

            subcommand = Command(**kwargs)
            self.subcommands.append(subcommand)

            return subcommand

        return decorator

    def group(self, **kwargs) -> Callable[..., "Group"]:
        def decorator(func: Callable) -> "Group":
            kwargs["type"] = CommandTypes.GROUP
            kwargs["callback"] = func

            group = Group(**kwargs)
            self.subcommands.append(group)

            return group

        return decorator

    def get_subcommand(self, command: str) -> Union[Command, None]:
        index = get_index(self.subcommands, command, key=lambda c: c.name)

        if index is None:
            for command_object_index, command_object in enumerate(self.subcommands):
                if command in command_object.aliases:
                    index = command_object_index

        if index is None:
            return

        return self.subcommands[index]

    def walk_subcommands(self) -> List[Command]:
        commands = []

        for command in self.subcommands:
            if command.type == CommandTypes.GROUP:
                commands.extend(command.walk_subcommands())

            commands.append(command)

        return commands

class Listener:
    def __init__(self, callback: Callable) -> None:
        self.callback: Callable = callback
        self.cog: Union[Cog, None] = None
        self.__name__ = callback.__name__

    def __str__(self) -> str:
        return f"{self.callback!r}"

    def __repr__(self) -> str:
        return f"{self.callback!r}"

    async def __call__(self, *args, **kwargs) -> None:
        if self.cog is not None:
            return await self.callback(self.cog, *args, **kwargs)

        return await self.callback(*args, **kwargs)

class Cog:
    name: str
    description: Union[str, None]
    hidden: bool
    listeners: List[Listener]
    commands: List[Command]

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def walk_commands(self) -> List[Command]:
        commands = []

        for command in self.commands:
            if command.type == CommandTypes.GROUP:
                commands.extend(command.walk_subcommands())

            commands.append(command)

        return commands