
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

import re
from ..types import *
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import Bot
    from .context import Context

pattern = re.compile(r"\d{16,19}")

def set_functions(bot: "Bot"):
    @bot.func_for(User)
    def from_arg(ctx: "Context", argument) -> User:
        result = pattern.search(argument)

        if result is not None:
            argument = result.group()

        return bot.gateway.get_user(argument)

    @bot.func_for(Member)
    def from_arg(ctx: "Context", argument) -> Member:
        result = pattern.search(argument)

        if result is not None:
            argument = result.group()

        return ctx.guild.get_member(argument)

    @bot.func_for(Channel)
    def from_arg(ctx: "Context", argument) -> Union[Channel, None]:
        result = pattern.search(argument)

        if result is not None:
            argument = result.group()

        return ctx.guild.get_channel(argument)

    @bot.func_for(Role)
    def from_arg(ctx: "Context", argument):
        result = pattern.search(argument)

        if result is not None:
            argument = result.group()

        return ctx.guild.get_role(argument)