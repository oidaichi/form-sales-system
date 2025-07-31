#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動フォーム送信システム - メインアプリケーション
LOVANTVICTORIA営業支援システム
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import threading
import logging

# フォーム自動化ロジックをインポート
from form_automation import process_urls, setup_logging

# Flaskアプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = 'lovantvictoria-form-automation-2025'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB制限

# アップロードフォルダを作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ロギング設定
setup_logging()
logger = logging.getLogger(__name__)

# グローバル変数で処理状態を管理
processing_status = {
    'is_running': False,
    'current_url': '',
    'total_urls': 0,
    'processed': 0,
    'success': 0,
    'failed': 0,
    'results': [],
    'output_file': None
}

# グローバルで実行中のスレッドとWebDriverを管理
current_thread = None
current_driver = None

def allowed_file(filename):
    """アップロード可能なファイル形式をチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx', 'xls'}

@app.route('/')
def index():
    """メインページを表示"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """ファイルアップロードを処理"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'ファイルが選択されていません'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # タイムスタンプを追加してファイル名の重複を避ける
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # ファイルを読み取ってURL数をカウント
            from form_automation import read_input_file, get_target_urls
            
            try:
                df = read_input_file(filepath)
                urls = get_target_urls(df)
                url_count = len(urls)
                
                logger.info(f"ファイルアップロード成功: {filename}, URL数: {url_count}")
                return jsonify({
                    'message': 'ファイルアップロード成功',
                    'filename': filename,
                    'filepath': filepath,
                    'url_count': url_count,
                    'total_rows': len(df)
                })
                
            except Exception as e:
                logger.error(f"ファイル解析エラー: {str(e)}")
                return jsonify({
                    'message': 'ファイルアップロード成功（URL数解析失敗）',
                    'filename': filename,
                    'filepath': filepath,
                    'url_count': 0,
                    'error': f'ファイル解析エラー: {str(e)}'
                })
        else:
            return jsonify({'error': 'CSVまたはExcelファイルを選択してください'}), 400
            
    except Exception as e:
        logger.error(f"ファイルアップロードエラー: {str(e)}")
        return jsonify({'error': f'アップロードエラー: {str(e)}'}), 500

@app.route('/start_processing', methods=['POST'])
def start_processing():
    """フォーム送信処理を開始"""
    try:
        if processing_status['is_running']:
            return jsonify({'error': '既に処理中です'}), 400
        
        data = request.get_json()
        if not data or 'filepath' not in data:
            return jsonify({'error': 'ファイルパスが指定されていません'}), 400
        
        filepath = data['filepath']
        if not os.path.exists(filepath):
            return jsonify({'error': 'ファイルが見つかりません'}), 400
        
        # 処理状態を初期化
        processing_status.update({
            'is_running': True,
            'current_url': '',
            'total_urls': 0,
            'processed': 0,
            'success': 0,
            'failed': 0,
            'results': [],
            'output_file': None
        })
        
        # バックグラウンドで処理を開始
        global current_thread
        current_thread = threading.Thread(
            target=run_automation_background,
            args=(filepath,)
        )
        current_thread.daemon = True
        current_thread.start()
        
        logger.info(f"自動化処理開始: {filepath}")
        return jsonify({'message': '処理を開始しました'})
        
    except Exception as e:
        logger.error(f"処理開始エラー: {str(e)}")
        return jsonify({'error': f'処理開始エラー: {str(e)}'}), 500

def run_automation_background(filepath):
    """バックグラウンドで自動化処理を実行"""
    global current_driver
    try:
        # フォーム自動化処理を実行
        # WebDriverコールバック関数を定義
        def set_current_driver(driver):
            global current_driver
            current_driver = driver
        
        result = process_urls(
            filepath,
            processing_status,
            update_status_callback,
            driver_callback=set_current_driver
        )
        
        # 処理完了
        processing_status['is_running'] = False
        processing_status['output_file'] = result.get('output_file')
        
        logger.info(f"処理完了: 成功={processing_status['success']}, 失敗={processing_status['failed']}")
        
        # WebDriver参照をクリア
        current_driver = None
        
    except Exception as e:
        logger.error(f"バックグラウンド処理エラー: {str(e)}")
        processing_status['is_running'] = False
        current_driver = None

def update_status_callback(current_url, processed, success, failed, total, results):
    """処理状況を更新するコールバック関数"""
    processing_status.update({
        'current_url': current_url,
        'processed': processed,
        'success': success,
        'failed': failed,
        'total_urls': total,
        'results': results
    })

@app.route('/status')
def get_status():
    """現在の処理状況を取得"""
    return jsonify(processing_status)

@app.route('/stop', methods=['POST'])
def stop_processing():
    """処理を停止"""
    try:
        global current_driver, current_thread
        
        # 処理状態を停止に設定
        processing_status['is_running'] = False
        logger.info("処理停止要求")
        
        # WebDriverが存在する場合は強制終了
        if current_driver:
            try:
                logger.info("WebDriverを強制終了中...")
                current_driver.quit()
                current_driver = None
                logger.info("WebDriver終了完了")
            except Exception as e:
                logger.warning(f"WebDriver終了エラー（無視）: {str(e)}")
        
        # スレッドが存在し実行中の場合は終了を待機
        if current_thread and current_thread.is_alive():
            logger.info("バックグラウンドスレッドの終了を待機中...")
            # スレッドの終了を少し待機（最大3秒）
            current_thread.join(timeout=3)
            if current_thread.is_alive():
                logger.warning("スレッドが終了しませんでしたが、処理を続行します")
            current_thread = None
        
        return jsonify({'message': '処理を停止しました'})
    except Exception as e:
        logger.error(f"処理停止エラー: {str(e)}")
        return jsonify({'error': f'停止エラー: {str(e)}'}), 500

@app.route('/download')
def download_result():
    """処理結果ファイルをダウンロード"""
    try:
        output_file = processing_status.get('output_file')
        if not output_file or not os.path.exists(output_file):
            return jsonify({'error': '結果ファイルが見つかりません'}), 404
        
        logger.info(f"結果ファイルダウンロード: {output_file}")
        return send_file(
            output_file,
            as_attachment=True,
            download_name=os.path.basename(output_file)
        )
    except Exception as e:
        logger.error(f"ダウンロードエラー: {str(e)}")
        return jsonify({'error': f'ダウンロードエラー: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    """404エラーハンドラ"""
    return jsonify({'error': 'ページが見つかりません'}), 404

@app.errorhandler(500)
def internal_error(error):
    """500エラーハンドラ"""
    logger.error(f"内部エラー: {str(error)}")
    return jsonify({'error': '内部サーバーエラーが発生しました'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🤖 LOVANTVICTORIA 自動フォーム送信システム")
    print("=" * 60)
    print("📡 サーバー起動中...")
    print("🌐 アクセス方法:")
    print("   👉 ローカル: http://127.0.0.1:5000")
    print("   👉 ローカル: http://localhost:5000")
    print("   👉 GCE外部: http://[EXTERNAL_IP]:5000")
    print("=" * 60)
    print("✅ システム準備完了")
    print("✅ ファイルアップロード機能: 有効")
    print("✅ フォーム自動送信機能: 有効")
    print("✅ 結果ダウンロード機能: 有効")
    print("")
    print("💡 GCE環境での初回起動時:")
    print("   1. ./setup_gce.sh でセットアップ実行")
    print("   2. source ~/.bashrc で環境変数読み込み")
    print("   3. export DISPLAY=:99 でディスプレイ設定")
    print("=" * 60)
    
    # GCE本番環境対応（外部からのアクセスを許可）
    app.run(host='0.0.0.0', port=5000, debug=False)