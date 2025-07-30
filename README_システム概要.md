# フォーム営業自動化システム 詳細要件定義書

## 1. システム概要

### 1.1 目的と背景
本システムは、CSVファイルで管理された企業リストに対して、各企業のWebサイトにある問い合わせフォームへの自動入力・送信を行うことを目的とする。従来の手動によるフォーム入力作業を自動化し、営業効率の大幅な向上を実現する。

### 1.2 システムの価値提案
- **効率化**: 手動で1社あたり3-5分かかるフォーム入力を自動化
- **品質向上**: 人的ミスの削減と一貫した入力品質の保証
- **スケーラビリティ**: 大量企業への同時アプローチが可能
- **トレーサビリティ**: 全処理のログ記録と結果追跡

### 1.3 技術アーキテクチャ
- **フロントエンド**: HTML5 + CSS3 + JavaScript (Socket.IO)
- **バックエンド**: Python Flask + Flask-SocketIO
- **ブラウザ自動化**: Playwright (Chromium)
- **データベース**: SQLite (WALモード)
- **対応OS**: Windows, macOS, Ubuntu

## 2. 機能要件

### 2.1 CSVデータ処理機能

#### 2.1.1 CSVファイル形式仕様
システムが処理するCSVファイルは以下の10列構造を持つ：

```csv
company,url,contact_url,industry_class,postal_code,address,phone,fax,business_tags,list_tags
株式会社サンプル,https://example.com,https://example.com/contact,IT,100-0001,東京都千代田区,03-1234-5678,03-1234-5679,IT・ソフトウェア,優良企業
```

**各列の詳細仕様：**
- `company`: 企業名（必須、最大100文字）
- `url`: 企業のメインURL（必須、有効なHTTP/HTTPS URL）
- `contact_url`: 問い合わせページURL（任意）
- `industry_class`: 業界分類（任意、最大50文字）
- `postal_code`: 郵便番号（任意、XXX-XXXX形式）
- `address`: 住所（任意、最大200文字）
- `phone`: 電話番号（任意、ハイフン区切り可）
- `fax`: FAX番号（任意、ハイフン区切り可）
- `business_tags`: 事業タグ（任意、カンマ区切り可）
- `list_tags`: リストタグ（任意、カンマ区切り可）

#### 2.1.2 CSVファイル読み込み処理
1. **文字エンコーディング自動検出**: UTF-8, Shift_JIS, EUC-JPに対応
2. **データ検証**: 必須項目の存在確認、URL形式の妥当性検証
3. **重複チェック**: 企業名とURLの組み合わせによる重複検出
4. **データクレンジング**: 前後空白の除去、不正文字の除去

#### 2.1.3 バッチ処理仕様
- **処理単位**: 30社ずつのバッチ処理
- **処理間隔**: 企業間で2秒のインターバル
- **リトライ機能**: 失敗時の自動リトライ（最大3回）
- **処理ログ**: 全処理の詳細ログ記録

### 2.2 フォーム検出・処理機能

#### 2.2.1 フォームページ自動検出アルゴリズム

**Phase 1: URLパターン解析**
以下のキーワードを含むURLを優先的に検査：
```
contact, inquiry, form, お問い合わせ, 問合せ, consultation, 
consult, toiawase, soudan, apply, request, booking, 
reservation, estimate, 申込, 申し込み, 見積, 相談, 予約
```

**Phase 2: リンクテキスト解析**
以下のテキストを含むリンクを自動検出：
```
日本語: お問い合わせ, 相談, Contact Us, Get in Touch, 
       お申し込み, 申込み, ご相談, 問い合わせ, コンタクト, 
       連絡, フォーム, 見積, 資料請求, 無料相談, ご予約, 予約
英語: contact, inquiry, form, consultation, apply, 
      register, booking, reservation, estimate, quote
```

**Phase 3: ページ内容解析**
- HTMLコンテンツ内のキーワード密度分析
- フォーム要素（input, textarea, select）の存在確認
- 送信ボタン（submit, button）の検出

#### 2.2.2 フォーム要素識別システム

**入力フィールド自動分類アルゴリズム:**

1. **企業名フィールド検出**
   - name属性: `company`, `company_name`, `corporation`
   - id属性: `company`, `corp`, `organization`
   - placeholder: `会社名`, `企業名`, `法人名`, `Company Name`
   - ラベルテキスト: `会社`, `企業`, `法人`, `組織`

2. **担当者名フィールド検出**
   - name属性: `name`, `your_name`, `contact_name`, `representative`
   - placeholder: `お名前`, `氏名`, `担当者名`, `代表者名`, `Your Name`
   - 分割フィールド対応: `sei`(姓), `mei`(名), `first_name`, `last_name`
   - ふりがなフィールド: `furigana`, `kana`, `reading`

3. **メールアドレスフィールド検出**
   - input type="email"の自動検出
   - name属性: `email`, `mail`, `e_mail`, `contact_email`
   - 確認用フィールド: `email_confirm`, `email2`, `confirm_email`

4. **電話番号フィールド検出**
   - input type="tel"の自動検出
   - name属性: `phone`, `tel`, `telephone`, `mobile`
   - placeholder: `電話番号`, `TEL`, `Phone Number`

5. **住所関連フィールド検出**
   - 郵便番号: `zip`, `postal_code`, `postcode`, `郵便番号`
   - 都道府県: `prefecture`, `pref`, `state`, `都道府県`
   - 住所: `address`, `location`, `住所`

6. **メッセージフィールド検出**
   - textarea要素の自動検出
   - name属性: `message`, `content`, `inquiry`, `details`, `comment`
   - placeholder: `メッセージ`, `お問い合わせ内容`, `ご相談内容`

7. **選択フィールド検出**
   - 問い合わせ種別: `inquiry_type`, `consultation_type`
   - ドロップダウンメニュー: select要素
   - ラジオボタン: input type="radio"
   - チェックボックス: input type="checkbox"

#### 2.2.3 送信ボタン検出システム

**送信ボタン検出パターン:**
```
Type属性: submit
ボタンテキスト: 送信, 確認, 申し込み, 問い合わせ, Submit, Send, 
               確認画面, 確認画面へ, 確認する, 次へ, Continue, 
               この内容で送信, 送信する, Apply, Register
Value属性: 送信, 確認, 申込, Submit
Class属性: submit, send, apply, confirm
```

### 2.3 フォーム入力データ仕様

#### 2.3.1 標準入力データセット
システムが各フィールドに入力する標準データ：

```json
{
  "company_data": {
    "target_company": "{{CSV企業名}}", // CSVから取得
    "sender_company": "株式会社みねふじこ",
    "sender_name": "富安　朱",
    "sender_furigana": "とみやす　あや",
    "sender_email": "minefujiko.honbu@gmail.com",
    "sender_phone": "08036855092",
    "sender_address": "東京都港区南青山3丁目1番36号青山丸竹ビル6F",
    "sender_postal_code": "107-0062"
  },
  "message_data": {
    "subject": "業務提携のご相談",
    "message": "お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。ぜひ一度お打ち合わせの機会をいただければと思います。ご検討のほど、よろしくお願いいたします。"
  },
  "form_defaults": {
    "inquiry_type": "その他",
    "consultation_type": "お問い合わせ",
    "privacy_agreement": true,
    "newsletter_subscription": false
  }
}
```

#### 2.3.2 動的フィールド対応
- **日付フィールド**: 現在日時から7-9営業日後の平日を自動設定
- **時間フィールド**: デフォルト13:00を設定
- **選択肢フィールド**: キーワードマッチングによる自動選択
- **必須項目優先**: アスタリスク(*)や「必須」表示がある項目を優先処理

### 2.4 ブラウザ自動化仕様

#### 2.4.1 Playwrightブラウザ設定
```python
browser_config = {
    "headless": True,  # ヘッドレスモード
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "timeout": 30000,  # 30秒タイムアウト
    "ignore_https_errors": True,
    "java_script_enabled": True,
    "accept_downloads": False
}
```

#### 2.4.2 人間らしい操作シミュレーション
1. **マウス操作**
   - ランダムな移動軌跡
   - 要素中央付近へのクリック（±20%のオフセット）
   - クリック前の0.1-0.3秒待機

2. **キーボード入力**
   - 1文字ずつの順次入力
   - 50-150ms/文字のランダム速度
   - 入力前のフィールドクリア（Ctrl+A → Delete）

3. **待機時間**
   - ページロード: networkidle状態まで待機
   - 要素表示: 最大5秒の表示待機
   - 操作間隔: 0.3-0.8秒のランダム待機

#### 2.4.3 自動検出回避機能
- **User-Agent回転**: 複数のUser-Agentをランダム使用
- **リクエスト間隔**: 2秒の固定間隔でサーバー負荷軽減
- **エラー処理**: CAPTCHA検出時の適切な処理停止

### 2.5 ログ・監視機能

#### 2.5.1 データベーススキーマ
```sql
CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    company_name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL,  -- success, failed, skipped
    message TEXT,
    processing_time INTEGER,  -- 処理時間（秒）
    form_fields_found INTEGER,  -- 検出フィールド数
    form_fields_filled INTEGER,  -- 入力成功フィールド数
    error_details TEXT,  -- エラー詳細
    page_title TEXT,  -- ページタイトル
    final_url TEXT   -- 最終到達URL
);
```

#### 2.5.2 リアルタイム進捗監視
- **WebSocket通信**: Flask-SocketIOによるリアルタイム更新
- **進捗バー**: 0-100%の処理進捗表示
- **ステータス表示**: 現在処理中の企業名と状態
- **統計情報**: 成功率、処理速度、残り時間の表示

## 3. 非機能要件

### 3.1 パフォーマンス要件
- **処理速度**: 1企業あたり平均30-60秒以内
- **同時処理**: 最大30社の並列処理対応
- **メモリ使用量**: 最大2GB以内での動作
- **レスポンス時間**: Web画面操作の応答時間1秒以内

### 3.2 可用性要件
- **稼働率**: 99%以上の安定動作
- **エラー復旧**: 自動リトライ機能による処理継続
- **ログ保持**: 30日間の処理ログ保持
- **バックアップ**: 処理結果の自動保存

### 3.3 セキュリティ要件
- **データ保護**: 企業情報の暗号化保存
- **アクセス制御**: ローカルホストからのみアクセス許可
- **ログ保護**: 機密情報のマスキング処理
- **通信暗号化**: HTTPS通信の強制

### 3.4 互換性要件
- **OS対応**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Python**: Python 3.8以上
- **ブラウザ**: Chromium 90以上
- **文字エンコーディング**: UTF-8, Shift_JIS, EUC-JP

## 4. ユーザーインターフェース要件

### 4.1 Webインターフェース仕様

#### 4.1.1 メイン画面レイアウト
```
┌─────────────────────────────────────────────────────────────┐
│ 🚀 ヘッドレス フォーム営業システム                               │
├─────────────────────────────────────────────────────────────┤
│ 📁 CSVファイルアップロード                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │  📊 CSVファイルを選択またはドラッグ&ドロップ                │ │
│ │  [ファイルを選択]                                        │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ 📊 処理統計                                                  │
│ ┌──────────┬──────────┬──────────┬──────────┐              │
│ │   総企業数  │  未処理企業  │  次回処理数  │   成功率   │              │
│ │     23     │     15      │     15      │   67.3%   │              │
│ └──────────┴──────────┴──────────┴──────────┘              │
├─────────────────────────────────────────────────────────────┤
│ ⚡ 処理実行                                                  │
│ [🤖 ヘッドレス処理開始] [🖥️ タブベース処理開始] [⏹️ 停止]     │
│ Progress: ████████████████████████████████ 85%              │
│ 現在処理中: 株式会社サンプル (15/30)                          │
├─────────────────────────────────────────────────────────────┤
│ 👀 データプレビュー                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 企業名          │ URL              │ 処理状況          │ │
│ │ 株式会社A       │ https://a.com    │ [処理済み]        │ │
│ │ 株式会社B       │ https://b.com    │ [未処理]          │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### 4.1.2 レスポンシブデザイン要件
- **デスクトップ**: 1920x1080以上の解像度に最適化
- **タブレット**: 768px以上の画面幅に対応
- **モバイル**: 320px以上の画面幅に対応
- **ブラウザ対応**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

### 4.2 操作フロー設計

#### 4.2.1 標準操作フロー
1. **CSVファイル選択**
   - ドラッグ&ドロップまたはファイル選択ダイアログ
   - ファイル形式・内容の自動検証
   - プレビューデータの表示（最初の10件）

2. **処理設定確認**
   - 総企業数と未処理企業数の表示
   - 処理予定数（最大30件）の確認
   - バッチサイズの調整（必要に応じて）

3. **処理実行**
   - ヘッドレスまたはタブベース処理の選択
   - リアルタイム進捗監視
   - 処理中断・再開機能

4. **結果確認**
   - 処理結果サマリーの表示
   - 成功・失敗企業のリスト表示
   - ログの詳細確認

## 5. エラーハンドリング仕様

### 5.1 エラー分類と対応

#### 5.1.1 ネットワークエラー
```
エラー種別: DNS解決失敗, 接続タイムアウト, SSL証明書エラー
対応: 3回の自動リトライ → スキップ → 次企業へ進行
ログレベル: WARNING
ユーザー表示: "❌ 接続エラー: example.com にアクセスできません"
```

#### 5.1.2 フォーム検出エラー
```
エラー種別: フォーム要素なし, 送信ボタンなし, アクセス権限なし
対応: 代替ページ検索 → contact_urlの確認 → スキップ
ログレベル: INFO
ユーザー表示: "⚠️ フォームが見つかりません: example.com"
```

#### 5.1.3 入力エラー
```
エラー種別: フィールド入力失敗, バリデーションエラー, 必須項目不足
対応: 代替入力方法の試行 → 部分入力での送信試行 → 失敗記録
ログレベル: WARNING
ユーザー表示: "⚠️ 入力エラー: 一部フィールドの入力に失敗しました"
```

#### 5.1.4 CAPTCHA・認証エラー
```
エラー種別: reCAPTCHA検出, 画像認証, 電話認証
対応: 即座に処理停止 → 手動処理フラグ設定 → 次企業へ
ログレベル: INFO
ユーザー表示: "🔒 人間認証が必要です: 手動で処理してください"
```

### 5.2 ログ出力仕様

#### 5.2.1 ログレベル定義
- **DEBUG**: 詳細な処理情報（開発時のみ）
- **INFO**: 正常な処理完了、スキップ情報
- **WARNING**: 軽微なエラー、リトライ情報
- **ERROR**: 処理失敗、システムエラー
- **CRITICAL**: システム停止レベルのエラー

#### 5.2.2 ログフォーマット
```
[2024-07-28 17:35:23] INFO - 🏢 [15/30] 処理開始: 株式会社サンプル - https://example.com
[2024-07-28 17:35:25] INFO - 🔍 フォームページ判定: スコア8.5 (閾値7.0以上)
[2024-07-28 17:35:27] INFO - 📝 フォーム入力: 5フィールド検出 → 4フィールド入力成功
[2024-07-28 17:35:30] INFO - ✅ [15/30] 成功: 株式会社サンプル - フォーム送信完了
```

## 6. データ処理仕様

### 6.1 重複処理防止

#### 6.1.1 処理履歴管理
- **キー**: 企業名 + URL のハッシュ値
- **有効期間**: 30日間（設定で変更可能）
- **チェック機能**: 処理前の自動重複チェック
- **スキップ機能**: 重複企業の自動スキップ

#### 6.1.2 手動リセット機能
```python
# 特定企業の処理履歴をリセット
DELETE FROM processing_logs WHERE company_name = '株式会社サンプル';

# 全処理履歴をリセット（開発時）
DELETE FROM processing_logs WHERE action_type = 'form_processing';

# 古い履歴の自動削除（30日以上）
DELETE FROM processing_logs WHERE timestamp < datetime('now', '-30 days');
```

### 6.2 データ検証仕様

#### 6.2.1 CSV検証ルール
```python
validation_rules = {
    "company": {
        "required": True,
        "max_length": 100,
        "pattern": r"^[^\t\n\r]*$"  # タブ・改行なし
    },
    "url": {
        "required": True,
        "format": "url",
        "schemes": ["http", "https"]
    },
    "contact_url": {
        "required": False,
        "format": "url",
        "schemes": ["http", "https"]
    },
    "phone": {
        "required": False,
        "pattern": r"^[\d\-\(\)\+\s]*$"  # 数字・ハイフン・括弧・スペース
    },
    "postal_code": {
        "required": False,
        "pattern": r"^\d{3}-?\d{4}$"  # XXX-XXXX または XXXXXXX
    }
}
```

### 6.3 結果出力仕様

#### 6.3.1 処理結果CSVフォーマット
```csv
original_index,company,url,status,message,processed_at,form_fields_found,form_fields_filled,processing_time,final_url
1,株式会社A,https://a.com,success,フォーム送信完了,2024-07-28 17:35:30,5,4,45,https://a.com/thanks
2,株式会社B,https://b.com,failed,フォームが見つかりません,2024-07-28 17:36:15,0,0,30,https://b.com
```

#### 6.3.2 統計レポート生成
```json
{
  "summary": {
    "total_processed": 30,
    "successful": 22,
    "failed": 8,
    "success_rate": 73.3,
    "average_processing_time": 42.5,
    "start_time": "2024-07-28T17:30:00",
    "end_time": "2024-07-28T17:52:30"
  },
  "error_breakdown": {
    "network_errors": 3,
    "form_not_found": 4,
    "captcha_detected": 1
  },
  "field_statistics": {
    "avg_fields_found": 4.8,
    "avg_fields_filled": 4.2,
    "field_success_rate": 87.5
  }
}
```

## 7. セットアップ・デプロイメント要件

### 7.1 システム要件

#### 7.1.1 ハードウェア要件
- **CPU**: 2GHz以上のマルチコアプロセッサ
- **メモリ**: 4GB以上（推奨8GB）
- **ストレージ**: 1GB以上の空き容量
- **ネットワーク**: インターネット接続（10Mbps以上推奨）

#### 7.1.2 ソフトウェア要件
```bash
# Python環境
Python 3.8.0 以上

# 必須パッケージ
flask>=2.3.0
flask-socketio>=5.3.0
playwright>=1.30.0
pandas>=1.5.0
openpyxl>=3.1.0
requests>=2.28.0
beautifulsoup4>=4.11.0

# システムパッケージ（Ubuntu）
sudo apt-get install python3-dev python3-pip chromium-browser

# システムパッケージ（macOS）
brew install python@3.9 chromium

# システムパッケージ（Windows）
# Python 3.8+ をMicrosoft Storeまたは公式サイトからインストール
```

### 7.2 インストール手順

#### 7.2.1 自動セットアップスクリプト
```bash
#!/bin/bash
# setup.sh - 自動セットアップスクリプト

echo "🚀 フォーム営業システム セットアップ開始"

# Python バージョンチェック
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📋 Python バージョン: $python_version"

# 仮想環境作成
echo "📦 仮想環境作成中..."
python3 -m venv venv
source venv/bin/activate

# パッケージインストール
echo "📚 パッケージインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

# Playwright セットアップ
echo "🎭 Playwright セットアップ中..."
playwright install chromium

# ディレクトリ作成
echo "📁 ディレクトリ作成中..."
mkdir -p uploads
mkdir -p logs
mkdir -p backups

# 権限設定
chmod +x app.py

echo "✅ セットアップ完了！"
echo "🌐 起動コマンド: python app.py"
echo "🔗 アクセスURL: http://localhost:5000"
```

#### 7.2.2 設定ファイル
```python
# config.py - システム設定ファイル
import os

class Config:
    """システム設定クラス"""
    
    # Flask設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    
    # ファイル設定
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 処理設定
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 30))
    PROCESSING_INTERVAL = int(os.environ.get('PROCESSING_INTERVAL', 2))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    
    # データベース設定
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///form_sales.db')
    DATABASE_TIMEOUT = 30
    
    # ブラウザ設定
    BROWSER_HEADLESS = os.environ.get('BROWSER_HEADLESS', 'true').lower() == 'true'
    BROWSER_TIMEOUT = int(os.environ.get('BROWSER_TIMEOUT', 30))
    
    # ログ設定
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 30))
```

### 7.3 運用・保守要件

#### 7.3.1 ログローテーション
```python
# daily_maintenance.py - 日次メンテナンススクリ