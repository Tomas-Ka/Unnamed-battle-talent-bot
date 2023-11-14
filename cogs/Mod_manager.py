# -*- coding: UTF-8 -*-
from discord.ext import commands
from discord import app_commands
import discord

# TODO; WRITE DOCUMENTATION
# I'm just too tired rn :P

class Mod_manager(commands.Cog):
    bot: commands.Bot

    def __init__(self, bot):
        self.bot = bot
        self.moderators = {}
        self.ctx_register_moderator = app_commands.ContextMenu(
            name="Register moderator", callback=self.register_moderator)
        self.ctx_deregister_moderator = app_commands.ContextMenu(
            name="De-register moderator", callback=self.deregister_moderator)
        self.ctx_get_moderator = app_commands.ContextMenu(
            name = "Get moderator stats", callback = self.get_moderator)

        self.bot.tree.add_command(self.ctx_register_moderator)
        self.bot.tree.add_command(self.ctx_deregister_moderator)
        self.bot.tree.add_command(self.ctx_get_moderator)
    

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # skip if the message isn't sent by a moderator
        if msg.author.id in self.moderators:
            self.moderators[msg.author.id] += 1
        
    
    async def register_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if not user.id in self.moderators:
            print(F"Adding user {user.display_name} to moderators")
            self.moderators[user.id] = 0
            await interaction.response.send_message(f"Adding user {user.display_name} to the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is already in the moderator list", ephemeral=True)

    async def deregister_moderator(self, interaction: discord.Interaction, user:discord.Member) -> None:
        if user.id in self.moderators:
            print(F"Removing user {user.display_name} from moderators")
            del self.moderators[user.id]
            await interaction.response.send_message(f"Removing user {user.display_name} from the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is not in the moderator list", ephemeral=True)
    

    async def get_moderator(self, interaction: discord.Interaction, user:discord.Member) -> None:
        if user.id in self.moderators:
            await interaction.response.send_message(f"moderator {user.display_name} has written {self.moderators[user.id]} messages!", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.display_name} is not a moderator", ephemeral=True)
    
    @app_commands.command(description="Sends the current moderator list as an embed")
    async def list_moderators(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title = "Moderator list",
            description= "Here are all the moderators and how many messages they've sent:",
            color=discord.Color.from_str("#ffffff")
        )
        for user in self.moderators:
            embed.add_field(name=interaction.guild.get_member(user).display_name, value=self.moderators[user], inline=False)
        
        await interaction.response.send_message(embed=embed)
    


# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Mod_manager begin loading")
    await bot.add_cog(Mod_manager(bot))
