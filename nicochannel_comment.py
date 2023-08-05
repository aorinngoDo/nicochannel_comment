import argparse
import logging
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from xml.dom import minidom

import dateutil.parser as dp
import prompt_toolkit as pt
import requests
from pathvalidate import sanitize_filename


def setup_logger(verbose=False) -> logging.Logger :
    """画面に出力されるログを設定します.

    Args:
        verbose (bool, optional): verboseオプション. 
        指定された(True)場合はdebugレベルまで出力されます. 
        指定されない(False)場合はinfoレベルまで出力されます. 
        デフォルト値は False.

    Returns:
        logging.Logger: ロガー
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    return logging.getLogger(__name__)

def parse_args() -> tuple[argparse.Namespace, logging.Logger]:
    """コマンドライン引数をパースします.

    Returns:
        tuple[argparse.Namespace, logging.Logger]: 引数, ロガー
    """
    parser = argparse.ArgumentParser(description='nicochannel.jp comment(s) downloader.', add_help=True)
    parser.add_argument('nico_url', help='Video URL or Channel URL.', nargs='?', default=None)
    parser.add_argument('-v','--verbose', action='store_true', help="Verbose log output")
    parser.add_argument('-o', '--output', help='Output directory / filename.')
    parser.add_argument('--allow-broken-timestamp', action='store_true', help='Save comments that may have broken timestamps. It is recommended to add this option for videos longer than 8 hours.')
    args = parser.parse_args()
    logger = setup_logger(args.verbose)
    return args, logger

def check_video_url(video_url: str) -> str:
    """動画URLの正当性をチェックします.

    Args:
        video_url (str): ニコニコチャンネルプラスの動画URL

    Returns:
        str: 動画URLの動画ID
    """
    video_url_match = re.search(r'nicochannel.jp/[^/]+/video/([0-9A-Za-z]+)$', video_url)

    if video_url_match:
        video_id = video_url_match.group(1)
    else :
        logger.debug(f'{video_url=} は正しいフォーマットではないようです.')
        return False

    return str(video_id)

def check_channel_url(channel_url: str) -> str:
    """チャンネルURLの正当性をチェックします.

    Args:
        channel_url (str): ニコニコチャンネルプラスのチャンネルURL

    Returns:
        str: チャンネルURLのチャンネルID
    """
    channel_url_match = re.search(r'nicochannel.jp/([0-9A-Za-z\-]+)/*$', channel_url)
    if channel_url_match:
        channel_id = channel_url_match.group(1)
    else :
        logger.debug(f'{channel_url=} は正しいフォーマットではないようです.')
        return False
    return str(channel_id)

def check_output_dir(output_dir: str) -> str:
    """出力先ディレクトリの正当性をチェックします.

    Args:
        output_dir (str): 出力先ディレクトリ

    Returns:
        str: 絶対パスでの出力先ディレクトリ
    """
    try:
        output_dir = os.path.abspath(output_dir)
    except TypeError as e:
        logger.debug(e)
        return None
    logger.debug(f'{output_dir=}')
    if os.path.isdir(output_dir):
        return output_dir
    else:
        logger.debug(f'{output_dir=} はディレクトリではありません.')
        return None

def check_output_filename(output_filename: str) -> str:
    """出力ファイル名の正当性をチェックします.

    Args:
        output_filename (str): 出力ファイル名

    Returns:
        str: 整形された出力ファイル名
    """
    try:
        output_filename = sanitize_filename(output_filename)
    except Exception as e:
        logger.debug(e)
    if not output_filename.lower().endswith('.xml'):
        output_filename = f'{output_filename}.xml'

    logger.debug(f'{output_filename=}')

    return str(output_filename)

def exists_filepath(output_filepath : str) -> bool:
    """出力先ファイルパスが存在するかチェックします.

    Args:
        output_filepath (str): 出力先ファイルパス

    Returns:
        bool: 出力先ファイルパスが存在するか否か
    """
    return os.path.exists(output_filepath)

def get_channel_fc_id(channel_id: str) -> str:
    """チャンネルIDからチャンネルのfc_idを取得します.

    Args:
        channel_id (str): ニコニコチャンネルプラスのチャンネルID

    Returns:
        str: チャンネルのfc_id
    """
    headers = {
        'authority': 'nfc-api.nicochannel.jp',
        'fc_use_device': 'null',
        'origin': 'https://nicochannel.jp',
        'referer': 'https://nicochannel.jp/',
        'user-agent': USERAGENT,
    }
    all_channel_info_resp = requests.get(f'https://nfc-api.nicochannel.jp/fc/content_providers/channels', headers=headers)
    try:
        all_channel_info_resp.raise_for_status()
        all_channel_info = all_channel_info_resp.json()
    except Exception as e:
        logger.error(f'チャンネル一覧を取得できませんでした. {e}')
        return None
    for channel_info in all_channel_info.get('data', {}).get('content_providers', []):
        if channel_info.get('domain') == f'https://nicochannel.jp/{channel_id}':
            return str(channel_info.get('fanclub_site', {}).get('id'))
    logger.error(f'チャンネルID {channel_id} が見つかりませんでした.')
    return None

def get_channel_videos_page(fc_id: str, page=1) -> list:
    """_summary_

    Args:
        fc_id (str): チャンネルのfc_id
        page (int, optional): 動画一覧のページ数. デフォルト値は 1.

    Returns:
        list: 動画一覧の情報
    """
    headers = {
        'authority': 'nfc-api.nicochannel.jp',
        'fc_use_device': 'null',
        'origin': 'https://nicochannel.jp',
        'referer': 'https://nicochannel.jp/',
        'user-agent': USERAGENT,
    }

    params = (
        ('page', page),
        ('per_page', '100'),
        ('sort', '-display_date'),
    )

    videos_resp = requests.get(f'https://nfc-api.nicochannel.jp/fc/fanclub_sites/{fc_id}/video_pages', headers=headers, params=params)
    try:
        videos_resp.raise_for_status()
        videos_data = videos_resp.json()
    except Exception as e:
        logger.error(f'チャンネル内の動画一覧を取得できませんでした. {e}')
        return None
    videos_info_list = videos_data.get('data', {}).get('video_pages', {}).get('list', [])
    return videos_info_list

def get_channel_videos_list(channel_id: str) -> list:
    """チャンネルIDからチャンネル内の動画一覧を取得します.

    Args:
        channel_id (str): ニコニコチャンネルプラスのチャンネルID

    Returns:
        list: 動画一覧の情報
    """
    fc_id = get_channel_fc_id(channel_id)
    if fc_id is None:
        return None
    videos_info_list = get_channel_videos_page(fc_id)
    return videos_info_list

def get_video_info(video_id: str) -> dict:
    """動画IDから動画情報を取得します.

    Args:
        video_id (str): ニコニコチャンネルプラスの動画ID

    Returns:
        dict: 動画情報
    """
    headers = {
        'authority': 'nfc-api.nicochannel.jp',
        'fc_use_device': 'null',
        'origin': 'https://nicochannel.jp',
        'referer': 'https://nicochannel.jp/',
        'user-agent': USERAGENT,
    }
    video_info_resp = requests.get(f'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}', headers=headers)
    try:
        video_info_resp.raise_for_status()
        video_info = video_info_resp.json()
    except Exception as e:
        logger.error(f'動画情報を取得できませんでした. {e}')
        return None
    video_title = video_info.get('data', {}).get('video_page', {}).get('title')
    if video_title is None:
        logger.error(f'{video_id=} の動画タイトルを取得できませんでした.')
        return None
    logger.info(f'{video_title} の情報を取得しました.')
    return video_info

def get_user_token(video_id: str) -> str:
    """動画IDからアクセストークンを取得します.

    Args:
        video_id (str): ニコニコチャンネルプラスの動画ID

    Returns:
        str: アクセストークン文字列
    """
    headers = {
        'authority': 'nfc-api.nicochannel.jp',
        'fc_use_device': 'null',
        'origin': 'https://nicochannel.jp',
        'referer': 'https://nicochannel.jp/',
        'user-agent': USERAGENT,
    }
    user_token_resp = requests.get(f'https://nfc-api.nicochannel.jp/fc/video_pages/{video_id}/comments_user_token', headers=headers)
    try:
        user_token_resp.raise_for_status()
        user_token_info = user_token_resp.json()
    except Exception as e:
        logger.error(f'アクセストークンを取得できませんでした. {e}')
        return None

    access_token = user_token_info.get('data', {}).get('access_token')
    if access_token is None:
        logger.error('アクセストークンを正しく取得できませんでした.')
        return None
    return access_token

def get_comments(user_token: str, comments_group_id: str, oldest_time: str) -> list:
    """指定範囲のコメントを取得します.

    Args:
        user_token (str): アクセストークン文字列
        comments_group_id (str): コメントのグループID
        oldest_time (str): 取得するコメントの最古の時間

    Returns:
        list: コメントのリスト
    """
    query = {
        "oldest": oldest_time,
        "sort_direction": "asc",
        "limit": "120",
        "inclusive": "true"
    }

    payload_json = {
        "token": user_token,
        "group_id": comments_group_id
    }

    headers = {
        "authority": "comm-api.sheeta.com",
        "content-type": "application/json",
        "fc_use_device": "null",
        "origin": "https://nicochannel.jp",
        "referer": "https://nicochannel.jp/",
        "user-agent": USERAGENT
    }

    comments_resp = requests.post('https://comm-api.sheeta.com/messages.history', json=payload_json, headers=headers, params=query)
    try:
        comments_resp.raise_for_status()
        comments_data = comments_resp.json()
    except Exception as e:
        logger.error(f'コメント取得でエラーが発生しました. {e}')
        return None
    return comments_data

def get_all_comments(user_token: str, comments_group_id: str) -> list:
    """全てのコメントを取得します.

    Args:
        user_token (str): アクセストークン文字列
        comments_group_id (str): コメントのグループID

    Returns:
        list: 全コメントのリスト
    """
    comments = []
    oldest_time = 0
    while True:
        logger.debug(f'{oldest_time=} からコメントを取得します.')
        comments_data = get_comments(user_token, comments_group_id, oldest_time)
        if comments_data is None:
            return None
        comments.extend(comments_data)
        logger.debug(f'{len(comments_data)} コメントを取得しました.')
        logger.info(f'現在 {len(comments)} 個のコメントを取得済み')
        if len(comments_data) < 120:
            break
        oldest_time = comments_data[-1]['created_at']
        oldest_time_dt = datetime.strptime(oldest_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        new_oldest_time_dt = oldest_time_dt + timedelta(milliseconds=1)
        oldest_time = new_oldest_time_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return comments

def remove_control_characters(_s: str) -> str:
    """制御文字を削除します.

    Args:
        _s (str): 制御文字が含まれる可能性のある文字列

    Returns:
        str: 制御文字を削除した文字列
    """
    return "".join(ch for ch in _s if unicodedata.category(ch)[0]!="C")

def all_download_confirm_dialog() -> bool:
    """チャンネルURLが入力された場合の確認ダイアログを表示します.

    Returns:
        bool: 全動画のコメントダウンロードするか否か
    """
    result = pt.shortcuts.yes_no_dialog(
        title='ダウンロード確認',
        text='チャンネルURLが入力されたようです. 全ての動画コメントをダウンロードしますか?').run()
    return result

def output_filepath_input_dialog(filepath=None) -> str:
    """出力先ファイルパスを入力するダイアログを表示します.

    Args:
        filepath (str, optional): 出力先のファイルパス候補. デフォルト値は None.

    Returns:
        str: 入力された出力先ファイルパス
    """
    output_filepath = pt.shortcuts.input_dialog(
        title='出力先ファイルパス',
        text='出力先ファイルパスを入力してください. 上下キーで補完できます.',
        completer=pt.completion.PathCompleter(only_directories=True),
        default=(filepath if filepath else '')
        ).run()
    return output_filepath

def url_input_dialog() -> str:
    """URLを入力するダイアログを表示します.

    Returns:
        str: 入力されたURL
    """
    url = pt.shortcuts.input_dialog(
        title='URLを入力',
        text='ニコニコチャンネルプラスのチャンネルURL もしくは 動画URL').run()
    if url is None or url == '':
        return None
    return str(url)

def download_checkbox_dialog(video_list: list) -> list:
    """ダウンロードする動画を選択するダイアログを表示します.

    Args:
        video_list (list): チャンネル内の動画一覧

    Returns:
        list: ダウンロードする動画の, 動画IDのリスト
    """
    result = pt.shortcuts.checkboxlist_dialog(
        title='ダウンロードする動画を選択',
        text='コメントをダウンロードする動画を選択してください.',
        values=[(video.get("content_code"), video.get("title")) for video in video_list]
        ).run()
    return result

def comments_to_tree(comments_list: list, comment_group_id: str) -> ET.Element:
    """コメントのリストをXMLツリーに変換します.

    Args:
        comments_list (list): コメントのリスト
        comment_group_id (str): コメントのグループID

    Returns:
        ET.Element: 変換されたコメントのXMLツリー
    """
    # packet にコメント情報が入る
    packet = ET.Element('packet')
    for comment in comments_list:
        created_at = str(comment['created_at'])
        unix_time_sec = str(dp.parse(created_at).timestamp()).split('.')[0]
        message = remove_control_characters(str(comment['message']))
        playback_time = (int(comment['playback_time']) * 100)
        sender_id = str(comment['sender_id'])
        nickname = remove_control_characters(str(comment['nickname']))

        # タイムスタンプ破損によるコメントのスキップ
        if not args.allow_broken_timestamp and playback_time > 3200000:
            logger.warning('コメントのタイムスタンプが破損している可能性があるため,スキップされたコメントがあります。保存するには --allow-broken-timestamp オプションを指定してください.')
            continue

        ET.SubElement(
            packet,
            'chat',
            {
                'thread': comment_group_id,
                'vpos': str(playback_time),
                'date': unix_time_sec,
                'user_id': sender_id,
                'name': nickname}
        ).text = message
    return packet

def comments_file_save(packet: ET.Element, filename: str) -> None:
    """コメントのXMLツリーをファイルに保存します.

    Args:
        packet (ET.Element): コメントのXMLツリー
        filename (str): 保存するファイル名
    """
    tree = minidom.parseString(ET.tostring(packet, 'utf-8'))
    with open(filename,'w', encoding='utf-8') as f:
        tree.writexml(f, encoding='utf-8', newl='\n', indent='')
    logger.info(f'{filename} にコメントを保存しました.')

if __name__ == "__main__":
    USERAGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

    args, logger = parse_args()

    if args.nico_url is None:
        nico_url = url_input_dialog()
        if nico_url is None:
            logger.error('URLが入力されませんでした.')
            sys.exit(1)
    else:
        nico_url = args.nico_url

    channel_id = check_channel_url(nico_url)
    video_id = check_video_url(nico_url)

    if channel_id:
        videos_info_list = get_channel_videos_list(channel_id)
        channel_all_download = all_download_confirm_dialog()
        if channel_all_download:
            videos_id_list = [video.get('content_code') for video in videos_info_list]
        else:
            videos_id_list = download_checkbox_dialog(videos_info_list)
    elif video_id:
        videos_id_list = [video_id]
    else:
        logger.error(f'{nico_url=} は正しいURLフォーマットではないようです.')
        sys.exit(1)

    if videos_id_list is None:
        logger.error('ダウンロード対象が指定されていないようです.')
        sys.exit(1)

    for video_id in videos_id_list:
        video_info = get_video_info(video_id)

        default_output_dir = os.path.dirname(os.path.abspath(__file__))
        default_output_filename = video_info.get('data', {}).get('video_page', {}).get('title', '') + '.xml'
        default_output_filename = check_output_filename(default_output_filename)

        if args.output:
            try:
                output_filename = os.path.abspath(args.output)
            except TypeError as e:
                logger.debug(e)
                output_filename = os.path.join(default_output_dir, default_output_filename)
        else:
            output_filename = output_filepath_input_dialog(os.path.join(default_output_dir, default_output_filename))

        if output_filename is None:
            logger.warning('出力先ファイルパスが入力されていないため, デフォルト値を使用します.')
            output_filename = os.path.join(default_output_dir, default_output_filename)
        elif check_output_dir(output_filename):
            output_filename = os.path.join(output_filename, default_output_filename)
        elif check_output_dir(os.path.dirname(output_filename)):
            output_filename = os.path.join(os.path.dirname(output_filename), check_output_filename(os.path.basename(output_filename)))
        else:
            logger.warning('出力先ファイルパスが正しくないため, デフォルト値を使用します.')
            output_filename = os.path.join(default_output_dir, default_output_filename)


        if exists_filepath(output_filename):
            logger.info(f'{output_filename=} は既に存在します.')
            continue
        logger.info(f'{output_filename=}にコメントファイルを出力します.')

        comment_group_id = video_info.get('data', {}).get('video_page', {}).get('video_comment_setting', {}).get('comment_group_id')
        user_token = get_user_token(video_id)
        comments_list = get_all_comments(user_token, comment_group_id)
        if comments_list is None:
            logger.error(f'{video_id=} のコメントが0件, もしくは取得できませんでした.')
            continue

        comments_tree = comments_to_tree(comments_list, comment_group_id)
        comments_file_save(comments_tree, output_filename)

    logger.info('処理が完了しました.')
    sys.exit(0)
