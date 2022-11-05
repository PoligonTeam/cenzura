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

import femcord
from femcord import types
from femscript import Dict, List
from aiohttp import ClientSession
from httpx import AsyncClient, Timeout
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from json.decoder import JSONDecodeError
from models import Artists, Guilds, LastFM, Lyrics
from tortoise.queryset import QuerySet
from config import LASTFM_API_URL, LASTFM_API_KEY
from lastfm import Track
import asyncio, random, re, config

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

async def update_lastfm_avatars():
    async def get_lastfm_avatar(lastfm_user: LastFM):
        async with ClientSession() as session:
            async with session.get(LASTFM_API_URL + f"?method=user.getinfo&user={user.username}&api_key={LASTFM_API_KEY}&format=json") as response:
                data = await response.json()

                if not "image" in data:
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

    async with ClientSession() as session:
        async with session.get("https://www.last.fm/music/" + artist) as response:
            if not response.status == 200:
                return "https://www.last.fm/static/images/marvin.05ccf89325af.png"

            await Artists.create(artist=artist, image=re.search(r"<meta property=\"og:image\"[ ]+content=\"([\w/:.]+)\" data-replaceable-head-tag>", await response.text()).group(1))

    return await get_artist_image(artist)

async def get_track_lyrics(artist, title: str, user_agent: str):
    lyrics_db = await Lyrics.filter(title__istartswith=title).first()

    if lyrics_db:
        return lyrics_db

    name = artist + " " + title

    lyrics = None

    async with ClientSession() as session:
        async with session.get(f"https://api.musixmatch.com/ws/1.1/track.search?q_track_artist={name}&page_size=1&page=1&s_track_rating=desc&s_artist_rating=desc&country=us&apikey={config.MUSIXMATCH}") as response:
            data = await response.json(content_type=None)

            track_list = data["message"]["body"]["track_list"]

            if track_list:
                track = track_list[0]["track"]

                artist_name = track["artist_name"]
                track_name = track["track_name"]
                track_share_url = track["track_share_url"]

                async with session.get(track_share_url, headers={"user-agent": user_agent}) as response:
                    content = await response.content.read()
                    soup = BeautifulSoup(content, features="lxml")

                    elements = soup.find_all("p", {"class": "mxm-lyrics__content"})

                    if elements:
                        source = "Musixmatch"
                        lyrics = "\n".join([element.get_text() for element in elements])

            if lyrics is None:
                async with session.get(f"https://api.genius.com/search?q={name}&access_token={config.GENIUS}") as response:
                    data = await response.json()

                    hits = data["response"]["hits"]

                    if hits:
                        track = hits[0]["result"]

                        artist_name = track["artist_names"]
                        track_name = track["title"]
                        track_share_url = track["url"]

                        async with session.get(track_share_url, headers={"user-agent": user_agent}) as response:
                            content = await response.content.read()
                            soup = BeautifulSoup(content, features="lxml")

                            element = soup.find("div", {"data-lyrics-container": True})

                            if element:
                                source = "Genius"
                                lyrics = element.get_text("\n")

            lyrics_db = await Lyrics.filter(title__icontains=track_name).first()

            if not lyrics_db:
                lyrics_db = Lyrics(artist=artist_name, title=track_name, source=source, lyrics=lyrics)
                await lyrics_db.save()

            return lyrics_db

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
        ),
        Track: lambda track: Dict(
            artist = Dict(
                name = track.artist.name,
                url = track.artist.url,
                image = List(
                    *(
                        Dict(
                            url = image.url,
                            size = image.size
                        ) for image in track.artist.image
                    )
                ),
                streamable = track.artist.streamable,
                ontour = track.artist.ontour,
                stats = Dict(
                    listeners = track.artist.stats.listeners,
                    playcount = track.artist.stats.playcount,
                    userplaycount = track.artist.stats.userplaycount
                ),
                similar = List(
                    *(
                        Dict(
                            name = similar.name,
                            url = similar.url,
                            image = List(
                                *(
                                    Dict(
                                        url = image.url,
                                        size = image.size
                                    ) for image in similar.image
                                )
                            )
                        ) for similar in track.artist.similar
                    )
                ),
                tags = List(
                    *(
                        Dict(
                            name = tag.name,
                            url = tag.url
                        )
                        for tag in track.artist.tags
                    )
                ),
                bio = Dict(
                    links = Dict(
                        name = track.artist.bio.links.name,
                        rel = track.artist.bio.links.rel,
                        url = track.artist.bio.links.url
                    ),
                    published = track.artist.bio.published,
                    summary = track.artist.bio.summary,
                    content = track.artist.bio.content
                )
            ),
            image = List(
                *(
                    Dict(
                        url = image.url,
                        size = image.size
                    ) for image in track.image
                )
            ),
            album = Dict(
                name = track.album.name,
                mbid = track.album.mbid
            ),
            title = track.title,
            url = track.url,
            date = Dict(
                uts = track.date.uts,
                text = track.date.text,
                date = track.date.date

            ) if track.date else False,
            listeners = track.listeners,
            playcount = track.playcount,
            scrobbles = track.scrobbles,
            tags = List(
                *(
                    Dict(
                        name = tag.name,
                        url = tag.url
                    )
                    for tag in track.tags
                )
            )
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

async def request(method, url, *, headers = None, data = None, proxy = None):
    proxy_address = random.choice(list(config.PROXIES.values()))

    if proxy and proxy in config.PROXIES:
        proxy_address = config.PROXIES[proxy]

    proxy = config.PROXY_TEMPLATE.format(proxy_address)

    proxies = {
        "https://": proxy,
        "http://": proxy
    }

    async with AsyncClient(proxies=proxies, timeout=Timeout(60)) as session:
        response = await session.request(method, url, headers=headers, json=data)

        try:
            json = response.json()
        except JSONDecodeError:
            json = {}

        if isinstance(json, dict):
            json = Dict(**json)
        elif isinstance(json, list):
            json = List(*json)

        return {
            "status": response.status_code,
            "text": response.text,
            "json": json
        }

async def execute_webhook(webhook_id, webhook_token, *, username = None, avatar_url = None, content = None, embed: femcord.Embed = None):
    data = {}

    if username:
        data["username"] = username
    if avatar_url:
        data["avatar_url"] = avatar_url
    if content:
        data["content"] = content
    if embed:
        data["embeds"] = [embed.__dict__]

    await request("POST", femcord.http.Http.URL + "/webhooks/" + webhook_id + "/" + webhook_token, data=data)

def void(*args, **kwargs):
    return False

modules = {
    "requests": {
        "builtins": {
            "request": request,
            "get": lambda *args, **kwargs: request("GET", *args, **kwargs),
            "post": lambda *args, **kwargs: request("POST", *args, **kwargs),
            "patch": lambda *args, **kwargs: request("PATCH", *args, **kwargs),
            "put": lambda *args, **kwargs: request("PUT", *args, **kwargs),
            "delete": lambda *args, **kwargs: request("DELETE", *args, **kwargs)
        }
    }
}
builtins = {
    "Embed": femcord.Embed,
    "execute_webhook": execute_webhook,
    "table": table
}

async def get_modules(bot, guild, *, ctx = None, user = None, message_errors = False):
    query = Guilds.filter(guild_id=guild.id)
    db_guild = await query.first()

    database = db_guild.database

    async def db_update(key, value):
        database[key] = value
        await query.update(database=database)
        return value

    async def db_delete(key):
        database.pop(key)
        await query.update(database=database)

    async def lastfm():
        nonlocal user

        user = user or ctx.author
        lastfm = await LastFM.filter(user_id=user.id).first()

        if lastfm is None:
            if message_errors is True:
                if ctx.author is user:
                    await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

                await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

            return {}

        async with ClientSession() as session:
            async with session.get(LASTFM_API_URL + f"?method=user.getRecentTracks&user={lastfm.username}&limit=2&extended=1&api_key={LASTFM_API_KEY}&format=json") as response:
                if not response.status == 200:
                    return await ctx.reply("Takie konto LastFM nie istnieje")

                data = await response.json()
                data = data["recenttracks"]
                tracks = data["track"]
                lastfm_user = data["@attr"]

                fs_data = {
                    "tracks": [],
                    "lastfm_user": {
                        "username": lastfm_user["user"],
                        "scrobbles": lastfm_user["total"],
                    },
                    "nowplaying": False
                }

                if not tracks:
                    return await ctx.reply("Nie ma żadnych utworów")

                if len(tracks) == 3:
                    fs_data["nowplaying"] = True

                async def append_track(index, track):
                    async with session.get(LASTFM_API_URL + f"?method=track.getInfo&user={lastfm.username}&artist={quote_plus(track['artist']['name'])}&track={quote_plus(track['name'])}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()
                        track_info = data["track"]
                        del track_info["artist"]

                    async with session.get(LASTFM_API_URL + f"?method=artist.getInfo&user={lastfm.username}&artist={quote_plus(track['artist']['name'])}&api_key={LASTFM_API_KEY}&format=json") as response:
                        data = await response.json()
                        artist_info = data["artist"]

                    cs_track = Track.from_raw({
                        "artist": artist_info,
                        "image": track["image"],
                        "album": track["album"],
                        "title": track["name"],
                        "url": track["url"],
                        "listeners": track_info["listeners"],
                        "playcount": track_info["playcount"],
                        "scrobbles": track_info["userplaycount"],
                        "tags": track_info["toptags"]["tag"],
                        **(
                            {
                                "date": track["date"]
                            }
                            if "date" in track else
                            {

                            }
                        )
                    })

                    fs_data["tracks"].append((index, cs_track))

                for index, track in enumerate(tracks):
                    bot.loop.create_task(append_track(index, track))

                while len(fs_data["tracks"]) < 2:
                    await asyncio.sleep(0.1)

                fs_data["tracks"].sort(key=lambda track: track[0])
                fs_data["tracks"] = [track[1] for track in fs_data["tracks"]]

                return fs_data

    return {
        **modules,
        "database": {
            "builtins": {
                "get_all": lambda: Dict(**database),
                "get": lambda key: database.get(key, False),
                "update": db_update,
                "delete": db_delete
            },
            "variables": database
        },
        "lastfm": {
            "variables": {
                **convert(tracks=(lfm := await lastfm()).get("tracks", [])),
                "lastfm_user": lfm.get("lastfm_user"),
                "nowplaying": lfm.get("nowplaying")
            }
        }
        if ctx is not None else {
            "variables": {}
        }
    }