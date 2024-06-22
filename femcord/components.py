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

from .enums import ButtonStyles, TextInputStyles

from typing import Union, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Emoji

class Components:
    def __init__(self, *rows: List["Row"]) -> None:
        self.components = [row.__dict__ for row in rows]

    def add_row(self, row: "Row") -> None:
        self.components.append(row.__dict__)

class Row:
    def __init__(self, *items: List[Union["Button", "SelectMenu"]]) -> None:
        self.type = 1
        self.components = [item.__dict__ for item in items]

    def add_item(self, item: Union["Button", "SelectMenu"]) -> None:
        self.components.append(item.__dict__)

class Button:
    def __init__(self, label: Optional[str] = None, *, custom_id: Optional[str] = None, style: Optional[ButtonStyles] = None, url: Optional[str] = None, disabled: Optional[bool] = False, emoji: Optional["Emoji"] = None) -> None:
        self.type: int = 2
        self.label: str = label
        if style:
            self.style: int = style.value
        if custom_id:
            self.custom_id: str = custom_id
        if url:
            self.style = ButtonStyles.LINK.value
            self.url: str = url
        if disabled:
            self.disabled: bool = disabled
        if emoji:
            self.emoji: dict = {"id": emoji.id, "name": emoji.name}

class SelectMenu:
    def __init__(self, *, custom_id: str, placeholder: str, min_values: int = 1, max_values: int = 1, disabled: bool = False, options: List["Option"]):
        self.type: int = 3
        self.custom_id: str = custom_id
        self.placeholder: str = placeholder
        self.min_values: int = min_values
        self.max_values: int = max_values
        self.disabled: bool = disabled
        self.options: List[dict] = [option.__dict__ for option in options]

    def add_option(self, option: "Option"):
        self.options.append(option.__dict__)

class Option:
    def __init__(self, label: str, value: str, *, description: Optional[str] = None, emoji: Optional["Emoji"] = None, default: Optional[bool] = False):
        self.label: str = label
        self.value: str = value
        self.description: str = description
        if emoji:
            self.emoji: dict = {"id": emoji.id, "name": emoji.name}
        self.default: bool = default

class TextInput:
    def __init__(self, label: str, *, custom_id: str, style: TextInputStyles, min_length: Optional[int] = None, max_length: Optional[int] = None, required: bool = True, value: Optional[str] = None, placeholder: Optional[str] = None):
        self.type: int = 4
        self.label: str = label
        self.custom_id: str = custom_id
        self.style: int = style.value
        if min_length:
            self.min_length: int = min_length
        if max_length:
            self.max_length: int = max_length
        self.required: bool = required
        if value:
            self.value: str = value
        if placeholder:
            self.placeholder: str = placeholder