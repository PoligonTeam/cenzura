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

import femcord
from femcord import commands
from femcord.types import Emoji
from korrumzthegame import Renderer
from typing import Union
import asyncio, random

class Games(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(description="https://korrumzthegame.wtf", usage="[name] [avatar-number_1-20]", aliases=["ktg"])
    async def korrumzthegame(self, ctx: commands.Context, username: Union[int, str] = None, avatar: int = None):
        if isinstance(username, int) and avatar is None:
            avatar = username
            username = None

        username = username or ctx.author.username
        avatar = avatar or random.randint(1, 20)

        if not 20 >= avatar >= 1:
            avatar = random.randint(1, 20)

        components = femcord.Components(
            femcord.Row(
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left up", emoji=Emoji("\N{NORTH WEST ARROW}")),
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="up", emoji=Emoji("\N{UPWARDS BLACK ARROW}")),
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right up", emoji=Emoji("\N{NORTH EAST ARROW}"))
            ),
            femcord.Row(
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left", emoji=Emoji("\N{LEFTWARDS BLACK ARROW}")),
                femcord.Button(style=femcord.ButtonStyles.DANGER, custom_id="close", emoji=Emoji("\N{BLACK SQUARE FOR STOP}")),
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right", emoji=Emoji("\N{BLACK RIGHTWARDS ARROW}"))
            ),
            femcord.Row(
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left down", emoji=Emoji("\N{SOUTH WEST ARROW}")),
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="down", emoji=Emoji("\N{DOWNWARDS BLACK ARROW}")),
                femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right down", emoji=Emoji("\N{SOUTH EAST ARROW}"))
            )
        )

        renderer = Renderer()
        renderer.start(username, avatar)

        await asyncio.sleep(0.5)

        renderer.update()

        embed = femcord.Embed(title="Pull requests:", color=self.bot.embed_color)
        embed.set_thumbnail(url=f"https://korrumzthegame.wtf/images/player{renderer.client.image_number}.png")
        embed.set_image(url=f"attachment://image.png")
        embed.set_footer(text="korrumzthegame.wtf")

        def update_embed():
            embed.description = "\n".join(f"{player.username if not renderer.client.username == player.username else '**' + player.username + '**'} {player.pull_requests}" for player in sorted(renderer.client.players + [renderer.client], reverse=True, key=lambda player: player.pull_requests))

        update_embed()

        message = await ctx.reply(embed=embed, components=components, files=[("image.png", renderer.get_image())])

        async def on_select(interaction):
            if interaction.data.custom_id == "close":
                await renderer.client.close()
                return await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, "Thank you for playing", embed=femcord.Embed(), components=femcord.Components(), files=[], other={"attachments": []})

            await renderer.client.move(interaction.data.custom_id)

            renderer.update()
            update_embed()

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, embed=embed, files=[("image.png", renderer.get_image())])

            await self.bot.wait_for("interaction_create", on_select, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60, on_timeout=on_timeout)

        async def on_timeout():
            await renderer.client.close()
            await message.edit("Session expired", embeds=[], components=[], files=[], other={"attachments": []})

        await self.bot.wait_for("interaction_create", on_select, lambda interaction: interaction.member.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id, timeout=60, on_timeout=on_timeout)

def setup(bot: commands.Bot) -> None:
    bot.load_cog(Games(bot))