# 🚀 GCE Ubuntu環境での自動フォーム送信システム セットアップガイド

## ❌ 重要: App Engineでは動作しません！

**`gcloud app deploy`は使用できません。** このアプリはSelenium WebDriverを使用するため、GCE VM インスタンスで実行する必要があります。

## 📋 前提条件
- GCP Compute Engine (Ubuntu 22.04 LTS推奨)
- gcloud CLI設定済み
- プロジェクト作成済み
- 課金設定済み

## 🚀 簡単デプロイ（推奨）

### 自動デプロイスクリプトを使用
```bash
# プロジェクトIDを指定して実行
./deploy_gce.sh your-project-id
```

このスクリプトで以下が自動実行されます：
- GCE VMインスタンスの作成
- ファイアウォール設定
- アプリケーションのデプロイ
- 自動起動

実行後、表示されるURLにアクセスしてください。

---

## 🔧 手動インストール手順

### 1. GCE VMインスタンス作成
```bash
gcloud compute instances create form-automation-vm \
    --zone=asia-northeast1-a \
    --machine-type=e2-medium \
    --boot-disk-size=30GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --tags=http-server,https-server

# ファイアウォール設定
gcloud compute firewall-rules create allow-form-automation \
    --allow tcp:5000 \
    --source-ranges 0.0.0.0/0
```

### 2. SSH接続とセットアップ
```bash
# SSH接続
gcloud compute ssh form-automation-vm --zone=asia-northeast1-a

# リポジトリクローン
git clone https://github.com/oidaichi/form-sales-system.git
cd form-sales-system
```

### 3. システムの自動セットアップ
```bash
# セットアップスクリプトを実行
./setup_gce.sh
```

このスクリプトで以下が自動実行されます：
- システムパッケージの更新
- Google Chrome Stableのインストール
- GUIデスクトップ環境のセットアップ
- Python依存関係のインストール
- 必要な環境変数の設定

### 2. GCE環境でのGUI設定

#### デスクトップ環境での起動（推奨）
```bash
# GCEインスタンスでデスクトップ環境を起動
# RDP接続またはVNC接続でGUIデスクトップにアクセス
export DISPLAY=:0
```

#### 仮想ディスプレイでの起動（ヘッドレス環境）
```bash
source ~/.bashrc
export DISPLAY=:99
# Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
```

### 3. ブラウザ動作テスト
```bash
# GUI環境でのブラウザ動作をテスト
python3 test_gui_browser.py
```

### 4. システム起動
```bash
python3 app.py
```

## 🌐 アクセス方法

### ローカルアクセス
```
http://127.0.0.1:5000
http://localhost:5000
```

### 外部アクセス (GCE外部IP)
```
http://[EXTERNAL_IP]:5000
```

**注意**: 外部アクセスの場合、GCPのファイアウォール設定でポート5000を開放する必要があります。

## 🔒 ファイアウォール設定 (GCP Console)

1. GCP Console → VPC Network → Firewall
2. "Create Firewall Rule" をクリック
3. 以下を設定：
   - Name: `allow-form-automation-5000`
   - Direction: Ingress
   - Action: Allow
   - Targets: All instances in the network
   - Source IP ranges: `0.0.0.0/0`
   - Protocols and ports: TCP → 5000

## 🛠️ トラブルシューティング

### Chrome起動エラー
```bash
sudo apt install --fix-broken
sudo apt install -y google-chrome-stable
```

### Display設定エラー
```bash
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
```

### WebDriver権限エラー
```bash
sudo chown -R $USER:$USER ~/.wdm
chmod 755 ~/.wdm/drivers/chromedriver/*/chromedriver
```

### ポート5000が使用中
```bash
sudo lsof -i :5000
sudo kill -9 [PID]
```

## 📊 システム動作確認

### 1. Chrome動作確認
```bash
google-chrome --version
google-chrome --headless --disable-gpu --dump-dom https://www.google.com
```

### 2. WebDriver動作確認
```bash
python3 -c "
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.binary_location = '/usr/bin/google-chrome'

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get('https://www.google.com')
print('✅ WebDriver動作正常')
driver.quit()
"
```

## 🔍 ログ確認
```bash
# アプリケーションログ
tail -f form_automation.log

# システムログ
journalctl -f
```

## 💡 最適化設定

### メモリ使用量の削減
```bash
# スワップファイルの作成 (必要に応じて)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### セキュリティ設定
```bash
# UFWファイアウォールの設定
sudo ufw enable
sudo ufw allow 22
sudo ufw allow 5000
```

## 🚨 本番運用時の注意点

1. **セキュリティ**: 本番環境では適切なアクセス制限を設定
2. **モニタリング**: システムリソースの監視を設定
3. **バックアップ**: 重要なデータの定期バックアップ
4. **ログローテーション**: ログファイルの自動ローテーション設定

## 📞 サポート

システムに関する問題や質問がある場合は、ログファイルと共にお問い合わせください。