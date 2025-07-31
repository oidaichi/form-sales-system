# 🤖 自動フォーム送信システム

LOVANTVICTORIAの営業活動用の自動フォーム入力・送信システムです。

## 📋 機能

- CSVファイルからURLリストを読み込み
- 各サイトのお問い合わせフォームを自動検出
- 会社情報を自動入力・送信
- リアルタイムでの進捗確認
- 処理結果の詳細レポート

## 🚀 使用方法

### 1. ファイル準備
`urls.csv` ファイルに対象サイトのURLを記載：
```csv
URL
https://example.com/contact
https://demo-site.com/inquiry
```

### 2. システム起動
```bash
python main.py
```

### 3. Web画面で操作
ブラウザで `http://localhost:5000` にアクセスし、「処理開始」ボタンをクリック

## 📦 Render デプロイ用ファイル

- `main.py` - メインアプリケーション
- `requirements-simple.txt` - 依存関係
- `urls.csv` - 対象URLリスト
- `templates/index.html` - Web画面

## 🏢 送信する会社情報

- **会社名**: LOVANTVICTORIA
- **代表者**: 冨安 朱
- **メール**: info@lovantvictoria.com
- **所在地**: 東京都目黒区八雲3-18-9
- **事業内容**: 生成AI技術の企業普及、AI研修、助成金活用支援

## ⚠️ 注意事項

- 正当な営業目的でのみ使用してください
- 各サイトの利用規約を確認してください
- 送信間隔は適切に設定されています（3秒間隔）
- エラーが発生したサイトは手動で確認してください

## 🔧 技術仕様

- **フレームワーク**: Flask
- **ブラウザ自動化**: Selenium + Chrome WebDriver
- **フォーム検出**: 複数パターンでの自動検出
- **デプロイ**: Render対応

## 📊 処理結果

- 成功/失敗の統計表示
- 詳細ログの自動保存
- 失敗したURLの別途出力