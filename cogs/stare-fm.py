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

import lib
from lib import commands, types
from bs4 import BeautifulSoup
from datetime import datetime
from config import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL
import urllib, urllib.parse, hashlib, asyncio

def paginator(content, limit = 4096):
    for x in range(0, len(content), limit):
        yield content[x:x+limit]

def sign(method, token):
    return hashlib.md5(("api_token%smethod%stoken%s%s" % (LASTFM_API_KEY, method, token, LASTFM_API_SECRET)).encode("utf-8")).hexdigest()

class Fm(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Łączenie konta LastFM do bota")
    async def login(self, ctx):
        resp = await self.bot.http.session.get(LASTFM_API_URL + f"?method=auth.gettoken&api_key={LASTFM_API_KEY}&format=json")
        data = await resp.json()

        try:
            msg = await ctx.author.send(f"Aby połączyć konto LastFM z botem musisz wejść w poniższy link\nhttps://www.last.fm/api/auth?api_key={LASTFM_API_KEY}&token={data['token']}")
        except lib.HTTPException:
            return await ctx.reply("Bot nie może wysłać ci wiadomości prywatnej")

        await ctx.reply("Wiadomość z linkiem została wysłana w wiadomości prywatnej")

        signature = sign("auth.getSession", data["token"])

        for attempt in range(9):
            await asyncio.sleep(20)

            resp = await self.bot.http.session.get(LASTFM_API_URL + f"?method=auth.getSession&token={data['token']}&api_key={LASTFM_API_KEY}&api_sig={signature}&format=json")

            if not resp.status == 200:
                if attempt == 8:
                    return await msg.edit("Logowanie się nie powiodło... link się przedawnił lub coś poszło nie tak")

                continue

            data = (await resp.json())["session"]

            await self.bot.psql.execute("INSERT INTO lastfm (user_id, username, token) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET username = $2, token = $3 WHERE user_id = $1", ctx.author.id, data["name"], data["key"])
            return await msg.edit("Pomyślnie połączono konto " + data["name"])

    @commands.command(description="Statystyki konta LastFM", usage="[użytkownik]")
    async def fmstats(self, ctx, user: types.User = None):
        user = user or ctx.author

        query = await self.bot.psql.fetch(f"SELECT * FROM lastfm WHERE user_id = '{user.id}'")

        if not query:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        resp = await self.bot.http.session.get(LASTFM_API_URL + f"?method=user.getinfo&user={query[0][1]}&limit=1&api_key={LASTFM_API_KEY}&format=json")

        if not resp.status == 200:
            return await ctx.reply("Takie konto LastFM nie istnieje")

        resp = await resp.json()
        user_info = resp["user"]

        embed = lib.Embed(title=f"Informacje o {user.username}:", color=self.bot.embed_color)
        embed.set_thumbnail(url=user_info["image"][3]["#text"])
        embed.add_field(name="Nick:", value=user_info["name"], inline=True)
        embed.add_field(name="Scrobbles:", value=user_info["playcount"], inline=True)
        embed.add_field(name="Data Utworzenia Konta:", value="<t:" + user_info["registered"]["unixtime"] + ">")

        await ctx.reply(embed=embed)

    @commands.command(description="Wybieranie trybu komendy fm", usage="(tryb)", other={"embed": lib.Embed(description="Tryby: `embedfull`, `embedmini`, `textfull`, `textmini`")})
    async def mode(self, ctx, mode: lambda arg: arg if arg in "embedfull embedmini textfull textmini".split() else None):
        query = await self.bot.psql.fetch(f"SELECT * FROM lastfm WHERE user_id = '{ctx.author.id}'")

        if not query:
            return await ctx.reply("Nie masz połączonego konta LastFM, użyj link aby je połączyć")

        await self.bot.psql.execute(f"UPDATE lastfm SET mode = $1 WHERE user_id = '{ctx.author.id}'", mode)

        await ctx.reply("Ustawiono tryb na `" + mode + "`")

    @commands.command(description="Ostatnie utwory", usage="[użytkownik]")
    async def fm(self, ctx, user: types.User = None):
        user = user or ctx.author

        query = await self.bot.psql.fetch(f"SELECT * FROM lastfm WHERE user_id = '{user.id}'")

        if not query:
            if ctx.author is user:
                return await ctx.reply("Nie masz połączonego konta LastFM, użyj `login` aby je połączyć")

            return await ctx.reply("Ta osoba nie ma połączonego konta LastFM")

        resp = await self.bot.http.session.get(LASTFM_API_URL + f"?method=user.getrecenttracks&user={query[0][1]}&limit={2 if query[0][3] in ('embedfull', 'textfull') else 1}&api_key={LASTFM_API_KEY}&format=json")

        resp = await resp.json()

        track_info = resp["recenttracks"]["track"]

        if "@attr" in track_info[0]:
            track_info = resp["recenttracks"]["track"][:-1]

        user_info = resp["recenttracks"]["@attr"]

        if query[0][3] in ("textfull", "textmini"):
            text = ""

            for track in track_info:
                if track_info.index(track) == 0:
                    text += f"**Obecny:**\n{track['name']}\n**{track['artist']['#text']}** | {track['album']['#text']}"
                else:
                    text += f"\n\n**Poprzedni:**\n{track['name']}\n**{track['artist']['#text']}** | {track['album']['#text']}"

            if not "@attr" in track_info[0]:
                text += f"\n`{user_info['user']} posiada {user_info['total']} scrobbli | Ostatni scrobble: " + datetime.utcfromtimestamp(int(track_info[0]["date"]["uts"])).strftime("%H:%M:%S %d/%M/%Y`")

                return await ctx.reply(text)

            text += f"\n`{user_info['user']} posiada {user_info['total']} scrobbli`"

            return await ctx.reply(text)

        embed = lib.Embed(title=f"Ostatnie utwory {user.username}:", color=self.bot.embed_color)
        embed.set_thumbnail(url=track_info[0]["image"][3]["#text"])
        footer_text = f"{user_info['user']} posiada {user_info['total']} scrobbli"

        if not "@attr" in track_info[0]:
            footer_text += " | Ostatni scrobble"
            embed.timestamp = datetime.fromtimestamp(int(track_info[0]["date"]["uts"])).isoformat()

        for track in track_info:
            if track_info.index(track) == 0:
                embed.add_field(name="Obecny:", value=f"[{track['name']}]({track['url']})\n**{track['artist']['#text']}** | {track['album']['#text']}")
            else:
                embed.add_field(name="Poprzedni:", value=f"[{track['name']}]({track['url']})\n**{track['artist']['#text']}** | {track['album']['#text']}")

        embed.set_footer(text=footer_text)
        await ctx.reply(embed=embed)

    # @commands.command(description="Pokazuje osoby które znają obecną piosenkę")
    # async def whoknows(self, ctx):

    #     check = await self.bot.psql.fetch(f"SELECT * FROM lastfm WHERE id = '{ctx.author.id}'")

    #     if not check:
    #         return await ctx.reply("Nie masz połączonego konta LastFM, użyj login aby je połączyć")

    #     resp = await self.bot.http.session.get(f"{LASTFM_API_URL}?method=user.getrecenttracks&user={check[0][1]}&limit={1}&api_key={LASTFM_API_KEY}&format=json")

    #     if not resp.status == 200:
    #         return await ctx.reply("Błąd: Spróbuj ponownie")

    #     resp = await resp.json()

    #     track_info = resp["recenttracks"]["track"]

    #     if "@attr" in track_info[0]:
    #         track_info = resp["recenttracks"]["track"][:-1]

    #     fmusers = await self.bot.psql.fetch(F"SELECT id, username FROM lastfm")
    #     wk = []

    #     for fmuser in fmusers:
    #         try:
    #             user = await ctx.guild.get_member(fmuser[0])

    #             if user:
    #                 wkresp = await self.bot.http.session.get(f"{LASTFM_API_URL}?method=artist.getInfo&api_key={LASTFM_API_KEY}&artist={track_info[0]['artist']['#text']}&username={fmuser[1]}&format=json")
    #                 wkresp = (await wkresp.json())["artist"]
    #                 wk.append((int(wkresp["stats"]["userplaycount"]), fmuser[1], user.nick or user.user.username))
    #         except:
    #             pass

    #     wk.sort(key=lambda tup: tup[0], reverse=True)

    #     description = ""

    #     for index, fmuser in enumerate(wk, 1):
    #         description += f"{index}. [{fmuser[2]}](https://lastfm.com/user/{fmuser[1]}) - {fmuser[0]} Odtworzenia\n"

    #     embed = lib.Embed(title=f"{track_info[0]['artist']['#text']} w {ctx.guild.name}", description=description, color=self.bot.embed_color)
    #     embed.set_thumbnail(url=wkresp["image"][2]["#text"])

    #     await ctx.send(embed=embed)


    @commands.command(description="Pokazuje tekst piosenki", usage="(nazwa)")
    async def lyrics(self, ctx, *, name = None):
        index = lib.utils.get_index(ctx.member.presence.activities, "Spotify", key=lambda activity: activity.name)

        if not index or not name:
            return await ctx.reply("Nie podałeś nazwy")

        activity = ctx.member.presence.activities[index]

        if activity and not name:
            name = activity.details + " " + activity.state

        start_index = None
        end_index = None

        for index, char in enumerate(name):
            if char in "([":
                start_index = index
            elif char in "])":
                end_index = index

        if (start_index, end_index) != (None, None):
            name = name[0:start_index] + name[end_index+1:]

        word_blacklist = ("█▬█ █ ▀█▀", "HD", "4K", "HIT", "4k", "hd", "-", "oficjalne video", "\"", "-")

        for word in word_blacklist:
            name = name.replace(word, "")

        resp = (await (await self.bot.http.session.get(f"https://api.musixmatch.com/ws/1.1/track.search?q_track_artist={urllib.parse.quote_plus(name)}&page_size=1&page=1&s_track_rating=desc&s_artist_rating=desc&country=us&f_has_lyrics=true&apikey=a9122ae7335ae3e46fc7d983ba150c05", headers={"User-Agent": self.bot.user_agent})).json(content_type=None))["message"]["body"]["track_list"]

        if not resp:
            return await ctx.send("Nie znaleziono piosenki")

        resp = resp[0]

        lyrics = await (await self.bot.http.session.get(resp["track"]["track_share_url"], headers={"User-Agent": self.bot.user_agent})).content.read()

        soup = BeautifulSoup(lyrics, features="lxml")

        img = soup.find_all("img")[1]

        lyric = soup.find_all("p", {"class": "mxm-lyrics__content"})
        lyric = "\n".join([x.get_text() for x in lyric])

        embeds = [lib.Embed(description=content, color=self.bot.embed_color) for content in paginator(lyric)]

        if not embeds:
            return await ctx.send("Nie znaleziono piosenki")

        embeds[0].title = f"Wyniki dla: {name}"
        embeds[0].set_thumbnail(url=f"https:{img['src']}")
        embeds[-1].set_footer(text=f"{resp['track']['track_name']} | {resp['track']['artist_name']}")

        await ctx.reply(embed=embeds[0])

        for embed in embeds[1:]:
            await ctx.send(embed=embed)

def setup(bot):
    pass
    # bot.load_cog(Fm(bot))