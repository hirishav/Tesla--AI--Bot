import discord
from discord.ext import commands, tasks
import json
import os
import time

SETTINGS_FILE = 'settings.json'

class BumpReminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.disboard_id = 302050872383242240
        self.bump_duration = 2 * 60 * 60  # 2 hours in seconds
        self.check_bump.start()

    def cog_unload(self):
        self.check_bump.cancel()

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_settings(self, settings):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from bots other than Disboard
        if not message.author.bot:
            return
            
        if message.author.id == self.disboard_id:
            # Check for bump success message in embeds
            if message.embeds:
                embed = message.embeds[0]
                description = embed.description or ""
                title = embed.title or ""
                
                # Disboard usually says "Bump done!" in the description
                if "bump done" in description.lower() or "bump done" in title.lower():
                    settings = self._load_settings()
                    
                    # Store the channel ID and the timestamp when the next bump is due
                    settings['next_bump_time'] = time.time() + self.bump_duration
                    settings['bump_channel'] = message.channel.id
                    self._save_settings(settings)
                    
                    await message.channel.send("⏱️ **Bump detected!** I will remind you to bump again in exactly 2 hours.")

    @tasks.loop(minutes=1)
    async def check_bump(self):
        settings = self._load_settings()
        next_bump = settings.get('next_bump_time')
        channel_id = settings.get('bump_channel')
        
        if next_bump and channel_id:
            if time.time() >= next_bump:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"⏰ **BUMP TIME!** ⏰\nIt has been 2 hours! Please use `/bump` to bump the server again on Disboard!")
                
                # Clear the reminder
                settings['next_bump_time'] = None
                self._save_settings(settings)

    @check_bump.before_loop
    async def before_check_bump(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
