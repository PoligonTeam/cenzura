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

from .errors import *
from functools import wraps

def check(check_function, *, error=CheckFailure):
    def decorator(func):
        @wraps(func)
        def wrapper(self, ctx, *args, **kwargs):
            if not check_function(self, ctx):
                raise error(f"Check failed for {func.__name__}")

            return func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator

def is_owner(func):
    def check_function(self, ctx):
        return ctx.author.id in self.bot.owners

    return check(check_function, error=NotOwner)(func)

def is_nsfw(func):
    def check_function(self, ctx):
        return ctx.channel.nsfw

    return check(check_function, error=NotNsfw)(func)

def has_permissions(*permissions):
    def decorator(func):
        def check_function(self, ctx):
            for permission in permissions:
                if ctx.guild.owner.user.id == ctx.author.id:
                    return True
                if not ctx.member.permissions.has(permission):
                    return False

                return True

        return check(check_function, error=NoPermission)(func)

    return decorator