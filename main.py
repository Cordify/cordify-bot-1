import discord
from discord import FFmpegPCMAudio
from discord.utils import get
import discord.utils
from discord.ext import commands, tasks
from discord.ext.commands import command
from discord.ext.commands import has_permissions, MissingPermissions
from discord import Embed, Member
from typing import Optional

import asyncio
import aiohttp
import sqlite3
import datetime

import datetime as dt
import random

import config

import socket
import threading

import os

import youtube_dl
import traceback, os, json
from youtube_search import YoutubeSearch

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename

def get_url(url):
    if "www.youtube.com" not in url:
        search = url
        yt = YoutubeSearch(search, max_results=1).to_json()
        try:
            yt_id = str(json.loads(yt)['videos'][0]['id'])
            yt_url = 'https://www.youtube.com/watch?v='+yt_id
            print(yt_url)
            url = yt_url
        except Exception as e:
            print(e)
    return url

def updatejson():
    import time
    while True:
        #print(config.user_dict)
        f = open('playlists.json', 'w')
        json.dump(config.user_dict, f,indent = 4)
        f.close()
        print("Updated playlist json")
        time.sleep(10.0)

TOKEN=config.TOKEN

intents = discord.Intents().all()
client=commands.Bot(command_prefix=["cd!","CD!","cD!","Cd!"], intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    guilds = len(list(client.guilds))
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"{len(client.guilds)} servers!"))

@client.event
async def on_message(message):
    if message.author.id != client.id and not message.author.bot:
        print(message.content)
    await client.process_commands(message)

@client.command()
@commands.is_owner()
async def invite(ctx):
    '''Get the invite link'''
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Invite Link"
    em.description="Click on the link to Invite Me"
    em.url = "https://discord.com/api/oauth2/authorize?client_id=880672701646258196&permissions=8&scope=bot"
    em.set_author(name="Cordify 1")
    await ctx.send(embed=em)

@client.command(aliases=['connect'])
async def join(ctx):
    '''Join a voice channel'''
    print("Connecting to voice channel")
    voice_client = ctx.message.guild.voice_client
    if ctx.author.voice is None:
        await ctx.send("❌ You are not connected to a voice channel.")
        return
    try:
        if voice_client.is_playing():
            await ctx.send("Sorry The bot is playing something on another channel")
            return
    except Exception as e:
        print(e)
    if ctx.guild.id not in config.queue_dict.keys():
        config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
    config.queue_dict[ctx.guild.id]['queue'] = []
    config.queue_dict[ctx.guild.id]['names'] = []
    config.queue_dict[ctx.guild.id]['pos'] = 0
    config.queue_dict[ctx.guild.id]['pause'] = 0
    config.queue_dict[ctx.guild.id]['stop'] = 1
    config.queue_dict[ctx.guild.id]['loop'] = 0
    channel = ctx.message.author.voice.channel
    #print(channel)
    voice = get(client.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await ctx.send(f"✔ Connected successfully.")
        await voice.move_to(channel)
    else:
        await ctx.send(f"✔ Connected successfully.")
        voice = await channel.connect()

@client.command(aliases=['sp','savep'])
async def saveplaylist(ctx,*,name:str):
    '''Save the current queue as a playlist'''
    if ctx.guild.id in config.queue_dict.keys():
        if str(ctx.author.id) not in config.user_dict.keys():
            config.user_dict[str(ctx.author.id)] = []
        for i in range(len(config.user_dict[str(ctx.author.id)])):
            if name == config.user_dict[str(ctx.author.id)][i]['playlistname']:
                await ctx.send('A playlist with the same name exists')
                return
        d = {'playlistname':"",'queue':[],'names':[]}
        d['playlistname'] = name
        d['queue'] = config.queue_dict[ctx.guild.id]['queue']
        d['names'] = config.queue_dict[ctx.guild.id]['names']
        print("Adding playlist "+ name +" to user id -",str(ctx.author.id))
        config.user_dict[str(ctx.author.id)].append(d)
        await ctx.send("Saved the current playlist with the name **{}**".format(name))
    else:
        await ctx.send("Please create a queue then create a playlist")

@client.command(aliases=['rp','removep'])
async def removeplaylist(ctx,*,name:str):
    '''Remove the playlist from your playlists'''
    if str(ctx.author.id) not in config.user_dict.keys():
        await ctx.send("You don't have a playlist")
        return
    pop = -1
    for i in range(len(config.user_dict[str(ctx.author.id)])):
        if name == config.user_dict[str(ctx.author.id)][i]['playlistname']:
            pop = i
            break
    config.user_dict[str(ctx.author.id)].pop(i)
    await ctx.send("Removed the playlist with the name **{}**".format(name))

@client.command(aliases=['vp'])
async def viewplaylist(ctx,*,name:str=""):
    '''Show your playlists'''
    if str(ctx.author.id) not in config.user_dict.keys():
        await ctx.send("Please create a queue then create a playlist")
        return
    if name != "":
        for i in range(len(config.user_dict[str(ctx.author.id)])):
            if name == config.user_dict[str(ctx.author.id)][i]['playlistname']:
                names = config.user_dict[str(ctx.author.id)][i]['names']
                song_names = ""
                for j in range(len(names)):
                    song_names+= '**{}** \t {}\n'.format((j+1),names[j])
                color_choice = random.choice(config.color_list)
                #print(color_list.index(color_choice))
                em = discord.Embed(color = color_choice)
                em.title = name
                em.description = str(song_names)
                await ctx.send(embed=em)
                return
        color_choice = random.choice(config.color_list)
        #print(color_list.index(color_choice))
        em = discord.Embed(color = color_choice)
        em.title = name
        em.description = "No playlist with the name **{}**".format(name)
        await ctx.send(embed=em)
        return
    names = ""
    for i in range(len(config.user_dict[str(ctx.author.id)])):
        names = names + config.user_dict[str(ctx.author.id)][i]['playlistname'] +"\n"
    names = names.strip("\n")
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Saved Playlists"
    em.description = names
    await ctx.send(embed=em)

@client.command(aliases=['q'])
async def queue(ctx):
    '''Shows the current queue'''
    queue = ""
    current = ""
    if ctx.guild.id in config.queue_dict.keys():
        if len(config.queue_dict[ctx.guild.id]['names']) != 0:
            for i in range(len(config.queue_dict[ctx.guild.id]['names'])):
                name = config.queue_dict[ctx.guild.id]['names'][i]
                if i == (int(config.queue_dict[ctx.guild.id]['pos']) - 1):
                    current = '**Current Song:** \t {} \t {}'.format((i+1),name)
                #queue+= str(i+1) + "\t"+ name + '\n'
                queue+= '**{}** \t {}\n'.format((i+1),name)
    if queue == "":
        queue = "No songs in the Queue. Use play command to add songs to queue."
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = current
    em.description = queue
    await ctx.send(embed=em)
    #await ctx.send(queue)

@client.command(aliases=['np'])
async def nowPlaying(ctx):
    '''Shows the current playing song'''
    current = ""
    try:
        pos = int(config.queue_dict[ctx.guild.id]['pos']) - 1
    except Exception as e:
        print(e)
        current = "No song playing. Use play command to add songs to queue."
        color_choice = random.choice(config.color_list)
        #print(color_list.index(color_choice))
        em = discord.Embed(color = color_choice)
        em.title = "Now Playing"
        em.description = current
        await ctx.send(embed=em)
        return
    if pos >= len(config.queue_dict[ctx.guild.id]['queue']) or len(config.queue_dict[ctx.guild.id]['queue']) <= 0:
        current = "No song playing. Use play command to add songs to queue."
        color_choice = random.choice(config.color_list)
        #print(color_list.index(color_choice))
        em = discord.Embed(color = color_choice)
        em.title = "Now Playing"
        em.description = current
        await ctx.send(embed=em)
        return
    #pos = int(config.queue_dict[ctx.guild.id]['pos'])
    name = config.queue_dict[ctx.guild.id]['names'][pos]
    current = '**Current Song:** \t {}'.format(name)
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Now Playing"
    em.description = current
    await ctx.send(embed=em)

@client.command(aliases=['lp'])
async def loop(ctx):
    '''Loop the current queue'''
    if config.queue_dict[ctx.guild.id]['loop'] == 1:
        config.queue_dict[ctx.guild.id]['loop'] = 0
        await ctx.send("Removed the loop")
    else:
        config.queue_dict[ctx.guild.id]['loop'] = 1
        await ctx.send("Looped")

async def queue_play(ctx,url,voice_channel):
    while config.queue_dict[ctx.guild.id]['pos'] <= len(config.queue_dict[ctx.guild.id]['queue']):
        #print(config.queue_dict[ctx.guild.id])
        #print("playing songs guild -",ctx.guild.id)
        if config.queue_dict[ctx.guild.id]['loop'] == 1 and config.queue_dict[ctx.guild.id]['pos'] >= len(config.queue_dict[ctx.guild.id]['queue']):
                config.queue_dict[ctx.guild.id]['pos'] = 0
        if config.queue_dict[ctx.guild.id]['stop'] == 1:
            break
        if (config.queue_dict[ctx.guild.id]['pos'] >= len(config.queue_dict[ctx.guild.id]['queue']) and voice_channel.is_playing() == False):
            break
        if voice_channel.is_playing() == False and config.queue_dict[ctx.guild.id]['pause'] == 0:
            #pass
            #print("Already playing a song in the channel", ctx.guild.id)
            async with ctx.typing():
                message = await ctx.send("Downloading new song")
                try:
                    print("Queue Position ",config.queue_dict[ctx.guild.id]['pos'])
                    url = config.queue_dict[ctx.guild.id]['queue'][config.queue_dict[ctx.guild.id]['pos']]
                    name = config.queue_dict[ctx.guild.id]['names'][config.queue_dict[ctx.guild.id]['pos']]
                    filename = await YTDLSource.from_url(url, loop=client.loop)
                    voice_channel.play(discord.FFmpegPCMAudio(executable=config.ffmpeg_path, source=filename))
                except Exception as e:
                    print (e)
                except IndexError as e:
                    print(e)
                    config.queue_dict[ctx.guild.id] = config.default_dict
                    await message.delete()
                    break
                await message.delete()
                color_choice = random.choice(config.color_list)
                #print(color_list.index(color_choice))
                em = discord.Embed(color = color_choice)
                em.title = "Playing"
                em.description = '**Now playing:** {}'.format(name)
            await ctx.send(embed=em)
            #config.queue_dict[ctx.guild.id].pop(0)
            config.queue_dict[ctx.guild.id]['pos']+= 1
            if config.queue_dict[ctx.guild.id]['loop'] == 1 and config.queue_dict[ctx.guild.id]['pos'] >= len(config.queue_dict[ctx.guild.id]['queue']):
                config.queue_dict[ctx.guild.id]['pos'] = 0
            print("Playing Song")
        await asyncio.sleep(5)

@client.command(aliases=['p'])
async def play(ctx,*,url:str):
    '''Play songs'''
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client

        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}

        url = get_url(url)
        if voice_channel.is_playing() or config.queue_dict[ctx.guild.id]['pause'] == 1:
            if ctx.guild.id not in config.queue_dict.keys():
                config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
            with youtube_dl.YoutubeDL(config.ydl_opts) as ydl:
                meta = ydl.extract_info(url, download=False)
            config.queue_dict[ctx.guild.id]['queue'].append(url)
            config.queue_dict[ctx.guild.id]['names'].append(meta['title'])
            color_choice = random.choice(config.color_list)
            #print(color_list.index(color_choice))
            em = discord.Embed(color = color_choice)
            em.title = "Addition to the Queue"
            em.description = '**Added to the Queue:** {}'.format(meta['title'])
            await ctx.send(embed=em)
            #await ctx.send("**Added to queue:** {}".format(meta['title']))
        else:
        #async with ctx.typing():
            if ctx.guild.id not in config.queue_dict.keys():
                config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
            with youtube_dl.YoutubeDL(config.ydl_opts) as ydl:
                meta = ydl.extract_info(url, download=False)
            config.queue_dict[ctx.guild.id]['queue'].append(url)
            config.queue_dict[ctx.guild.id]['names'].append(meta['title'])
            if len(config.queue_dict[ctx.guild.id]['queue']) != 0:
                #config.queue_dict[ctx.guild.id]['pos'] = 0
                config.queue_dict[ctx.guild.id]['stop'] = 0
                await asyncio.ensure_future(queue_play(ctx,url,voice_channel))
    except Exception as e:
        print(e)
        await ctx.send("The bot is not connected to a voice channel.")

@client.command(aliases=['pp'])
async def playPlaylist(ctx,*,name:str):
    '''Play playlist songs'''
    try:
        server = ctx.message.guild
        voice_channel = server.voice_client
        names = []
        queue = []
        f = 0
        voice_client = ctx.message.guild.voice_client
        if str(ctx.author.id) not in config.user_dict.keys():
            await ctx.send("You don't have a playlist yet")
            return
        for i in range(len(config.user_dict[str(ctx.author.id)])):
            if name == config.user_dict[str(ctx.author.id)][i]['playlistname']:
                await ctx.send('Found playlist with the same name')
                names = config.user_dict[str(ctx.author.id)][i]['names']
                queue = config.user_dict[str(ctx.author.id)][i]['queue']
                f = 1
                break
        print(names)
        print(queue)
        if f == 0:
            await ctx.send('No playlist found with the above name')
            return
        if len(names) == 0 or len(queue) == 0:
            await ctx.send('Playlist is empty')
            return
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        config.queue_dict[ctx.guild.id]['queue'] = []
        config.queue_dict[ctx.guild.id]['names'] = []
        config.queue_dict[ctx.guild.id]['pos'] = 0
        config.queue_dict[ctx.guild.id]['pause'] = 0
        config.queue_dict[ctx.guild.id]['stop'] = 1
        config.queue_dict[ctx.guild.id]['loop'] = 0
        if voice_client.is_playing():
            voice_client.stop()
        config.queue_dict[ctx.guild.id]['queue'].extend(queue)
        config.queue_dict[ctx.guild.id]['names'].extend(names)
        url = config.queue_dict[ctx.guild.id]['queue'][0]
        if len(config.queue_dict[ctx.guild.id]['queue']) != 0:
            #config.queue_dict[ctx.guild.id]['pos'] = 0
            config.queue_dict[ctx.guild.id]['stop'] = 0
            await asyncio.ensure_future(queue_play(ctx,url,voice_channel))
    except Exception as e:
        print(e)
        await ctx.send("The bot is not connected to a voice channel.")

@client.command(aliases=["prev"])
async def previous(ctx):
    '''Go to the previous song (under testing)'''
    print("Going to the previous song")
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        if ctx.guild.id not in config.queue_dict.keys():
            await ctx.send("There is no queue. Please create a queue first.")
            return
        if config.queue_dict[ctx.guild.id]['pos'] - 2 >= 0:
            config.queue_dict[ctx.guild.id]['pos']-= 2
            voice_client.pause()
            await ctx.send("Previous song")
        else:
            await ctx.send("unable to go to previous song.")
            return
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@client.command(aliases=["next"])
async def skip(ctx,n:int = None):
    '''Skip a song (under testing)'''
    print("Skipping current song")
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        if n != None:
            num = int(n)
            if num >= len(config.queue_dict[ctx.guild.id]['queue']) and num < 0:
                await ctx.send("Invalid entry")
            else:
                config.queue_dict[ctx.guild.id]['pos'] = num
        voice_client.pause()
        await ctx.send("Skipped current song")
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@client.command()
async def remove(ctx,*,position:int):
    '''Remove a song from queue'''
    if position - 1 == config.queue_dict[ctx.guild.id]['pos'] - 1:
        await ctx.send("Cannot remove the current song")
        return
    if position - 1 >= len(config.queue_dict[ctx.guild.id]['queue']) or position - 1 < 0:
        await ctx.send("Invalid Position")
        return
    url = config.queue_dict[ctx.guild.id]['queue'].pop(position-1)
    name = config.queue_dict[ctx.guild.id]['names'].pop(position-1)
    if position - 1 <= config.queue_dict[ctx.guild.id]['pos'] - 1:
        config.queue_dict[ctx.guild.id]['pos']-= 1
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Reduction to the Queue"
    em.description = '**Removed from the Queue:** {}'.format(name)
    await ctx.send(embed=em)
    #await ctx.send("**Removed from queue:** {}".format(name))

@client.command(aliases=['mv','MV'])
async def move(ctx,*,pos:str):
    '''Move a song in the queue add , in between the positions'''
    raw_pos = pos
    raw_pos1 = raw_pos.strip().split(',')
    pos1 = int(raw_pos1[0].strip())
    pos2 = int(raw_pos1[1].strip())
    if pos1 - 1 == config.queue_dict[ctx.guild.id]['pos'] - 1 or pos1 - 1 == config.queue_dict[ctx.guild.id]['pos'] - 1:
        await ctx.send("Cannot move the current songs")
        return
    if (pos1 - 1 >= len(config.queue_dict[ctx.guild.id]['queue']) or pos1 - 1 < 0):
        await ctx.send("Invalid Position 1")
        return
    if (pos2 - 1 >= len(config.queue_dict[ctx.guild.id]['queue']) or pos2 - 1 < 0):
        await ctx.send("Invalid Position 2")
        return
    config.queue_dict[ctx.guild.id]['queue'][pos1-1],config.queue_dict[ctx.guild.id]['queue'][pos2-1] = config.queue_dict[ctx.guild.id]['queue'][pos2-1] , config.queue_dict[ctx.guild.id]['queue'][pos1-1]
    config.queue_dict[ctx.guild.id]['names'][pos1-1],config.queue_dict[ctx.guild.id]['names'][pos2-1] = config.queue_dict[ctx.guild.id]['names'][pos2-1] , config.queue_dict[ctx.guild.id]['names'][pos1-1]
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Swapped Songs in the Queue"
    em.description = '**Swapped in the Queue:** {} \t {}'.format(pos1,pos2)
    await ctx.send(embed=em)

@client.command()
async def pause(ctx):
    '''Pause songs'''
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        config.queue_dict[ctx.guild.id]['pause'] = 1
        voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@client.command()
async def resume(ctx):
    '''Resume songs'''
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        config.queue_dict[ctx.guild.id]['pause'] = 0
        config.queue_dict[ctx.guild.id]['pos']-= 1
        voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use play command")

@client.command()
async def stop(ctx):
    '''Stop playing songs and reset the queue'''
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        config.queue_dict[ctx.guild.id]['queue'] = []
        config.queue_dict[ctx.guild.id]['names'] = []
        config.queue_dict[ctx.guild.id]['pos'] = 0
        config.queue_dict[ctx.guild.id]['pause'] = 0
        config.queue_dict[ctx.guild.id]['stop'] = 1
        config.queue_dict[ctx.guild.id]['loop'] = 0
        voice_client.stop()
    else:
        config.queue_dict[ctx.guild.id]['queue'] = []
        config.queue_dict[ctx.guild.id]['names'] = []
        config.queue_dict[ctx.guild.id]['pos'] = 0
        config.queue_dict[ctx.guild.id]['pause'] = 0
        config.queue_dict[ctx.guild.id]['stop'] = 1
        config.queue_dict[ctx.guild.id]['loop'] = 0
        await ctx.send("The bot is not playing anything at the moment.")

@client.command(aliases=["dc","disconnect"])
async def leave(ctx):
    '''Leave a voice channel'''
    print("Disconnecting from voice channel")
    voice_client = ctx.message.guild.voice_client
    if ctx.guild.id not in config.queue_dict.keys():
        config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
    config.queue_dict[ctx.guild.id]['queue'] = []
    config.queue_dict[ctx.guild.id]['names'] = []
    config.queue_dict[ctx.guild.id]['pos'] = 0
    config.queue_dict[ctx.guild.id]['pause'] = 0
    config.queue_dict[ctx.guild.id]['stop'] = 1
    config.queue_dict[ctx.guild.id]['loop'] = 0
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if ctx.voice_client is None:
        await ctx.send("❌ I am not connected to any voice channel.")
        return
    if voice_client.is_playing():
        if ctx.guild.id not in config.queue_dict.keys():
            config.queue_dict[ctx.guild.id] = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
        config.queue_dict[ctx.guild.id]['queue'] = []
        config.queue_dict[ctx.guild.id]['names'] = []
        config.queue_dict[ctx.guild.id]['pos'] = 0
        config.queue_dict[ctx.guild.id]['pause'] = 0
        config.queue_dict[ctx.guild.id]['stop'] = 1
        config.queue_dict[ctx.guild.id]['loop'] = 0
        voice_client.stop()
    await ctx.send("✔ Disconnected successfully")
    await ctx.voice_client.disconnect()

@client.command()
@commands.has_role("Cordify Manager")
async def mute(ctx):
    '''Force Server Mute Users'''
    if ctx.author.voice is None:
        await ctx.send("❌ You are not connected to a voice channel.")
        return
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if config.debug == True:
        print(ctx)
    members = channel.members
    member_name = []
    for member in members:
        if str(member.id) != config.BOT_ID and str(member.id) != config.OWNER_ID:
            member_name.append(member.name)
            user_obj = await ctx.guild.fetch_member(member.id)
            await user_obj.edit(mute=True)
            await ctx.send("Muted "+"<@"+str(member.id)+">")
    if config.debug == True:
        print("Muting")
        print(member_name)

@client.command()
@commands.has_role("Cordify Manager")
async def unmute(ctx):
    '''Force Server Unmute Users'''
    if ctx.author.voice is None:
        await ctx.send("❌ You are not connected to a voice channel.")
        return
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)
    if config.debug == True:
        print(ctx)
    members = channel.members
    member_name = []
    for member in members:
        if str(member.id) != config.BOT_ID and str(member.id) != config.OWNER_ID:
            member_name.append(member.name)
            user_obj = await ctx.guild.fetch_member(member.id)
            await user_obj.edit(mute=False)
            await ctx.send("Unmuted "+"<@"+str(member.id)+">")
    if config.debug == True:
        print("UnMuting")
        print(member_name)

@client.command()
async def ping(ctx):
    '''Pong! Get the bot's response time'''
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Pong!"
    em.description = f'{client.latency * 1000} ms'
    await ctx.send(embed=em)

@client.command(aliases = ['AV','av'])
async def avatar(ctx, avamember : discord.Member=None):
    '''Show User Avatar'''
    userAvatarUrl = avamember.avatar_url
    color_choice = random.choice(config.color_list)
    #print(color_list.index(color_choice))
    em = discord.Embed(color = color_choice)
    em.title = "Avatar"
    em.description = f'Avatar of {avamember}'
    em.set_image(url = userAvatarUrl)
    #await ctx.send(userAvatarUrl)
    await ctx.send(embed=em)

@client.command(aliases=["memberinfo", "ui", "mi"])
async def userinfo(ctx, target: Optional[Member]):
    '''Get User Info'''
    target = target or ctx.author
    from datetime import datetime
    color_choice = random.choice(config.color_list)
    embed = Embed(title="User information",
                  colour=color_choice,
                  timestamp=datetime.utcnow())

    embed.set_thumbnail(url=target.avatar_url)

    fields = [("Name", str(target), True),
              ("ID", target.id, True),
              ("Bot?", target.bot, True),
              ("Top role", target.top_role.mention, True),
              ("Status", str(target.status).title(), True),
              ("Activity", f"{str(target.activity.type).split('.')[-1].title() if target.activity else 'N/A'} {target.activity.name if target.activity else ''}", True),
              ("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
              ("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
              ("Boosted", bool(target.premium_since), True)]

    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed)

@client.command(aliases=["guildinfo", "si", "gi"])
async def serverinfo(ctx):
    '''Get Server Info'''
    from datetime import datetime
    color_choice = random.choice(config.color_list)
    embed = Embed(title="Server information",
                  colour=color_choice,
                  timestamp=datetime.utcnow())

    embed.set_thumbnail(url=ctx.guild.icon_url)

    statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

    fields = [("ID", ctx.guild.id, True),
              ("Owner", ctx.guild.owner, True),
              ("Region", ctx.guild.region, True),
              ("Created at", ctx.guild.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
              ("Members", len(ctx.guild.members), True),
              ("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
              ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
              ("Banned members", len(await ctx.guild.bans()), True),
              ("Statuses", f"🟢 {statuses[0]} 🟠 {statuses[1]} 🔴 {statuses[2]} ⚪ {statuses[3]}", True),
              ("Text channels", len(ctx.guild.text_channels), True),
              ("Voice channels", len(ctx.guild.voice_channels), True),
              ("Categories", len(ctx.guild.categories), True),
              ("Roles", len(ctx.guild.roles), True),
              ("Invites", len(await ctx.guild.invites()), True),
              ("\u200b", "\u200b", True)]

    for name, value, inline in fields:
        embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed)

def json_check(verification_skip):
    if os.path.exists("playlists.json"):
        try:
            f = open('playlists.json','r')
            config.user_dict = json.load(f)
            print("Json loaded from file")
            total = 0
            fail = 0
            if verification_skip != True:
                for user in config.user_dict.keys():
                    playlists = config.user_dict[user]
                    for p in playlists:
                        queue = p['queue']
                        name = p['names']
                        for i in range(len(queue)):
                            verified_name = ""
                            total+= 1
                            url = queue[i]
                            song_name = name[i]
                            try:
                                with youtube_dl.YoutubeDL(config.ydl_opts) as ydl:
                                    meta = ydl.extract_info(url, download=False)
                                verified_name = meta['title']
                            except Exception as e:
                                print("Error",e)
                            if verified_name != song_name:
                                fail+= 1
                print(f"Integrity score - {((total-fail)*100)/total}%")
            #print(config.user_dict.keys())
            f.close()
        except Exception as e:
            print(e)
    else:
        f = open("playlists.json", "w")
        f.close()

print ("Execution Started")
print("Checking Playlist Json for Integrity")
verification_skip = False
json_check(verification_skip)
print("Playlist Json Verified")

play_thread = threading.Thread(target=updatejson)
play_thread.start()

print ("All Checks done starting Bot")
client.run(TOKEN[::-1],bot=True,reconnect=True)
