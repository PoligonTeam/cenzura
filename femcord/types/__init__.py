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

from .channel import PermissionOverwrite, ThreadMetadata, ThreadMember, Channel
from .embed import EmbedFooter, EmbedImage, EmbedThumbnail, EmbedVideo, EmbedProvider, EmbedAuthor, EmbedField, Embed
from .emoji import Emoji
from .guild import Guild, WelcomeScreenChannel, WelcomeScreen
from .interaction import InteractionDataOption, InteractionData, Interaction
from .member import Member
from .presence import ActivityTimestamps, ActivityParty, ActivityAssets, ActivitySecrets, ActivityButton, Activity, ClientStatus, Presence
from .message import Attachment, MessageReference, MessageSticker, SelectOptions, MessageComponents, MessageReaction, Message
from .role import Role
from .sticker import Sticker
from .user import User
from .voice import VoiceState

channel.Message = Message

interaction.MessageComponents = MessageComponents

from datetime import datetime

class M:
    def __matmul__(self, item):
        if isinstance(item, User):
            return f"<@{item.id}>"
        elif isinstance(item, Member):
            return f"<@{item.user.id}>"
        elif isinstance(item, Channel):
            return f"<#{item.id}>"
        elif isinstance(item, Role):
            return f"<@&{item.id}>"

class T:
    styles = {
        "t": "16:20",
        "T": "16:20:30",
        "d": "20/04/2021",
        "D": "20 April 2021",
        "f": "20 April 2021 16:20",
        "F": "Tuesday, 20 April 2021 16:20",
        "R": "2 months ago"
    }
    style = "f"

    def __getitem__(self, style):
        if style in self.styles:
            self.style = style

        return self

    def __matmul__(self, item: datetime):
        text = f"<t:{int(item.timestamp())}:{self.style}>"
        self.style = "f"

        return text

m = M()
t = T()