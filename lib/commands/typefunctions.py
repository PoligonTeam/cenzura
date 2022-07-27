
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

def set_functions(bot):
    @bot.func_for(User)
    def from_arg(ctx, argument):
        return bot.gateway.get_user(user_id.group() if (user_id := re.search("\d+", argument)) is not None else argument)

    @bot.func_for(Member)
    def from_arg(ctx, argument):
        return ctx.guild.get_member(member_id.group() if (member_id := re.search("\d+", argument)) is not None else argument)

    @bot.func_for(Channel)
    def from_arg(ctx, argument):
        return ctx.guild.get_channel(channel_id.group() if (channel_id := re.search("\d+", argument)) is not None else argument)

    @bot.func_for(Role)
    def from_arg(ctx, argument):
        return ctx.guild.get_role(role_id.group() if (role_id := re.search("\d+", argument)) is not None else argument)