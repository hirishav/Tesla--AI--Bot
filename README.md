# Tesla - Discord AI & Music Assistant

Tesla is a powerful, multilingual Discord AI assistant built with Discord.py, Groq API (Llama 3), and yt-dlp. It can answer complex questions, perform research, chat in multiple languages (including Hinglish), and even play high-quality audio directly into voice channels using YouTube-DL!

## Features 🚀

- **Smart AI Chat:** Powered by Groq's high-speed inference engine (Llama 3 / GPT models).
- **Multilingual Support:** Seamlessly understands and responds in multiple languages.
- **Hinglish Mode:** If you speak Hinglish, Tesla replies in natural Hinglish!
- **Music Playback:** Type `play <song name>` and Tesla will join your voice channel and stream music in high quality.
- **Tool Calling:** The AI can autonomously decide to play music for you when requested naturally in a sentence.

## Setup Instructions 🛠️

### Prerequisites

1. **Python 3.10+** installed on your system.
2. A **Discord Bot Token** (Get it from [Discord Developer Portal](https://discord.com/developers/applications)).
3. A **Groq API Key** (Get it from [Groq Console](https://console.groq.com)).

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd Tesla
   ```

2. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the root directory (where `bot.py` is located) and add your API keys:
   
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Run the bot!**
   ```bash
   python bot.py
   ```

## Usage 💡
- **Chat:** Just ping the bot (`@Tesla`) and ask anything.
- **Music:** Type `!play <song name>` or just ask the AI, e.g., `@Tesla can you play some lo-fi music for me?`
- **Leave VC:** Type `!leave` to make the bot disconnect.

## License
MIT License
