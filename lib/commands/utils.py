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

def check(check_func, *, error=CheckFailure):
    def decorator(func):
        @wraps(func)
        def wrapper(self, ctx, *args, **kwargs):
            if not check_func(self, ctx):
                raise error(f"Check failed for {func.__name__}")

            return func(self, ctx, *args, **kwargs)

        return wrapper

    return decorator

def is_owner(func):
    def check_func(self, ctx):
        return ctx.author.id in self.bot.owners

    return check(check_func, error=NotOwner)(func)

def is_nsfw(func):
    def check_func(self, ctx):
        return ctx.channel.nsfw

    return check(check_func, error=NotNsfw)(func)

def has_permission(permission):
    def decorator(func):
        def check_func(self, ctx):
            return ctx.member.permissions.has(permission)

        return check(check_func, error=NoPermission)(func)

    return decorator