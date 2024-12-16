# nicochannel_comment

nicochannel.jp (and sheeta) comment(s) downloader.  
ニコニコチャンネルプラスなど sheeta 利用サイトからコメントをダウンロードし, 各種ソフトで扱えるxmlファイルに変換します.

## Usage/利用方法

### 対話形式での操作

- オプションを指定せずとも利用しやすくなりました

![image](https://github.com/aorinngoDo/nicochannel_comment/assets/90427309/906bb073-5e56-4dc5-a0d2-786919b5b998)

![image](https://github.com/aorinngoDo/nicochannel_comment/assets/90427309/59c4b4b0-cb52-4816-8df7-45325395cdd0)

![image](https://github.com/aorinngoDo/nicochannel_comment/assets/90427309/eac4a038-feaa-45a9-aa5f-ce4a7d45e5fb)

![image](https://github.com/aorinngoDo/nicochannel_comment/assets/90427309/b4b5f296-935e-4de9-990e-e719c6c93841)

### 非対話形式での操作

- `-b` オプションを指定することで, 対話画面をスキップできます. URLは引数で指定する必要があります. チャンネルURLを入力する場合に便利

```
usage: nicochannel_comment.py [-h] [-v] [-o OUTPUT] [--allow-broken-timestamp] [-b] [nico_url]

nicochannel.jp comment(s) downloader.

positional arguments:
  nico_url              Video URL or Channel URL.

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose log output
  -o OUTPUT, --output OUTPUT
                        Output directory / filename.
  --allow-broken-timestamp
                        Save comments that may have broken timestamps. It is recommended to add this option for videos longer than 8 hours.
  -b, --batch           Non-interactive mode. If no output is specified in the argument, the default value is used.
```

nico_url Example: ```https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB```

Example 1: [D:\Videos\] にコメントファイルを保存  
```nicochannel_comment.py https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB -o "D:\Videos\"```
Example 2: カレントディレクトリ下にある[Videos]ディレクトリにファイル名を[comments.xml]としてコメントを全て保存  
```nicochannel_comment.py https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB -o "./Videos/comments.xml" --allowbrokentimestamp```

---
Requirements:

- Python 3.9 or later
- Check requirements.txt

## Bugs/不具合

- サーバから送られるコメントファイルの一部の時間データがおかしい  
確認できた限り,32000秒以降のコメントとして保存されているようなので無視するようにしている  
→ 20220412から ```--allow-broken-timestamp``` オプションで保存できるようにした(32000秒=約9時間以上の動画だと,正常なタイムスタンプのコメントも無視されてしまうため)

## FAQ

- 動画ダウンロード機能は?  
追加予定はありません  

- コメントを扱えるソフトは?  
Windowsなら [akpg tools](http://air.fem.jp/)の各種ソフトなど  
Androidなら[ひま動ぷれいや](https://s368.web.fc2.com/)など  
**※これらはこのツールと一切関係ありません**  

- Releasesのビルドについて  
～20220412_fix: Pyinstallerを利用  
20220505～:     Nuitkaを利用  

```shell-session
$ python -m nuitka --follow-imports --onefile nicochannel_comment.py
```

- 動かない,何かおかしい,不具合や要望等がある  
Issues/Pull requestsを利用するか,直接連絡をお願いします  
