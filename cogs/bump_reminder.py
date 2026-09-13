import discord
from discord.ext import commands, tasks
import json
import os
import time

import re

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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setbumprole(self, ctx, role: discord.Role = None):
        """Sets the role to ping when it is time to bump.
        Usage: tesla setbumprole @Role
        """
        settings = self._load_settings()
        if role:
            settings['bump_role'] = role.id
            self._save_settings(settings)
            await ctx.send(f"✅ Bump reminder will now ping {role.mention}!")
        else:
            if 'bump_role' in settings:
                del settings['bump_role']
                self._save_settings(settings)
            await ctx.send("✅ Bump reminder role has been removed. It will no longer ping a specific role.")

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
                # Check for cooldown message
                elif "wait another" in description.lower():
                    match = re.search(r'wait another (?:(\d+)\s*hour[s]?)?\s*(?:(\d+)\s*minute[s]?)?', description, re.IGNORECASE)
                    if match:
                        hours = int(match.group(1)) if match.group(1) else 0
                        minutes = int(match.group(2)) if match.group(2) else 0
                        total_seconds = (hours * 3600) + (minutes * 60)
                        
                        if total_seconds > 0:
                            settings = self._load_settings()
                            settings['next_bump_time'] = time.time() + total_seconds
                            settings['bump_channel'] = message.channel.id
                            self._save_settings(settings)
                            
                            await message.channel.send(f"⏱️ **Cooldown detected!** I'll remind you to bump again in {hours}h {minutes}m.")

    @tasks.loop(minutes=1)
    async def check_bump(self):
        settings = self._load_settings()
        next_bump = settings.get('next_bump_time')
        channel_id = settings.get('bump_channel')
        role_id = settings.get('bump_role')
        
        if next_bump and channel_id:
            if time.time() >= next_bump:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    ping_text = f"<@&{role_id}> " if role_id else ""
                    await channel.send(f"⏰ **BUMP TIME!** ⏰\n{ping_text}It's time to use `/bump` to bump the server again on Disboard!")
                
                # Clear the reminder
                settings['next_bump_time'] = None
                self._save_settings(settings)

    @check_bump.before_loop
    async def before_check_bump(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
