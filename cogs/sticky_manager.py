from discord.ext import commands
from discord import app_commands
import discord
from db_handler import DBHandler

# ? global colour for the cog. Change this when we get around to a cohesive theme and whatnot.
global colour
colour = 0x2db83d


class StickyManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # Don't resend if the message is from the bot:
        if msg.author.id == self.bot.user.id:
            return

        # Make sure we have a sticky in the current channel.
        sticky = self.db.get_sticky(msg.channel.id)
        if sticky:
            # Create and then send the sticky embed.
            sticky_embed = discord.Embed(
                title=sticky.title,
                description=sticky.description,
                colour=colour)
            sticky_embed.set_footer(
                text=f"Stickied by {self.bot.user.display_name}")
            new_sticky = await msg.channel.send(embed=sticky_embed)

            # Delete the old sticky message and update database
            await msg.channel.get_partial_message(sticky.message_id).delete()
            self.db.update_sticky(sticky.channel_id, new_sticky.id)

    @app_commands.command()
    async def create_sticky(self, interaction: discord.Interaction) -> None:
        """Creates a sticky in this channel.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        if self.db.get_sticky(interaction.channel_id):
            await interaction.response.send_message("There is already a sticky in this channel.", ephemeral=True)
            return
        await interaction.response.send_modal(CreateStickyModal(self, interaction, self.bot.user.display_name))

    @app_commands.command()
    async def delete_sticky(self, interaction: discord.Interaction, del_message: bool = False) -> None:
        """Deletes a sticky in the current channel.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            del_message (bool): Whether or not to delete the sticky message.
        """
        sticky = self.db.get_sticky(interaction.channel_id)
        if sticky:
            if del_message:
                await interaction.channel.get_partial_message(sticky.message_id).delete()
            self.db.del_sticky(interaction.channel_id)
            await interaction.response.send_message(f"Removed sticky in {interaction.channel.name}.", ephemeral=True)
        else:
            await interaction.response.send_message("There isn't a sticky in this channel.", ephemeral=True)


class CreateStickyModal(discord.ui.Modal):
    """Modal to create a new sticky message"""

    def __init__(
            self,
            cog: StickyManager,
            prev_interaction: discord.Interaction,
            bot_name: str) -> None:
        # Run inherited init to set the modal title properly
        super().__init__(
            title=f"Create new sticky in {prev_interaction.channel.name}")
        self.db = cog.db
        self.bot_name = bot_name

    sticky_title = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Sticky title:",
        placeholder="title",
        max_length=256)

    description = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label="Sticky main body text:",
        placeholder="main body",
        max_length=2048)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Create and send Embed.
        sticky_embed = discord.Embed(
            title=self.sticky_title.value,
            description=self.description.value,
            colour=colour)
        sticky_embed.set_footer(text=f"Stickied by {self.bot_name}")
        new_sticky = await interaction.channel.send(embed=sticky_embed)

        # Create database entry for sticky message.
        self.db.create_sticky(
            interaction.channel_id,
            new_sticky.id,
            self.sticky_title.value,
            self.description.value)

        # Tell discord we're done here.
        await interaction.response.defer()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message("Something went wrong, please try again.", ephemeral=True)
        # The super of this function logs our error with the setup logging
        # methods.
        await super().on_error(interaction, error)


# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.sticky_manager begin loading")
    await bot.add_cog(StickyManager(bot))
