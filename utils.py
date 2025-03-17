"""
Copyright 2022-2025 PoligonTeam

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

from femcord.femcord import types
from femcord.femcord.enums import ChannelTypes
from femscript import Femscript, generate_tokens, parse_equation, FemscriptException, Token
from aiohttp import ClientSession, ClientTimeout, ClientHttpProxyError
from models import Artists, LastFM, Lyrics
from config import LASTFM_API_URL, LASTFM_API_KEY
from lastfm import Client, Track, exceptions
from lyrics import GeniusClient, MusixmatchClient, TrackNotFound, LyricsNotFound, Lyrics as LyricsTrack

import asyncio
import config
import random
import json
import re
import operator

from typing import Optional

class fg:
    black = "\u001b[30m"
    red = "\u001b[31m"
    green = "\u001b[32m"
    yellow = "\u001b[33m"
    blue = "\u001b[34m"
    magenta = "\u001b[35m"
    cyan = "\u001b[36m"
    white = "\u001b[37m"
    reset = "\u001b[0m"

class bg:
    black = "\u001b[40m"
    red = "\u001b[41m"
    green = "\u001b[42m"
    yellow = "\u001b[43m"
    blue = "\u001b[44m"
    magenta = "\u001b[45m"
    cyan = "\u001b[46m"
    white = "\u001b[47m"
    reset = "\u001b[0m"

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

def get_random_username():
    gender = random.randint(0, 1)

    with open("assets/words%d.txt" % gender, "r") as f:
        word = random.choice(f.read().splitlines())

    with open("assets/names%d.txt" % gender, "r") as f:
        name = random.choice(f.read().splitlines()).replace(" ", "_").lower()

    return f"{word}_{name}{random.randint(1, 100)}"

async def update_lastfm_avatars():
    async def get_lastfm_avatar(lastfm_user: LastFM):
        async with ClientSession() as session:
            async with session.get(LASTFM_API_URL + f"?method=user.getinfo&user={user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                data = await response.json()

                if "image" not in data:
                    return

                elif data["image"][-1] == lastfm_user.avatar:
                    return

                await LastFM.filter(id=lastfm_user.id).update(avatar=data["image"][-1])

    users = LastFM.all()

    for user in await users:
        asyncio.create_task(get_lastfm_avatar(user))

async def get_artist_image(artist: str):
    artist_db = await Artists.filter(artist=artist).first()

    if artist_db:
        return artist_db.image

    async with Client() as client:
        try:
            image = await client.artist_image(artist)
        except exceptions.NotFound:
            return "https://www.last.fm/static/images/marvin.05ccf89325af.png"

        await Artists.create(artist=artist, image=image)

    return await get_artist_image(artist)

async def get_track_lyrics(artist: str, title: str, session: ClientSession):
    lyrics_db = await Lyrics.get_or_none(title__icontains=title)

    if lyrics_db is None:
        name = artist + " " + title
        track = LyricsTrack(artist, title)

        async with MusixmatchClient(config.MUSIXMATCH, session) as musixmatch:
            try:
                track = await musixmatch.get_lyrics(name)
                source = "Musixmatch"
            except (TrackNotFound, LyricsNotFound):
                pass

            if track.lyrics is None:
                async with GeniusClient(config.GENIUS, session) as genius:
                    try:
                        track = await genius.get_lyrics(name)
                        source = "Genius"
                    except (TrackNotFound, LyricsNotFound):
                        return None

            lyrics_db = await Lyrics.get_or_none(title__icontains=track.title)

            if lyrics_db is None:
                lyrics_db = Lyrics(artist=track.artist, title=track.title, source=source, lyrics=track.lyrics)
                await lyrics_db.save()

    return lyrics_db

def convert(**items):
    objects = {
        types.Guild: lambda guild: dict(
            id = guild.id,
            name = guild.name,
            description = guild.description,
            icon_url = guild.icon_url,
            banner_url = guild.banner_url,
            owner = dict(
                id = guild.owner.user.id,
                username = guild.owner.user.username,
                avatar_url = guild.owner.user.avatar_url,
                bot = guild.owner.user.bot
            ),
            members = len(guild.members),
            channels = [channel_convert(channel) for channel in guild.channels],
            roles = [role_convert(role) for role in guild.roles],
            emojis = [emoji_convert(emoji) for emoji in guild.emojis],
            stickers = [sticker_convert(sticker) for sticker in guild.stickers]
        ),
        types.User: lambda user: dict(
            id = user.id,
            username = user.username,
            avatar_url = user.avatar_url,
            bot = user.bot
        ),
        types.Channel: (channel_convert := lambda channel: dict(
            type = channel.type.name if channel.type else ChannelTypes.DM.name,
            id = channel.id,
            name = channel.name,
            topic = channel.topic,
            nsfw = channel.nsfw,
            position = channel.position
        )),
        types.Role: (role_convert := lambda role: dict(
            id = role.id,
            name = role.name,
            color = role.color,
            hoist = role.hoist,
            mentionable = role.mentionable,
            position = role.position
        )),
        types.Emoji: (emoji_convert := lambda emoji: dict(
            id = emoji.id,
            name = emoji.name,
            animated = emoji.animated,
            url = emoji.url
        )),
        types.Sticker: (sticker_convert := lambda sticker: dict(
            id = sticker.id,
            name = sticker.name,
            type = sticker.type.name,
            format_type = sticker.format_type.name,
            url = sticker.url
        )),
        Track: lambda track: dict(
            artist = dict(
                name = track.artist.name,
                url = track.artist.url,
                image = [
                    dict(
                        url = image.url,
                        size = image.size
                    ) for image in track.artist.image
                ],
                streamable = track.artist.streamable,
                on_tour = track.artist.on_tour,
                stats = dict(
                    listeners = track.artist.stats.listeners,
                    playcount = track.artist.stats.playcount,
                    userplaycount = track.artist.stats.userplaycount
                ),
                similar = [
                    dict(
                        name = similar.name,
                        url = similar.url,
                        image = [
                            dict(
                                url = image.url,
                                size = image.size
                            ) for image in similar.image
                        ]
                    ) for similar in track.artist.similar
                ],
                tags = [
                    dict(
                        name = tag.name,
                        url = tag.url
                    ) for tag in track.artist.tags
                ],
                bio = dict(
                    links = dict(
                        name = track.artist.bio.links.name,
                        rel = track.artist.bio.links.rel,
                        url = track.artist.bio.links.url
                    ),
                    published = track.artist.bio.published,
                    summary = track.artist.bio.summary,
                    content = track.artist.bio.content
                )
            ),
            image = [
                dict(
                    url = image.url,
                    size = image.size
                ) for image in track.image
            ] if track.image else [],
            album = dict(
                name = track.album.name,
                mbid = track.album.mbid,
                image = [
                    dict(
                        url = image.url,
                        size = image.size
                    ) for image in track.image
                ] if track.image else [],
                position = track.album.position
            ) if track.album else None,
            title = track.title,
            url = track.url,
            date = dict(
                uts = track.date.uts,
                text = track.date.text,
                date = track.date.date
            ) if track.date else None,
            listeners = track.listeners,
            playcount = track.playcount,
            scrobbles = track.scrobbles or "0",
            tags = [
                dict(
                    name = tag.name,
                    url = tag.url
                ) for tag in track.tags
            ],
            streamable = track.streamable,
            duration = track.duration,
            mbid = track.mbid,
            loved = track.loved,
            userloved = track.userloved
        )
    }

    converted = {}

    for key, value in items.items():
        if (_type := type(value)) in objects:
            converted[key] = objects[type(value)](value)
        elif _type is list:
            converted[key] = [objects[type(item)](item) for item in value]

    return converted

def get_int(user, user2 = None):
    user2 = user2 or user

    user_avatar = user.avatar
    user2_avatar = user2.avatar

    if user_avatar is None:
        user_avatar = "".join(chr(int(char)) for char in str(int(user.created_at.timestamp())))
    if user2_avatar is None:
        user2_avatar = "".join(chr(int(char)) for char in str(int(user2.created_at.timestamp())))

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

async def request(method: str, url: str, *, headers: Optional[dict] = None, cookies: Optional[dict] = None, data: Optional[dict] = None):
    async with ClientSession(timeout=ClientTimeout(10)) as session:
        try:
            async with session.request(method, url, headers={"User-Agent": "femscript/1.0"} | (headers or {}), cookies=cookies, json=data, proxy=config.PROXY) as response:
                length = response.content_length

                if length is not None and length > 10 * 1024 * 1024:
                    return {
                        "status": -1,
                        "text": "Content too large",
                        "json": {}
                    }

                content = await response.read()

                data = {}

                if response.content_type == "application/json":
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        data = {}

                return {
                    "status": response.status,
                    "text": content.decode(response.get_encoding()),
                    "json": data
                }
        except ClientHttpProxyError as exc:
            raise FemscriptException(f"ClientHttpProxyError: {exc.status}")

token_specification = [
    ("COMMENT",     r"#.*"),
    ("STRING",      r"\"(?:\\.|[^\\\"])*\""),
    ("NUMBER",      r"\b\d+(\.\d*)?\b"),
    ("BOOL",        r"\b(true|false)\b"),
    ("NONE",        r"\b(none)\b"),
    ("KEYWORD",     r"\b(fn|import|return|if|else|and|or|borrow)\b"),
    ("FUNCTION",    r"\b[_a-zA-Z][\w]*(?:\.[_a-zA-Z][\w]*)*\b(?=\s*(\(|\{))"),
    ("IDENTIFIER",  r"\b[_a-zA-Z][\w]*\b"),
    ("OPERATOR",    r"[%=+*/-]"),
    ("BRACKET",     r"[{}()\[\]]"),
    ("PUNCTUATION", r"[!.,&:;]"),
    ("NEWLINE",     r"\n"),
    ("SKIP",        r"[ \t]+")
]

get_token = re.compile("|".join(f"(?P<{kind}>{value})" for kind, value in token_specification)).match

colors = {
    "COMMENT": fg.green,
    "STRING": fg.cyan,
    "NUMBER": fg.red,
    "BOOL": fg.yellow,
    "FUNCTION": fg.blue,
    "IDENTIFIER": fg.white,
    "OPERATOR": fg.yellow,
    "KEYWORD": fg.magenta,
    "BRACKET": fg.cyan,
    "PUNCTUATION": fg.white
}

def highlight(code: str) -> str:
    tokens = []
    mo = get_token(code)

    while mo is not None:
        kind = mo.lastgroup
        value = mo.group(kind)
        if kind == "STRING":
            value = value.replace("\n", "\\n")
        tokens.append((kind, value))
        mo = get_token(code, mo.end())

    highlighted_code = ""

    for kind, value in tokens:
        if kind in colors:
            highlighted_code += colors[kind] + value + fg.reset
        else:
            highlighted_code += value

    return highlighted_code

def run_equation(tokens: list[Token]) -> float:
    tokens = parse_equation(tokens)

    stack = []

    operators = {
        "Plus": operator.add,
        "Minus": operator.sub,
        "Multiply": operator.mul,
        "Divide": operator.truediv,
        "Modulo": operator.mod
    }

    for token in tokens:
        if token["type"] == "Int":
            stack.append(token["number"])
        elif token["type"] in operators:
            stack.append(operators[token["type"]](stack.pop(-2), stack.pop()))
        else:
            stack.append(token)

    return stack[0]