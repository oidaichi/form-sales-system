#!/usr/bin/env python3
"""
ポート8080でのテストサーバー
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
    <head><title>接続テスト成功!</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>🎉 接続成功!</h1>
        <h2>自動フォーム送信システム</h2>
        <p>Flask サーバーが正常に動作しています</p>
        <p><strong>ポート:</strong> 8080</p>
        <p><strong>URL:</strong> http://127.0.0.1:8080</p>
        <hr>
        <p>システムが正常に動作していることを確認しました。</p>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 テストサーバー起動中...")
    print("ブラウザで以下のURLにアクセス:")
    print("👉 http://127.0.0.1:8080")
    print("👉 http://localhost:8080")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)