#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pkgutil import extend_path
import sys
import os
import re
import requests
import json
import datetime
import dateutil.parser as dp
import argparse
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Safe Filenames
_invalid = (
        34,  # " QUOTATION MARK
        60,  # < LESS-THAN SIGN
        62,  # > GREATER-THAN SIGN
        124, # | VERTICAL LINE
        0, 1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23,
        24, 25, 26, 27, 28, 29, 30, 31,
        58, # : COLON
        42, # * ASTERISK
        63, # ? QUESTION MARK
        92, # \ REVERSE SOLIDUS
        47, # / SOLIDUS
        )

table1 = {}
for i in _invalid:
    table1[i] = 95 # LOW LINE _

table2 = dict(table1)
table2.update((
        (34, 0x201d), # ”
        (60, 0xff1c), # ＜
        (62, 0xff1e), # ＞
        (124, 0xff5c), # ｜
        (58, 0xff1a), # ：
        (42, 0xff0a), # ＊
        (63, 0xff1f), # ？
        (92, 0xffe5), # ￥
        (47, 0xff0f), # ／
        ))

def safefilenames(names, table=table1, add_table=None):
    if add_table is None:
        m = table
    else:
        m = dict(table)
        m.update(add_table)
    for name in names:
        yield name.translate(m)

def safefilename(name, table=table1, add_table=None):
    return next(safefilenames([name], table, add_table))

ua='Mozilla/5.0'

if __name__=='__main__' :
    parser = argparse.ArgumentParser(description='nicochannel.jp comment(s) downloader.', add_help=True)
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
        output = os.getcwd()

    if os.path.isdir(output) :
        os.chdir(output)
    elif os.path.isdir(os.path.dirname(output)) :
        os.chdir(os.path.dirname(output))
        if os.path.basename(output).split(".")[-1] == "xml" :
            filename = os.path.basename(output)
        else :
            filename = os.path.basename(output) + '.xml'
    else :
        print('ERROR! / Output directory is not found.')
        sys.exit(1)

# Get Video Info
headers = {'User-Agent': ua, 'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'ja', 
'Accept-Encoding': 'gzip, deflate, br', 'fc_site_id': '105', 'fc_use_device': 'null', 'Origin': 'https://nicochannel.jp', 'DNT': '1', 'Connection': 'keep-alive', 'Referer': 'https://nicochannel.jp/', 'Sec-Fetch-Dest': 'empty', 'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'same-site', 'TE': 'trailers'}
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

filename = safefilename(filename,table=table2)

if os.path.isfile(filename) :
    print('ERROR! / File exists.')
    sys.exit(1)

packet = ET.Element('packet')

print('Start saving comments ...')
print('Title:' + title)
print('Comment ID: ' + comment_group_id)

while True :
    comments_req = requests.post('https://comm-api.sheeta.com/messages.history?limit=120&oldest=' + oldest_time + '&sort_direction=asc', headers=headers, json=post_json)
    try :
        comments_req_response = comments_req.raise_for_status()
    except Exception :
        print('ERROR! / Could not get comments file.')
        sys.exit(1)

    print(oldest_time)
    comments_req_data = json.loads(comments_req.text)
    if len(comments_req_data) == 0 or len(comments_req_data) == 1 :
        tree = minidom.parseString(ET.tostring(packet, 'utf-8'))
        with open(filename,'w', encoding='utf-8') as f:
            tree.writexml(f, encoding='utf-8', newl='\n', indent='')
        print('Finished!')
        sys.exit(0)

    for i in comments_req_data :
        created_at = str(i['created_at'])
        unix_time_sec = str(dp.parse(created_at).timestamp()).split('.')
        message = str(i['message'])
        playback_time = int(i['playback_time']) * 100
        sender_id = str(i['sender_id'])
        nickname = str(i['nickname'])

        # For broken time data
        if args.allowbrokentimestamp :
            ET.SubElement(packet, 'chat', {'thread': comment_group_id, 'vpos': str(playback_time), 'date': str(unix_time_sec[0]), 'user_id': sender_id, 'name': nickname}).text = message

        elif playback_time < 3200000 :
            ET.SubElement(packet, 'chat', {'thread': comment_group_id, 'vpos': str(playback_time), 'date': str(unix_time_sec[0]), 'user_id': sender_id, 'name': nickname}).text = message

    oldest_time_datetime = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ') + datetime.timedelta(milliseconds=1)
    oldest_time = oldest_time_datetime.isoformat()[:-3] + 'Z'
