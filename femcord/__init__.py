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

__title__ = "femcord"
__author__ = "PoligonTeam"
__license__ = "Apache License"
__copyright__ = "Copyright 2022-2024 PoligonTeam"
__version__ = "0.6.9a"
__pronouns__ = "they/them"
__hotel__ = "trivago"

__import__("warnings").filterwarnings("ignore")

from .client import Client
from .intents import Intents
from .embed import Embed
from .components import Components, Row, Button, SelectMenu, Option, TextInput
from .types import Presence, Activity
from .enums import ActivityTypes, StatusTypes, ButtonStyles, TextInputStyles, InteractionCallbackTypes, InteractionTypes
from .errors import *
from .typing import Typing
from . import utils

from . import types
from . import commands