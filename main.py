# -*- coding: UTF-8 -*-
import discord
import logging
import traceback
from discord.ext import commands
from dotenv import load_dotenv
from os import environ, listdir

load_dotenv()
token = environ["TEST_TOKEN"]

# set up logging
logging_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# test guild (so we can easily sync and test commands)
TEST_GUILD = discord.Object(environ["TEST_GUILD_ID"])

class BTBot(commands.Bot):
    def __init__(self, command_prefix: str) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            intents=intents,
            command_prefix = command_prefix,
            description = "Battle Talent Bot",
            activity = discord.Game(
                name="Battle Talent, of course ;D"))
    
    async def on_ready(self) -> None:
        # When we're all loaded in and ready, send this to give a clear indication in the console
        # mostly for when logging things
        print(f'logged in as {self.user} (ID: {self.user.id})')
        print("-----------------")
    
    async def setup_hook(self) -> None:
        # any data processing to get stuff into memory goes here

        # load cogs:
        print("loading cogs:")
        cogs = [f"cogs.{c[:-3]}" for c in listdir("./cogs") if c[-3:] == ".py"]

        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f'\t{cog} loaded')
            except Exception as e:
                # if we fail to load the cog we want to print the cog's error
                # thus the traceback
                print(f'Failed to load extension {cog}!')
                traceback.print_exc()
        

        # * If we are debugging, sync slash commands with discord here
        # await self.tree.sync()
        # self.tree.copy_global_to(guild=TEST_GUILD)
        # await self.tree.sync(guild=TEST_GUILD)



# ------------------------------MAIN CODE------------------------------
bot = BTBot(command_prefix="!")
if __name__ == "__main__":
    bot.run(token , log_handler=logging_handler) # Run our bot!