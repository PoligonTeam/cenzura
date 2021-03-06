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

from lib import types
from cenzurascript import Dict

CHARS = (("\u200b", ("0", "1", "2", "3")), ("\u200c", ("4", "5", "6", "7")), ("\u200d", ("8", "9", "A", "B")), ("\u200e", ("C", "D", "E", "F")))
SEPARATOR = "\u200f"

def encode_text(text):
    return "".join(CHARS[int(char, 16) // 4][0] * ((int(char, 16) % 4) + 1) + SEPARATOR for char in "%X" % int("".join(("0" * (7 - len(f"{ord(char):b}")) + f"{ord(char):b}" for char in text)), 2))

def decode_text(text):
    return [binary := f"{int(''.join([group[1] for group in CHARS if group[0] == chars[0]][0][int(len(chars) - 1)] for chars in text.split(SEPARATOR)[:-1]), 16):b}", "".join(chr(int(binary[i:i+7], 2)) for i in range(0, len(binary), 7))][1]

def replace_chars(text):
    to_replace = [("ą", "a"), ("ś", "s"), ("ó", "o"), ("ł", "l"), ("ę", "e"), ("ń", "n"), ("ź", "z"), ("ż", "z"), ("ć", "c")]

    for x, y in to_replace:
        text = text.replace(x, y)

    return text

def convert(**items):
    objects = {
        types.Guild: lambda guild: Dict(
            id = guild.id,
            name = guild.name,
            description = guild.description or False,
            icon_url = guild.icon_url or False,
            banner_url = guild.banner_url or False,
            owner = Dict(
                id = guild.owner.user.id,
                username = guild.owner.user.username,
                discriminator = guild.owner.user.discriminator,
                avatar_url = guild.owner.user.avatar_url or False,
                bot = guild.owner.user.bot
            ),
            members = len(guild.members),
            channels = len(guild.channels),
            roles = len(guild.roles),
            emojis = len(guild.emojis),
            stickers = len(guild.stickers)
        ),
        types.Channel: lambda channel: Dict(
            id = channel.id,
            name = channel.name,
            topic = channel.topic or False,
            nsfw = channel.nsfw,
            position = channel.position
        ),
        types.Role: lambda role: Dict(
            id = role.id,
            name = role.name,
            color = role.color,
            hoist = role.hoist,
            mentionable = role.mentionable,
            position = role.position
        ),
        types.User: lambda user: Dict(
            id = user.id,
            username = user.username,
            discriminator = user.discriminator,
            avatar_url = user.avatar_url,
            bot = user.bot or False
        )
    }

    converted = {}

    for key, value in items.items():
        if type(value) in objects:
            converted[key] = objects[type(value)](value)

    return converted

def get_int(user, user2 = None):
    user2 = user2 or user

    user_avatar = user.avatar
    user2_avatar = user2.avatar

    if user_avatar is None:
        user_avatar = "".join(chr(int(a)) for a in str(int(user.created_at.timestamp())))
    if user2_avatar is None:
        user2_avatar = "".join(chr(int(a)) for a in str(int(user2.created_at.timestamp())))

    return (int(user.id) + int(user2.id)) * sum(ord(a) + ord(b) for a, b in list(zip(user_avatar, user2_avatar))) % 10000 // 100

def table(names, rows):
    text = ""
    spaces = max([len(str(name)) for name in names] + [len(str(value)) for row in rows for value in row]) + 1

    text += "\n+" + ("-" * (spaces + 1) + "+") * len(names) + "\n"
    text += "|"

    for name in names:
        text += " " + name + " " * (spaces - len(name)) + "|"

    text += "\n+" + ("-" * (spaces + 1) + "+") * len(names) + "\n"

    for row in rows:
        text += "|"
        for value in row:
            text += " " + str(value) + " " * (spaces - len(str(value))) + "|"
        text += "\n"

    text += "+" + ("-" * (spaces + 1) + "+") * len(names) + "\n"

    return text