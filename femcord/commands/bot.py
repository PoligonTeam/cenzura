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

from ..client import Client
from ..intents import Intents
from ..errors import InvalidArgument
from ..utils import get_index
from .errors import *
from .extension import Cog, Command, Group, Listener
from .enums import CommandTypes
from .context import Context
from .typefunctions import set_functions
from types import CoroutineType
from dataclasses import is_dataclass
from typing import Callable, Union, Iterable
import importlib.util, inspect, traceback, sys

class Bot(Client):
    def __init__(self, *, command_prefix, intents: Intents = Intents.all(), messages_limit: int = 1000, owners: Iterable = []):
        super().__init__(intents = intents, messages_limit = messages_limit)

        self.original_prefix = self.command_prefix = command_prefix
        self.owners = list(owners)

        if not callable(self.command_prefix):
            async def command_prefix(self, message):
                return self.original_prefix

            self.command_prefix = command_prefix

        self.extensions = []
        self.cogs = []
        self.commands = []

        self.before_call_functions = []
        self.after_call_functions = []

        set_functions(self)

        @self.event
        async def on_message_create(message):
            if message.author.bot:
                return

            await self.process_commands(message)

    def before_call(self, func):
        self.before_call_functions.append(func)

    def after_call(self, func):
        self.after_call_functions.append(func)

    def command(self, **kwargs):
        def decorator(func):
            kwargs["type"] = CommandTypes.COMMAND
            kwargs["callback"] = func

            command = Command(**kwargs)
            self.commands.append(command)

            return command

        return decorator

    def group(self, **kwargs):
        def decorator(func):
            kwargs["type"] = CommandTypes.GROUP
            kwargs["callback"] = func

            group = Group(**kwargs)
            self.commands.append(group)

            return group

        return decorator

    def get_command(self, command, guild_id = None):
        commands = self.commands

        if guild_id is not None:
            commands = [command for command in commands if command.guild_id and command.guild_id == guild_id]

        index = get_index(commands, command, key=lambda command: command.name)

        if index is None:
            for command_object_index, command_object in enumerate(commands):
                if command in command_object.aliases:
                    index = command_object_index

        if index is None:
            return

        return commands[index]

    def remove_command(self, command: Union[Command, str]):
        if isinstance(command, str):
            index = get_index(self.commands, command, key=lambda command: command.name)

            if index is None:
                raise CommandNotFound(command)

            command = self.commands[index]

        if command.cog is not None:
            command.cog.commands.remove(command)

        self.commands.remove(command)

    def load_cog(self, cog):
        if cog.__class__ in (cog.__class__ for cog in self.cogs):
            raise CogAlreadyLoaded(cog.__class__.__name__)

        cog.name = getattr(cog, "name", cog.__class__.__name__)
        cog.description = getattr(cog, "description", None)
        cog.hidden = getattr(cog, "hidden", False)

        cog.commands = [getattr(cog, command) for command in dir(cog) if isinstance(getattr(cog, command), Command)]
        cog.listeners = [getattr(cog, listener) for listener in dir(cog) if isinstance(getattr(cog, listener), Listener)]

        for command in cog.commands:
            command.cog = cog

        for listener in cog.listeners:
            listener.cog = cog

        self.commands += [command for command in cog.commands if not command.type == CommandTypes.SUBCOMMAND]
        self.listeners += cog.listeners

        self.cogs.append(cog)

        cog.on_load()

    def get_cog(self, cog):
        index = get_index(self.cogs, cog, key=lambda cog: cog.name)

        if index is None:
            return

        return self.cogs[index]

    def unload_cog(self, cog: Union[Cog, str]):
        if isinstance(cog, str):
            index = get_index(self.cogs, cog, key=lambda cog: cog.__class__.__name__)

            if index is None:
                raise CogNotFound(cog)

            cog = self.cogs[index]

        cog.on_unload()

        for command in cog.commands:
            self.remove_command(command)

        for listener in cog.listeners:
            self.listeners.remove(listener)

        self.cogs.remove(cog)

    def load_extension(self, name):
        name = importlib.util.resolve_name(name, None)

        if name in (name.__name__ for name in self.extensions):
            raise ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)

        if spec is None:
            raise ExtensionNotFound(name)

        extension = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(extension)

        sys.modules[name] = extension

        setup = getattr(extension, "setup")
        setup(self)

        self.extensions.append(extension)

    def get_extension(self, extension):
        index = get_index(self.extensions, extension, key=lambda command: command.__name__)

        if index is None:
            return

        return self.extensions[index]

    def unload_extension(self, name):
        name = importlib.util.resolve_name(name, None)
        index = get_index(self.extensions, name, key=lambda extension: extension.__name__)

        if index is None:
            raise ExtensionNotLoaded(name)

        for cog in self.cogs:
            if inspect.getmodule(cog) == self.extensions[index]:
                self.unload_cog(cog)

        del sys.modules[name]
        del self.extensions[index]

    async def process_commands(self, message, *, before_call_functions: Union[list, Callable] = [], after_call_functions: Union[list, Callable] = []):
        if isinstance(before_call_functions, Callable):
            before_call_functions = [before_call_functions]
        if isinstance(after_call_functions, Callable):
            after_call_functions = [after_call_functions]

        prefixes = prefix = await self.command_prefix(self, message)

        if not isinstance(prefix, str):
            for _prefix in prefixes:
                if len(message.content) > len(_prefix) and message.content[0:len(_prefix)] == _prefix:
                    prefix = _prefix

        if not (len(message.content) > len(prefix) and message.content[0:len(prefix)] == prefix): return

        on_error = True if "on_error" in (listener.__name__ for listener in self.listeners) else False

        content_split = message.content[len(prefix):].split(" ")

        command = content_split[0]
        arguments = content_split[1:]

        context = Context(self, message)

        command_object = self.get_command(command)
        skip_arguments = 1

        if command_object and command_object.guild_id and not context.guild.id == command_object.guild_id:
            command_object = self.get_command(command, guild_id=context.guild.id)

        while command_object and arguments and command_object.type is CommandTypes.GROUP:
            command_object = command_object.get_subcommand(arguments[0])
            arguments = arguments[1:]

        if command_object is None:
            error = CommandNotFound(f"{command} was not found")
            context.arguments = arguments

            if not on_error:
                raise error

            return await self.gateway.dispatch("error", context, error)

        if command_object.cog is not None:
            skip_arguments += 1

        context.command = command = command_object
        command_arguments = list(inspect.signature(command.callback).parameters.values())[skip_arguments:]
        default_arguments = [argument for argument in command_arguments if argument.default != argument.empty]

        if command.enabled is False:
            error = CommandDisabled(f"{command.name} command is disabled", command)

            if not on_error:
                raise error

            return await self.gateway.dispatch("error", context, error)

        args = []
        kwargs = {}

        if not len(arguments) >= len(command_arguments) - len(default_arguments):
            command_argument = command_arguments[len(arguments)].name
            error = MissingArgument(f"{command_argument} was not specified", command, command_arguments, arguments, command_argument)
            context.arguments = arguments

            if not on_error:
                raise error

            return await self.gateway.dispatch("error", context, error)

        for index, command_argument in enumerate(command_arguments):
            annotations = [command_argument.annotation]

            if hasattr(annotations[0], "__origin__") and annotations[0].__origin__ == Union:
                annotations = annotations[0].__args__

            if annotations[0] == command_argument.empty:
                annotations = [str]

            if index + 1 > len(arguments) and command_argument.default != command_argument.empty:
                break

            errors = []

            for annotation in annotations:
                parsed_argument = None

                try:
                    if is_dataclass(annotation) is True:
                        annotation = getattr(annotation, "from_arg", annotation)
                        parsed_argument = annotation(context, arguments[index])
                    else:
                        parsed_argument = annotation(arguments[index])

                    if isinstance(parsed_argument, CoroutineType):
                        parsed_argument = await parsed_argument

                    if parsed_argument is None:
                        raise InvalidArgument()

                    arguments[index] = parsed_argument
                    break
                except Exception:
                    errors.append(annotation.__name__)

            if (len(errors), len(annotations)) == (1, 1):
                error = InvalidArgumentType(f"'{annotations[0].__name__}' type is not valid for '{command_argument.name}' argument", command, command_arguments, arguments, command_argument.name)
                context.arguments = arguments

                if not on_error:
                    raise error

                return await self.gateway.dispatch("error", context, error)

            if len(errors) == len(annotations):
                apostrophe = "'"
                error = InvalidArgumentType(f"{', '.join(apostrophe + annotation.__name__ + apostrophe for annotation in annotations[:-1]) + ' and ' + apostrophe + annotations[-1].__name__ + apostrophe} types are not valid for '{command_argument.name}' argument", command, command_arguments, arguments, command_argument.name)
                context.arguments = arguments

                if not on_error:
                    raise error

                return await self.gateway.dispatch("error", context, error)

            if command_argument.kind == command_argument.POSITIONAL_OR_KEYWORD:
                argument = arguments[index]
                context.arguments.append(argument)
                args.append(argument)

            elif command_argument.kind == command_argument.VAR_POSITIONAL:
                argument = arguments[index:]
                context.arguments.append(argument)
                args.append(argument)

            elif command_argument.kind == command_argument.KEYWORD_ONLY:
                argument = arguments[index:][0]
                if all(isinstance(x, str) for x in arguments[index:]):
                    argument = " ".join(arguments[index:])
                context.arguments.append(argument)
                kwargs[command_argument.name] = argument

        async def run_command():
            for before_call in self.before_call_functions + before_call_functions:
                await before_call(context)

            try:
                await command(context, *args, **kwargs)
            except Exception as error:
                context.arguments = arguments

                if not on_error:
                    return traceback.print_exc()

                await self.gateway.dispatch("error", context, error)

            for after_call in self.after_call_functions + after_call_functions:
                await after_call(context)

        self.loop.create_task(run_command())