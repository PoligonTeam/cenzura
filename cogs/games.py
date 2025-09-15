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

import femcord.femcord as femcord
from femcord.femcord import commands
from femcord.femcord.types import Emoji
from korrumzthegame import Renderer
from concurrent.futures import ThreadPoolExecutor
import asyncio
import random

from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot, Context, AppContext

class Games(commands.Cog):
    def __init__(self, bot: "Bot") -> None:
        self.bot = bot

    @commands.hybrid_command(description="https://korrumzthegame.wtf", usage="[name] [avatar-number_1-20]", aliases=["ktg"])
    async def korrumzthegame(self, ctx: Union["Context", "AppContext"], username: int | str = None, avatar: int = None) -> None:
        if isinstance(username, int) and avatar is None:
            avatar = username
            username = None

        username = username or ctx.author.username
        avatar = avatar or random.randint(1, 20)

        if not 20 >= avatar >= 1:
            avatar = random.randint(1, 20)

        components = femcord.Components(
            components = [
                femcord.ActionRow(
                    components = [
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left up", emoji=Emoji(ctx.bot, "\N{NORTH WEST ARROW}")),
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="up", emoji=Emoji(ctx.bot, "\N{UPWARDS BLACK ARROW}")),
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right up", emoji=Emoji(ctx.bot, "\N{NORTH EAST ARROW}"))
                    ]
                ),
                femcord.ActionRow(
                    components = [
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left", emoji=Emoji(ctx.bot, "\N{LEFTWARDS BLACK ARROW}")),
                        femcord.Button(style=femcord.ButtonStyles.DANGER, custom_id="close", emoji=Emoji(ctx.bot, "\N{BLACK SQUARE FOR STOP}")),
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right", emoji=Emoji(ctx.bot, "\N{BLACK RIGHTWARDS ARROW}"))
                    ]
                ),
                femcord.ActionRow(
                    components = [
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="left down", emoji=Emoji(ctx.bot, "\N{SOUTH WEST ARROW}")),
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="down", emoji=Emoji(ctx.bot, "\N{DOWNWARDS BLACK ARROW}")),
                        femcord.Button(style=femcord.ButtonStyles.SECONDARY, custom_id="right down", emoji=Emoji(ctx.bot, "\N{SOUTH EAST ARROW}"))
                    ]
                )
            ]
        )

        renderer = Renderer()
        renderer.start(username, avatar)

        await asyncio.sleep(0.5)

        async def async_render():
            await self.bot.loop.run_in_executor(ThreadPoolExecutor(), renderer.update)

        await self.bot.loop.create_task(async_render())

        embed = femcord.Embed(title="Pull requests:", color=self.bot.embed_color)
        embed.set_thumbnail(url=f"https://korrumzthegame.wtf/images/player{renderer.client.image_number}.png")
        embed.set_image(url="attachment://image.png")
        embed.set_footer(text="ktg.poligon.lgbt")

        is_app = isinstance(ctx, commands.AppContext)

        if is_app:
            await ctx.think()

        def update_embed():
            embed.set_description("\n".join(f"{player.username if not renderer.client.username == player.username else '**' + player.username + '**'} {player.pull_requests}" for player in sorted(renderer.client.players + [renderer.client], reverse=True, key=lambda player: player.pull_requests)))

        update_embed()

        message = await ctx.reply(embed=embed, components=components, files=[("image.png", renderer.get_image())])

        obj: commands.AppContext | femcord.types.Message = ctx if is_app else message

        def check(interaction: femcord.types.Interaction, _: Optional[femcord.types.Message] = None) -> bool:
            if is_app:
                return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message is not None and interaction.message.interaction_metadata.id == ctx.interaction.id
            return interaction.user.id == ctx.author.id and interaction.channel.id == ctx.channel.id and interaction.message.id == message.id

        while True:
            try:
                interaction, = await self.bot.wait_for("interaction_create", check, timeout=60)
            except TimeoutError:
                await renderer.client.close()
                await obj.edit("Session expired", embeds=[], components=[], files=[], other={"attachments": []})
                return

            if interaction.data.custom_id == "close":
                await renderer.client.close()
                return await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, "Thank you for playing", embed=femcord.Embed(), components=[], files=[], other={"attachments": []})

            await renderer.client.move(interaction.data.custom_id)

            renderer.update()
            update_embed()

            await interaction.callback(femcord.InteractionCallbackTypes.UPDATE_MESSAGE, embed=embed, files=[("image.png", renderer.get_image())])

def setup(bot: "Bot") -> None:
    bot.load_cog(Games(bot))