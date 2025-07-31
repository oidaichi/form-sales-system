
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import pandas as pd
import os
import asyncio
import time
from playwright.async_api import async_playwright
import csv_processor
from form_filler import FormFiller
from form_detector import FormDetector
from logger_config import setup_logging
from database import init_app, get_db
import sqlite3
import hashlib

app = Flask(__name__)
app.config.from_object('config.Config')
init_app(app)
socketio = SocketIO(app)

# ロギング設定
logger = setup_logging(log_level=app.config['LOG_LEVEL'])

# 標準入力データセット (README_システム概要.mdより)
FORM_DATA = {
  "company_data": {
    "target_company": "", # CSVから取得
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
    "privacy_agreement": True,
    "newsletter_subscription": False
  }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        processed_df, message = csv_processor.process_csv_file(filepath)

        if processed_df is None:
            return jsonify({'error': message}), 400
        
        # セッションではなく、JSONレスポンスで全データを返す
        all_data = processed_df.to_dict(orient='records')
        preview_data = processed_df.head().to_dict(orient='records')
        
        return jsonify({
            'message': 'File uploaded successfully', 
            'preview': preview_data, 
            'total_companies': len(processed_df),
            'processed_csv_data': all_data  # 全データを追加
        }), 200
    return jsonify({'error': 'Invalid file type'}), 400

@socketio.on('connect')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

async def process_company(company_data, browser_config):
    company_name = company_data['company']
    company_url = company_data['url']
    contact_url_from_csv = company_data.get('contact_url') # CSVから取得したcontact_url

    logger.info(f"[START] {company_name} - {company_url}")
    socketio.emit('processing_status', {'message': f'Processing: {company_name}', 'company': company_name, 'status': 'processing'})

    status = "failed"
    message = "Unknown error"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=browser_config["headless"])
            page = await browser.new_page()
            await page.set_viewport_size(browser_config["viewport"])
            await page.set_extra_http_headers({'User-Agent': browser_config["user_agent"]})
            page.set_default_timeout(browser_config["timeout"])

            # 1. 企業URLにアクセス
            try:
                await page.goto(company_url, wait_until="networkidle")
                page_title = await page.title()
                current_url = page.url
                logger.info(f"Accessed {company_url}. Current URL: {current_url}")
            except Exception as e:
                message = f"❌ URLアクセスエラー: {company_url} - {e}"
                logger.error(message)
                await browser.close()
                socketio.emit('processing_status', {'message': message, 'company': company_name, 'status': 'failed'})
                return {'status': 'failed', 'message': message, 'company': company_name}

            # 2. お問い合わせページの特定と遷移
            form_detector = FormDetector(await page.content(), current_url)
            contact_links = form_detector.find_contact_links()
            
            target_contact_url = None

            # CSVにcontact_urlがあれば最優先
            if contact_url_from_csv and form_detector._is_valid_http_url(contact_url_from_csv):
                target_contact_url = contact_url_from_csv
                logger.info(f"Using contact_url from CSV: {target_contact_url}")
            elif contact_links:
                target_contact_url = contact_links[0] # 最もスコアの高いリンクを使用
                logger.info(f"Found contact link: {target_contact_url}")
            
            if target_contact_url:
                try:
                    await page.goto(target_contact_url, wait_until="networkidle")
                    current_url = page.url
                    logger.info(f"Navigated to potential contact page: {current_url}")
                    
                    # 遷移先がフォームページか再判定
                    form_detector_on_contact_page = FormDetector(await page.content(), current_url)
                    is_form_page, score = form_detector_on_contact_page.detect_form_page()

                    if is_form_page:
                        logger.info(f"Form page detected with score {score} at {current_url}")
                        # ここでフォーム入力・送信ロジックを呼び出す
                        # 現時点ではまだ実装されていないため、成功として終了
                        status = "success"
                        message = f"お問い合わせページ検出・遷移成功: {current_url}"
                    else:
                        status = "failed"
                        message = f"お問い合わせページにフォームが見つかりませんでした: {current_url}"
                        logger.warning(message)

                except Exception as e:
                    status = "failed"
                    message = f"お問い合わせページへの遷移エラー: {target_contact_url} - {e}"
                    logger.error(message)
            else:
                status = "failed"
                message = "お問い合わせページへのリンクが見つかりませんでした。"
                logger.warning(message)
            
            # スクリーンショットを撮る (デバッグ用)
            screenshot_path = f"screenshots/{company_name.replace('/', '_')}_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            await browser.close()

    except Exception as e:
        message = f"システムエラー: {e}"
        logger.critical(f"Critical error during processing {company_name}: {e}")
    finally:
        socketio.emit('processing_status', {'message': message, 'company': company_name, 'status': status})
        return {'status': status, 'message': message, 'company': company_name}

@socketio.on('start_processing')
def start_processing(data):
    if 'csv_data' not in data or not data['csv_data']:
        emit('processing_complete', {'message': 'No CSV data received. Please upload a CSV first.'})
        return

    companies_to_process = data['csv_data']
    total_companies = len(companies_to_process)
    browser_config = {
        "headless": app.config['BROWSER_HEADLESS'],
        "viewport": {"width": 1280, "height": 720}, # 少し小さくして視認性を上げる
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "timeout": app.config['BROWSER_TIMEOUT'] * 1000,
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "accept_downloads": False
    }

    emit('processing_start', {'total_companies': total_companies})
    logger.info(f"Processing started for {total_companies} companies.")

    # eventlet.spawnを使用してバックグラウンドで処理を実行
    socketio.start_background_task(
        target=_run_processing_loop, 
        companies=companies_to_process, 
        browser_config=browser_config
    )

def _run_processing_loop(companies, browser_config):
    """会社リストを順番に処理するループ"""
    total_companies = len(companies)
    for i, company_data in enumerate(companies):
        logger.info(f"Processing batch {i + 1} / {total_companies}")
        result = asyncio.run(process_company(company_data, browser_config))
        
        socketio.emit('processing_progress', {
            'progress': int(((i + 1) / total_companies) * 100),
            'current_index': i,
            'current_company': result.get('company', 'N/A'),
            'status': result.get('status', 'N/A'),
            'message': result.get('message', 'N/A'),
            'processed_count': i + 1,
            'total_companies': total_companies
        })
        socketio.sleep(app.config['PROCESSING_INTERVAL']) # 企業間のインターバル

    logger.info("All companies processed.")
    socketio.emit('processing_complete', {'message': '全ての処理が完了しました。'})



if __name__ == '__main__':
    # eventletを使用して非同期処理を有効にする
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
