import discord
from discord.ext import commands
import os
import asyncio
from config import DISCORD_TOKEN

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for mentions

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    # Change bot status
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="mentions"))

async def load_cogs():
    """Load all cogs from the cogs directory."""
    if not os.path.exists('./cogs'):
        os.makedirs('./cogs')
        
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded cog: {filename}')
            except Exception as e:
                print(f'Failed to load cog {filename}: {e}')

async def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN is missing. Please set it in your .env file.")
        return
        
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # Run the bot
    asyncio.run(main())
