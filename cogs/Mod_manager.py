# -*- coding: UTF-8 -*-
from discord.ext import commands, tasks
from discord import app_commands
import discord
from db_handler import DBHandler
from datetime import datetime, timezone, timedelta
import time

# ? global colour for the cog. Change this when we get around to a cohesive theme and whatnot.
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

        # Setting up the member count voice channel.
        count = interaction.guild.member_count
        member_count_channel = await interaction.guild.create_voice_channel(f"members-{count}", reason="Setting up bot, creating channel for tracking member count", position=0, overwrites={interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=False)})

        guild = self.db.get_guild(interaction.guild_id)
        if not guild:
            # Set some initial config stuff from the values we just recieved.
            self.db.add_guild(interaction.guild_id, (0, 0, 0),
                              self.mod_category_id, time.time(),
                              wait_time, member_count_channel.id)
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

        self.ctx_set_quotas = app_commands.ContextMenu(
            name="Set quotas", callback=self.set_quotas)
        self.ctx_get_quotas = app_commands.ContextMenu(
            name="Get quotas", callback=self.get_quotas)

        self.bot.tree.add_command(self.ctx_register_moderator)
        self.bot.tree.add_command(self.ctx_deregister_moderator)
        self.bot.tree.add_command(self.ctx_get_moderator)

        self.bot.tree.add_command(self.ctx_set_quotas)
        self.bot.tree.add_command(self.ctx_get_quotas)

    def cog_unload(self):
        self.quota_check.cancel()

    @tasks.loop(minutes=1)
    async def quota_check(self) -> None:
        guilds = self.db.get_all_guilds()
        for guild in guilds:
            if guild.time_between_checks <= datetime.timestamp(
                    datetime.now()) - guild.last_mod_check:
                # Do moderator status check:
                mods = self.db.get_all_moderators()
                for moderator in mods:
                    if moderator.guild_id == guild.id:
                        pass

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message) -> None:
        # Check to make sure author isn't the bot itself.
        if msg.author == self.bot.user:
            return
        # Make sure message is by moderator and not in moderator chats.
        guild = self.db.get_guild(msg.guild.id)
        if not guild:
            return
        if not msg.channel.category_id == guild.mod_category_id and self.is_moderator(
                msg.author):
            self.db.create_action("sent", msg.author.id, int(
                msg.created_at.timestamp()), msg.channel.id, guild, msg.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        # Check to make sure author isn't the bot itself.
        if before.author == self.bot.user:
            pass
        # Make sure message is by moderator and not in moderator chats.
        guild = self.db.get_guild(after.guild.id)
        if not guild:
            return
        if not after.channel.category_id == guild.mod_category_id and self.is_moderator(
                after.author):
            self.db.create_action("edited", after.author.id, int(
                after.edited_at.timestamp()), after.channel.id, guild, after.id)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:

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
            if not category_id == guild.mod_category_id and self.is_moderator(
                    entry.user):
                self.db.create_action(
                    "deleted", entry.user.id, int(
                        entry.created_at.timestamp()), channel_id, guild)

    async def register_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Command to register a user as a moderator with the bot.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            user (discord.Member): The user who the command should run on, is also passed automatically.
        """
        # TODO; Make this an embed
        if not self.is_moderator(user):
            guild = self.db.get_guild(interaction.guild_id)
            self.db.register_moderator(user.id, guild.default_quotas, guild)
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
        if self.is_moderator(user):
            self.db.de_register_moderator(user.id, interaction.guild_id)
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
        if self.is_moderator(user):
            sent, edited, deleted = self.db.get_amount_of_actions_by_type(
                0, int(time.time()), user.id, interaction.guild_id)
            await interaction.response.send_message(f"moderator {user.display_name} has sent {sent} messages, edited {edited} messages and deleted {deleted} messages.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.display_name} is not a moderator", ephemeral=True)

    async def set_quotas(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Command to set the quotas of a given moderator.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
            user (discord.Member): The user who the command should run on, is also passed automatically.
        """
        # TODO; Make embed
        if not self.is_moderator(user):
            await interaction.response.send_message(f"User {user.display_name} is not a moderator.")
            return
        await interaction.response.send_modal(SetUserQuotaModal(user, self))

    async def get_quotas(self, interaction: discord.Interaction, user: discord.Member) -> None:
        # TODO; Make this an embed
        mod = self.db.get_moderator(user.id, interaction.guild_id)
        if not mod:
            await interaction.response.send_message(f"User {user.display_name} is not a moderator.")
            return
        await interaction.response.send_message(f"User {user.display_name} has the following quotas:\n``{mod.send_quota} sent messages, {mod.edit_quota} edited messages & {mod.delete_quota} deleted messages``", ephemeral=True)

    # TODO! Maybe spin this out into it's own cog
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

    @app_commands.command(description="Sends the current moderator list as an embed")
    async def list_moderators(self, interaction: discord.Interaction) -> None:
        """Slash command to send a list of all moderators and their stats as an embed.

        Args:
            interaction (discord.Interaction): The discord interaction obj that is passed automatically.
        """
        moderators = self.db.get_all_moderators()
        if not moderators:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Moderator list",
                    description="There are no moderators in this server",
                    color=discord.Color.from_str("#ffffff")
                )
            )
            return
        # Create embed object.
        embed = discord.Embed(
            title="Moderator list",
            description="Here are all the moderators and how many messages they've sent:",
            colour=discord.Colour.from_str("#ffffff"))
        # Add new field to the embed for every moderator.
        for id in [mod.id for mod in moderators]:
            sent, edited, deleted = self.db.get_amount_of_actions_by_type(
                0, int(time.time()), id, interaction.guild_id)
            embed.add_field(
                name=interaction.guild.get_member(id).display_name,
                value=f"sent: {sent}, edited: {edited}, deleted: {deleted}",
                inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Gets the moderator stats for a user in a timeframe")
    async def get_moderator_stats(self, interaction: discord.Interaction, user: discord.Member, earlier_time: str, later_time: str = None) -> None:

        if not self.is_moderator(user):
            await interaction.response.send_message(f"User {user.display_name} is not a moderator.")

        # Check if first input was in the x days ago format:
        if earlier_time[-1:] == 'd':
            try:
                start_time = datetime.now(
                    timezone.utc) - timedelta(days=int(earlier_time[:-1]))
                earlier_date = start_time.strftime("%d/%m/%Y")
                start_time = int(start_time.timestamp())

            except ValueError:
                await interaction.response.send_message(f'"{earlier_time}" is not a valid input format, try either a date (DD/MM/YYY) or an amount of days ago (xd). (7d would check a week back per example)')
                return

        # Instead check if first input was a date:
        else:
            try:
                # So, I wanted to use the ISO 8601 standard here
                # but on request we use DD/MM/YYYY instead. Don't blame me,
                # blame imadiskordnoob...
                start_time = int(
                    datetime.strptime(
                        earlier_time,
                        "%d/%m/%Y").timestamp())
                earlier_date = earlier_time
            except ValueError:
                try:
                    # Checking if someone imputted data the american way.
                    _ = datetime.strptime(earlier_time, "%m/%d/%Y")
                    await interaction.response.send_message("Hey you, American, fuck you, we use the Swedish standard here...\n// Kind regards imadiskordnoob")
                    return
                except (ValueError):
                    await interaction.response.send_message(f'"{earlier_time}" is not a valid input format, try either a date (DD/MM/YYY) or an amount of days ago (xd). (7d would check a week back per example)')
                    return

        # Check if we have a second time or should just use the current time
        if later_time:
            # Check if second input was in the x days ago format:
            if later_time[-1:] == 'd':
                try:
                    end_time = datetime.now(
                        timezone.utc) - timedelta(days=int(later_time[:-1]))
                    later_date = end_time.strftime("%d/%m/%Y")
                    end_time = int(end_time.timestamp())

                except ValueError:
                    await interaction.response.send_message(f'"{later_time}" is not a valid input format, try either a date (DD/MM/YYY) or an amount of days ago (xd). (7d would check a week back per example)')
                    return

            # Instead check if second input was a date:
            else:
                try:
                    # So, I wanted to use the ISO 8601 standard here
                    # but on request we use DD/MM/YYYY instead. Don't blame me,
                    # blame imadiskordnoob...
                    end_time = int(
                        datetime.strptime(
                            later_time,
                            "%d/%m/%Y").timestamp())
                    later_date = later_time
                except ValueError:
                    try:
                        # Checking if someone imputted data the american way.
                        _ = datetime.strptime(later_time, "%m/%d/%Y")
                        await interaction.response.send_message("Hey you, American, fuck you, we use the Swedish standard here...\n// Kind regards imadiskordnoob")
                        return
                    except (ValueError):
                        await interaction.response.send_message(f'"{later_time}" is not a valid input format, try either a date (DD/MM/YYY) or an amount of days ago (xd). (7d would check a week back per example)')
                        return
        else:
            later_date = datetime.now(timezone.utc)
            end_time = int(later_date.timestamp())
            later_date = later_date.strftime("%d/%m/%Y")

        # We now have checked and both the timestamps are valid.
        sent, edited, deleted = self.db.get_amount_of_actions_by_type(
            start_time, end_time, user.id, interaction.guild_id)

        embed = discord.Embed(
            title=f"Moderator stats for {user.display_name}",
            description=f"Timeframe is {earlier_date} - {later_date}",
            colour=discord.Colour.from_str("#ffffff"))
        embed.add_field(name=f"sent: {sent}", value="", inline=False)
        embed.add_field(name=f"edited: {edited}", value="", inline=False)
        embed.add_field(name=f"deleted: {deleted}", value="", inline=False)

        await interaction.response.send_message(embed=embed)

    def is_moderator_channel(self, channel: discord.abc.GuildChannel) -> bool:
        """Function that checks if the given channel is under the moderator category in it's server.

        Args:
            channel (discord.abc.GuildChannel): The channel object to check for.

        Returns:
            bool: If the channel was in the moderator category or not
        """
        return channel.category.id == self.db.get_guild(
            channel.guild.id).mod_category_id

    def is_moderator(self, user: discord.Member) -> bool:
        """Function that checks if the given user is a moderator.

        Args:
            user (discord.Member): The user to check.

        Returns:
            bool: If the user is a moderator or not.
        """
        if self.db.get_moderator(user.id, user.guild.id):
            return True
        return False


class SetUserQuotaModal(discord.ui.Modal):
    """Modal to set the quotas for a certain user."""

    def __init__(self, user: discord.Member, cog: ModManager) -> None:
        super().__init__(title=f"Editing quotas for {user.display_name}")
        self.user = user
        self.db = cog.db

        # Setting the default values to be the moderator's current quota.
        moderator = cog.db.get_moderator(user.id, user.guild.id)

        self.sent_messages.default = str(moderator.send_quota)
        self.edited_messages.default = str(moderator.edit_quota)
        self.deleted_messages.default = str(moderator.delete_quota)

    # The default is replaced with runtime values
    # in the init fucntion.
    sent_messages = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Sent message quota: ",
        default=""
    )

    edited_messages = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Edited message quota: ",
        default=""
    )

    deleted_messages = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Deleted message quota: ",
        default=""
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            quotas = (
                self.sent_messages.value,
                self.edited_messages.value,
                self.deleted_messages.value,
            )
            self.db.set_quota(self.user.id, quotas, interaction.guild_id)
            await interaction.response.send_message(f"Updated quotas for {self.user.display_name} to be: sent: {quotas[0]}, edited: {quotas[1]}, deleted: {quotas[2]}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(f"one of the following is not a number: {self.sent_messages.value}, {self.edited_messages.value}, {self.deleted_messages.value}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message("something went wrong, please try again", ephemeral=True)
        # The super of this function logs our error with the setup logging
        # methods.
        return await super().on_error(interaction, error)


# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Mod_manager begin loading")
    await bot.add_cog(ModManager(bot))
