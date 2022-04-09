# nicochannel_comment
nicochannel.jp comment downloader.  
ニコニコチャンネルプラスからコメントをダウンロードし,各種ソフトで扱えるxmlファイルに変換します。

## Usage/利用方法:
```nicochannel_comment{.py .exe}  VIDEO_URL```  
動画URLを引数にして nicochannel_comment{.py .exe}  を実行  
  
OR  
  
Start nicochannel_comment{.py .exe} and input video URL.  
nicochannel_comment{.py .exe}  を実行すると,動画URLを尋ねられるため入力  

VIDEO_URL Example: ```https://nicochannel.jp/yojyo-bergamo/video/smvm4YYLRKyMreUq4sfjtawB```

---
Tested on ```Windows 10 Python 3.10.2``` / ```Ubuntu 18.04.6 LTS    Python 3.7.5```

## Bugs/不具合:
- サーバから送られるコメントファイルの一部の時間データがおかしい  
確認できた限り,32000秒以降のコメントとして保存されているようなので無視するようにしている

## Future plans/追加予定の機能,改良すべき点
- [ ] 保存先フォルダ指定  
- [ ] 保存ファイル名指定

## FAQ
- 動画ダウンロード機能は?  
追加予定はありません  

- コメントを扱えるソフトは?  
Windowsなら [akpg tools](http://air.fem.jp/)の各種ソフトなど  
Androidなら[ひま動ぷれいや](https://s368.web.fc2.com/)など  
**※これらはこのツールと一切関係はありません**  

- 動かない,何かおかしい,不具合や要望等がある  
Issues/Pull requestsを利用するか,直接連絡をお願いします
