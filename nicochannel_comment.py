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
from prompt_toolkit.completion import PathCompleter

import sheeta_utils


class SheetaVideoCommentGetter(sheeta_utils.SheetaVideo):

    def __init__(self, url: str):
        super().__init__(url)
        self.comments_user_token = None
        self.comment_dumps = []

    def get_comments_user_token(self):
        if not self.video_info_dump:
            self.get_video_info()
        try:
            user_token_request = requests.get(f'{self.site_settings.get("api_base_url")}/video_pages/{self.video_id}/comments_user_token', headers=self.base_headers, timeout=20)
            user_token_request.raise_for_status()
            user_token_dump = user_token_request.json()
            self.comments_user_token = user_token_dump.get("data", {}).get("access_token")
            if not self.comments_user_token and not isinstance(self.comments_user_token, str):
                raise ValueError("Failed to get comments user token")
        except Exception as e:
            raise ValueError(f"Failed to get comments user token: {e}")

    def get_all_comments_list(self):

        def get_comments_single_page(oldest_playback_time):
            _query = {
                "oldest_playback_time": oldest_playback_time,
                "sort_direction": "asc",
                "limit": 500,
                "inclusive": "true"
            }

            _payload_json = {
                "token": self.comments_user_token,
                "group_id": self.video_info_dump.get("data", {}).get("video_page", {}).get("video_comment_setting", {}).get("comment_group_id")
            }

            try:
                comments_request = requests.post(f"https://comm-api.sheeta.com/messages.history", json=_payload_json, headers=self.base_headers, params=_query, timeout=20)
                comments_request.raise_for_status()
                comments_dump = comments_request.json()
                self.comment_dumps.extend(comments_dump)
                return len(comments_dump)
            except Exception as e:
                raise ValueError(f"Failed to get comments: {e}")

        def get_unique_list(_list):
            seen = []
            return [x for x in _list if x not in seen and not seen.append(x)]

        if not self.comments_user_token:
            self.get_comments_user_token()

        oldest_time = 0
        while True:
            comments_length_per_page = get_comments_single_page(oldest_time)
            if comments_length_per_page <= 1:
                break
            oldest_time = self.comment_dumps[-1].get("playback_time")


        self.comment_dumps = get_unique_list(self.comment_dumps)
        # print(f"Total comments: {len(self.comment_dumps)=} / {type(self.comment_dumps)=}")


class SheetaChannelCommentGetter(sheeta_utils.SheetaChannel):
    def __init__(self, url: str):
        super().__init__(url)


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
    parser.add_argument('-b', '--batch', action='store_true', help='Non-interactive mode. If no output is specified in the argument, the default value is used.')
    args = parser.parse_args()
    logger = setup_logger(args.verbose)
    return args, logger

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
        return ''
    logger.debug(f'{output_dir=}')
    if os.path.isdir(output_dir):
        return output_dir
    else:
        logger.debug(f'{output_dir=} はディレクトリではありません.')
        return ''

def validate_output_filename(output_filename: str) -> str:
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
        completer=PathCompleter(only_directories=True),
        default=(filepath if filepath else ''),
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
        values=video_list,
        ).run()
    return [] if result is None else result

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

    if args.nico_url is None and not args.batch:
        nico_url = url_input_dialog()
        if nico_url is None or nico_url == '':
            logger.error('URLが入力されませんでした.')
            sys.exit(1)
    elif args.nico_url is None and args.batch:
        logger.error('URLが指定されていません.')
        sys.exit(1)
    else:
        nico_url = str(args.nico_url)


    sheeta_obj = sheeta_utils.utils.get_sheeta_class(nico_url)
    if type(sheeta_obj) == sheeta_utils.SheetaVideo:
        video_obj_list = [SheetaVideoCommentGetter(nico_url)]
    elif type(sheeta_obj) == sheeta_utils.SheetaChannel:
        sheeta_obj = SheetaChannelCommentGetter(nico_url)
        sheeta_obj.get_videos_list()

        video_obj_list = [SheetaVideoCommentGetter(f'https://{sheeta_obj.base_domain}/{sheeta_obj.channel_id + "/" if sheeta_obj.channel_id else "" }video/{video_dump.get("content_code")}') for video_dump in sheeta_obj.video_dumps]

        if not args.batch and not all_download_confirm_dialog():
            video_list_for_dialog = [
                (
                    f'https://{sheeta_obj.base_domain}/{sheeta_obj.channel_id + "/" if sheeta_obj.channel_id else "" }video/{video_dump.get("content_code")}',
                    f'{video_dump.get("title")} ({video_dump.get("display_date")[:10]})',
                )
                for video_dump in sheeta_obj.video_dumps
            ]
            video_obj_list = [SheetaVideoCommentGetter(video_item) for video_item in download_checkbox_dialog(video_list_for_dialog)]
    else:
        logger.error(f'{nico_url=} は非対応のURLの可能性があります.')
        sys.exit(1)

    for video_obj in video_obj_list:
        video_obj.get_video_info()

        default_output_dir = os.getcwd()
        default_output_filename = validate_output_filename(video_obj.video_info_dump.get('data', {}).get('video_page', {}).get('title'))

        if args.output:
            try:
                replace_dict = video_obj.video_info_dump.get('data', {}).get('video_page', {})
                replace_dict = {k: validate_output_filename(v) for k, v in replace_dict.items() if isinstance(v, str)} | {k: datetime.strptime(f"{v} +00:00", '%Y-%m-%d %H:%M:%S %z').astimezone().strftime("%Y%m%d") for k, v in replace_dict.items() if isinstance(v, str) and re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$', v)}
                output_filename = os.path.abspath(args.output % replace_dict)
            except TypeError as e:
                logger.debug(e)
                output_filename = os.path.join(default_output_dir, default_output_filename)
        elif args.batch:
            output_filename = os.path.join(default_output_dir, default_output_filename)
        else:
            try:
                output_filename = output_filepath_input_dialog(os.path.join(default_output_dir, default_output_filename))
            except TypeError as e:
                logger.debug(e)
                output_filename = os.path.join(default_output_dir, default_output_filename)

        if output_filename is None:
            logger.warning('キャンセルされました.')
            continue
        elif output_filename == '':
            logger.warning('出力先ファイルパスが入力されていないため, デフォルト値を使用します.')
            output_filename = os.path.join(default_output_dir, default_output_filename)
        elif check_output_dir(output_filename):
            output_filename = os.path.join(output_filename, default_output_filename)
        elif check_output_dir(os.path.dirname(output_filename)):
            output_filename = os.path.join(os.path.dirname(output_filename), validate_output_filename(os.path.basename(output_filename)))
        else:
            logger.warning('出力先ファイルパスが正しくないため, デフォルト値を使用します.')
            output_filename = os.path.join(default_output_dir, default_output_filename)


        if exists_filepath(output_filename):
            logger.info(f'{output_filename=} は既に存在します.')
            continue
        logger.info(f'{output_filename=}にコメントファイルを出力します.')

        video_obj.get_all_comments_list()
        logger.info(f'{len(video_obj.comment_dumps)} 件のコメントを取得しました.')
        comments_tree = comments_to_tree(video_obj.comment_dumps, video_obj.video_info_dump.get("data", {}).get("video_page", {}).get("video_comment_setting", {}).get("comment_group_id"))
        comments_file_save(comments_tree, output_filename)

    logger.info('処理が完了しました.')
    sys.exit(0)
