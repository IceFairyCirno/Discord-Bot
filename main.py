import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import json
import yt_dlp
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER_ID = int(os.getenv('SERVER_ID'))
GUILD_ID = discord.Object(id=SERVER_ID)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True
}

class Client(commands.Bot):

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        try:
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f'Synced {len(synced)} command(s) to guild {GUILD_ID.id}')
        except Exception as e:
            print(f'Failed to sync commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.content in ['hello', 'hi', 'hey', "Hello", "Hi", "Hey"]:
            await message.channel.send(f'Hi there {(message.author).mention}!')
        if message.content in ['nigga', 'nigger', "Nigger", "Nigga"]:
            await message.channel.send(f'https://tenor.com/view/plane-angry-man-kick-of-plane-gif-21332726')

        await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send('You reacted')

    async def on_member_join(self, member):
        server_id = member.guild.id
        if not os.path.exists(f'{server_id}.json'):
            with open(f'{server_id}.json', 'w') as f:
                json.dump({'greeting_channel': None}, f)
        with open(f'{server_id}.json', 'r') as f:
            data = json.load(f)
        Greeting_Channel = member.guild.get_channel(data['greeting_channel'])
        if Greeting_Channel is not None:
            embed = discord.Embed(title=f"A New Member Has Joined!", 
                                  description=f"Welcome to the server, {member.mention}!\nEnjoy your stay in the Gensokyo!",
                                  color=discord.Color.green())
            embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
            await Greeting_Channel.send(embed=embed)
        else:
            return

intents = discord. Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

client = Client(command_prefix="!", intents=intents)

@client.tree.command(name="check", description="check the online status", guild=GUILD_ID)
async def check(interaction: discord.Interaction):
    await interaction.response.send_message("I'm here!")

@client.tree.command(name="info", description="Return the server info", guild=GUILD_ID)
async def info(interaction: discord.Interaction):
    await interaction.response.send_message(f"Server: {interaction.guild.name}\nMembers: {interaction.guild.member_count}")

@client.tree.command(name="set_welcome_channel", description="Return the server info", guild=GUILD_ID)
async def select_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.send_message(f"You selected {channel.mention} as the greeting channel.")
    server_id = interaction.guild.id
    if not os.path.exists(f'{server_id}.json'):
        with open(f'{server_id}.json', 'w') as f:
            json.dump({'greeting_channel': channel.id}, f)
    else:
        with open(f'{server_id}.json', 'r') as f:
            data = json.load(f)
        data['greeting_channel'] = channel.id
        with open(f'{server_id}.json', 'w') as f:
            json.dump(data, f)

@client.tree.command(name="play", description="Play music from URL", guild=GUILD_ID)
async def play(interaction: discord.Interaction, url: str):
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
        return

    # Get the voice channel of the user
    voice_channel = interaction.user.voice.channel

    # Connect to the voice channel if not already connected
    if not interaction.guild.voice_client:
        await voice_channel.connect()
    # If already connected to a different channel, move to the user's channel
    elif interaction.guild.voice_client.channel != voice_channel:
        await interaction.guild.voice_client.move_to(voice_channel)

    # Get the voice client
    voice = interaction.guild.voice_client

    # If already playing, stop the current audio
    if voice.is_playing():
        voice.stop()

    # Defer the response to allow time for processing
    await interaction.response.defer()

    # Extract audio info using yt_dlp in a separate thread
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
    audio_url = info['url']

    # Create audio source
    source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)

    # Play the audio
    voice.play(source)

    # Send an embed with the song title and thumbnail
    thumbnail_url = (
        f"https://img.youtube.com/vi/{info['id']}/maxresdefault.jpg" or
        f"https://img.youtube.com/vi/{info['id']}/sddefault.jpg" or
        f"https://img.youtube.com/vi/{info['id']}/hqdefault.jpg" or
        info.get('thumbnail')
    )
    
    if thumbnail_url:
        embed = discord.Embed(title="Now Playing:", description=info.get('title', 'Unknown Title'), color=discord.Color.green())
        embed.set_thumbnail(url=thumbnail_url)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Now playing: {info.get('title', url)}")

@client.tree.command(name="pause", description="Pause current music", guild=GUILD_ID)
async def pause(interaction: discord.Interaction):
    if not interaction.guild.voice_client:
        await interaction.response.send_message("Not playing anything.", ephemeral=True)
        return

    voice = interaction.guild.voice_client

    if voice.is_playing():
        voice.pause()
        await interaction.response.send_message("Paused")
    elif voice.is_paused():
        await interaction.response.send_message("Already paused.", ephemeral=True)
    else:
        await interaction.response.send_message("Nothing is playing.", ephemeral=True)

@client.tree.command(name="resume", description="Resume paused music", guild=GUILD_ID)
async def resume(interaction: discord.Interaction):
    if not interaction.guild.voice_client:
        await interaction.response.send_message("Not in voice channel.", ephemeral=True)
        return

    voice = interaction.guild.voice_client

    if voice.is_paused():
        voice.resume()
        await interaction.response.send_message("Resumed")
    else:
        await interaction.response.send_message("Not paused.", ephemeral=True)

if __name__ == "__main__":
    client.run(TOKEN)