
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import random

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.messages = True 

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': False}

class RadioBratva(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.voice_clients = {}
        self.previous_track = None  # Variable to store the last played track
        self.repeat_count = 0  # Variable to store the repeat count

    @app_commands.command(name="play", description="Adiciona uma música à fila e toca se não estiver tocando nada.")
    async def play(self, interaction: discord.Interaction, search: str, repeat_count: int = 1):
        await interaction.response.send_message("Processando sua solicitação, por favor aguarde...", ephemeral=True)

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None
        if not voice_channel:
            return await interaction.edit_original_response(content="Você não está em um canal de voz!")

        if not interaction.guild.voice_client:
            self.voice_clients[interaction.guild.id] = await voice_channel.connect()

        async with interaction.channel.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info['url']
                    title = info['title']
                    
                    # Store the previous track's information and the repeat count
                    self.previous_track = {'url': url, 'title': title}
                    self.repeat_count = repeat_count

                    # Add the track to the queue and start playback
                    self.queue.append(url)
                    await self.play_next(interaction)

                except Exception as e:
                    await interaction.edit_original_response(content=f"Erro ao tocar música: {str(e)}")

    async def play_next(self, interaction):
        if self.queue:
            url = self.queue.pop(0)
            voice_client = self.voice_clients[interaction.guild.id]

            def after_playing(error):
                if error:
                    print(f"Erro ao tocar música: {error}")

                # Check repeat count and re-queue if necessary
                if self.repeat_count > 1:
                    self.queue.insert(0, url)  # Reinsert the URL to play it again
                    self.repeat_count -= 1

            # Play the audio file
            voice_client.play(discord.FFmpegPCMAudio(url), after=after_playing)
            await interaction.edit_original_response(content=f"Tocando agora: {self.previous_track['title']} (repetir {self.repeat_count - 1}x restantes)")

    @app_commands.command(name="repeat", description="Reproduz a última música tocada.")
    async def repeat(self, interaction: discord.Interaction, repeat_count: int = 1):
        if self.previous_track:
            self.queue = [self.previous_track['url']] * repeat_count + self.queue  # Insert the previous track multiple times at the start of the queue
            await self.play_next(interaction)
            await interaction.response.send_message(f"Reproduzindo {self.previous_track['title']} {repeat_count} vezes.")
        else:
            await interaction.response.send_message("Nenhuma música foi tocada ainda!", ephemeral=True)

# Assuming bot setup code is here
