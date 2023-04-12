import discord
from discord.ext import commands
from pytube import YouTube
from youtubesearchpython import VideosSearch
import os
import asyncio

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # uvloop is not installed, will use default asyncio event loop

TOKEN = os.environ['DISCORD_BOT_TOKEN']

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

queues = {}

async def join_voice_channel(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be connected to a voice channel to use this command.")
        return

    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    else:
        await ctx.voice_client.move_to(channel)

async def play_audio(ctx, url):
    video = YouTube(url)
    stream = video.streams.get_audio_only()
    url2 = stream.url

    ctx.voice_client.stop()

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ctx.voice_client.play(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS, executable="ffmpeg"), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_async(ctx, e), bot.loop))

    ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=0.5)
    await ctx.send(f'Now playing: {video.title}')

async def play_next(ctx, e):
    await ctx.invoke(ctx.bot.get_command("play_next"))

async def play_next_async(ctx, e):
    await play_next(ctx)

@bot.command()
async def play_next(ctx):
    if len(queues[ctx.guild.id]) > 0:
        url = queues[ctx.guild.id].pop(0)
        await play_audio(ctx, url)

@bot.command()
async def join(ctx):
    await join_voice_channel(ctx)

@bot.command()
async def play(ctx, *, query):
    query_string = query
    results = VideosSearch(query_string, limit=1).result()
    url = f"https://www.youtube.com/watch?v={results['result'][0]['id']}"

    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await join_voice_channel(ctx) # Make sure the bot is connected to the voice channel before playing
        await play_audio(ctx, url)
    else:
        queues[ctx.guild.id].append(url)
        await ctx.send(f"Added to queue: {results['result'][0]['title']}")

@bot.command()
async def stop(ctx):
    ctx.voice_client.stop()

@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()

@bot.command()
async def next(ctx):
    await play_next(ctx)

@bot.command()
async def previous(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await play_audio(ctx, queues[ctx.guild.id].pop())

@bot.command()
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Paused")

@bot.command()
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Resumed")

@bot.command()
async def volume(ctx, volume: int):
    if ctx.voice_client is not None:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Volume set to {volume}%")

@bot.command()
async def help(ctx):
    help_message = (
        "```\n"
        "!join          - Makes the bot join your voice channel\n"
        "!play [query]  - Plays a song from YouTube based on the search query\n"
        "!stop          - Stops the currently playing song\n"
        "!leave         - Makes the bot leave the voice channel\n"
        "!next          - Skips the current song and plays the next in the queue\n"
        "!previous      - Plays the last song\n"
        "!pause         - Pauses the currently playing song\n"
        "!resume        - Resumes the paused song\n"
        "!volume [0-100]- Sets the volume of the bot (0-100)\n"
        "!help          - Lists all available commands\n"
        "```")
    await ctx.send(help_message)

bot.run(TOKEN)
