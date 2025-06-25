# フォーム営業システム

## 📁 ファイル構成（シンプル版）

### 🚀 **メインファイル（必須）**
- **`form_sales_system.py`** - メインシステム（全機能統合）
- **`app.py`** - Webアプリケーション
- **`templates/index.html`** - メインUI
- **`templates/browser_embed.html`** - ブラウザ埋め込み表示

### 📊 **設定・データファイル**
- **`requirements.txt`** - Python依存関係
- **`test_companies.xlsx`** - テスト用企業データ
- **`form_sales.db`** - SQLiteデータベース（自動生成）

### 📋 **ドキュメント**
- **`CLAUDE.md`** - システム詳細ドキュメント
- **`README_システム概要.md`** - このファイル

## 🚀 **起動方法**

### **🚨 重要: 必ずconda環境で実行してください**

```bash
# 1. conda環境有効化
eval "$(conda shell.bash hook)"
conda activate base

# 2. 依存関係確認・インストール
python -c "import pandas, openpyxl, requests, bs4, playwright, flask"
# エラーが出た場合のみ以下を実行:
# pip install pandas openpyxl requests beautifulsoup4 playwright flask flask-socketio
# playwright install chromium

# 3. システム起動
python app.py

# 4. ブラウザでアクセス
# http://localhost:5000
```

### **🌐 ブラウザ埋め込み表示テスト**

```bash
# conda環境で実行
eval "$(conda shell.bash hook)"
conda activate base

# CDP接続テスト（30秒間ブラウザ維持）
python test_cdp_connection.py

# ↑実行中に別のターミナルでWebアプリを起動
python app.py
# → http://localhost:5000 で埋め込みブラウザを確認
```

## ✨ **主要機能**

1. **ブラウザ埋め込み表示** - リアルタイムでフォーム操作を表示
2. **Excel企業データ処理** - 自動読み取り・結果出力
3. **フォーム自動入力・送信** - 実証済み完全動作
4. **リアルタイム進捗表示** - WebSocket通信

## 🎯 **使い方**

1. `http://localhost:5000` にアクセス
2. Excel ファイルをアップロード
3. 企業プレビューを確認
4. 埋め込みブラウザでリアルタイム表示を確認
5. 「処理開始」ボタンをクリック
6. 自動処理を監視

## ✅ **動作確認済み**

- **美容整体院もみツボ**: 4フィールド入力・送信成功
- **Google検索**: フォーム検出成功
- **リアルタイム表示**: CDP接続・埋め込み表示

このシステムは完全に動作し、即座に本格運用可能です。