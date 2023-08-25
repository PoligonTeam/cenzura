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

from .types import *
from .enums import *
from .utils import *

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import Gateway

CDN_URL = "https://cdn.discordapp.com"

async def channel_create(gateway: "Gateway", channel):
    if "guild_id" not in channel:
        return

    guild = gateway.get_guild(channel["guild_id"])
    channel = Channel.from_raw(channel)

    guild.channels.append(channel)

    return channel,

async def channel_update(gateway: "Gateway", channel):
    if "guild_id" not in channel:
        return

    guild = gateway.get_guild(channel["guild_id"])
    channel = Channel.from_raw(channel)

    index = get_index(guild.channels, channel.id, key=lambda c: c.id)

    old_channel = gateway.copy(guild.channels[index])
    guild.channels[index] = channel

    return old_channel, channel

async def channel_delete(gateway: "Gateway", channel):
    if "guild_id" not in channel:
        return

    guild = gateway.get_guild(channel["guild_id"])

    index = get_index(guild.channels, channel["id"], key=lambda c: c.id)

    channel = guild.channels[index]
    del guild.channels[index]

    return channel,

async def thread_create(gateway: "Gateway", thread):
    guild = gateway.get_guild(thread["guild_id"])
    thread = Channel.from_raw(thread)

    guild.threads.append(thread)

    return thread,

async def thread_update(gateway: "Gateway", thread):
    guild = gateway.get_guild(thread["guild_id"])
    thread = Channel.from_raw(thread)

    index = get_index(guild.threads, thread.id, key=lambda t: t.id)

    if index is None:
        return

    old_thread = gateway.copy(guild.threads[index])
    guild.threads[index] = thread

    return old_thread, thread

async def thread_delete(gateway: "Gateway", thread):
    guild = gateway.get_guild(thread["guild_id"])

    index = get_index(guild.threads, thread["id"], key=lambda t: t.id)

    thread = guild.threads[index]
    del guild.threads[index]

    return thread,

async def guild_create(gateway: "Gateway", guild):
    guild = Guild.from_raw(guild)
    gateway.guilds.append(guild)

    if len(gateway.unavailable_guilds) <= len(gateway.guilds):
        gateway.unavailable_guilds = []

        if not gateway.guilds[0].id in gateway.requested_guilds:
            await gateway.ws.send(Opcodes.REQUEST_GUILD_MEMBERS, {"guild_id": gateway.guilds[0].id, "query": "", "limit": 0, "presences": gateway.intents.has(Intents.GUILD_PRESENCES)})

        gateway.request_members += [guild.id for guild in gateway.guilds[1:]]

        return guild,

    if not guild.id in gateway.requested_guilds and gateway.dispatched_ready and not gateway.request_members:
        await gateway.ws.send(Opcodes.REQUEST_GUILD_MEMBERS, {"guild_id": guild.id, "query": "", "limit": 0, "presences": gateway.intents.has(Intents.GUILD_PRESENCES)})

    return guild,

async def guild_members_chunk(gateway: "Gateway", chunk):
    guild = gateway.get_guild(chunk["guild_id"])

    # gateway.member_chunks.append(chunk)

    # return None,

    for member in chunk["members"]:
        member = await guild.get_member(member)

        if member.user.id == guild.owner:
            guild.owner = member
        elif member.user.id == gateway.bot_user.id:
            guild.me = member

        if gateway.intents.has(Intents.GUILD_PRESENCES) is True:
            for presence in chunk["presences"]:
                if "user" in presence and presence["user"]["id"] == member.user.id:
                    member.presence = Presence.from_raw(presence)

    if chunk["chunk_index"] + 1 == chunk["chunk_count"]:
        gateway.requested_guilds.append(chunk["guild_id"])

        if gateway.request_members and not gateway.request_members[0] in gateway.requested_guilds:
            await gateway.ws.send(Opcodes.REQUEST_GUILD_MEMBERS, {"guild_id": gateway.request_members.pop(0), "query": "", "limit": 0, "presences": gateway.intents.has(Intents.GUILD_PRESENCES)})

    # if not gateway.dispatched_ready and len(gateway.requested_guilds) == len(gateway.guilds):
    #     print(2)

    return chunk,

async def presence_update(gateway: "Gateway", presence):
    # return None,
    guild = gateway.get_guild(presence["guild_id"])
    member = await guild.get_member(presence["user"]["id"])

    member.presence = Presence.from_raw(presence)

    return member,

async def guild_update(gateway: "Gateway", guild):
    index = get_index(gateway.guilds, guild["id"], key=lambda g: g.id)

    old_guild = gateway.copy(gateway.guilds[index])

    guild_object = gateway.guilds[index]

    guild_object.premium_tier = guild["premium_tier"]
    guild_object.discovery_splash = guild["discovery_splash"]
    guild_object.owner = await guild_object.get_member(guild["owner_id"])
    guild_object.banner = guild["banner"]
    guild_object.features = guild["features"]
    guild_object.premium_progress_bar_enabled = guild["premium_progress_bar_enabled"]
    guild_object.nsfw_level = NSFWLevel(guild["nsfw_level"])
    guild_object.verification_level = VerificationLevel(guild["verification_level"])
    guild_object.splash = guild["splash"]
    guild_object.afk_timeout = guild["afk_timeout"]
    guild_object.icon = guild["icon"]
    guild_object.preferred_locale = guild["preferred_locale"]
    guild_object.explicit_content_filter = ExplicitContentFilter(guild["explicit_content_filter"])
    guild_object.default_message_notifications = DefaultMessageNotification(guild["default_message_notifications"])
    guild_object.name = guild["name"]
    guild_object.widget_enabled = guild["widget_enabled"]
    guild_object.description = guild["description"]
    guild_object.premium_subscription_count = guild["premium_subscription_count"]
    guild_object.mfa_level = MfaLevel(guild["mfa_level"])

    if guild["public_updates_channel_id"] is not None:
        guild_object.public_updates_channel = guild_object.get_channel(guild["public_updates_channel_id"])

    if guild["rules_channel_id"] is not None:
        guild_object.rules_channel = guild_object.get_channel(guild["rules_channel_id"])

    if guild["afk_channel_id"] is not None:
        guild_object.afk_channel = guild_object.get_channel(guild["afk_channel_id"])

    if "vanity_url" in guild and guild["vanity_url"] is not None:
        guild_object.vanity_url = guild["vanity_url"]

    if guild["icon"] is None:
        icon_url = CDN_URL + "/embed/avatars/%s.png" % (int(guild["id"]) % 5)
    else:
        icon_format = "gif" if guild["icon"][0:2] == "a_" else "png"
        icon_url = CDN_URL + "/icons/%s/%s.%s" % (guild["id"], guild["icon"], icon_format)

    guild_object.icon_url = icon_url

    return old_guild, guild_object

async def guild_delete(gateway: "Gateway", guild):
    guild = gateway.get_guild(guild["id"])

    if guild is None:
        return

    index = get_index(gateway.guilds, guild.id, key=lambda g: g.id)
    del gateway.guilds[index]

    return guild,

async def guild_ban_add(gateway: "Gateway", ban):
    guild = gateway.get_guild(ban["guild_id"])
    user = await gateway.get_user(ban["user"])

    return guild, user

async def guild_ban_remove(gateway: "Gateway", ban):
    guild = gateway.get_guild(ban["guild_id"])
    user = await gateway.get_user(ban["user"])

    return guild, user

async def guild_emojis_update(gateway: "Gateway", emojis):
    guild = gateway.get_guild(emojis["guild_id"])

    old_emojis = gateway.copy(guild.emojis)
    guild.emojis = [Emoji.from_raw(emoji) for emoji in emojis["emojis"]]

    return old_emojis, guild.emojis

async def guild_stickers_update(gateway: "Gateway", stickers):
    guild = gateway.get_guild(stickers["guild_id"])

    old_stickers = gateway.copy(guild.stickers)
    guild.stickers = [Sticker.from_raw(sticker) for sticker in stickers["stickers"]]

    return old_stickers, guild.stickers

async def guild_member_add(gateway: "Gateway", member):
    guild = gateway.get_guild(member["guild_id"])
    del member["guild_id"]

    member = await guild.get_member(member)

    return guild, member

async def guild_member_update(gateway: "Gateway", member):
    if not gateway.guilds: return

    guild = gateway.get_guild(member["guild_id"])

    if guild is None:
        return None, None, member

    old_member = gateway.copy(await guild.get_member(member["user"]["id"]))

    del member["guild_id"]

    user = User.from_raw(member["user"])
    del member["user"]

    user_index = get_index(gateway.users, user.id, key=lambda u: u.id)

    if user_index is None:
        gateway.users.append(user)
    else:
        gateway.users[user_index] = user

    member = Member.from_raw(guild, member, user)
    member_index = get_index(guild.members, member.user.id, key=lambda m: m.user.id)

    if member_index is None:
        guild.members.append(member)
    else:
        guild.members[member_index] = member

    return guild, old_member, member

async def guild_member_remove(gateway: "Gateway", user):
    guild = gateway.get_guild(user["guild_id"])

    user = await gateway.get_user(user["user"])

    index = get_index(guild.members, user.id, key=lambda m: m.user.id)

    if index is not None:
        del guild.members[index]

    return guild, user

async def guild_role_create(gateway: "Gateway", role):
    guild = gateway.get_guild(role["guild_id"])

    role = Role.from_raw(role["role"])
    guild.roles.append(role)

    return guild, role

async def guild_role_update(gateway: "Gateway", role):
    guild = gateway.get_guild(role["guild_id"])
    role = Role.from_raw(role["role"])

    index = get_index(guild.roles, role.id, key=lambda r: r.id)

    old_role = gateway.copy(guild.roles[index])
    guild.roles[index] = role

    return guild, old_role, role

async def guild_role_delete(gateway: "Gateway", role):
    guild = gateway.get_guild(role["guild_id"])

    role = guild.get_role(role["role_id"])

    index = get_index(guild.roles, role.id, key=lambda r: r.id)
    del guild.roles[index]

    return guild, role

async def interaction_create(gateway: "Gateway", interaction):
    return await Interaction.from_raw(gateway, interaction),

async def message_create(gateway: "Gateway", message):
    message = await Message.from_raw(gateway, message)

    gateway.messages.append(message)

    if len(gateway.messages) > gateway.messages_limit:
        del gateway.messages[0]

    return message,

async def message_update(gateway: "Gateway", message):
    index = get_index(gateway.messages, message["id"], key=lambda m: m.id)

    if index is None:
        return None, None

    old_message = gateway.messages[index]
    new_message = gateway.copy(old_message)

    if "content" in message:
        new_message.content = message["content"]
    if "edited_timestamp" in message:
        new_message.edited_timestamp = parse_time(message["edited_timestamp"])
    if "attachments" in message:
        new_message.attachments = [Attachment(**attachment) for attachment in message["attachments"]]
    if "embeds" in message:
        new_message.embeds = [Embed.from_raw(embed) for embed in message["embeds"]]
    if "components" in message:
        new_message.components = [MessageComponents.from_raw(component) for component in message["components"]]

    gateway.messages[index] = new_message

    return old_message, new_message

async def message_delete(gateway: "Gateway", message):
    index = get_index(gateway.messages, message["id"], key=lambda m: m.id)

    if index is None:
        return message["id"],

    message = gateway.messages[index]
    del gateway.messages[index]

    return message,

async def message_delete_bulk(gateway: "Gateway", message):
    messages = []

    for message_id in message["ids"]:
        index = get_index(gateway.messages, message_id, key=lambda m: m.id)

        if index is None:
            messages.append(message_id)
        else:
            messages.append(gateway.messages[index])

    return messages,

async def message_reaction_add(gateway: "Gateway", reaction):
    guild = gateway.get_guild(reaction["guild_id"])
    channel = guild.get_channel(reaction["channel_id"])
    user = await gateway.get_user(reaction["user_id"])

    if user is None:
        return

    emoji = Emoji.from_raw(reaction["emoji"])

    index = get_index(gateway.messages, reaction["message_id"], key=lambda m: m.id)

    if index is None:
        message = reaction["message_id"]
    else:
        message = gateway.messages[index]

    if "member" in reaction:
        member = await guild.get_member(reaction["member"])

        return guild, channel, member, message, emoji

    return guild, channel, user, message, emoji

async def message_reaction_remove(gateway: "Gateway", reaction):
    guild = gateway.get_guild(reaction["guild_id"])
    channel = guild.get_channel(reaction["channel_id"])
    user = await gateway.get_user(reaction["user_id"])

    if user is None:
        return

    emoji = Emoji.from_raw(reaction["emoji"])

    index = get_index(gateway.messages, reaction["message_id"], key=lambda m: m.id)

    if index is None:
        message = reaction["message_id"]
    else:
        message = gateway.messages[index]

    if "member" in reaction:
        member = await guild.get_member(reaction["member"])

        return guild, channel, member, message, emoji

    return guild, channel, user, message, emoji

async def message_reaction_remove_all(gateway: "Gateway", reaction):
    guild = gateway.get_guild(reaction["guild_id"])
    channel = guild.get_channel(reaction["channel_id"])

    index = get_index(gateway.messages, reaction["message_id"], key=lambda m: m.id)

    if index is None:
        message = reaction["message_id"]
    else:
        message = gateway.messages[index]

    return guild, channel, message

async def message_reaction_remove_emoji(gateway: "Gateway", reaction):
    guild = gateway.get_guild(reaction["guild_id"])
    channel = guild.get_channel(reaction["channel_id"])
    emoji = Emoji.from_raw(reaction["emoji"])

    index = get_index(gateway.messages, reaction["message_id"], key=lambda m: m.id)

    if index is None:
        message = reaction["message_id"]
    else:
        message = gateway.messages[index]

    return guild, channel, message, emoji

async def voice_state_update(gateway: "Gateway", voice_state):
    guild = None
    channel = None
    member = None

    if voice_state["channel_id"] is not None:
        guild = gateway.get_guild_by_channel_id(voice_state["channel_id"])
        channel = guild.get_channel(voice_state["channel_id"])

    if voice_state["guild_id"] is not None:
        guild = gateway.get_guild(voice_state["guild_id"])

    member = await guild.get_member(voice_state["user_id"])

    old_voice_state = gateway.copy(member.voice_state)

    _voice_state = VoiceState.from_raw(gateway, voice_state)
    _voice_state.guild = guild
    _voice_state.channel = channel
    member.voice_state = _voice_state

    return member, old_voice_state, _voice_state