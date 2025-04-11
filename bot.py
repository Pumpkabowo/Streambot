import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

# Set up bot and intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

streamers_file = "streamers.json"
streamers = []

# Load streamer list
async def load_streamers():
    global streamers
    if os.path.exists(streamers_file):
        with open(streamers_file, "r") as f:
            streamers = json.load(f)

# Save streamer list
async def save_streamers():
    with open(streamers_file, "w") as f:
        json.dump(streamers, f, indent=2)

# Get Twitch OAuth token
async def get_twitch_token():
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }) as resp:
            data = await resp.json()
            if "access_token" not in data:
                print("Twitch Token Error:", data)
            return data["access_token"]

# Check Twitch status
async def check_streams():
    token = await get_twitch_token()
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}"
    }

    while True:
        for streamer in streamers:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.twitch.tv/helix/streams?user_login={streamer['twitch']}"
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    is_live = len(data.get("data", [])) > 0

                    if is_live and not streamer["was_live"]:
                        stream_data = data["data"][0]
                        game = stream_data.get("game_name", "Unknown Game")
                        viewers = stream_data.get("viewer_count", 0)
                        title = stream_data.get("title", "Untitled Stream")

                        embed = discord.Embed(
                            title=f"{streamer['twitch']} is now LIVE!",
                            url=f"https://twitch.tv/{streamer['twitch']}",
                            description=(
                                f"{streamer['message']}\n\n"
                                f"[**{title}**](https://twitch.tv/{streamer['twitch']})\n\n"
                                f"Playing: **{game}**\n"
                                f"With: **{viewers}**\n\n"
                                
                                
                            ),
                            color=0x9146FF
                        )
                        embed.set_image(url=f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{streamer['twitch']}-440x248.jpg?rand={os.urandom(4).hex()}")

                        channel = bot.get_channel(streamer["discord_channel"])
                        if channel:
                            await channel.send(embed=embed)

                        streamer["was_live"] = True
                        await save_streamers()

                    elif not is_live and streamer["was_live"]:
                        streamer["was_live"] = False
                        await save_streamers()

        await asyncio.sleep(60)

# EVENTS
@bot.event
async def on_ready():
    await load_streamers()
    guild = discord.Object(id=REPLACE-WITH-SERVER-ID)  # Replace with your server ID
    try:
        await bot.tree.sync(guild=guild)
        print("✅ Slash commands re-synced to guild.")
    except Exception as e:
        print("❌ Failed to sync commands:", e)
    bot.loop.create_task(check_streams())
    print(f"Logged in as {bot.user} | Slash commands synced to specific server.")

# SLASH COMMANDS
@bot.tree.command(name="twitchadd", description="Add a streamer to list")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(username="Twitch username", message="Custom message for the alert")
async def twitchadd(interaction: discord.Interaction, username: str, message: str):
    streamers.append({
        "twitch": username.lower(),
        "discord_channel": interaction.channel_id,
        "message": message,
        "was_live": False
    })
    await save_streamers()
    await interaction.response.send_message(f"✅ Added `{username}` with message: {message}")

@bot.tree.command(name="twitchremove", description="Remove a Twitch streamer from the list")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(username="Twitch username to remove")
async def twitchremove(interaction: discord.Interaction, username: str):
    before = len(streamers)
    streamers[:] = [s for s in streamers if s["twitch"] != username.lower()]
    await save_streamers()

    if len(streamers) < before:
        await interaction.response.send_message(f"❌ Removed `{username}`")
    else:
        await interaction.response.send_message(f"⚠️ `{username}` was not found.")

@bot.tree.command(name="twitchlist", description="Lists all streamers that are on the list")
@app_commands.checks.has_permissions(administrator=True)
async def twitchlist(interaction: discord.Interaction):
    if not streamers:
        await interaction.response.send_message("📋 There are no streamers on the list")
    else:
        msg = "\n".join([f"- **{s['twitch']}** in <#{s['discord_channel']}>: {s['message']}" for s in streamers])
        await interaction.response.send_message(f"📺 Currently tracking:\n{msg}")

@bot.tree.command(name="pingme", description="Test command to confirm the bot is responsive.")
@app_commands.checks.has_permissions(administrator=True)
async def pingme(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Pong! Bot is alive and slash commands work!")

bot.run(DISCORD_TOKEN)


