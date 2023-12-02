# -*- conding: UTF-8 -*-
from discord.ext import commands, tasks
from discord import app_commands
import discord
from db_handler import DBHandler
#! TODO; ADD MORE COMMENTS

class MemberCountManager(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db: DBHandler = bot.db
        self.check_member_count.start()

    # ! Change to minutes after testing.
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

            # Finally get the member count and edit the title
            member_count = discord_guild.member_count
            await channel.edit(name=f"members - {member_count}")

    @check_member_count.before_loop
    async def before_check_member_count(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    print(f"\tcogs.Member_count_manager begin loading")
    await bot.add_cog(MemberCountManager(bot))
