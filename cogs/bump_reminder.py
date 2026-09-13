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

    def _is_allowed_channel(self, ctx):
        settings = self._load_settings()
        restricted = settings.get('bump_restricted_channel')
        if not restricted:
            return True, None
        return ctx.channel.id == restricted, restricted

    async def _do_bumpstatus(self, ctx):
        settings = self._load_settings()
        next_bump = settings.get('next_bump_time')
        
        if not next_bump:
            await ctx.send("There is no active bump timer. The server can be bumped right now!")
            return
            
        remaining = int(next_bump - time.time())
        if remaining <= 0:
            await ctx.send("It's time to bump! The server can be bumped right now!")
        else:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await ctx.send(f"The next bump is available in {hours}h {minutes}m.")

    @commands.command(aliases=['bs'])
    async def bumpstatus(self, ctx):
        """Shows the time remaining for the next bump."""
        allowed, restricted_id = self._is_allowed_channel(ctx)
        if not allowed:
            await ctx.reply(f"I am restricted to <#{restricted_id}> only", silent=True)
            return
            
        await self._do_bumpstatus(ctx)

    async def _do_setbump(self, ctx, arg: str, check_admin=False):
        # Check if argument is a channel mention
        if arg.startswith('<#') and arg.endswith('>'):
            if check_admin and not ctx.author.guild_permissions.administrator:
                await ctx.send("❌ Only administrators can restrict the bump channel!")
                return
            channel_id = int(arg[2:-1])
            channel = self.bot.get_channel(channel_id)
            if channel:
                settings = self._load_settings()
                settings['bump_restricted_channel'] = channel.id
                self._save_settings(settings)
                await ctx.send(f"✅ Bump commands are now restricted to {channel.mention}.")
                return
        
        # If the argument is exactly "remove", we remove the restriction
        if arg.lower() == "remove":
            if check_admin and not ctx.author.guild_permissions.administrator:
                await ctx.send("❌ Only administrators can remove the bump channel restriction!")
                return
            settings = self._load_settings()
            if 'bump_restricted_channel' in settings:
                del settings['bump_restricted_channel']
                self._save_settings(settings)
            await ctx.send("✅ Bump channel restriction removed.")
            return
            
        # Otherwise, parse it as time
        total_seconds = 0
        h_match = re.search(r'(\d+)\s*h', arg, re.IGNORECASE)
        m_match = re.search(r'(\d+)\s*m', arg, re.IGNORECASE)
        
        if h_match:
            total_seconds += int(h_match.group(1)) * 3600
        if m_match:
            total_seconds += int(m_match.group(1)) * 60
            
        if total_seconds > 0:
            settings = self._load_settings()
            settings['next_bump_time'] = time.time() + total_seconds
            settings['bump_channel'] = ctx.channel.id
            self._save_settings(settings)
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            await ctx.send(f"✅ I have manually synced the bump timer! I will remind you to bump again in {hours}h {minutes}m.")
        else:
            await ctx.send("❌ Invalid time format! Please use `1h 46m` or `#channel` to restrict.")

    @commands.command(aliases=['sb'])
    @commands.has_permissions(administrator=True)
    async def setbump(self, ctx, *, arg: str):
        """Manually sets the bump reminder timer OR sets the restricted bump channel."""
        allowed, restricted_id = self._is_allowed_channel(ctx)
        if not allowed:
            await ctx.reply(f"I am restricted to <#{restricted_id}> only", silent=True)
            return
            
        await self._do_setbump(ctx, arg, check_admin=False)

    @commands.Cog.listener()
    async def on_message(self, message):
        # Allow prefix-less commands if in restricted bump channel
        if not message.author.bot:
            settings = self._load_settings()
            restricted = settings.get('bump_restricted_channel')
            if restricted and message.channel.id == restricted:
                content_lower = message.content.strip().lower()
                if content_lower in ("bs", "bumpstatus"):
                    ctx = await self.bot.get_context(message)
                    await self._do_bumpstatus(ctx)
                    return
                elif content_lower.startswith("sb ") or content_lower.startswith("setbump "):
                    prefix_len = 3 if content_lower.startswith("sb ") else 8
                    arg = message.content.strip()[prefix_len:].strip()
                    ctx = await self.bot.get_context(message)
                    await self._do_setbump(ctx, arg, check_admin=True)
                    return
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
                    restricted = settings.get('bump_restricted_channel')
                    if restricted and message.channel.id != restricted:
                        return # Ignore bumps outside restricted channel
                    
                    # Store the channel ID and the timestamp when the next bump is due
                    settings['next_bump_time'] = time.time() + self.bump_duration
                    settings['bump_channel'] = message.channel.id
                    self._save_settings(settings)
                    
                    await message.channel.send("⏱️ **Bump detected!** I will remind you to bump again in exactly 2 hours.")
                # Check for cooldown message
                elif "wait another" in description.lower():
                    settings = self._load_settings()
                    restricted = settings.get('bump_restricted_channel')
                    if restricted and message.channel.id != restricted:
                        return # Ignore cooldowns outside restricted channel
                        
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
                    ping_text = f"<@&{role_id}>" if role_id else ""
                    embed = discord.Embed(
                        title="⏰ BUMP TIME! ⏰",
                        description="It's time to bump the server again!\nPlease use the `/bump` command to bump the server on Disboard.",
                        color=0x2b2d31  # Discord dark theme color to look clean
                    )
                    await channel.send(content=ping_text, embed=embed)
                
                # Clear the reminder
                settings['next_bump_time'] = None
                self._save_settings(settings)

    @check_bump.before_loop
    async def before_check_bump(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BumpReminder(bot))
