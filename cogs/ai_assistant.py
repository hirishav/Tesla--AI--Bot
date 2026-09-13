import discord
from discord.ext import commands
from groq import AsyncGroq  # type: ignore
from config import GROQ_API_KEY
import asyncio
import time
import json

class AIAssistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configure Groq API
        if GROQ_API_KEY:
            self.client = AsyncGroq(api_key=GROQ_API_KEY)
            self.model_name = 'openai/gpt-oss-120b'
            self.system_instruction = (
                "You are Tesla, a helpful, multilingual Discord AI assistant. "
                "Always answer in the exact same language and script the user asks you in. "
                "If the user writes in Hinglish, reply in Hinglish using the English alphabet. "
                "CRITICAL FORMATTING RULES: "
                "1. You MUST use standard Discord Markdown (e.g., **bold**, *italics*, `code`). "
                "2. For code blocks, you MUST use triple backticks (```) followed by the language name. DO NOT escape backticks with slashes. "
                "3. NEVER use HTML tags (like <br> or <b>) under any circumstances. "
                "You can play music if asked. If asked about your creator, say: 'Rishav, my dad, my god, my idol, my developer'."
            )
            
            # Groq uses OpenAI's tool format
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "play_music",
                        "description": "Plays a song in the voice channel the user is currently in. Use this when the user asks you to play music or a song.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "song_name": {
                                    "type": "string",
                                    "description": "The name of the song to play"
                                }
                            },
                            "required": ["song_name"]
                        }
                    }
                }
            ]
        else:
            self.client = None
            print("WARNING: GROQ_API_KEY is not set. AI features will not work.")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return

        # Check if the bot is mentioned in the message
        if self.bot.user.mentioned_in(message):
            # Owner can use the bot anywhere
            if message.author.id != self.bot.owner_id:
                restricted_id = getattr(self.bot, 'settings', {}).get('restricted_channel')
                if restricted_id and message.channel.id != restricted_id:
                    await message.reply(f"I am restricted to <#{restricted_id}> only", silent=True)
                    return

            if not self.client:
                await message.reply("Sorry, my AI capabilities are currently offline (Missing API Key).")
                return

            # Remove the bot mention from the message content so the AI just sees the prompt
            prompt = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            # If the user only pinged the bot with no message
            if not prompt:
                await message.reply("Hello! I am Tesla. How can I help you today? Ask me anything in any language!")
                return

            try:
                # Send an initial message to show we're thinking
                sent_messages = [await message.reply("🤔 Thinking...")]
                
                messages = [
                    {"role": "system", "content": self.system_instruction},
                    {"role": "user", "content": prompt}
                ]
                
                full_text = ""
                last_edit_time = time.time()
                tool_calls_accumulator = {}
                
                # Generate streaming response using async generator
                response_stream = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=True,
                    tools=self.tools,
                    temperature=0.7
                )
                
                async for chunk in response_stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                if tc.index not in tool_calls_accumulator:
                                    tool_calls_accumulator[tc.index] = {"name": tc.function.name, "arguments": ""}
                                if tc.function.arguments:
                                    tool_calls_accumulator[tc.index]["arguments"] += tc.function.arguments
                        
                        elif delta.content:
                            full_text += delta.content
                            
                            # Only edit message every 1.5 seconds to avoid Discord rate limits
                            current_time = time.time()
                            if current_time - last_edit_time > 1.5:
                                chunks = [full_text[i:i+1900] for i in range(0, len(full_text), 1900)]
                                
                                # Create new messages if we need more chunks
                                while len(sent_messages) < len(chunks):
                                    # Edit the previous message one last time to ensure it's complete before moving on
                                    if len(sent_messages) > 0 and len(chunks) > 1:
                                        await sent_messages[-1].edit(content=chunks[len(sent_messages)-1])
                                    sent_messages.append(await message.channel.send("..."))
                                    
                                # Edit the last message with the latest chunk
                                if chunks:
                                    await sent_messages[-1].edit(content=chunks[-1])
                                    
                                last_edit_time = current_time

                # Check if we accumulated any tool calls
                if tool_calls_accumulator:
                    for tc_idx, tc_data in tool_calls_accumulator.items():
                        if tc_data["name"] == "play_music":
                            args_str = tc_data["arguments"]
                            try:
                                args = json.loads(args_str)
                                song_name = args.get("song_name")
                                if song_name:
                                    full_text += f"\n🎵 I will now play **{song_name}** for you!"
                                    
                                    chunks = [full_text[i:i+1900] for i in range(0, len(full_text), 1900)]
                                    while len(sent_messages) < len(chunks):
                                        sent_messages.append(await message.channel.send("..."))
                                    await sent_messages[-1].edit(content=chunks[-1])
                                    
                                    # Get the music cog and invoke play
                                    music_cog = self.bot.get_cog("Music")
                                    if music_cog:
                                        ctx = await self.bot.get_context(message)
                                        self.bot.loop.create_task(ctx.invoke(music_cog.play, query=song_name))
                            except json.JSONDecodeError:
                                print(f"Error parsing tool call args: {args_str}")
                else:
                    # Final edit to ensure the complete message is sent
                    if full_text:
                        chunks = [full_text[i:i+1900] for i in range(0, len(full_text), 1900)]
                        while len(sent_messages) < len(chunks):
                            sent_messages.append(await message.channel.send("..."))
                        
                        # Update all chunks to ensure nothing is missed
                        for i, chunk in enumerate(chunks):
                            if i < len(sent_messages):
                                await sent_messages[i].edit(content=chunk)
                    
            except Exception as e:
                print(f"Error generating AI response: {e}")
                await message.reply(f"I encountered an error while trying to process your request. Please try again later.")

async def setup(bot):
    await bot.add_cog(AIAssistant(bot))
