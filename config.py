TOKEN = ""
BOT_ID = ""
OWNER_ID = ""

#Debug
debug = True

#FFMPEG
ffmpeg_path = "ffmpeg"

#Music
queue_dict = {}
pause_dict = {}
queue_pos_dict = {}

user_dict = {}

ydl_opts = {
    'format': 'beataudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192'
    }]
}
states = {}
default_dict = {'queue':[],'names':[],'pos':0,'pause':0,'stop':0,'loop':0}
default_user_dict = {'playlistname':"",'queue':[],'names':[]}

#Embed
import discord
color_list = [discord.Color.green(),discord.Color.blue(),discord.Color.red(),discord.Color.teal(),discord.Color.purple(),discord.Color.gold(),discord.Color.orange(),discord.Color.blurple(),discord.Color.greyple()]
