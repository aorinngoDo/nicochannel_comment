#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pkgutil import extend_path
import sys
import os
import re
import requests
import json
import dateutil.parser as dp
import argparse

ua='Mozilla/5.0'

if __name__=='__main__' :
    parser = argparse.ArgumentParser(description='nicochannel.jp comment downloader.', add_help=True)
    parser.add_argument('video_url', help='Video URL.')
    parser.add_argument('-o', '--output', help='Output directory / filename.')
    parser.add_argument('--allowbrokentimestamp', action='store_true', help='Save comments that may have broken timestamps. It is recommended to add this option for videos longer than 8 hours.')
    args = parser.parse_args()

    # Check Video URL
    if re.compile('nicochannel.jp/[^/]+/video/[0-9A-Za-z]+$').search(args.video_url) :
        vid = re.search('[0-9A-Za-z]+$',args.video_url).group()
    else :
        print('ERROR! / Argument. (VIDEO_URL) Usage: nicochannel_comment.py VIDEO_URL')
        sys.exit(1)

    # Check Output
    try :
        output = os.path.abspath(args.output)
    except TypeError as e :
        print(e + 'ERROR! / Output path format is incorrect.')
        exit(1)

    if os.path.isdir(output) :
        os.chdir(output)
    elif os.path.isdir(os.path.dirname(output)) :
        os.chdir(os.path.dirname(output))
        if output.split(".")[-1] == ".xml" :
            filename = os.path.basename(output)
        else :
            filename = os.path.basename(output) + '.xml'
    else :
        print('ERROR! / Output directory is not found.')
        sys.exit(1)

# Get Video Info
headers = {'User-Agent': ua, 'Origin': 'https://nicochannel.jp', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}
video_data_req = requests.get('https://nfc-api.nicochannel.jp/fc/video_pages/' + vid, headers=headers)
try :
    video_data_req_response = video_data_req.raise_for_status()
except Exception as e :
    print(e + 'ERROR! / Could not get video information. Video URL may be incorrect.')
    sys.exit(1)

video_data = json.loads(video_data_req.text)
comment_group_id = str(video_data.get('data', {}).get('video_page', {}).get('video_comment_setting', {}).get('comment_group_id'))
if comment_group_id == 'None' :
    print('ERROR! / Could not get comment group information.')
    sys.exit(1)

print(comment_group_id)

oldest_time = str(video_data.get('data', {}).get('video_page', {}).get('live_started_at'))
if oldest_time == 'None' :
    oldest_time = str(video_data.get('data', {}).get('video_page', {}).get('released_at'))

if not re.compile('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$').search(oldest_time) :
    print('ERROR! / Could not get time information.')
    sys.exit(1)
oldest_time = re.sub(' (\d{2}:\d{2}):\d{2}$', 'T\\1:00.000Z', oldest_time)

title = str(video_data.get('data', {}).get('video_page', {}).get('title'))


# Get User Access Token
headers = {'User-Agent': ua, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Origin': 'https://nicochannel.jp', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}
user_token_req = requests.get('https://nfc-api.nicochannel.jp/fc/video_pages/' + vid + '/comments_user_token', headers=headers)
try :
    user_token_req_response = user_token_req.raise_for_status()
except Exception :
    print('ERROR! / Could not get user token.')
    sys.exit(1)

user_token_data = json.loads(user_token_req.text)
user_token = str(user_token_data.get('data', {}).get('access_token'))
if user_token == 'None' :
    print('ERROR! / Could not get user token data.')
    sys.exit(1)

# Get Comments
headers = {'User-Agent': ua, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Origin': 'https://nicochannel.jp', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'cross-site'}
post_json = {'token': user_token,'group_id': comment_group_id}

try :
    filename
except NameError:
    filename = title + '.xml'

filename = filename.translate(str.maketrans({'\"': '_', '\'': '_', '<': '_', '>': '_', '\\': '_', '/': '_', ':': '_', '|': '_', '?': '_', '*': '_'}))

try :
    f = open(filename, 'x', encoding='UTF-8')
except FileExistsError :
    print('ERROR! / Comments file Exists.')
    sys.exit(1)

f.write('<?xml version="1.0" encoding="UTF-8"?>\n<packet>\n')

while True :
    comments_req = requests.post('https://comm-api.sheeta.com/messages.history?limit=120&oldest=' + oldest_time + '&sort_direction=asc', headers=headers, json=post_json)
    try :
        comments_req_response = comments_req.raise_for_status()
    except Exception :
        print('ERROR! / Could not get comments file! Deleting the file...')
        f.close()
        os.remove(title + '.xml')
        sys.exit(1)

    print(oldest_time)
    comments_req_data = json.loads(comments_req.text)
    if len(comments_req_data) == 0 :
        print('Finised!')
        f.write('</packet>\n')
        f.close()
        sys.exit(0)

    for i in comments_req_data :
        created_at = str(i['created_at'])
        unix_time_sec = str(dp.parse(created_at).timestamp()).split('.')
        message = str(i['message']).translate(str.maketrans({'\"': '&quot;', '\'': '&apos;', '<': '&lt;', '<': '&gt;', '&': '&amp;'}))
        playback_time = int(i['playback_time']) * 100
        sender_id = str(i['sender_id'])
        nickname = str(i['nickname']).translate(str.maketrans({'\"': '&quot;', '\'': '&apos;', '<': '&lt;', '<': '&gt;', '&': '&amp;'}))

        # For broken time data
        if args.allowbrokentimestamp :
            f.write('<chat thread=\"' + comment_group_id + '\" vpos=\"' + str(playback_time) + '\" date=\"' + str(unix_time_sec[0]) + '\" date_usec=\"' + str(unix_time_sec[1]) + '\" user_id=\"' + sender_id + '\" name=\"' + nickname + '\">' + message + '</chat>\n')
        else :
            if playback_time < 3200000 :
                f.write('<chat thread=\"' + comment_group_id + '\" vpos=\"' + str(playback_time) + '\" date=\"' + str(unix_time_sec[0]) + '\" date_usec=\"' + str(unix_time_sec[1]) + '\" user_id=\"' + sender_id + '\" name=\"' + nickname + '\">' + message + '</chat>\n')
    oldest_time = created_at
