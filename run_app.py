#!/usr/bin/env python3
"""
自動フォーム送信システム - 直接実行版
WSL2/Linux環境対応
"""

import os
import json
import csv
import time
import logging
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

app = Flask(__name__)

# 処理状況
status = {
    "is_running": False,
    "current_url": "",
    "total_urls": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "results": []
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>🤖 自動フォーム送信システム - LOVANTVICTORIA</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .company-info { background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .status-panel { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff; }
        .controls { text-align: center; margin: 30px 0; }
        button { padding: 15px 30px; margin: 0 10px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .btn-start { background: #28a745; color: white; }
        .btn-start:hover { background: #218838; }
        .btn-stop { background: #dc3545; color: white; }
        .btn-stop:disabled { background: #6c757d; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #ddd; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .progress-bar { width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; margin: 10px 0; }
        .progress-fill { height: 100%; background: #007bff; border-radius: 10px; transition: width 0.3s; }
        .results { margin-top: 30px; }
        .result-item { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; }
        .failed { background: #f8d7da; color: #721c24; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 自動フォーム送信システム</h1>
        
        <div class="company-info">
            <h3>📋 送信する会社情報</h3>
            <p><strong>会社名:</strong> LOVANTVICTORIA</p>
            <p><strong>代表者:</strong> 冨安 朱</p>
            <p><strong>メール:</strong> info@lovantvictoria.com</p>
            <p><strong>所在地:</strong> 東京都目黒区八雲3-18-9</p>
            <p><strong>事業内容:</strong> 生成AI技術の企業普及、AI研修、助成金活用支援</p>
        </div>

        <div class="status-panel">
            <h3>📊 システム状況</h3>
            <p id="status-text">待機中</p>
            <p id="current-url"></p>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
            </div>
            <p id="progress-text">0 / 0 処理完了</p>
        </div>

        <div class="controls">
            <button id="start-btn" class="btn-start" onclick="startProcess()">
                <span id="start-text">🚀 処理開始</span>
            </button>
            <button id="stop-btn" class="btn-stop" onclick="stopProcess()" disabled>
                ⏹️ 処理停止
            </button>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="total-count">0</div>
                <div>総URL数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="success-count">0</div>
                <div>成功</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="failed-count">0</div>
                <div>失敗</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="processed-count">0</div>
                <div>処理済み</div>
            </div>
        </div>

        <div class="results" id="results-section" style="display: none;">
            <h3>📈 処理結果</h3>
            <div id="results-list"></div>
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('total-count').textContent = data.total_urls;
                    document.getElementById('success-count').textContent = data.success;
                    document.getElementById('failed-count').textContent = data.failed;
                    document.getElementById('processed-count').textContent = data.processed;

                    const progress = data.total_urls > 0 ? (data.processed / data.total_urls) * 100 : 0;
                    document.getElementById('progress-fill').style.width = progress + '%';
                    document.getElementById('progress-text').textContent = data.processed + ' / ' + data.total_urls + ' 処理完了';

                    if (data.is_running) {
                        document.getElementById('status-text').innerHTML = '<span class="loading"></span> 処理中...';
                        document.getElementById('current-url').textContent = data.current_url ? '現在処理中: ' + data.current_url : '';
                        document.getElementById('start-btn').disabled = true;
                        document.getElementById('stop-btn').disabled = false;
                        document.getElementById('start-text').textContent = '処理中...';
                    } else {
                        document.getElementById('status-text').textContent = data.processed > 0 ? '処理完了' : '待機中';
                        document.getElementById('current-url').textContent = '';
                        document.getElementById('start-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = true;
                        document.getElementById('start-text').textContent = '🚀 処理開始';
                    }

                    if (data.results && data.results.length > 0) {
                        showResults(data.results);
                    }
                })
                .catch(error => console.error('Status update error:', error));
        }

        function showResults(results) {
            const resultsSection = document.getElementById('results-section');
            const resultsList = document.getElementById('results-list');
            
            resultsList.innerHTML = '';
            results.forEach(result => {
                const div = document.createElement('div');
                div.className = 'result-item ' + (result.status === 'success' ? 'success' : 'failed');
                div.innerHTML = '<strong>' + result.url + '</strong> - ' + 
                               (result.status === 'success' ? '✅ 成功' : '❌ 失敗') + 
                               ' (' + result.message + ')';
                resultsList.appendChild(div);
            });
            
            resultsSection.style.display = 'block';
        }

        function startProcess() {
            fetch('/api/start', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('エラー: ' + data.error);
                    } else {
                        alert('処理を開始しました！総URL数: ' + data.total_urls);
                    }
                })
                .catch(error => alert('処理開始でエラーが発生しました: ' + error));
        }

        function stopProcess() {
            fetch('/api/stop', { method: 'POST' })
                .then(() => alert('処理を停止しました'))
                .catch(error => alert('停止でエラーが発生しました: ' + error));
        }

        // 初期化と定期更新
        updateStatus();
        setInterval(updateStatus, 3000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    return jsonify(status)

@app.route('/api/start', methods=['POST'])
def start_automation():
    if status["is_running"]:
        return jsonify({"error": "Already running"}), 400
    
    # URLリストの読み込み
    urls = []
    if os.path.exists('urls.csv'):
        with open('urls.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # ヘッダーをスキップ
            urls = [row[0].strip() for row in reader if row and row[0].strip()]
    
    if not urls:
        return jsonify({"error": "urls.csvにURLが見つかりません"}), 400
    
    # ステータス初期化
    status.update({
        "is_running": True,
        "total_urls": len(urls),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "results": []
    })
    
    # バックグラウンドで処理開始
    import threading
    thread = threading.Thread(target=run_automation, args=(urls,))
    thread.start()
    
    return jsonify({"message": "処理開始", "total_urls": len(urls)})

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    status["is_running"] = False
    return jsonify({"message": "処理停止"})

def run_automation(urls):
    """自動化処理の実行"""
    for i, url in enumerate(urls):
        if not status["is_running"]:
            break
            
        status["current_url"] = url
        
        # 簡易処理（実際の処理に置き換え）
        result = {
            "url": url,
            "status": "success" if i % 2 == 0 else "failed",  # デモ用
            "message": "フォーム送信完了" if i % 2 == 0 else "フォームが見つかりません",
            "timestamp": datetime.now().isoformat()
        }
        
        status["results"].append(result)
        status["processed"] += 1
        
        if result["status"] == "success":
            status["success"] += 1
        else:
            status["failed"] += 1
        
        time.sleep(2)  # 処理間隔
    
    status["is_running"] = False
    status["current_url"] = ""

if __name__ == '__main__':
    # urls.csvの作成
    if not os.path.exists('urls.csv'):
        with open('urls.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL'])
            writer.writerow(['https://example.com/contact'])
            writer.writerow(['https://demo-site.com/inquiry'])
    
    print("\n" + "="*60)
    print("🚀 自動フォーム送信システム - LOVANTVICTORIA")
    print("="*60)
    print("ブラウザで以下のURLにアクセスしてください:")
    print("👉 http://127.0.0.1:8080")
    print("👉 http://localhost:8080")
    print("="*60)
    print("✅ システム準備完了！")
    print("✅ 会社情報設定済み: LOVANTVICTORIA")
    print("✅ urls.csvを編集して対象URLを設定してください")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)