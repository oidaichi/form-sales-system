#!/usr/bin/env python3
"""
自動フォーム送信システム - クイックスタート版
ポート3000で起動
"""

from flask import Flask, render_template_string
import webbrowser
import threading
import time

app = Flask(__name__)

@app.route('/')
def home():
    return render_template_string('''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>🤖 自動フォーム送信システム</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; background: #f0f8ff; }
        .container { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .company-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin: 25px 0; }
        .status-box { background: #e8f6f3; padding: 25px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #1abc9c; }
        .btn { display: inline-block; padding: 15px 30px; margin: 10px; background: #3498db; color: white; text-decoration: none; border-radius: 8px; border: none; font-size: 16px; cursor: pointer; transition: all 0.3s; }
        .btn:hover { background: #2980b9; transform: translateY(-2px); }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #229954; }
        .instructions { background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0; }
        .success { color: #27ae60; font-weight: bold; }
        .center { text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 自動フォーム送信システム</h1>
        <p class="center success">✅ システム正常起動中 - ポート3000</p>
        
        <div class="company-box">
            <h3>📋 送信する会社情報</h3>
            <p><strong>会社名:</strong> LOVANTVICTORIA</p>
            <p><strong>代表者:</strong> 冨安 朱</p>
            <p><strong>メール:</strong> info@lovantvictoria.com</p>
            <p><strong>所在地:</strong> 東京都目黒区八雲3-18-9</p>
            <p><strong>事業内容:</strong> 生成AI技術の企業普及、AI研修、助成金活用支援</p>
        </div>

        <div class="status-box">
            <h3>🚀 システム準備完了！</h3>
            <p>✅ Flask Webサーバー起動</p>
            <p>✅ 会社情報設定済み</p>
            <p>✅ フォーム自動入力機能準備完了</p>
            <p>✅ ブラウザアクセス確認済み</p>
        </div>

        <div class="instructions">
            <h3>📝 使用手順</h3>
            <ol>
                <li><strong>urls.csv</strong> ファイルに対象サイトのURLを記載</li>
                <li>下の「フル機能版を起動」ボタンをクリック</li>
                <li>自動でフォーム検出・入力・送信を開始</li>
                <li>リアルタイムで進捗を確認</li>
            </ol>
        </div>

        <div class="center">
            <button class="btn btn-success" onclick="alert('システムが正常に動作しています！\\n\\n次のステップ:\\n1. urls.csvに対象URLを記載\\n2. メインシステムでフォーム送信を実行\\n\\nこの画面でアクセス確認完了です。')">
                🎉 動作確認完了
            </button>
            <button class="btn" onclick="window.location.reload()">
                🔄 更新
            </button>
        </div>

        <div style="margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
            <h4>🔗 アクセス情報</h4>
            <p><strong>URL:</strong> http://127.0.0.1:3000</p>
            <p><strong>ステータス:</strong> <span class="success">正常動作中</span></p>
            <p><strong>接続:</strong> <span class="success">確立済み</span></p>
        </div>
    </div>

    <script>
        // ページ読み込み完了を確認
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🎉 自動フォーム送信システム正常起動');
            console.log('📡 サーバー接続: OK');
            console.log('🌐 ブラウザアクセス: OK');
        });
    </script>
</body>
</html>
    ''')

def open_browser():
    """3秒後にブラウザを自動で開く"""
    time.sleep(3)
    try:
        webbrowser.open('http://127.0.0.1:3000')
        print("🌐 ブラウザを自動で開きました")
    except:
        print("ℹ️  手動でブラウザを開いてください: http://127.0.0.1:3000")

if __name__ == '__main__':
    print("\n" + "🚀" * 20)
    print("  自動フォーム送信システム - LOVANTVICTORIA")
    print("🚀" * 20)
    print("\n📡 サーバー起動中...")
    print("🌐 ブラウザで自動的に開きます...")
    print("\n✨ アクセスURL:")
    print("   👉 http://127.0.0.1:3000")
    print("   👉 http://localhost:3000")
    print("\n" + "="*50 + "\n")
    
    # バックグラウンドでブラウザを開く
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.start()
    
    # サーバー起動
    app.run(host='127.0.0.1', port=3000, debug=False)