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

from .http import Route
from .types import *
from .embed import Embed
from .components import Components
from .http import Route
from .enums import *
from typing import Optional, Callable, Union, Sequence, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client

def set_functions(client: "Client"):
    @client.func_for(Guild)
    async def fetch_member(self: Guild, member_id: str) -> Dict[str, str]:
        return await client.http.request(Route("GET", "guilds", self.id, "members", member_id))

    @client.func_for(Guild)
    async def get_member(self: Guild, member: Union[dict, str], user: Optional[Union[User, dict]] = None) -> Member:
        for cached_member in self.members:
            if isinstance(member, str):
                if member.lower() in (cached_member.user.username.lower(), (cached_member.nick or "").lower(), cached_member.user.id):
                    return cached_member
            elif isinstance(member, dict):
                if user is not None:
                    if isinstance(user, User):
                        if user.id == cached_member.user.id:
                            return cached_member
                    elif isinstance(user, dict):
                        if user["id"] == cached_member.user.id:
                            return cached_member
                elif "user" in member:
                    if member["user"]["id"] == cached_member.user.id:
                        return cached_member

        if isinstance(member, str):
            member: Dict = await self.fetch_member(member)

        if isinstance(user, dict):
            user = await client.gateway.get_user(user)

        if not user and "user" in member:
            user = await client.gateway.get_user(member["user"])

        member = Member.from_raw(self, member, user)
        self.members.append(member)

        return member

    @client.func_for(Channel)
    async def fetch_message(self: Channel, message_id: str) -> Message:
        return await client.http.request(Route("GET", "channels", self.id, "messages", message_id))

    @client.func_for(Channel)
    async def start_typing(self: Channel):
        return await client.http.start_typing(self.id)

    @client.func_for(Channel)
    async def send(self: Channel, content: Optional[str] = None, *, embed: Optional[Embed] = None, embeds: Optional[Sequence[Embed]] = None, components: Optional[Components] = None, files: Optional[list] = [], mentions: Optional[list] = [], stickers: Optional[List[Sticker]] = None, other: Optional[dict] = {}) -> Message:
        resp = await client.http.send_message(self.id, content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

        if resp is not None:
            return await Message.from_raw(client.gateway, resp)

    @client.func_for(Message)
    async def reply(self: Message, content: Optional[str] = None, *, embed: Optional[Embed] = None, embeds: Optional[Sequence[Embed]] = [], components: Optional[Components] = None, files: Optional[list] = None, mentions: Optional[list] = [], stickers: Optional[List[Sticker]] = None, other: Optional[dict] = {}) -> Message:
        other["message_reference"] = {"guild_id": self.guild.id, "channel_id": self.channel.id, "message_id": self.id}
        return await self.channel.send(content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)

    @client.func_for(Message)
    async def edit(self: Message, content: Optional[str] = None, *, embed: Optional[Embed] = None, embeds: Optional[Sequence[Embed]] = None, components: Optional[Components] = None, files: Optional[list] = None, mentions: Optional[list] = [], stickers: Optional[List[Sticker]] = None, other: Optional[dict] = {}) -> Message:
        channel_id = self.channel

        if isinstance(self.channel, Channel):
            channel_id = self.channel.id

        resp = await client.http.edit_message(channel_id, self.id, content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, stickers=stickers, other=other)

        if resp is not None:
            return await Message.from_raw(client.gateway, resp)

    @client.func_for(Message)
    async def delete(self: Message):
        return await client.http.delete_message(self.channel.id, self.id)

    @client.func_for(Interaction)
    async def callback(self: Interaction, interaction_type: InteractionCallbackTypes, content: Optional[str] = None, *, title: Optional[str] = None, custom_id: Optional[str] = None, embed: Embed = None, embeds: Sequence[Embed] = None, components: Optional[Components] = None, files: Optional[list] = None, mentions: Optional[list] = [], other: Optional[dict] = {}):
        return await client.http.interaction_callback(self.id, self.token, interaction_type, content, title=title, custom_id=custom_id, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)

    @client.func_for(User)
    async def send(self: User, content: Optional[str] = None, *, embed: Optional[Embed] = None, embeds: Optional[Sequence[Embed]] = None, components: Optional[Components] = None, files: Optional[list] = [], mentions: Optional[list] = [], other: Optional[dict] = {}) -> Message:
        if self.dm is None:
            resp = await client.http.open_dm(self.id)
            self.dm = Channel.from_raw(resp)

        resp = await client.http.send_message(self.dm.id, content, embed=embed, embeds=embeds, components=components, files=files, mentions=mentions, other=other)

        if resp is not None:
            return await Message.from_raw(client.gateway, resp)

    @client.func_for(Member)
    async def kick(self: Member, reason: Optional[str] = None):
        return await client.http.kick_member(self.guild_id, self.user.id, reason=reason)

    @client.func_for(Member)
    async def ban(self: Member, reason: Optional[str] = None, delete_message_seconds: Optional[int] = 0):
        return await client.http.ban_member(self.guild_id, self.user.id, reason=reason, delete_message_seconds=delete_message_seconds)

    @client.func_for(Member)
    async def add_role(self: Member, role: Role):
        return await client.http.add_role(self.guild_id, self.user.id, role.id)

    @client.func_for(Member)
    async def remove_role(self: Member, role: Role):
        return await client.http.remove_role(self.guild_id, self.user.id, role.id)

    @client.func_for(Guild)
    async def ban(self: Guild, user: User, reason: Optional[str] = None, delete_message_seconds: Optional[int] = 0):
        return await client.http.ban_member(self.id, user.id, reason=reason, delete_message_seconds=delete_message_seconds)

    @client.func_for(Guild)
    async def unban(self: Guild, member_id: str, reason: Optional[str] = None):
        return await client.http.unban_member(self.id, member_id, reason=reason)

    @client.func_for(Channel)
    async def get_messages(self: Channel, *, around: Optional[int] = None, before: Optional[int] = None, after: Optional[int] = None, limit: Optional[int] = None) -> List[Message]:
        resp = await client.http.get_messages(self.id, around=around, before=before, after=after, limit=limit)

        if resp is not None:
            return [await Message.from_raw(client.gateway, message) for message in resp]

    @client.func_for(Channel)
    async def purge(self: Channel, *, limit: Optional[int] = None, messages: Optional[Sequence[Union[Message, str]]] = [], key: Optional[Callable[[Message], bool]] = None) -> List[dict]:
        if limit is not None:
            messages += [message for message in client.gateway.messages if message.channel.id == self.id][-limit:]

            if len(messages) < limit:
                missing_messages = limit - len(messages)
                messages += await self.get_messages(limit=missing_messages)

        if key is not None:
            messages = [message for message in messages if isinstance(message, Message) and key(message) is True]

        messages = list(set([message.id if isinstance(message, Message) else message for message in messages]))

        chunks = [messages[x:x+100] for x in range(0, len(messages), 100)]

        responses = []

        for messages in chunks:
            responses.append(await client.http.purge_channel(self.id, messages))

        return responses