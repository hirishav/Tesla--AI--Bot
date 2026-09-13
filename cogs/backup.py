import discord
from discord.ext import commands, tasks
import os
import io

BACKUP_CHANNEL_ID = 1548706099153338428
FILES_TO_BACKUP = ['settings.json']

class Backup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.has_restored = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.has_restored:
            print("Attempting to restore from backup channel...")
            await self.restore_backup()
            self.has_restored = True
            
            # Start the loop after we have restored
            if not self.backup_task.is_running():
                self.backup_task.start()

    async def restore_backup(self):
        channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
        if not channel:
            print(f"Backup channel {BACKUP_CHANNEL_ID} not found.")
            return

        try:
            # Look at the last 10 messages to find the most recent backup
            async for message in channel.history(limit=10):
                if message.author.id == self.bot.user.id and message.attachments:
                    restored_any = False
                    for attachment in message.attachments:
                        if attachment.filename in FILES_TO_BACKUP:
                            # Download and save the file
                            file_data = await attachment.read()
                            with open(attachment.filename, 'wb') as f:
                                f.write(file_data)
                            print(f"Restored {attachment.filename} from backup.")
                            restored_any = True
                    
                    if restored_any:
                        # Reload settings into bot memory if needed
                        if hasattr(self.bot, 'settings'):
                            try:
                                import json
                                with open('settings.json', 'r') as f:
                                    self.bot.settings = json.load(f)
                            except Exception as e:
                                print(f"Error reloading settings into bot memory: {e}")
                                
                        print("Backup restoration complete.")
                        return # Only restore from the newest backup message, then stop
            print("No backups found in the channel.")
        except Exception as e:
            print(f"Failed to restore backup: {e}")

    @tasks.loop(minutes=10)
    async def backup_task(self):
        channel = self.bot.get_channel(BACKUP_CHANNEL_ID)
        if not channel:
            return

        files = []
        for filename in FILES_TO_BACKUP:
            if os.path.exists(filename):
                files.append(discord.File(filename))

        if files:
            try:
                # Optionally delete older backup messages to keep channel clean
                # We won't delete right away to keep a small history, but we can purge old ones.
                # Actually, let's just send the new one.
                await channel.send(content="🔄 Automatic Backup", files=files)
                print("Successfully uploaded backup.")
            except Exception as e:
                print(f"Failed to upload backup: {e}")

    def cog_unload(self):
        self.backup_task.cancel()

async def setup(bot):
    await bot.add_cog(Backup(bot))
