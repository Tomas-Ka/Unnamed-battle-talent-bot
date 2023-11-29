# -*- coding: UTF-8 -*-
from discord.ext import commands
from discord import app_commands
import discord
from db_handler import DBHandler

# ? global colour for the cog. Change this when we get around to a cohesive theme and whatnot.
global colour
colour = 0x2db83d

class StickyManager(commands.Cog):
    def __init__(self, bot: commands.Bot, sticky_channels: list) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db
        self.sticky_channels = sticky_channels
    
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # Don't resend if the message is from the bot:
        if msg.author.id == self.bot.user.id:
            return
        
        # Make sure we have a sticky in the current channel.
        sticky = self.db.get_sticky(msg.channel.id)
        if sticky:
            # Create and then send the sticky embed.
            sticky_embed = discord.Embed(title=sticky.title, description=sticky.description, colour=colour)
            sticky_embed.set_footer(text=f"Stickied by {self.bot.user.display_name}")
            new_sticky = await msg.channel.send(embed=sticky_embed)
            
            # Delete the old sticky message and update database
            await msg.channel.get_partial_message(sticky.message_id).delete()
            self.db.update_sticky(sticky.channel_id, new_sticky.id)

    
    @app_commands.command(description="Create a new sticky in this channel. Use \\n for newline")
    async def new_sticky(self, interaction: discord.Interaction, title: str, description: str) -> None:
        # TODO; add descriptions to the vars using @app_commands.describe() decorator
        if self.db.get_sticky(interaction.channel_id):
            await interaction.response.send_message("There is already a sticky in this channel")
            return
        sticky_embed = discord.Embed(title=title, description=description, colour=colour)
        sticky_embed.set_footer(text=f"Stickied by {self.bot.user.display_name}")
        new_sticky = await interaction.channel.send(embed=sticky_embed)
        self.db.create_sticky(interaction.channel_id, new_sticky.id, title, description)
        await interaction.response.send_message(f"Sticky created in channel {interaction.channel}", ephemeral=True)
    
    @app_commands.command()
    async def delete_sticky(self, interaction: discord.Interaction) -> None:
        # TODO; finish this function
        pass
    
    
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Mod_manager begin loading")
    await bot.add_cog(StickyManager(bot))