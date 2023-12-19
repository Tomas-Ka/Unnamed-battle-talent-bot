from discord.ext import commands, tasks
from discord import app_commands
import discord
from db_handler import DBHandler


class MemberCountManager(commands.GroupCog, name="member_count"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db
        self.check_member_count.start()

    @tasks.loop(minutes=10)
    async def check_member_count(self):
        guilds = self.db.get_all_guilds()
        for guild in guilds:
            discord_guild = self.bot.get_guild(guild.id)
            if discord_guild is None:
                # Guild has not been initalized, we don't have to worry about
                # member count.
                return

            channel = discord_guild.get_channel(guild.member_count_channel_id)
            if channel is None:
                # The member count channel is either gone or hasn't been set
                # up.
                return

            # Finally get the member count and edit the title.
            member_count = discord_guild.member_count
            await channel.edit(name=f"members - {member_count}")

    @check_member_count.before_loop
    async def before_check_member_count(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="create")
    async def create_member_count_channel(self, interaction: discord.Interaction):
        """Sets up a new member count channel in the given server (if one does not already exist).

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        # Check to make sure there isn't already a channel.
        guild = self.db.get_guild(interaction.guild_id)
        if interaction.guild.get_channel(guild.member_count_channel_id):
            await interaction.response.send_message("There is already a member count channel!", ephemeral=True)
            return

        # Setting up a new member count voice channel.
        count = interaction.guild.member_count
        member_count_channel = await interaction.guild.create_voice_channel(f"members - {count}",
                                                                            reason="Setting up bot, creating channel for tracking member count",
                                                                            position=0,
                                                                            overwrites={
                                                                                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False)
                                                                            }
                                                                            )
        self.db.set_member_count_channel_id(
            interaction.guild_id,
            member_count_channel.id)
        await interaction.response.send_message("Member count channel created!", ephemeral=True)

    @app_commands.command(name="delete")
    async def delete_member_count_channel(self, interaction: discord.Interaction):
        """Removes the member count channel from both the server and the database.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        guild = self.db.get_guild(interaction.guild_id)
        if guild:
            channel = self.bot.get_guild(
                guild.id).get_channel(
                guild.member_count_channel_id)
            self.db.set_member_count_channel_id(guild.id, None)
            if channel:
                await channel.delete()
                await interaction.response.send_message("Successfuly deleted the member count channel.", ephemeral=True)
                return
            await interaction.response.send_message("Could not find channel, but deleted database entry.", ephemeral=True)
            return
        await interaction.response.send_message("Server is not set up with this bot yet.\nPlease run /configure to do so.", ephemeral=True)



# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.member_count_manager begin loading")
    await bot.add_cog(MemberCountManager(bot))
