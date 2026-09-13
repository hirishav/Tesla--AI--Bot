import discord
from discord.ext import commands
import json
import os
import re
import asyncio

SETTINGS_FILE = 'settings.json'

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    def _parse_time(self, time_str):
        time_str = time_str.lower()
        if time_str == 'permanent':
            return None
            
        total_seconds = 0
        s_match = re.search(r'(\d+)\s*s', time_str)
        m_match = re.search(r'(\d+)\s*m', time_str)
        h_match = re.search(r'(\d+)\s*h', time_str)
        d_match = re.search(r'(\d+)\s*d', time_str)
        
        if s_match: total_seconds += int(s_match.group(1))
        if m_match: total_seconds += int(m_match.group(1)) * 60
        if h_match: total_seconds += int(h_match.group(1)) * 3600
        if d_match: total_seconds += int(d_match.group(1)) * 86400
        
        return total_seconds if total_seconds > 0 else None

    def _format_message(self, message, member):
        msg = message.replace('{user.mention}', member.mention)
        msg = msg.replace('{user.name}', member.name)
        msg = msg.replace('{server.name}', member.guild.name)
        msg = msg.replace('{member.count}', str(member.guild.member_count))
        return msg

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Manage the welcome messages."""
        embed = discord.Embed(title="Welcome Commands", color=0x2b2d31)
        embed.add_field(name="`tesla welcome setup <#channel> <time> <message...>`", value="Set up the welcome message.\n*Time options:* `5s`, `1m`, `1h`, `1d`, or `permanent`\n*Placeholders:* `{user.mention}`, `{user.name}`, `{server.name}`, `{member.count}`", inline=False)
        embed.add_field(name="`tesla welcome view`", value="View current welcome settings.", inline=False)
        embed.add_field(name="`tesla welcome test`", value="Send a test welcome message.", inline=False)
        embed.add_field(name="`tesla welcome disable`", value="Turn off welcome messages.", inline=False)
        embed.add_field(name="`tesla welcome edit msg <message...>`", value="Edit just the welcome message text.", inline=False)
        embed.add_field(name="`tesla welcome edit time <time>`", value="Edit just the auto-delete time.", inline=False)
        embed.add_field(name="`tesla welcome edit channel <#channel>`", value="Edit just the welcome channel.", inline=False)
        await ctx.send(embed=embed)

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, channel: discord.TextChannel, time_str: str, *, message: str):
        """Set up the welcome message system."""
        delete_after = self._parse_time(time_str)
        if delete_after is None and time_str.lower() != 'permanent':
            await ctx.send("❌ Invalid time format! Use `5s`, `1m`, `1d`, or `permanent`.")
            return

        settings = self._load_settings()
        if 'welcome' not in settings:
            settings['welcome'] = {}
            
        settings['welcome']['channel_id'] = channel.id
        settings['welcome']['delete_after'] = delete_after
        settings['welcome']['message'] = message
        self._save_settings(settings)
        
        await ctx.send(f"✅ Welcome message configured in {channel.mention}!\nAuto-delete: **{'Permanent' if delete_after is None else f'{delete_after} seconds'}**")

    @welcome.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def edit(self, ctx):
        """Edit specific parts of the welcome config."""
        await ctx.send("Use `tesla welcome edit msg`, `edit time`, or `edit channel`.")

    @edit.command(name="msg")
    @commands.has_permissions(administrator=True)
    async def edit_msg(self, ctx, *, message: str):
        """Edit the welcome message text."""
        settings = self._load_settings()
        if 'welcome' not in settings:
            await ctx.send("❌ Welcome system is not configured yet! Use `tesla welcome setup` first.")
            return
            
        settings['welcome']['message'] = message
        self._save_settings(settings)
        await ctx.send("✅ Welcome message text updated!")

    @edit.command(name="time")
    @commands.has_permissions(administrator=True)
    async def edit_time(self, ctx, time_str: str):
        """Edit the auto-delete time."""
        settings = self._load_settings()
        if 'welcome' not in settings:
            await ctx.send("❌ Welcome system is not configured yet!")
            return
            
        delete_after = self._parse_time(time_str)
        if delete_after is None and time_str.lower() != 'permanent':
            await ctx.send("❌ Invalid time format! Use `5s`, `1m`, `1d`, or `permanent`.")
            return
            
        settings['welcome']['delete_after'] = delete_after
        self._save_settings(settings)
        await ctx.send(f"✅ Welcome auto-delete time updated to: **{'Permanent' if delete_after is None else f'{delete_after} seconds'}**")

    @edit.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def edit_channel(self, ctx, channel: discord.TextChannel):
        """Edit the welcome channel."""
        settings = self._load_settings()
        if 'welcome' not in settings:
            await ctx.send("❌ Welcome system is not configured yet!")
            return
            
        settings['welcome']['channel_id'] = channel.id
        self._save_settings(settings)
        await ctx.send(f"✅ Welcome channel updated to {channel.mention}!")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def view(self, ctx):
        """View the current welcome settings."""
        settings = self._load_settings()
        welcome_cfg = settings.get('welcome')
        
        if not welcome_cfg:
            await ctx.send("❌ Welcome system is currently disabled or not set up.")
            return
            
        channel = self.bot.get_channel(welcome_cfg.get('channel_id'))
        channel_name = channel.mention if channel else "Unknown Channel"
        delete_after = welcome_cfg.get('delete_after')
        time_display = "Permanent" if delete_after is None else f"{delete_after} seconds"
        message = welcome_cfg.get('message', 'No message set')
        
        embed = discord.Embed(title="Welcome Settings", color=0x2b2d31)
        embed.add_field(name="Channel", value=channel_name, inline=True)
        embed.add_field(name="Auto-Delete", value=time_display, inline=True)
        embed.add_field(name="Message", value=f"```\n{message}\n```", inline=False)
        await ctx.send(embed=embed)

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        """Disable the welcome system."""
        settings = self._load_settings()
        if 'welcome' in settings:
            del settings['welcome']
            self._save_settings(settings)
            await ctx.send("✅ Welcome system has been disabled.")
        else:
            await ctx.send("It's already disabled.")

    @welcome.command()
    @commands.has_permissions(administrator=True)
    async def test(self, ctx):
        """Test the welcome message."""
        settings = self._load_settings()
        welcome_cfg = settings.get('welcome')
        
        if not welcome_cfg:
            await ctx.send("❌ Welcome system is not configured!")
            return
            
        channel = self.bot.get_channel(welcome_cfg.get('channel_id'))
        if not channel:
            await ctx.send("❌ Configured welcome channel not found.")
            return
            
        msg_text = self._format_message(welcome_cfg.get('message', ''), ctx.author)
        delete_after = welcome_cfg.get('delete_after')
        
        await ctx.send("Sending test message...")
        try:
            await channel.send(content=msg_text, delete_after=delete_after)
        except Exception as e:
            await ctx.send(f"❌ Failed to send welcome message: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        settings = self._load_settings()
        welcome_cfg = settings.get('welcome')
        
        if not welcome_cfg:
            return
            
        channel_id = welcome_cfg.get('channel_id')
        if not channel_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
            
        msg_text = self._format_message(welcome_cfg.get('message', ''), member)
        delete_after = welcome_cfg.get('delete_after')
        
        try:
            await channel.send(content=msg_text, delete_after=delete_after)
        except Exception as e:
            print(f"Error sending welcome message: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))
