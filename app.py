
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
    contact_url = company_data.get('contact_url')

    db = get_db()
    cursor = db.cursor()

    # 重複チェック
    company_hash = hashlib.sha256(f"{company_name}-{company_url}".encode()).hexdigest()
    cursor.execute("SELECT status FROM processing_logs WHERE company_name = ? AND url = ? AND timestamp > datetime('now', '-30 days')", (company_name, company_url))
    if cursor.fetchone():
        logger.info(f"[SKIP] {company_name} - {company_url}: Already processed within 30 days.")
        socketio.emit('processing_status', {'message': f'Skipped: {company_name} (already processed)', 'company': company_name, 'status': 'skipped'})
        return {'status': 'skipped', 'message': 'Already processed'}

    logger.info(f"[START] {company_name} - {company_url}")
    socketio.emit('processing_status', {'message': f'Processing: {company_name}', 'company': company_name, 'status': 'processing'})

    status = "failed"
    message = "Unknown error"
    processing_time = 0
    form_fields_found = 0
    form_fields_filled = 0
    error_details = ""
    page_title = ""
    final_url = company_url

    start_time = time.time()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=browser_config["headless"])
            page = await browser.new_page()
            await page.set_viewport_size(browser_config["viewport"])
            await page.set_extra_http_headers({'User-Agent': browser_config["user_agent"]})
            page.set_default_timeout(browser_config["timeout"])

            try:
                await page.goto(company_url, wait_until="networkidle")
                page_title = await page.title()
                final_url = page.url
            except Exception as e:
                error_details = f"Network Error: {e}"
                message = f"❌ 接続エラー: {company_url} にアクセスできません"
                logger.warning(f"Network Error for {company_url}: {e}")
                socketio.emit('processing_status', {'message': message, 'company': company_name, 'status': 'failed'})
                return {'status': 'failed', 'message': message, 'error_details': error_details}

            # フォーム検出
            html_content = await page.content()
            form_detector = FormDetector(html_content, final_url)
            is_form_page, score = form_detector.detect_form_page()
            logger.info(f"Form page detection for {company_name}: {is_form_page}, Score: {score}")

            if not is_form_page:
                # 代替ページ検索
                if contact_url:
                    try:
                        await page.goto(contact_url, wait_until="networkidle")
                        html_content = await page.content()
                        form_detector = FormDetector(html_content, page.url)
                        is_form_page, score = form_detector.detect_form_page()
                        if is_form_page:
                            logger.info(f"Form found on contact_url for {company_name}: {contact_url}")
                            final_url = page.url
                        else:
                            message = f"⚠️ フォームが見つかりません: {company_name} (contact_urlも含む)"
                            logger.info(message)
                            status = "failed"
                            error_details = "Form not found on main or contact URL."
                    except Exception as e:
                        message = f"⚠️ フォームが見つかりません: {company_name} (contact_urlアクセスエラー)"
                        logger.info(message)
                        status = "failed"
                        error_details = f"Form not found on main URL, and contact_url access error: {e}"
                else:
                    message = f"⚠️ フォームが見つかりません: {company_name}"
                    logger.info(message)
                    status = "failed"
                    error_details = "Form not found on main URL."

            if is_form_page:
                # フォーム入力
                current_form_data = FORM_DATA.copy()
                current_form_data['company_data']['target_company'] = company_name
                form_filler = FormFiller(page, current_form_data)
                
                try:
                    await form_filler.fill_form()
                    # TODO: 検出フィールド数と入力成功フィールド数を正確に取得するロジックを追加
                    form_fields_found = 0 # 仮
                    form_fields_filled = 0 # 仮

                    # CAPTCHA検出
                    if await page.locator("div[data-sitekey]").is_visible(timeout=5000): # reCAPTCHAの一般的なセレクタ
                        message = "🔒 人間認証が必要です: 手動で処理してください"
                        status = "failed"
                        error_details = "CAPTCHA detected."
                        logger.warning(f"CAPTCHA detected for {company_name}")
                    else:
                        # フォーム送信
                        if await form_filler.find_and_submit_form():
                            status = "success"
                            message = "フォーム送信完了"
                            logger.info(f"[SUCCESS] {company_name} - Form submitted.")
                        else:
                            status = "failed"
                            message = "送信ボタンが見つかりません/送信失敗"
                            error_details = "Submit button not found or submission failed."
                            logger.warning(f"Submit button not found or submission failed for {company_name}")
                except Exception as e:
                    status = "failed"
                    message = f"⚠️ 入力エラー: {e}"
                    error_details = f"Form filling/submission error: {e}"
                    logger.error(f"Form filling/submission error for {company_name}: {e}")
            
            await browser.close()

    except Exception as e:
        status = "failed"
        message = f"システムエラー: {e}"
        error_details = f"System error: {e}"
        logger.critical(f"Critical error during processing {company_name}: {e}")
    finally:
        processing_time = time.time() - start_time
        try:
            cursor.execute(
                "INSERT INTO processing_logs (company_name, url, status, message, processing_time, form_fields_found, form_fields_filled, error_details, page_title, final_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (company_name, company_url, status, message, processing_time, form_fields_found, form_fields_filled, error_details, page_title, final_url)
            )
            db.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error when logging for {company_name}: {e}")
            error_details += f" | DB Error: {e}"

        socketio.emit('processing_status', {'message': message, 'company': company_name, 'status': status})
        return {'status': status, 'message': message, 'company': company_name, 'processing_time': processing_time}

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
