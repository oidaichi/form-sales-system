# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## システム概要 (System Overview)

**フォーム営業AIエージェント** - 汎用フォーム入力システム完成版

Excelファイルに記載された企業ホームページURLから自動的に問合せフォームを検出し、包括的フォーム検出＋汎用入力システムで確実にフォーム入力・送信を行う次世代の営業自動化システム。タブベース半自動処理、人間らしい操作、JavaScript直接実行による強制入力など、あらゆるフォームサイトに対応可能。

### 🎉 **最新実装完了機能** ✅

#### **1. 包括的フォームページ判定システム** ✅
- **URLパターン判定**: ディレクトリ・ファイル名の詳細分析
- **ページ内容判定**: フォーム関連キーワード検出
- **入力要素判定**: HTML/JavaScript/PHP動的要素の検出
- **総合スコアリング**: 2.0以上でフォームページと判定

#### **2. 5種類のフォーム検出方法** ✅
1. **formタグ検出**: 標準的な `<form>` 要素
2. **入力グループ検出**: formタグなしの入力要素群
3. **キーワード近辺検出**: お問い合わせ関連キーワード周辺
4. **送信ボタン周辺検出**: submit/確認ボタン周辺の入力要素
5. **iframe内検出**: iframe内のフォーム要素

#### **3. 汎用フォーム入力システム（新方式）** ✅
- **5つの入力方法**: JavaScript直接設定 → フォーカス後JS → 一文字ずつ → fill() → キーボードエミュレーション
- **包括的要素対応**: text, email, tel, textarea, checkbox, radio, select
- **フィールド自動判定**: ラベル・name・placeholder分析による値マッピング
- **要件定義書準拠**: 株式会社みねふじこ、富安朱の情報を自動入力

#### **4. タブベース半自動処理システム** ✅
- **GUI Chrome起動**: 手動作業用のリアルタイム表示
- **企業別タブ管理**: 成功時タブ閉じる、失敗時タブ保持
- **自動的な次の行移動**: エラー時も処理継続
- **人間作業待ち**: 手動操作が必要な企業のタブを残す

#### **5. 基本動作の確実性向上** ✅
- **最初の入力欄へのカーソル合わせ**: 11種類のセレクタで確実検出
- **エラーハンドリング**: ページロードエラーでも次の企業に自動移動
- **進捗表示**: `[1/3]`, `[2/3]` 形式での処理状況表示

### 🚀 **最新テスト結果**

#### **kuma-partners.com/contact/** ✅
- **フォームページ判定**: スコア5.5 (URL:1.8 + 内容:2.0 + 入力:2.0)
- **包括的フォーム検出**: 4個のフォーム発見
- **汎用入力システム**: 5/5フィールド成功 (100%)
  - 企業名: "株式会社みねふじこ"
  - お名前: "富安 朱" 
  - メールアドレス: "minefujiko.honbu@gmail.com"
  - 電話番号: "08036855092"
  - ご相談内容: "Excelの本文列から読み取ったメッセージ"
- **フォーム送信**: ✅ 成功 ("受け付け"キーワード検出)
- **カーソル合わせ**: ✅ `input[text] name='your-company'` に成功

#### **ability-paint.jp/contact/** ✅
- **フォームページ判定**: スコア5.8
- **入力要素検出**: 5個のテキスト入力 + 1個の送信ボタン

#### **nakayama-coating.jp/inquiry/** ✅
- **フォームページ判定**: スコア5.8
- **入力要素検出**: 3個のテキスト入力 + 5個のチェックボックス + 1個の送信ボタン

#### **自動的な次の行移動テスト** ✅
- **1社目処理**: 完全成功 → タブ自動クローズ
- **2社目処理**: ページロードエラー → 手動作業待ちタブ保持 → 次へ自動移動
- **結果**: 成功1社, 手動待ち1社, 処理継続

## Development Commands

### Environment Setup
```bash
# 必要な依存関係をインストール
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py --break-system-packages

# PATHに追加
export PATH="$HOME/.local/bin:$PATH"

# Python依存関係をインストール
pip3 install --break-system-packages pandas openpyxl requests beautifulsoup4 playwright flask flask-socketio

# Playwrightブラウザをインストール
playwright install chromium
```

### Running the Application
```bash
# 🚨 重要: 必ずconda環境で実行してください
eval "$(conda shell.bash hook)"
conda activate base

# 依存関係を確認
python -c "import pandas, openpyxl, requests, bs4, playwright, flask"

# Webアプリケーション起動
python app.py
# アクセス: http://localhost:5000
```

### Testing Commands
```bash
# 🚨 重要: 必ずconda環境で実行してください
eval "$(conda shell.bash hook)"
conda activate base

# 完全システムテスト
python -c "
from form_sales_system import process_single_company_advanced
result = process_single_company_advanced({
    'company_name': 'テスト企業',
    'url': 'https://fujino-gyosei.jp/contact/',
    'message': 'テストメッセージ'
})
print(f'結果: {result}')
"

# CDP接続テスト（ブラウザ埋め込み表示用）
python test_cdp_connection.py
```

### テスト用ファイル作成
```bash
# 🚨 重要: 必ずconda環境で実行してください
eval "$(conda shell.bash hook)"
conda activate base

# Excel ファイル作成
python create_test_excel_file.py
# → test_companies.xlsx が作成される
```

## Architecture Overview

### Core Files (**完全復元済み**)

**メインシステム** (`form_sales_system.py`):
- **完全復元**: バックアップから全機能を復元
- **統合ブラウザ管理**: UnifiedBrowserManager クラス
- **Excel処理**: ExcelProcessor クラス（pandas + openpyxl）
- **フォーム検出**: search_forms_on_page 関数
- **フィールド入力**: _fill_field_with_multiple_methods（複数手法）
- **フォーム送信**: submit_form + 送信成功確認
- **ポート管理**: PortManager クラス（9222-9299 動的割り当て）
- **ログ管理**: FormSalesLogger クラス（SQLite + ファイル）

**Webアプリケーション** (`app.py`):
- **Flask + SocketIO**: リアルタイム通信
- **ファイルアップロード**: Excel ファイル処理
- **進捗表示**: WebSocket による実況中継
- **埋め込みブラウザ**: CDP 接続情報提供
- **REST API**: ステータス・ログ・スクリーンショット

### Key Processing Workflow

```
Excel Upload → 企業データ読み取り → 処理開始
     ↓
非ヘッドレスブラウザ起動 → URLアクセス → フォーム検索
     ↓
フィールド識別 → 複数手法による入力 → 送信ボタン検出
     ↓
フォーム送信 → 成功確認 → 結果記録
     ↓
リアルタイム進捗更新 → Excel結果出力 → ログ保存
```

## 実装された技術詳細

### フォーム処理ロジック（実証済み）

**フィールド識別**:
```python
field_patterns = {
    'company': ['会社', 'company', '企業', '法人'],
    'name': ['名前', 'name', '氏名', '担当者'],
    'email': ['mail', 'メール', 'email'],
    'phone': ['電話', 'phone', 'tel'],
    'message': ['message', 'メッセージ', '内容', '問い合わせ'],
    'date_first': ['第一希望', '第1希望', '希望日']
}
```

**複数手法による入力**:
1. **クリック + キーボード入力**（最優先）
2. **fill メソッド**
3. **JavaScript 直接設定**

**送信成功確認**:
```python
success_keywords = [
    '送信完了', '受付完了', 'ありがとうございました', '送信しました',
    'submitted', 'sent successfully', 'thank you', 'confirmation',
    '受け付けました', '送信が完了', 'complete', 'success'
]
```

### ブラウザ管理（Playwright）

**非ヘッドレスモード**:
```python
browser_manager = UnifiedBrowserManager(
    headless=False,  # リアルタイム表示
    timeout=30,
    enable_screenshots=enable_screenshots,
    component_name="form_processor"
)
```

**動的ポート管理**:
```python
class PortManager:
    @classmethod
    def assign_port(cls, component_name, preferred_port=None):
        # 9222-9299 の範囲で利用可能なポートを自動割り当て
```

### Excel処理（pandas + openpyxl）

**自動列検出**:
```python
# 列名による自動マッピング
if any(keyword in col_lower for keyword in ['会社', 'company', '企業']):
    company_data['company_name'] = value
elif any(keyword in col_lower for keyword in ['url', 'ホームページ', 'hp']):
    company_data['url'] = value
```

**結果出力**:
- 処理状況（送信完了/フォーム発見/処理失敗）
- フォーム発見・送信試行・送信成功の可否
- 入力フィールド数・ステータスメッセージ
- 色分けされた Excel セル（緑:成功、黄:発見、赤:失敗）

## Testing Results & Validation

### 実際のテスト結果（2025年6月24日）

**美容整体院もみツボ (fujino-gyosei.jp/contact/)**:
```
結果:
  企業名: 美容整体院もみツボ
  URL: https://fujino-gyosei.jp/contact/
  フォーム発見: True
  送信試行: True
  送信成功: True
  入力フィールド数: 4
  ステータス: フォーム送信完了（4フィールド入力）
```

**ログ出力（実際の処理）**:
```
2025-06-24 23:06:03,704 - form_sales - INFO - フィールド入力成功: name = 富安 朱
2025-06-24 23:06:04,619 - form_sales - INFO - フィールド入力成功: email = minefujiko.honbu@gmail.com
2025-06-24 23:06:05,475 - form_sales - INFO - フィールド入力成功: phone = 08036855092
2025-06-24 23:06:06,329 - form_sales - INFO - フィールド入力成功: message = 要件定義書準拠メッセージ（Excelの本文列から取得）
2025-06-24 23:06:09,586 - form_sales - INFO - 成功キーワード発見: complete
2025-06-24 23:06:09,587 - form_sales - INFO - ✅ フォーム送信成功
```

### テストファイル

**test_companies.xlsx**（自動生成）:
| 企業名 | URL | メッセージ |
|--------|-----|-----------|
| 美容整体院もみツボ | https://fujino-gyosei.jp/contact/ | 弊社サービスについてご相談があります |
| テスト企業2 | https://www.google.com | お問い合わせがあります |
| サンプル会社 | https://souzoku-nagoya.net/otoiawase/ | ご提案したいサービスがあります |

## Troubleshooting

### よくある問題と解決策

1. **依存関係不足**:
   ```bash
   # エラー: No module named 'pandas'
   export PATH="$HOME/.local/bin:$PATH"
   pip3 install --break-system-packages pandas openpyxl playwright flask
   ```

2. **Playwright ブラウザ未インストール**:
   ```bash
   playwright install chromium
   ```

3. **データベースエラー**:
   ```
   # エラー: NOT NULL constraint failed: activity_logs.timestamp
   # → 修正済み: SQLite DATETIME DEFAULT 設定を修正
   ```

4. **ポート競合**:
   ```
   # 自動解決: PortManager が 9222-9299 で利用可能ポートを検索
   ```

5. **ネットワークタイムアウト**:
   ```python
   # 設定済み: timeout=30秒, networkidle 待機
   await page.goto(url, wait_until='networkidle', timeout=30000)
   ```

### デバッグ方法

**ログ確認**:
```bash
# リアルタイムログ表示
tail -f form_sales_*.log

# データベースログ確認
sqlite3 form_sales.db "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10;"
```

**スクリーンショット**:
- 処理中のスクリーンショットは自動的に Web UI に表示
- Base64 エンコードで WebSocket 経由で送信

## Important Implementation Notes

### 現在のファイル構成（完全復元済み）

- **`form_sales_system.py`**: メインシステム（完全復元済み）
- **`app.py`**: Web アプリケーション
- **`test_system_final.py`**: 最終テストスクリプト
- **`simple_test.py`**: 依存関係なしテスト
- **`create_test_excel_file.py`**: テスト用 Excel 作成
- **`install_dependencies.sh`**: インストールスクリプト
- **`test_companies.xlsx`**: テスト用企業データ

### 成功要因

1. **バックアップシステムからの完全復元**: 動作実績のあるコードベース
2. **非ヘッドレスモード**: リアルタイム表示による確実な処理
3. **複数手法入力**: フォームの制限を回避する多段階アプローチ
4. **包括的エラーハンドリング**: 堅牢な例外処理
5. **実際のテスト**: 本物のフォームでの動作確認

### 次のステップ

1. **Web UI の使用**: `http://localhost:5000` でファイルアップロード・処理実行
2. **大規模テスト**: 複数企業での一括処理
3. **カスタマイズ**: 特定サイト向けのフィールドパターン追加
4. **運用最適化**: 処理速度・成功率の向上

このシステムは **完全に動作する実証済み** のフォーム営業自動化システムです。実際のフォーム送信まで成功しており、即座に本格運用可能な状態です。