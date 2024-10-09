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

    @app_commands.command(name="play", description="Adiciona uma música à fila e toca se não estiver tocando nada.")
    async def play(self, interaction: discord.Interaction, search: str):
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
                    self.queue.append((url, title))
                    await interaction.edit_original_response(content=f'Adicionado à fila: {title}')
                except Exception as e:
                    await interaction.edit_original_response(content=f"Erro ao buscar a música: {e}")

        if not interaction.guild.voice_client.is_playing():
            await self.play_next(interaction)

    @app_commands.command(name="playnow", description="Toca música/playlist agora")
    async def playnow(self, interaction: discord.Interaction, musica: str):
        """Toca música/playlist agora."""
        await interaction.response.send_message("Pesquisando...", ephemeral=True)
        
        voice_channel = interaction.user.voice.channel if interaction.user.voice else None
        if not voice_channel:
            return await interaction.edit_original_response(content="Você não está em um canal de voz", ephemeral=True)

        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel.id != voice_channel.id:
                return await interaction.edit_original_response(content="Já estou sendo usado em outro canal", ephemeral=True)
        else:
            self.voice_clients[interaction.guild.id] = await voice_channel.connect()

        async with interaction.channel.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(f"ytsearch:{musica}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info['url']
                    title = info['title']

                    voice_client = interaction.guild.voice_client
                    if voice_client.is_playing():
                        voice_client.stop()

                    source = discord.FFmpegPCMAudio(url, **{'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'})
                    voice_client.play(source)

                    await interaction.edit_original_response(content=f'Música(s) adicionada(s): {title}', ephemeral=True)
                except Exception as e:
                    print(e)
                    await interaction.edit_original_response(content='Erro ao executar comando', ephemeral=True)

    @app_commands.command(name="shuffle", description="Bagunça a playlist")
    async def shuffle(self, interaction: discord.Interaction):
        """Bagunça a playlist."""
        if not self.queue:
            return await interaction.response.send_message("A fila está vazia", ephemeral=True)

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None
        if not voice_channel:
            return await interaction.response.send_message("Você não está em um canal de voz", ephemeral=True)

        if interaction.guild.voice_client and interaction.guild.voice_client.channel.id != voice_channel.id:
            return await interaction.response.send_message("Você não está no mesmo canal que o bot", ephemeral=True)

        try:
            random.shuffle(self.queue)
            await interaction.response.send_message("Playlist embaralhada", ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.response.send_message("Erro ao executar comando", ephemeral=True)

    @app_commands.command(name="skip", description="Pula a música atual.")
    async def skip(self, interaction: discord.Interaction):
        """Pula a música atual."""
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Música pulada")
        else:
            await interaction.response.send_message("Nenhuma música está tocando no momento.", ephemeral=True)

    @app_commands.command(name="clear", description="Limpa o canal de texto")
    @app_commands.default_permissions(manage_messages=True)  
    async def clear(self, interaction: discord.Interaction, quantidade: int):
        await interaction.response.send_message(f" Limpando `{quantidade}` Mensagens...", ephemeral=True)
        """Limpa o canal de texto."""
        if quantidade < 1 or quantidade > 100:
            return await interaction.response.send_message("Quantidade inválida. Por favor, insira um número entre 1 e 100.", ephemeral=True)
        
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("Você não tem permissões suficientes para usar este comando.", ephemeral=True)

        try:
            await interaction.channel.purge(limit=quantidade)
            await interaction.response.send_message(f"Limpo `{quantidade}` mensagens.", ephemeral=True)
        except Exception as e:
            print(e)
            await interaction.response.send_message("Erro ao executar comando", ephemeral=True)

    @app_commands.command(name="ping", description="Verifica se o bot está online")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong 🏓", ephemeral=True)

    @app_commands.command(name="stop", description="Interrompe o bot e desconecta o mesmo")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.send_message("Parada Forçada.", ephemeral=True)
        voice_client = interaction.guild.voice_client

        if voice_client.is_connected():
            await voice_client.disconnect() 
            self.voice_clients.pop()

    async def play_next(self, interaction: discord.Interaction):
        """Toca a próxima música na fila."""
        if self.queue:
            url, title = self.queue.pop(0)
            voice_client = interaction.guild.voice_client
            if voice_client:
                try:
                    print(f"Preparando para tocar: {title} ({url})")
                    source = discord.FFmpegPCMAudio(url, **{'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'})
                    voice_client.play(source, after=lambda _: self.bot.loop.create_task(self.play_next(interaction)))
                    await interaction.channel.send(f'Agora tocando {title}')

                    self.bot.loop.create_task(self.check_voice_inactivity(interaction.guild.id, voice_client))

                except Exception as e:
                    print(f"Erro ao tocar música: {e}")
                    await interaction.channel.send(f'Musica Substituida: {e}')

        else:
            self.bot.loop.create_task(self.check_voice_inactivity(interaction.guild.id, interaction.guild.voice_client))

    async def check_voice_inactivity(self, guild_id: int, voice_client: discord.VoiceClient):
        await asyncio.sleep(10)

        if voice_client.is_connected() and not voice_client.is_playing():
            if len(voice_client.channel.members) == 1:  
                await voice_client.disconnect()
                self.voice_clients.pop(guild_id, None)  
                print(f"Bot desconectado do canal de voz por inatividade em {voice_client.guild}")

    async def monitor_voice_channels(self):
        while True:
            for guild_id, voice_client in list(self.voice_clients.items()):
                await self.check_voice_inactivity(guild_id, voice_client)
            await asyncio.sleep(10)  

    def start_monitoring(self):
        asyncio.create_task(self.monitor_voice_channels())



async def main():
    bot = commands.Bot(command_prefix="!", intents=intents)

    await bot.add_cog(RadioBratva(bot))
    
    @bot.event
    async def on_ready():
        await bot.tree.sync()
        print(f'Tamo on carai! 💀  {bot.user}')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='Tamo on! 👽'))
        bot.get_cog("RadioBratva").start_monitoring()

        commands = await bot.tree.fetch_commands()
        print("Comandos disponíveis:")
        for command in commands:
            print(f"- {command.name}")


    TOKEN = ''  
    await bot.start(TOKEN)

asyncio.run(main())

