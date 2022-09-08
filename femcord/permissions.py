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

from .enums import Permissions as PermissionsEnum
from .errors import PermissionNotExist
from functools import reduce
from typing import TypeVar, Union

__all__ = ("Permissions",)

Permissions = TypeVar("Permissions")

class Permissions:
    def __init__(self, *permissions: Union[PermissionsEnum, str]):
        self.permissions = []

        for permission in permissions:
            self.add(permission)

    def __str__(self) -> str:
        return "<Permissions permissions={!r} value={!r}>".format(self.permissions, self.get_int())

    def __repr__(self) -> str:
        return "<Permissions permissions={!r} value={!r}>".format(self.permissions, self.get_int())

    def check(self, permission: int) -> PermissionsEnum:
        if not isinstance(permission, PermissionsEnum) and permission.upper() in (i.name for i in PermissionsEnum):
            permission = PermissionsEnum[permission.upper()]

        if not isinstance(permission, PermissionsEnum):
            raise PermissionNotExist(f"{permission} doesn't exist")

        return permission

    def add(self, permission: int) -> Permissions:
        permission = self.check(permission)
        self.permissions.append(permission)

        return self

    def remove(self, permission: int) -> Permissions:
        permission = self.check(permission)
        self.permissions.remove(permission)

        return self

    def get_int(self) -> int:
        if not self.permissions:
            return 0

        return reduce(lambda a, b: a | b, [permission.value for permission in PermissionsEnum if permission in self.permissions])

    def has(self, permission: int) -> bool:
        permission = self.check(permission)

        if PermissionsEnum.ADMINISTRATOR in self.permissions:
            return True

        return permission in self.permissions

    @classmethod
    def all(cls):
        return cls(*PermissionsEnum)

    @classmethod
    def from_int(cls, permissions: int):
        return cls(*(permission for permission in PermissionsEnum if permissions & permission.value == permission.value))