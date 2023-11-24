# -*- coding: UTF-8 -*-
from discord.ext import commands
from discord import app_commands
import discord
from db_handler import DBHandler
from helpers import Action, Moderator, Guild, VacationWeek
import time
# TODO; WRITE DOCUMENTATION
# I'm just too tired rn :P


class ConfigView(discord.ui.View):
    def __init__(self, db: DBHandler) -> None:
        super().__init__()
        self.mod_category_id = 0
        self.mod_category_name = "Null"
        self.roles = []
        self.db = db

    @discord.ui.select(cls=discord.ui.ChannelSelect,
                       channel_types=[discord.ChannelType.category],
                       placeholder="Select moderator category")
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect) -> None:
        self.mod_category_id = select.values[0].id
        self.mod_category_name = select.values[0].name
        await interaction.response.defer()

    @discord.ui.select(cls=discord.ui.RoleSelect,
                       placeholder="Select moderator roles to track stats for",
                       min_values=0,
                       max_values=25)
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect) -> None:
        self.roles = select.values
        await interaction.response.defer()

    @discord.ui.button(style=discord.ButtonStyle.success, label="Confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if (self.mod_category_id == 0):
            await interaction.response.send_message("You have to select a category!", ephemeral=True)
            return

        guild = self.db.get_guild(interaction.guild_id)
        if not guild:
            # set some initial values that should very much be changed by the
            # user later
            self.db.add_guild(interaction.guild_id, (0, 0, 0),
                              self.mod_category_id, time.time(),
                              1_000_000_000,)
            guild = self.db.get_guild(interaction.guild_id)

        for role in self.roles:
            for member in role.members:
                if member.id not in [
                        mod.id for mod in self.db.get_all_moderators()]:
                    self.db.register_moderator(member.id, guild.default_quotas)

        self.confirm.disabled = True
        self.channel_select.disabled = True
        self.role_select.disabled = True
        # TODO; make this response an embed
        if self.roles:
            await interaction.channel.send(f"mod category is: {self.mod_category_name}\n you have registered the following roles as admins: {', '.join([r.name for r in self.roles])[:-2]}")
        else:
            await interaction.channel.send(f"mod category is: {self.mod_category_name}\n you have not registered any roles as admins")
        await interaction.response.edit_message(view=self)
        self.stop()


class ModManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db

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
        # make sure message is by moderator and not in moderator chats
        guild = self.db.get_guild(msg.guild.id)
        if not guild:
            return
        if not msg.channel.category_id == guild.mod_category_id and msg.author.id in [
                moderator.id for moderator in self.db.get_all_moderators()]:
            self.db.create_action("sent", msg.author.id, int(
                msg.created_at.timestamp()), msg.channel.id, msg.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        # make sure message is by moderator and not in moderator chats
        guild = self.db.get_guild(after.guild.id)
        if not guild:
            return
        if not after.channel.category_id == guild.mod_category_id and after.author.id in [
                moderator.id for moderator in self.db.get_all_moderators()]:
            self.db.create_action("edited", after.author.id, int(
                after.edited_at.timestamp()), after.channel.id, after.id)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        # make sure the audit log entry is a message deletion, and that it is
        # done by a moderator in a non moderator channel
        if entry.action == discord.AuditLogAction.message_delete:
            channel_id = entry.extra.channel.id
            category_id = entry.extra.channel.category_id
            guild = self.db.get_guild(entry.guild.id)
            if not guild:
                return
            if not category_id == guild.mod_category_id and entry.user.id in [
                    moderator.id for moderator in self.db.get_all_moderators()]:
                self.db.create_action(
                    "deleted", entry.user.id, int(
                        entry.created_at.timestamp()), channel_id)

    async def register_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.id not in [mod.id for mod in self.db.get_all_moderators()]:
            guild = self.db.get_guild(interaction.guild_id)
            self.db.register_moderator(user.id, guild.default_quotas)
            await interaction.response.send_message(f"Adding user {user.display_name} to the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is already in the moderator list", ephemeral=True)

    async def deregister_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.id in [mod.id for mod in self.db.get_all_moderators()]:
            self.db.de_register_moderator(user.id)
            await interaction.response.send_message(f"Removing user {user.display_name} from the moderator list", ephemeral=True)
        else:
            await interaction.response.send_message(f"User {user.display_name} is not in the moderator list", ephemeral=True)

    async def get_moderator(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if user.id in [mod.id for mod in self.db.get_all_moderators()]:
            sent, edited, deleted = self.db.get_amount_of_actions_by_type(
                0, int(time.time()), user.id)
            await interaction.response.send_message(f"moderator {user.display_name} has sent {sent} messages, edited {edited} messages and deleted {deleted} messages.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.display_name} is not a moderator", ephemeral=True)

    @app_commands.command(description="Sends the current moderator list as an embed")
    async def list_moderators(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Moderator list",
            description="Here are all the moderators and how many messages they've sent:",
            color=discord.Color.from_str("#ffffff"))
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
        await interaction.response.send_message("Configure", view=ConfigView(self.db))

    def is_moderator_channel(self, channel: discord.abc.GuildChannel) -> None:
        return channel.category.id == self.db.get_guild(
            channel.guild.id,).mod_category_id


# ------------------------------MAIN CODE------------------------------
# This setup is required for the cog to setup and run,
# and is run when the cog is loaded with bot.load_extensions()
async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Mod_manager begin loading")
    await bot.add_cog(ModManager(bot))
