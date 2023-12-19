from db_handler import DBHandler
import discord
from discord import app_commands
from discord.ext import commands
import time
from datetime import datetime

# ? global colour for the cog. Change this when we get around to a cohesive theme and whatnot.
global colour
colour = 0x1dff1a


class ConfigView(discord.ui.View):
    """View for the config message."""

    def __init__(self, db: DBHandler) -> None:
        super().__init__()
        self.mod_category_id = 0
        self.output_channel_id = 0
        self.mod_category_name = "Null"
        self.output_channel_name = "Null"
        self.roles = []
        self.wait_time = None
        self.db = db

    @discord.ui.select(cls=discord.ui.ChannelSelect,
                       channel_types=[discord.ChannelType.category],
                       placeholder="Select moderator category")
    async def channel_category_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        # Lets the user select a channel category from a dropdown.
        # This function is run every time they change the dropdown.
        # The channel select chooses what category we don't track messages in
        # when we initialize the bot for a new server/guild.
        self.mod_category_id = select.values[0].id
        self.mod_category_name = select.values[0].name
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.ChannelSelect,
                       channel_types=[discord.ChannelType.text],
                       placeholder="Select log output chat")
    async def log_output_chat(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        # Lets the user select a channel from a dropdown.
        # This function is run every time they change the dropdown.
        # The log output select chooses what channel we send our outputs in
        # when we initialize the bot for a new server/guild.
        self.output_channel_id = select.values[0].id
        self.output_channel_name = select.values[0].name
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect,
                       placeholder="Select moderator roles to track stats for",
                       min_values=0,
                       max_values=25)
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect) -> None:
        # Lets the user select one or multiple roles from a dropdown.
        # This function is run every time they change the dropdown.
        # The role select chooses who we add automatically as moderators
        # when we initialize the bot for a new server/guild
        self.roles = select.values
        await interaction.response.defer()

    @discord.ui.select(
        cls=discord.ui.Select,
        options=[
            discord.SelectOption(
                label="1 week",
                description="check moderator stats once every week",
                value="7"),
            discord.SelectOption(
                label="2 weeks",
                description="check moderator stats once every other week",
                value="14"),
            discord.SelectOption(
                label="4 weeks",
                description="check moderator stats once every 4 weeks",
                value="28")],
        placeholder="Select how much time we should wait between moderator checks")
    async def wait_time_select(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        # Lets the user select one of the predetermined valeus from the dropdown.
        # This setting can also be changed later with a slash command
        self.wait_time = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.success, label="Confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        # Make sure all our fields have proper values and error if not
        if (self.mod_category_id == 0):
            await interaction.response.send_message("You have to select a moderator category!", ephemeral=True)
            return
        if (self.output_channel_id == 0):
            await interaction.response.send_message("You have to select an output channel!", ephemeral=True)
            return
        if not self.wait_time:
            await interaction.response.send_message("You have to select a default wait time!", ephemeral=True)
            return

        # Get amount of seconds to wait by taking about of days * amount of
        # seconds in a day.
        wait_time = int(self.wait_time) * 86_400

        guild = self.db.get_guild(interaction.guild_id)
        if not guild:
            # Setting up the member count voice channel.
            count = interaction.guild.member_count
            member_count_channel = await interaction.guild.create_voice_channel(f"members - {count}", reason="Setting up bot, creating channel for tracking member count", position=0, overwrites={interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False)})

            # Set some initial config stuff from the values we just recieved.
            self.db.add_guild(
                interaction.guild_id, (0, 0, 0), self.mod_category_id, int(
                    datetime.timestamp(
                        datetime.now())), wait_time, member_count_channel.id, self.output_channel_id)
            guild = self.db.get_guild(interaction.guild_id)

        # Register all users who have the selected roles as moderators in the
        # database.
        for role in self.roles:
            for member in role.members:
                if member.id not in [
                        mod.id for mod in self.db.get_all_moderators()]:
                    self.db.register_moderator(
                        member.id, guild.default_quotas, guild)

        # Disable all the now used dropdowns (as well as the button).
        self.confirm.disabled = True
        self.channel_category_select.disabled = True
        self.log_output_chat.disabled = True
        self.role_select.disabled = True
        self.wait_time_select.disabled = True

        # Create embed to update the message with.
        embed = discord.Embed(
            title="Config",
            description="Config set! Please make sure to update your quotas using the ``/configure default_quotas command``!:",
            colour=colour)
        embed.add_field(
            name="Moderator category:",
            value=self.mod_category_name,
            inline=False)
        embed.add_field(
            name="Output chat:",
            value=self.output_channel_name,
            inline=False)

        if self.roles:
            # Can't put a \n in an fstring without python 3.12, and so we spin
            # it out into a var here.
            names = '\n'.join([role.name for role in self.roles])
            embed.add_field(
                name="Registered admins:",
                value=f"You have registered the following roles as admins:\n{names}",
                inline=False)
        else:
            embed.add_field(
                name="Registered admins:",
                value="You have not registered any roles as admin.",
                inline=False)

        embed.add_field(
            name="Moderator checks:",
            value=f"Moderator checks will be done every {self.wait_time} days",
            inline=False)

        # Update the embed in the sent message.
        await interaction.response.edit_message(view=None, embed=embed)
        self.stop()


@app_commands.guild_only()
class ConfigManager(commands.GroupCog, name="configure"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db

    @app_commands.command(name="setup", description="Configures the bot")
    async def configure(self, interaction: discord.Interaction) -> None:
        """Slash command that configures a bot, adds it to the database and makes sure
        it has all the default settings it requires

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        embed = discord.Embed(
            title="Config",
            description="Please fill in the dropdowns at the bottom of this message (and hit the button) to get this bot set up and running on your server. Once you have finished this, please make sure to set a quota for your moderators by running ``/set_quota``!",
            colour=colour)
        await interaction.response.send_message(view=ConfigView(self.db), embed=embed)

    @app_commands.command(name="default_quotas",
                          description="Set default server quotas")
    async def config_set_quotas(self, interaction: discord.Interaction, send_quota: int, edit_quota: int, delete_quota: int) -> None:
        """Slash command that sets the default quotas of the guild in the db.
        This does not update the quotas of current members, only the default for new members.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            send_quota (int): Quota for sent messages every timeframe.
            edit_quota (int): Quota for edited messages every timeframe.
            delete_quota (int): Quota for deleted messages every timeframe.
        """
        self.db.set_default_quotas(
            interaction.guild_id, (send_quota, edit_quota, delete_quota,))
        embed = discord.Embed(
            title="Set quotas",
            description=f"The default quota that the moderators need to fufill every week is:\n``{send_quota} sent messages, {edit_quota} edited messages & {delete_quota} deleted messages``\n### Please note that this command has **not** updated any quotas for current moderators",
            colour=colour)

        await interaction.response.send_message(embed=embed)

# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.config_manager begin loading")
    await bot.add_cog(ConfigManager(bot))
