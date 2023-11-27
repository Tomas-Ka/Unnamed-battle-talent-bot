# -*- coding: UTF-8 -*-
from discord.ext import commands
from discord import app_commands
import discord
from db_handler import DBHandler
from helpers import Action, Moderator, Guild, VacationWeek
import time

# ? global colour for the bot. Change this when we get around to a cohesive theme and whatnot.
global colour
colour = 0x1dff1a


class ConfigView(discord.ui.View):
    """View for the config message."""

    def __init__(self, db: DBHandler) -> None:
        super().__init__()
        self.mod_category_id = 0
        self.mod_category_name = "Null"
        self.roles = []
        self.wait_time = None
        self.db = db

    @discord.ui.select(cls=discord.ui.ChannelSelect,
                       channel_types=[discord.ChannelType.category],
                       placeholder="Select moderator category")
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        # Lets the user select a channel category from a dropdown.
        # This function is run every time they change the dropdown.
        # The channel select chooses what category we don't track messages in
        # when we initialize the bot for a new server/guild.
        self.mod_category_id = select.values[0].id
        self.mod_category_name = select.values[0].name
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
            await interaction.response.send_message("You have to select a category!", ephemeral=True)
            return
        if not self.wait_time:
            await interaction.response.send_message("You have to select a default wait time!", ephemeral=True)
            return

        # Get amount of seconds to wait by taking about of days * amount of
        # seconds in a day.
        wait_time = int(self.wait_time) * 86_400

        guild = self.db.get_guild(interaction.guild_id)
        if not guild:
            # Set some initial config stuff from the values we just recieved.
            self.db.add_guild(interaction.guild_id, (0, 0, 0),
                              self.mod_category_id, time.time(),
                              wait_time,)
            guild = self.db.get_guild(interaction.guild_id)

        # Register all users who have the selected roles as moderators in the
        # database.
        for role in self.roles:
            for member in role.members:
                if member.id not in [
                        mod.id for mod in self.db.get_all_moderators()]:
                    self.db.register_moderator(member.id, guild.default_quotas)

        # Disable all the now used dropdowns (as well as the button).
        self.confirm.disabled = True
        self.channel_select.disabled = True
        self.role_select.disabled = True
        self.wait_time_select.disabled = True

        # Create embed to update the message with.
        embed = discord.Embed(
            title="Config",
            description="Config set! Please make sure to update your quotas using the ``/config_set_quotas command``!:",
            colour=colour)
        embed.add_field(
            name="Moderator category:",
            value=self.mod_category_name,
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


class ModManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db

        # Register context menu commands (right click commands)
        # and set their callbacks.
        self.ctx_register_moderator = app_commands.ContextMenu(
            name="Register moderator", callback=self.register_moderator)
        self.ctx_deregister_moderator = app_commands.ContextMenu(
            name="De-register moderator", callback=self.deregister_moderator)
        self.ctx_get_moderator = app_commands.ContextMenu(
            name="Get moderator stats", callback=self.get_moderator)

        self.bot.tree.add_command(self.ctx_register_moderator)
        self.bot.tree.add_command(self.ctx_deregister_moderator)
        self.bot.tree.add_command(self.ctx_get_moderator)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # Make sure message is by moderator and not in moderator chats.
        guild = self.db.get_guild(msg.guild.id)
        if not guild:
            return
        if not msg.channel.category_id == guild.mod_category_id and msg.author.id in [
                moderator.id for moderator in self.db.get_all_moderators()]:
            self.db.create_action("sent", msg.author.id, int(
                msg.created_at.timestamp()), msg.channel.id, msg.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        # Make sure message is by moderator and not in moderator chats.
        guild = self.db.get_guild(after.guild.id)
        if not guild:
            return
        if not after.channel.category_id == guild.mod_category_id and after.author.id in [
                moderator.id for moderator in self.db.get_all_moderators()]:
            self.db.create_action("edited", after.author.id, int(
                after.edited_at.timestamp()), after.channel.id, after.id)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):

        # TODO; Discord's audit logs are a bit strange. A new entry will only be
        # TODO; created if there is not already an entry containing the same 2 users,
        # TODO; and channel within the past 5 minutes. I have ideas for how to fix
        # TODO; this by setting off a coroutine to check if any more entries have
        # TODO; been created 5 minutes later, and first then add the action entries.
        # TODO; for now though, this works.

        # Make sure the audit log entry is a message deletion.
        if entry.action == discord.AuditLogAction.message_delete:
            # Get some extra data so it's easier to pass as arguments later.
            channel_id = entry.extra.channel.id
            category_id = entry.extra.channel.category_id

            # Make sure deletion is by a moderator and not in a moderator chat.
            guild = self.db.get_guild(entry.guild.id)
            if not guild:
                return
            if not category_id == guild.mod_category_id and entry.user.id in [
                    moderator.id for moderator in self.db.get_all_moderators()]:
                self.db.create_action(
                    "deleted", entry.user.id, int(
                        entry.created_at.timestamp()), channel_id)

    async def register_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Command to register a user as a moderator with the bot.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            user (discord.Member): The user who the command should run on, is also passed automatically.
        """
        # TODO; Make this an embed
        if user.id not in [mod.id for mod in self.db.get_all_moderators()]:
            guild = self.db.get_guild(interaction.guild_id)
            self.db.register_moderator(user.id, guild.default_quotas)
            await interaction.response.send_message(f"Adding user {user.display_name} to the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is already in the moderator list", ephemeral=True)

    async def deregister_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Command to de-register a user as a moderator with the bot.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            user (discord.Member): The user who the command should run on, is also passed automatically.
        """
        # TODO; Make this an embed
        if user.id in [mod.id for mod in self.db.get_all_moderators()]:
            self.db.de_register_moderator(user.id)
            await interaction.response.send_message(f"Removing user {user.display_name} from the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is not in the moderator list", ephemeral=True)

    async def get_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Command to get a moderator from the bot's moderator list and sends a small status on the user.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            user (discord.Member): The user who the command should run on, is also passed automatically.
        """
        # TODO; Make this an embed
        if user.id in [mod.id for mod in self.db.get_all_moderators()]:
            sent, edited, deleted = self.db.get_amount_of_actions_by_type(
                0, int(time.time()), user.id)
            await interaction.response.send_message(f"moderator {user.display_name} has sent {sent} messages, edited {edited} messages and deleted {deleted} messages.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.display_name} is not a moderator", ephemeral=True)

    @app_commands.command(description="Sends the current moderator list as an embed")
    async def list_moderators(self, interaction: discord.Interaction) -> None:
        """Slash command to send a list of all moderators and their stats as an embed.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        # Create embed object.
        embed = discord.Embed(
            title="Moderator list",
            description="Here are all the moderators and how many messages they've sent:",
            colour=discord.Colour.from_str("#ffffff"))
        # Add new field to the embed for every moderator.
        for id in [mod.id for mod in self.db.get_all_moderators()]:
            sent, edited, deleted = self.db.get_amount_of_actions_by_type(
                0, int(time.time()), id)
            embed.add_field(
                name=interaction.guild.get_member(id).display_name,
                value=f"sent: {sent}, edited: {edited}, deleted: {deleted}",
                inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Configures the bot")
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

    @app_commands.command(description="Set default server quotas")
    async def config_set_quotas(self, interaction: discord.Interaction, send_quota: int, edit_quota: int, delete_quota: int) -> None:
        self.db.set_default_quotas(
            interaction.guild_id, (send_quota, edit_quota, delete_quota,))
        embed = discord.Embed(
            title="Set quotas",
            description=f"The default quota that the moderators need to fufill every week is:\n``{send_quota} sent messages, {edit_quota} edited messages & {delete_quota} deleted messages``\n### Please note that this command has **not** updated any quotas for current moderators",
            colour=colour)

        await interaction.response.send_message(embed=embed)

    def is_moderator_channel(self, channel: discord.abc.GuildChannel) -> bool:
        """Function that checks if the given channel is under the moderator category in it's server.

        Args:
            channel (discord.abc.GuildChannel): The channel object to check for.

        Returns:
            bool: If the channel was in the moderator category or not
        """
        return channel.category.id == self.db.get_guild(
            channel.guild.id,).mod_category_id


# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Mod_manager begin loading")
    await bot.add_cog(ModManager(bot))
