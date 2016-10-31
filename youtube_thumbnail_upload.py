#!/usr/bin/python3
#
# Kleines Helferskript das ich zusammen mit Mr Moe auf der SUBSCRIBE8 geschrieben habe. 
# Es läd z.B. die PNGs vom Intro Generator als Thumnails für Youtube hoch  --Andi, Oktober 2016


import logging, requests, json
import youtube_client
import configparser




logger = logging.getLogger()

def main():    
    config = configparser.ConfigParser()
    config.read('client.conf')
    
    ticket = {}
    ticket['Publishing.YouTube.Token'] = config['youtube']['cleanup_tool_token']
    
    conference_slug = 'subscribe8'  # see tracker project
    
    yt = youtube_client.YoutubeAPI(ticket, config['youtube']) 

    r = requests.get('https://tracker.c3voc.de/api/v1/' + conference_slug + '/tickets/released.json')
    videos = r.json()

    i = 0
    for video_file in videos:
        if video_file['youtube_url']:
           i = i+1
           #print(video_file)
           print(video_file['youtube_url'])
           videoId = video_file['youtube_url'].split('=', 2)[1]

           yt.update_thumbnail(videoId, "thumbs/%d.ts.png" % video_file['fahrplan_id'])
           # break # comment this line for production mode, uncomment for debugging with one item

    #print( "%i of %i published files (including webm and audio releases) are on youtube" % (i, len(videos)) )


if __name__ == "__main__":
    main()