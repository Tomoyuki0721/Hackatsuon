# トラブルシューティング

当日つまずきやすい順に並んでいます。まずエラーメッセージをよく読む(または AI に貼り付ける)のが一番の近道です。

## Codespace まわり

**Q. 「Create codespace」を押しても起動しない / エラーになる**
- GitHub のメール認証が済んでいるか確認(登録メールに届いた確認リンクを踏む)
- ブラウザをリロードして再試行
- https://github.com/codespaces を開き、既に作成済みの Codespace があればそれを開く

**Q. ターミナルに🐟のようこそメッセージが出ない**
- セットアップが終わっていません。1〜2分待って、`+` ボタンで**新しいターミナルを**開き直す
- 5分以上待っても出ないときは、以下を手動実行:
  ```bash
  bash .devcontainer/setup.sh
  source ~/.bashrc
  ```

**Q. テンプレートから直接 Codespace を開いてしまった(自分のリポジトリがない)**
- そのまま作業を続けて大丈夫です。作品を保存するために、左のソース管理アイコン
  (枝分かれマーク)→「Publish to GitHub」で自分のリポジトリとして公開してください
- 公開しないまま放置すると、30日後に Codespace ごと作品が削除されます

**Q. ターミナルが見当たらない**
- 左上メニュー(≡) → Terminal → New Terminal
- ショートカット: `Ctrl + @`(Windows)/ `Cmd + J`(Mac)

## Claude Code まわり

**Q. `claude: command not found`**
```bash
source ~/.bashrc
```
それでもダメなら:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Q. 起動時の質問で「2. No (recommended)」を選んでしまい、ログイン画面になった**
- `Esc` や `Ctrl + C` で抜けて、もう一度 `claude` を起動
- 「Do you want to use this API key?」では **1. Yes** を選びます(recommended に釣られない)

**Q. APIキーが無効と言われる**
- `export ANTHROPIC_API_KEY=...` のコピペミスが9割。前後に空白や改行が入っていないか確認
- 配布されたキーを最初から貼り直し、`claude` を起動し直す

**Q. Claude Code の返答が途中で止まる / 429 エラー**
- 混雑しています。1〜2分待ってから続きを頼んでください

**Q. AIが作ったものが動かない**
- エラーメッセージやスクリーンショットの内容をそのまま AI に貼り付けて「直して」と言う
- 直らないときは「一度シンプルな構成に作り直して」と頼むのも有効

## プレビューまわり

**Q. `http-server -p 8080` してもページが開かない**
- 画面右下の通知「ポート8080が利用可能です」から Open を押す
- または「ポート」タブ(ターミナル横)→ 8080 の地球儀アイコンをクリック
- 変更が反映されないときはブラウザをスーパーリロード(`Ctrl+Shift+R` / `Cmd+Shift+R`)

## 公開(GitHub Pages)まわり

**Q. Pages を有効にしたのに、URLを開くと404**
- 1〜2分待ってからスーパーリロード(`Ctrl+Shift+R` / `Cmd+Shift+R`)
- Settings → Pages で Branch が **main / (root)** になっているか確認
- リポジトリ直下に `index.html` があるか確認(フォルダの中だと表示されません)

**Q. push したのに、公開ページが古いまま**
- 反映まで1〜2分かかります。待ってからスーパーリロード
- リポジトリの「Actions」タブで pages のビルドが動いているか見られます

**Q. ページは開くけど、見た目が崩れる / 画像が出ない**
- CSSや画像を `/style.css` のような **絶対パス**で参照していると壊れます
  (公開URLが `ユーザー名.github.io/リポジトリ名/` 配下のため)
- AI に「参照を相対パスに直して」と頼めば直ります

## GitHub への push まわり

**Q. `git push` が拒否される / 認証エラーになる**
- Codespace は起動時に GitHub 認証が済んでいるので、通常は追加操作なしで push できます
- 失敗するときは一度ブラウザをリロードして Codespace を開き直し、再度 `git push`

## その他

**Q. 無料枠が心配**
- Codespaces の無料枠は個人アカウントに月120コア時間(2コアで実質60時間)。今日1日では使い切りません
- 使い終わったら https://github.com/codespaces で該当の Codespace を「Stop」しておくと安心です

**Q. 家に帰ってから続きをやるには?**
- https://github.com/codespaces → 自分の Codespace をクリックで再開
- 再開後は `export ANTHROPIC_API_KEY=...` からやり直し(環境変数は再起動で消えます)
- わからないことは Discord の #helpdesk へ
