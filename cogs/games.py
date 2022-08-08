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
from femcord import commands
from femcord.types import Emoji
from korrumzthegame import Renderer
from typing import Union
import random

class Games(commands.Cog):
    name = "Gry"

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.interactions = []
        self.sessions = {}

    # @commands.Listener
    # async def on_interaction_create(self, interaction):
    #     if ("korrumzthegame", interaction.member.user.id, interaction.channel.id, interaction.message.id) in self.interactions:
    #         _, renderer, embed = self.sessions[("korrumzthegame", interaction.member.user.id)]

    #         if interaction.data.custom_id == "close":
    #             await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, "Dziękujemy za gre", embed=lib.Embed(), components=lib.Components(), other={"attachments": []})
    #             del self.sessions[("korrumzthegame", interaction.member.user.id)]
    #             self.interactions.remove(("korrumzthegame", interaction.member.user.id, interaction.channel.id, interaction.message.id))
    #             await renderer.client.ws.close()
    #             await renderer.client.session.close()
    #             del renderer
    #             return

    #         await renderer.client.move(interaction.data.custom_id)

    #         renderer.update()

    #         embed.title = "Pull requesty:"
    #         embed.description = "\n".join(f"{player.username if not renderer.client.username == player.username else player.username + ' (ty)'} {player.pull_requests}" for player in sorted(renderer.client.players + [renderer.client], reverse=True, key=lambda player: player.pull_requests))
    #         embed.set_image(url=f"attachment://image.png")
    #         embed.set_thumbnail(url=f"https://korrumzthegame.wtf/images/player{renderer.client.image_number}.png")
    #         embed.set_footer(text="www.korrumzthegame.wtf")

    #         await interaction.callback(lib.InteractionCallbackTypes.UPDATE_MESSAGE, "", embed=embed, files=[("image.png", renderer.get_image())], other={"attachments": []})

    # @commands.command(description="https://korrumzthegame.wtf", usage="[nazwa] [numer_avataru_1-20]", aliases=["ktg"])
    # async def korrumzthegame(self, ctx: commands.Context, username: Union[int, str] = None, avatar: int = None):
    #     if ("korrumzthegame", ctx.author.id) in self.sessions:
    #         guild_id, channel_id, message_id = self.sessions[("korrumzthegame", ctx.author.id)][0]
    #         return await ctx.reply(f"Pierw musisz zamknąć poprzednią sesje (<https://discord.com/channels/{guild_id}/{channel_id}/{message_id}>)")

    #     if isinstance(username, int) and avatar is None:
    #         avatar = username
    #         username = None

    #     username = username or ctx.author.username
    #     avatar = avatar or random.randint(1, 20)

    #     if not 20 >= avatar >= 1:
    #         avatar = random.randint(1, 20)

    #     components = lib.Components(
    #         lib.Row(
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="left up", emoji=Emoji("\N{NORTH WEST ARROW}")),
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="up", emoji=Emoji("\N{UPWARDS BLACK ARROW}")),
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="right up", emoji=Emoji("\N{NORTH EAST ARROW}"))
    #         ),
    #         lib.Row(
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="left", emoji=Emoji("\N{LEFTWARDS BLACK ARROW}")),
    #             lib.Button(style=lib.ButtonStyles.DANGER, custom_id="close", emoji=Emoji("\N{BLACK SQUARE FOR STOP}")),
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="right", emoji=Emoji("\N{BLACK RIGHTWARDS ARROW}"))
    #         ),
    #         lib.Row(
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="left down", emoji=Emoji("\N{SOUTH WEST ARROW}")),
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="down", emoji=Emoji("\N{DOWNWARDS BLACK ARROW}")),
    #             lib.Button(style=lib.ButtonStyles.SECONDARY, custom_id="right down", emoji=Emoji("\N{SOUTH EAST ARROW}"))
    #         )
    #     )

    #     renderer = Renderer()
    #     renderer.start(username, avatar)

    #     message = await ctx.reply("Naciśnij w jakis przycisk aby zaktualizować graczy/bugi", components=components)
    #     self.interactions.append(("korrumzthegame", ctx.author.id, ctx.channel.id, message.id))
    #     self.sessions[("korrumzthegame", ctx.author.id)] = ((ctx.guild.id, ctx.channel.id, message.id), renderer, lib.Embed(color=self.bot.embed_color))

def setup(bot):
    bot.load_cog(Games(bot))