#!/usr/bin/env bash
# Hackatsuon Starter - 環境セットアップスクリプト
# Codespace の初回起動時に自動実行されます(数分かかります)

set -x

# 1. Claude Code(AIコーディングエージェント)のインストール
curl -fsSL https://claude.ai/install.sh | bash

# PATH を通す(bash / zsh 両対応)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
echo 'export ANTHROPIC_MODEL="claude-sonnet-4-6"' >> "$HOME/.bashrc"

# 2. wrangler(Cloudflare デプロイ用CLI)のインストール
npm install -g wrangler

# 3. 簡易プレビュー用の http-server
npm install -g http-server

# 新しいターミナルを開くたびに案内を表示する
cat << 'BANNER' >> "$HOME/.bashrc"
echo ""
echo "🐟 Hackatsuon Starter へようこそ!"
echo "   環境チェック: claude --version && wrangler --version"
echo "   次の一歩は README.md の Step 3 から"
echo ""
BANNER
