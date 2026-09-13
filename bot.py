import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
import json
from config import DISCORD_TOKEN, OWNER_ID

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for mentions

# Initialize bot
bot = commands.Bot(command_prefix=["tesla ", "Tesla "], intents=intents, help_command=None, owner_id=OWNER_ID)

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

bot.settings = load_settings()

@bot.check
async def globally_block_channels(ctx):
    # Owner can use the bot anywhere
    if ctx.author.id == bot.owner_id:
        return True

    # Only check if restricted_channel is set and we're not running setchannel itself
    if ctx.command and ctx.command.name in ('setchannel', 'help', 'ss'):
        return True # let owner/admins run these anywhere, or at least let it proceed to command logic

    restricted_id = bot.settings.get('restricted_channel')
    if restricted_id and ctx.channel.id != restricted_id:
        # Avoid sending multiple messages if check is evaluated multiple times
        if not getattr(ctx, "restriction_handled", False):
            await ctx.reply(f"I am restricted to <#{restricted_id}> only", silent=True)
            ctx.restriction_handled = True
        return False
    return True

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    # Change bot status
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="mentions"))

@bot.command()
@commands.is_owner()
async def ss(ctx, presence_type: str, activity_type: str, *, status_name: str):
    """
    Set the bot's status and activity. Only the bot owner can run this.
    Usage: tesla ss <idle/dnd/online/offline> <watching/listening/playing/streaming> <status message>
    """
    presence_map = {
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd,
        "online": discord.Status.online,
        "offline": discord.Status.offline
    }
    
    activity_map = {
        "watching": discord.ActivityType.watching,
        "listening": discord.ActivityType.listening,
        "playing": discord.ActivityType.playing,
        "streaming": discord.ActivityType.streaming
    }
    
    p = presence_map.get(presence_type.lower())
    a = activity_map.get(activity_type.lower())
    
    if not p:
        await ctx.send("❌ Invalid presence type! Choose from: idle, dnd, online, offline")
        return
    if not a:
        await ctx.send("❌ Invalid activity type! Choose from: watching, listening, playing, streaming")
        return
        
    await bot.change_presence(status=p, activity=discord.Activity(type=a, name=status_name))
    await ctx.send(f"✅ Status updated successfully!\n**Presence:** {presence_type.title()}\n**Activity:** {activity_type.title()} {status_name}")

@ss.error
async def ss_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ You don't have permission to use this command! Only the bot owner can change the status.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing arguments!\nUsage: `tesla ss <idle/dnd/online> <watching/listening/playing> <message>`")

@bot.command(aliases=['sc'])
@commands.has_permissions(administrator=True)
async def setchannel(ctx, channel: discord.TextChannel = None):
    """
    Sets the restricted channel for the bot.
    Usage: tesla setchannel #channel
    """
    if channel:
        bot.settings['restricted_channel'] = channel.id
        save_settings(bot.settings)
        await ctx.send(f"✅ Bot is now restricted to {channel.mention}.")
    else:
        # If no channel is provided, remove restriction
        if 'restricted_channel' in bot.settings:
            del bot.settings['restricted_channel']
            save_settings(bot.settings)
        await ctx.send("✅ Bot restriction removed. It can now be used in any channel.")

@setchannel.error
async def setchannel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command! Only administrators can restrict the bot.", silent=True)
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Channel not found.", silent=True)

@bot.command()
async def help(ctx):
    """Shows this help message with all commands."""
    embed = discord.Embed(title="Tesla Bot Commands", color=0x00ff00)
    
    # ss command
    embed.add_field(
        name="`tesla ss <idle/dnd/online/offline> <watching/listening/playing/streaming> <status_message>`",
        value="Updates the bot's status and activity. **(Bot Owner Only)**\n*Example:* `tesla ss idle watching You<3`",
        inline=False
    )
    
    # settings command
    embed.add_field(
        name="`tesla setchannel / sc <#channel>`",
        value="Restricts the bot to only reply in the specified channel. (Admins only)\n*Example:* `tesla sc #general`\nRun without a channel to remove the restriction.",
        inline=False
    )
    
    # bump reminder command
    embed.add_field(
        name="`tesla setbumprole <@role>` / `tesla setbump/sb <#channel/time>` / `tesla bumpstatus/bs`",
        value="**setbumprole**: Sets the role to ping when it is time to bump.\n**setbump / sb**: Can be used to restrict bump commands to a `#channel`, OR manually set the timer (e.g., `tesla sb 1h 46m`).\n**bumpstatus / bs**: Shows how much time is left until the next bump.",
        inline=False
    )
    
    # music commands
    embed.add_field(
        name="`tesla play <song/url>`",
        value="Plays music in your voice channel.",
        inline=False
    )
    embed.add_field(
        name="`tesla join` / `tesla leave`",
        value="Joins or leaves the voice channel.",
        inline=False
    )

    # welcome commands
    embed.add_field(
        name="`tesla welcome setup <#channel> <time> <message>`",
        value="Configures an auto-deleting welcome message for new members.\nSee `tesla welcome` for more details.",
        inline=False
    )

    # ai assistant
    embed.add_field(
        name="`@Tesla <message>`",
        value="Chat with me! Just mention me and I will reply to you.",
        inline=False
    )
    
    await ctx.send(embed=embed)


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
