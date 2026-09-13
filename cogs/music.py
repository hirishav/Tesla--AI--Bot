import discord
from discord.ext import commands
import yt_dlp
import asyncio
import imageio_ffmpeg

# Get the bundled ffmpeg executable path
FFMPEG_EXECUTABLE = imageio_ffmpeg.get_ffmpeg_exe()

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda *args, **kwargs: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android']
        }
    }
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            if not data['entries']:
                raise Exception("No search results found.")
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_EXECUTABLE, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx):
        """Joins a voice channel"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                await channel.connect()
            else:
                if not ctx.voice_client.is_connected():
                    await ctx.voice_client.disconnect(force=True)
                    await channel.connect()
                elif ctx.voice_client.channel != channel:
                    await ctx.voice_client.move_to(channel)
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command()
    async def play(self, ctx, *, query):
        """Plays a url or search query"""
        async with ctx.typing():
            if not ctx.author.voice:
                await ctx.send("❌ You are not connected to a voice channel.")
                return
                
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                try:
                    await channel.connect()
                except Exception as e:
                    await ctx.send(f"❌ Could not connect to the voice channel: {e}")
                    return
            else:
                if not ctx.voice_client.is_connected():
                    try:
                        await ctx.voice_client.disconnect(force=True)
                        await channel.connect()
                    except Exception as e:
                        await ctx.send(f"❌ Could not reconnect to the voice channel: {e}")
                        return
                elif ctx.voice_client.channel != channel:
                    try:
                        await ctx.voice_client.move_to(channel)
                    except Exception as e:
                        await ctx.send(f"❌ Could not move to the voice channel: {e}")
                        return

        # Stop currently playing audio
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        try:
            player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            await ctx.send(f'🎵 Now playing: **{player.title}**')
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command()
    async def leave(self, ctx):
        """Stops and disconnects the bot from voice"""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected from voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
