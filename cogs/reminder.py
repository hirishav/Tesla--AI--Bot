import discord
from discord.ext import commands
import asyncio
import json
import os
import re

REMINDERS_FILE = "reminders.json"

TIME_REGEX = re.compile(
    r'(?:(?P<months>\d+)months?)?'
    r'(?:(?P<weeks>\d+)weeks?)?'
    r'(?:(?P<days>\d+)d)?'
    r'(?:(?P<hours>\d+)h)?'
    r'(?:(?P<minutes>\d+)m)?'
    r'(?:(?P<seconds>\d+)s)?'
)

def parse_duration(time_str: str) -> float:
    match = TIME_REGEX.fullmatch(time_str.lower())
    if not match or not time_str:
        return 0.0
    
    parts = match.groupdict()
    months = int(parts.get('months') or 0)
    weeks = int(parts.get('weeks') or 0)
    days = int(parts.get('days') or 0)
    hours = int(parts.get('hours') or 0)
    minutes = int(parts.get('minutes') or 0)
    seconds = int(parts.get('seconds') or 0)
    
    return float(months * 30 * 24 * 3600 +
                 weeks * 7 * 24 * 3600 +
                 days * 24 * 3600 +
                 hours * 3600 +
                 minutes * 60 +
                 seconds)

class ReminderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = []
        self.tasks_map = {}
        self.load_reminders()
        
    def load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            try:
                with open(REMINDERS_FILE, 'r') as f:
                    self.reminders = json.load(f)
                
                # Restart all active reminders
                for idx, r in enumerate(self.reminders):
                    self.start_reminder_task(idx, r)
            except Exception as e:
                print(f"Error loading reminders: {e}")
                self.reminders = []

    def save_reminders(self):
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(self.reminders, f)

    def start_reminder_task(self, idx, reminder_data):
        channel_id = reminder_data['channel_id']
        duration = reminder_data['duration']
        target = reminder_data['target']
        reason = reminder_data['reason']
        
        async def reminder_loop():
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            channel = self.bot.get_channel(channel_id)
            
            while True:
                await asyncio.sleep(duration)
                if not channel:
                    channel = self.bot.get_channel(channel_id)
                if channel:
                    try:
                        await channel.send(f"{target} ⏰ **Reminder:** {reason}")
                    except Exception as e:
                        print(f"Failed to send reminder: {e}")
                    
        task = self.bot.loop.create_task(reminder_loop())
        self.tasks_map[idx] = task

    @commands.command(name="reminder")
    async def reminder_cmd(self, ctx, mode: str, arg2: str = None, arg3: str = None, *, reason: str = None):
        """
        Set a recurring reminder.
        """
        if mode.lower() == "list":
            if not self.reminders:
                await ctx.send("No active reminders.")
                return
            desc = ""
            for i, r in enumerate(self.reminders):
                desc += f"**ID {i}**: Every {r['duration']}s -> {r['target']} - {r['reason']}\n"
            await ctx.send(f"**Active Reminders:**\n{desc}")
            return
            
        if mode.lower() in ("stop", "remove", "delete") and arg2:
            try:
                idx = int(arg2)
                if 0 <= idx < len(self.reminders):
                    # Cancel task
                    task = self.tasks_map.get(idx)
                    if task:
                        task.cancel()
                    self.reminders.pop(idx)
                    self.save_reminders()
                    
                    # Restart remaining to keep IDs mapped correctly
                    for t in self.tasks_map.values():
                        t.cancel()
                    self.tasks_map = {}
                    for i, r in enumerate(self.reminders):
                        self.start_reminder_task(i, r)
                        
                    await ctx.send(f"✅ Reminder {idx} removed!")
                else:
                    await ctx.send("❌ Invalid reminder ID.")
            except ValueError:
                await ctx.send("❌ Invalid reminder ID.")
            return

        if mode.lower() != "every" or not arg2 or not arg3:
            await ctx.send("❌ Usage: `tesla reminder every 2h30m @role/user <Reason>`")
            return
            
        if not reason:
            reason = "No reason provided."

        duration = parse_duration(arg2)
        if duration < 10:
            await ctx.send("❌ Invalid time format or duration is less than 10 seconds. Format example: `2h30m` or `1week3d`")
            return

        # Format target mention
        target_mention = arg3
        if arg3.isdigit():
            role = ctx.guild.get_role(int(arg3))
            if role:
                target_mention = role.mention
            else:
                target_mention = f"<@{arg3}>"

        reminder_data = {
            "channel_id": ctx.channel.id,
            "duration": duration,
            "target": target_mention,
            "reason": reason
        }
        
        self.reminders.append(reminder_data)
        idx = len(self.reminders) - 1
        
        self.save_reminders()
        self.start_reminder_task(idx, reminder_data)
        
        await ctx.send(f"✅ Reminder set! I will ping {target_mention} every `{arg2}` for: **{reason}**")

async def setup(bot):
    await bot.add_cog(ReminderCog(bot))
