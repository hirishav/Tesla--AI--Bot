import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
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

# --- Dummy Web Server for Render ---
async def handle_ping(request):
    return web.Response(text="Tesla Bot is alive and running!")

async def start_web_server():
    """Starts a dummy web server to keep Render happy."""
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Dummy Web server started on port {port} for Render")
# -----------------------------------

async def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN is missing. Please set it in your .env file.")
        return
        
    async with bot:
        await load_cogs()
        # Start the web server before the bot
        await start_web_server()
        await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # Run the bot
    asyncio.run(main())
