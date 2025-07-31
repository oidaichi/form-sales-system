#!/usr/bin/env python3
"""
自動フォーム送信システム
Render対応の簡単な営業フォーム自動入力システム
"""

import os
import json
import csv
import time
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('form_automation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask アプリケーション
app = Flask(__name__)

# 会社情報設定
COMPANY_INFO = {
    "company_name": "LOVANTVICTORIA",
    "representative": "冨安 朱",
    "address": "東京都目黒区八雲3-18-9",
    "email": "info@lovantvictoria.com",
    "phone": "080-XXXX-XXXX",
    "business_content": "生成AI技術の企業普及、AI研修、助成金活用支援",
    "message": """こんにちは、LOVANTVICTORIAの冨安と申します。

弊社は生成AI技術の企業普及を通じて、企業のデジタル変革を支援しております。
特に中小企業様向けのAI研修や助成金活用支援に力を入れており、
貴社のお役に立てる可能性があると考え、ご連絡いたします。

もしご興味がございましたら、お気軽にお返事いただければと思います。
どうぞよろしくお願いいたします。"""
}

# グローバル変数
processing_status = {
    "is_running": False,
    "current_url": "",
    "total_urls": 0,
    "processed": 0,
    "success": 0,
    "failed": 0,
    "results": []
}

class FormAutomation:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Chrome WebDriverの設定"""
        chrome_options = Options()
        
        # Render環境用の設定
        if os.environ.get('RENDER'):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--remote-debugging-port=9222')
        
        # 基本設定
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("WebDriver setup successful")
            return True
        except Exception as e:
            logger.error(f"WebDriver setup failed: {e}")
            return False
    
    def detect_form_fields(self):
        """フォームフィールドの検出"""
        fields = {}
        
        # フィールド候補の定義
        field_patterns = {
            'name': ['name', 'お名前', '氏名', 'username', 'your-name'],
            'company': ['company', '会社名', 'organization', 'corp', 'your-company'],
            'email': ['email', 'mail', 'メール', 'e-mail', 'your-email'],
            'phone': ['phone', 'tel', '電話', '電話番号', 'your-phone'],
            'message': ['message', 'content', 'body', 'inquiry', 'comment', 'お問い合わせ', 'your-message']
        }
        
        for field_type, patterns in field_patterns.items():
            element = None
            
            # name属性で検索
            for pattern in patterns:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, f'input[name*="{pattern}"], textarea[name*="{pattern}"]')
                    break
                except NoSuchElementException:
                    continue
            
            # id属性で検索
            if not element:
                for pattern in patterns:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, f'input[id*="{pattern}"], textarea[id*="{pattern}"]')
                        break
                    except NoSuchElementException:
                        continue
            
            # placeholder属性で検索
            if not element:
                for pattern in patterns:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, f'input[placeholder*="{pattern}"], textarea[placeholder*="{pattern}"]')
                        break
                    except NoSuchElementException:
                        continue
            
            if element:
                fields[field_type] = element
                logger.info(f"Found {field_type} field: {element.get_attribute('name') or element.get_attribute('id')}")
        
        return fields
    
    def fill_form(self, fields):
        """フォームの入力"""
        try:
            # 各フィールドに値を入力
            if 'name' in fields:
                fields['name'].clear()
                fields['name'].send_keys(COMPANY_INFO['representative'])
                time.sleep(0.5)
            
            if 'company' in fields:
                fields['company'].clear()
                fields['company'].send_keys(COMPANY_INFO['company_name'])
                time.sleep(0.5)
            
            if 'email' in fields:
                fields['email'].clear()
                fields['email'].send_keys(COMPANY_INFO['email'])
                time.sleep(0.5)
            
            if 'phone' in fields:
                fields['phone'].clear()
                fields['phone'].send_keys(COMPANY_INFO['phone'])
                time.sleep(0.5)
            
            if 'message' in fields:
                fields['message'].clear()
                fields['message'].send_keys(COMPANY_INFO['message'])
                time.sleep(1)
            
            logger.info("Form fields filled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error filling form: {e}")
            return False
    
    def find_submit_button(self):
        """送信ボタンの検出"""
        submit_selectors = [
            'input[type="submit"]',
            'button[type="submit"]',
            'input[value*="送信"]',
            'input[value*="Submit"]',
            'button:contains("送信")',
            'button:contains("Submit")',
            'input[value*="確認"]',
            'button:contains("確認")',
            'input[value*="次へ"]',
            'button:contains("次へ")'
        ]
        
        for selector in submit_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    return element
            except NoSuchElementException:
                continue
        
        # テキストで検索
        try:
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for button in buttons:
                if any(text in button.text for text in ['送信', 'Submit', '確認', '次へ']):
                    return button
        except:
            pass
        
        return None
    
    def check_success(self):
        """送信成功の判定"""
        # URL確認
        current_url = self.driver.current_url.lower()
        success_url_patterns = ['thanks', 'complete', 'success', 'finish', 'done']
        
        if any(pattern in current_url for pattern in success_url_patterns):
            return True
        
        # ページ内容確認
        try:
            success_messages = [
                '送信しました', 'ありがとう', '受け付けました', '完了',
                'thank you', 'success', 'submitted', 'received'
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
            if any(msg.lower() in page_text for msg in success_messages):
                return True
                
        except Exception as e:
            logger.error(f"Error checking success: {e}")
        
        return False
    
    def process_url(self, url):
        """単一URLの処理"""
        result = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "status": "failed",
            "message": "",
            "fields_found": 0,
            "screenshot": None
        }
        
        try:
            logger.info(f"Processing URL: {url}")
            
            # ページアクセス
            self.driver.get(url)
            time.sleep(2)
            
            # フォーム検出
            fields = self.detect_form_fields()
            result["fields_found"] = len(fields)
            
            if not fields:
                result["message"] = "No form fields detected"
                logger.warning(f"No form fields found on {url}")
                return result
            
            # フォーム入力
            if not self.fill_form(fields):
                result["message"] = "Failed to fill form"
                return result
            
            # 送信ボタン検出
            submit_button = self.find_submit_button()
            if not submit_button:
                result["message"] = "Submit button not found"
                logger.warning(f"Submit button not found on {url}")
                return result
            
            # フォーム送信
            submit_button.click()
            time.sleep(5)  # 送信後の待機
            
            # 成功判定
            if self.check_success():
                result["status"] = "success"
                result["message"] = "Form submitted successfully"
                logger.info(f"Successfully submitted form for {url}")
            else:
                result["message"] = "Form submission unclear"
                logger.warning(f"Form submission result unclear for {url}")
            
        except TimeoutException:
            result["message"] = "Page load timeout"
            logger.error(f"Timeout loading {url}")
        except Exception as e:
            result["message"] = f"Error: {str(e)}"
            logger.error(f"Error processing {url}: {e}")
        
        return result
    
    def run_automation(self, urls):
        """自動化処理の実行"""
        global processing_status
        
        processing_status["is_running"] = True
        processing_status["total_urls"] = len(urls)
        processing_status["processed"] = 0
        processing_status["success"] = 0
        processing_status["failed"] = 0
        processing_status["results"] = []
        
        if not self.setup_driver():
            processing_status["is_running"] = False
            return
        
        try:
            for url in urls:
                if not processing_status["is_running"]:
                    break
                    
                processing_status["current_url"] = url
                result = self.process_url(url)
                
                processing_status["results"].append(result)
                processing_status["processed"] += 1
                
                if result["status"] == "success":
                    processing_status["success"] += 1
                else:
                    processing_status["failed"] += 1
                
                # 次のURLまで待機
                time.sleep(3)
                
        finally:
            if self.driver:
                self.driver.quit()
            processing_status["is_running"] = False
            processing_status["current_url"] = ""
            
            # 結果保存
            self.save_results()
    
    def save_results(self):
        """結果の保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON形式で保存
        with open(f'results_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(processing_status["results"], f, ensure_ascii=False, indent=2)
        
        # 失敗したURLをCSV保存
        failed_urls = [r for r in processing_status["results"] if r["status"] != "success"]
        if failed_urls:
            with open(f'failed_urls_{timestamp}.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Error', 'Fields Found'])
                for result in failed_urls:
                    writer.writerow([result["url"], result["message"], result["fields_found"]])
        
        logger.info(f"Results saved: {len(processing_status['results'])} total, {processing_status['success']} success, {processing_status['failed']} failed")

# Flask ルート
@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """処理状況の取得"""
    return jsonify(processing_status)

@app.route('/api/start', methods=['POST'])
def start_automation():
    """自動化処理の開始"""
    if processing_status["is_running"]:
        return jsonify({"error": "Already running"}), 400
    
    try:
        # URLリストの読み込み
        urls = []
        if os.path.exists('urls.csv'):
            with open('urls.csv', 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # ヘッダーをスキップ
                urls = [row[0].strip() for row in reader if row and row[0].strip()]
        
        if not urls:
            return jsonify({"error": "No URLs found in urls.csv"}), 400
        
        # バックグラウンドで実行
        import threading
        automation = FormAutomation()
        thread = threading.Thread(target=automation.run_automation, args=(urls,))
        thread.start()
        
        return jsonify({"message": "Automation started", "total_urls": len(urls)})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_automation():
    """自動化処理の停止"""
    processing_status["is_running"] = False
    return jsonify({"message": "Automation stopped"})

if __name__ == '__main__':
    # urls.csvファイルの作成（存在しない場合）
    if not os.path.exists('urls.csv'):
        with open('urls.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL'])
            writer.writerow(['https://example.com/contact'])
    
    # テンプレートディレクトリの作成
    os.makedirs('templates', exist_ok=True)
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)