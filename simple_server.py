#!/usr/bin/env python3
"""
簡単な自動フォーム送信システム - テスト版
"""

from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>自動フォーム送信システム - テスト</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        .container { background: #f9f9f9; padding: 30px; border-radius: 10px; }
        h1 { color: #333; text-align: center; }
        .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
        button { background: #28a745; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #218838; }
        .info { background: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 自動フォーム送信システム</h1>
        
        <div class="info">
            <h3>システム情報</h3>
            <p><strong>状態:</strong> テストモードで正常動作中</p>
            <p><strong>サーバー:</strong> Flask 開発サーバー</p>
            <p><strong>アクセス:</strong> http://127.0.0.1:5000</p>
        </div>

        <div class="status">
            <h3>送信する会社情報</h3>
            <p><strong>会社名:</strong> LOVANTVICTORIA</p>
            <p><strong>代表者:</strong> 冨安 朱</p>
            <p><strong>メール:</strong> info@lovantvictoria.com</p>
            <p><strong>所在地:</strong> 東京都目黒区八雲3-18-9</p>
            <p><strong>事業内容:</strong> 生成AI技術の企業普及、AI研修、助成金活用支援</p>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <button onclick="testConnection()">接続テスト</button>
            <button onclick="alert('フルシステムは main.py で起動してください')">処理開始（デモ）</button>
        </div>

        <div id="result" style="margin-top: 20px;"></div>
    </div>

    <script>
        function testConnection() {
            fetch('/api/test')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('result').innerHTML = 
                        '<div style="background: #d4edda; color: #155724; padding: 15px; border-radius: 5px;">' +
                        '<strong>接続成功!</strong> サーバーは正常に動作しています。<br>' +
                        'メッセージ: ' + data.message + '</div>';
                })
                .catch(error => {
                    document.getElementById('result').innerHTML = 
                        '<div style="background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px;">' +
                        '<strong>接続エラー:</strong> ' + error + '</div>';
                });
        }
    </script>
</body>
</html>
    '''

@app.route('/api/test')
def test_api():
    return jsonify({
        "status": "success",
        "message": "Flask サーバーが正常に動作しています！",
        "system": "自動フォーム送信システム"
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 自動フォーム送信システム - テスト版")
    print("=" * 50)
    print("ブラウザで以下のURLにアクセスしてください:")
    print("http://127.0.0.1:5000")
    print("http://localhost:5000")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=5000, debug=True)