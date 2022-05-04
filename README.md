# nicochannel_comment
nicochannel.jp comment(s) downloader.  
ニコニコチャンネルプラスからコメントをダウンロードし,各種ソフトで扱えるxmlファイルに変換します。

## Usage/利用方法:
```
usage: nicochannel_comment.py [-h] [-o OUTPUT] [--allowbrokentimestamp] video_url

nicochannel.jp comment downloader.

positional arguments:
  video_url             Video URL.

optional arguments:
  -h, --help                    show this help message and exit
  -o OUTPUT, --output OUTPUT    Output directory / filename.
  --allowbrokentimestamp        Save comments that may have broken timestamps. It is
                                recommended to add this option for videos longer than
                                8 hours.
```  

VIDEO_URL Example: ```https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB```

Example 1: [D:\Videos\] にコメントファイルを保存  
``` nicochannel_comment.py https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB -o "D:\Videos\"```  
Example 2: カレントディレクトリ下にある[Videos]ディレクトリにファイル名を[comments.xml]としてコメントを全て保存  
``` nicochannel_comment.py https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB -o "./Videos/comments.xml" --allowbrokentimestamp```  

---
Tested on  
```Windows 10 64bit   Python 3.10.2```  
```Ubuntu 18.04.6 LTS amd64    Python 3.7.5 (～20220412_fix)```  
```Ubuntu 20.04.4 LTS amd64    Python 3.8.10 (20220505～)```  

## Bugs/不具合:
- サーバから送られるコメントファイルの一部の時間データがおかしい  
確認できた限り,32000秒以降のコメントとして保存されているようなので無視するようにしている  
→ 20220412から ```--allowbrokentimestamp``` オプションで保存できるようにした(32000秒=約9時間以上の動画だと,正常なタイムスタンプのコメントも無視されてしまうため)

## Future plans/追加予定の機能,改良すべき点
- [x] ~~保存先フォルダ指定~~  
- [x] ~~保存ファイル名指定~~

## FAQ
- 動画ダウンロード機能は?  
追加予定はありません  

- コメントを扱えるソフトは?  
Windowsなら [akpg tools](http://air.fem.jp/)の各種ソフトなど  
Androidなら[ひま動ぷれいや](https://s368.web.fc2.com/)など  
**※これらはこのツールと一切関係はありません**  

- Releasesのビルドについて  
～20220412_fix: Pyinstallerを利用  
20220505～:     Nuitkaを利用  

- 動かない,何かおかしい,不具合や要望等がある  
Issues/Pull requestsを利用するか,直接連絡をお願いします  
