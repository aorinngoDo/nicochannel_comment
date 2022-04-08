#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import requests
import json
import dateutil.parser as dp

# Usage: nicochannel_comment.py VIDEO_URL
ua='Mozilla/5.0'

if __name__=='__main__':
    if len(sys.argv) == 2:
        video_url = sys.argv[1]
    elif len(sys.argv) == 1:
        video_url = input('Enter Video URL: ')
    else:
        print('ERROR! / Argument. (number) Usage: nicochannel_comment.py VIDEO_URL')
        sys.exit(1)

    if re.compile('nicochannel.jp/[^/]+/video/[0-9A-Za-z]+$').search(video_url):
        vid = re.search('[0-9A-Za-z]+$',video_url).group()
    else:
        print('ERROR! / Argument. (VIDEO_URL) Usage: nicochannel_comment.py VIDEO_URL')
        sys.exit(1)

# Get Video Info
headers = {'User-Agent': ua, 'Origin': 'https://nicochannel.jp', 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}
video_data_req = requests.get('https://nfc-api.nicochannel.jp/fc/video_pages/' + vid, headers=headers)
try:
    video_data_req_response = video_data_req.raise_for_status()
except Exception:
    print('ERROR! / Could not get video information. Video URL may be incorrect.')
    sys.exit(1)

video_data = json.loads(video_data_req.text)
comment_group_id = str(video_data.get('data', {}).get('video_page', {}).get('video_comment_setting', {}).get('comment_group_id'))
if comment_group_id == 'None' or comment_group_id == '':
    print('ERROR! / Could not get comment group information.')
    sys.exit(1)

print(comment_group_id)

oldest_time = str(video_data.get('data', {}).get('video_page', {}).get('live_started_at'))
if oldest_time == 'None' :
    oldest_time = str(video_data.get('data', {}).get('video_page', {}).get('released_at'))

if not re.compile('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$').search(oldest_time):
    print('ERROR! / Could not get time information.')
    sys.exit(1)
oldest_time = re.sub(' (\d{2}:\d{2}):\d{2}$', 'T\\1:00.000Z', oldest_time)

title = str(video_data.get('data', {}).get('video_page', {}).get('title'))
title = title.translate(str.maketrans({'\"': '_', '\'': '_', '<': '_', '>': '_', '\\': '_', '/': '_', ':': '_', '|': '_', '?': '_', '*': '_'}))

#print(oldest_time)

# Get User Access Token
headers = {'User-Agent': ua, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Origin': 'https://nicochannel.jp', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site'}
user_token_req = requests.get('https://nfc-api.nicochannel.jp/fc/video_pages/' + vid + '/comments_user_token', headers=headers)
try:
    user_token_req_response = user_token_req.raise_for_status()
except Exception:
    print('ERROR! / Could not get user token.')
    sys.exit(1)

user_token_data = json.loads(user_token_req.text)
user_token = str(user_token_data.get('data', {}).get('access_token'))
if user_token == 'None' or user_token == '':
    print('ERROR! / Could not get user token data.')
    sys.exit(1)

# Get Comments
headers = {'User-Agent': ua, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 'Origin': 'https://nicochannel.jp', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'cross-site'}
post_json = {'token': user_token,'group_id': comment_group_id}

try:
    f = open(title + '.xml', 'x', encoding='UTF-8')
except FileExistsError:
    print('ERROR! / Comments file Exists.')
    sys.exit(1)
f.write('<?xml version="1.0" encoding="UTF-8"?>\n<packet>\n')

while True:
    comments_req = requests.post('https://comm-api.sheeta.com/messages.history?limit=120&oldest=' + oldest_time + '&sort_direction=asc', headers=headers, json=post_json)
    try:
        comments_req_response = comments_req.raise_for_status()
    except Exception:
        print('ERROR! / Could not get comments file! Deleting the file...')
        f.close()
        os.remove(title + '.xml')
        sys.exit(1)

    print(oldest_time)
    comments_req_data = json.loads(comments_req.text)
    #print(comments_req_data)
    #stop = input('Stopping... ')
    if len(comments_req_data) == 0:
        print('Finised!')
        f.write('</packet>\n')
        f.close()
        sys.exit(0)

    for i in comments_req_data:
        created_at = str(i['created_at'])
        unix_time_sec = str(dp.parse(created_at).timestamp()).split('.')
        #print(unix_time_sec)
        #stop = input('Stopping... ')
        message = str(i['message']).translate(str.maketrans({'\"': '&quot;', '\'': '&apos;', '<': '&lt;', '<': '&gt;', '&': '&amp;'}))
        playback_time = int(i['playback_time']) * 100
        sender_id = str(i['sender_id'])
        nickname = str(i['nickname']).translate(str.maketrans({'\"': '&quot;', '\'': '&apos;', '<': '&lt;', '<': '&gt;', '&': '&amp;'}))

        # For broken time data
        if playback_time < 3200000:
            f.write('<chat thread=\"' + comment_group_id + '\" vpos=\"' + str(playback_time) + '\" date=\"' + str(unix_time_sec[0]) + '\" date_usec=\"' + str(unix_time_sec[1]) + '\" user_id=\"' + sender_id + '\" name=\"' + nickname + '\">' + message + '</chat>\n')
    oldest_time = created_at
