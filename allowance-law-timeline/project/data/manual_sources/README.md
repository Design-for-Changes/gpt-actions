# manual_sources の使い方

Codex実行環境では `hourei.ndl.go.jp` への直接アクセス時に `Tunnel connection failed: 403 Forbidden` となる場合があります。
そのため、日本法令索引ページはユーザーがブラウザで手動保存し、このディレクトリ配下に配置してください。

## 保存先

- `project/data/manual_sources/hourei/`

## 保存対象（日本法令索引シンプル表示URL）と固定ファイル名

1. 児童手当法  
   URL: `https://hourei.ndl.go.jp/simple/detail?lawId=0000061613`  
   保存名: `jidou_teate_hou.html`

2. 児童扶養手当法  
   URL: `https://hourei.ndl.go.jp/simple/detail?lawId=0000053349`  
   保存名: `jidou_fuyou_teate_hou.html`

3. 児童扶養手当法施行令  
   URL: `https://hourei.ndl.go.jp/simple/detail?lawId=0000053370`  
   保存名: `jidou_fuyou_teate_hou_sekourei.html`

4. 特別児童扶養手当等の支給に関する法律  
   URL: `https://hourei.ndl.go.jp/simple/detail?lawId=0000055859`  
   保存名: `tokubetsu_jidou_fuyou_teate_hou.html`

5. 特別児童扶養手当等の支給に関する法律施行令  
   URL: `https://hourei.ndl.go.jp/simple/detail?lawId=0000065214`  
   保存名: `tokubetsu_jidou_fuyou_teate_hou_sekourei.html`

## 注意

- 文字コード変換や本文改変はしないでください。
- 不明値を埋めるための追記はしないでください。
- Codexは配置済みHTMLを解析し、`project/data/amendments_draft.json` を下書き生成します。
