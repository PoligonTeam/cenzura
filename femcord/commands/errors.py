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

class CommandError(Exception):
    def __init__(self, description, command):
        super().__init__(description)

        self.command = command

class CommandArgumentError(CommandError):
    def __init__(self, description, command, command_arguments, arguments, argument):
        super().__init__(description, command)

        self.command_arguments = command_arguments
        self.arguments = arguments
        self.argument = argument

class ExtensionNotFound(Exception):
    pass

class ExtensionAlreadyLoaded(Exception):
    pass

class ExtensionNotLoaded(Exception):
    pass

class CogAlreadyLoaded(Exception):
    pass

class CogNotFound(Exception):
    pass

class CommandNotFound(Exception):
    pass

class CommandDisabled(CommandError):
    pass

class MissingArgument(CommandArgumentError):
    pass

class InvalidArgumentType(CommandArgumentError):
    pass

class CheckFailure(Exception):
    pass

class NotOwner(CheckFailure):
    pass

class NotNsfw(CheckFailure):
    pass

class NoPermission(CheckFailure):
    pass