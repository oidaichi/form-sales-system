# ❌ Google App Engine では動作しません

## 🚫 重要な注意事項

**このアプリケーションは Google App Engine での実行に対応していません。**

### ❌ App Engine で動作しない理由

1. **Selenium WebDriver が動作しない**
   - App Engine はサーバーレス環境
   - Chrome/Chromium ブラウザがインストールされていない
   - GUI アプリケーションの実行不可

2. **システム要件の非互換**
   - ブラウザの新しいタブ作成・操作が必要
   - ファイルシステムへの書き込みが制限
   - 長時間実行プロセスが制限

3. **Service Unavailable エラーの原因**
   - WebDriver の初期化失敗
   - Chrome バイナリが見つからない
   - ディスプレイ環境が存在しない

## ✅ 正しい実行環境

### Google Compute Engine (GCE) を使用してください

```bash
# 自動デプロイスクリプトを使用（推奨）
./deploy_gce.sh your-project-id
```

### または手動でGCE VMインスタンスを作成

```bash
# VMインスタンス作成
gcloud compute instances create form-automation-vm \
    --zone=asia-northeast1-a \
    --machine-type=e2-medium \
    --boot-disk-size=30GB \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud

# SSH接続
gcloud compute ssh form-automation-vm --zone=asia-northeast1-a

# アプリケーションセットアップ
git clone https://github.com/oidaichi/form-sales-system.git
cd form-sales-system
./setup_gce.sh
python3 app.py
```

## 📚 詳細情報

詳しいセットアップ手順は `README_GCE.md` をご確認ください。

---

**※ `gcloud app deploy` ではなく、GCE VM インスタンスを使用してください。**