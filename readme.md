# Unnamed Battle Talent bot
### Purpose:
This is a python Discord bot that handles primarily some moderator things on the battle talent server, as well as some other things (such as stickies, roles, tickets, modmail and so on), basically it's supposed to create more tools for moderators, as well as be a drop in replacement to reduce the amount of bots on the server.

### System and usage:
This bot runs on the discord.py library, and the main.py is the entrypoint. For database setup, run db_handler.py (which handles our sqlite database with the sqlite3 library). All functionality is split into cogs in the /cogs directory.
This bot uses python-dotenv to load the bot token (and some other debugging things), as to not make any vulnerable information public.

#### Status:
This entire project is still a work in progress, and will get updated as time goes by