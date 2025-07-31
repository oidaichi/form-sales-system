#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
フォーム自動化ロジック
LOVANTVICTORIA営業支援システム
"""

import pandas as pd
import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# LOVANTVICTORIA会社情報
COMPANY_INFO = {
    'company_name': 'LOVANTVICTORIA',
    'full_name': '冨安 朱',
    'last_name': '冨安',
    'first_name': '朱',
    'address': '東京都目黒区八雲3-18-9',
    'phone': '08036855092',
    'email': 'info@lovantvictoria.com',
    'business': '住宅不動産業界特化のDXコンサル、助成金活用AI研修、人工知能システム開発',
    'message': '''こんにちは、LOVANTVICTORIAの冨安と申します。
弊社は生成AI技術の企業普及を通じて、企業のDX化を支援しております。
特に住宅不動産業界におけるAI活用やデータ活用、助成金活用研修に力を入れており、
貴社のお役に立てる可能性があると考えご連絡させていただきました。
もしAIやデータ活用、助成金活用研修に少しでも興味がございましたら、お気軽にお返事いただき、
zoomでお話させていただけたらと思います。
どうぞよろしくお願いいたします。'''
}

def setup_logging():
    """ログ設定を初期化"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('form_automation.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def setup_chrome_driver():
    """Chrome WebDriverを設定 (GCE Ubuntu対応 - GUI表示)"""
    try:
        chrome_options = Options()
        
        # GCE Ubuntu環境でGUI表示するための設定
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        # GCE環境でブラウザを表示するための設定
        # --disable-gpu は削除（GUI表示のため）
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        
        # Chrome実行ファイルのパスを検出
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium'
        ]
        
        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                break
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
            logging.info(f"Chrome バイナリ検出: {chrome_binary}")
        else:
            logging.warning("Chrome バイナリが見つかりません")
        
        # ディスプレイ設定（GCE GUI環境対応）
        display = os.environ.get('DISPLAY')
        if display:
            chrome_options.add_argument(f'--display={display}')
            logging.info(f"ディスプレイ設定: {display}")
        else:
            # DISPLAYが設定されていない場合はデフォルト設定
            logging.warning("DISPLAY環境変数が設定されていません")
            logging.warning("GCE GUI環境では 'export DISPLAY=:0' を実行してください")
            # 仮想ディスプレイを試す
            chrome_options.add_argument('--display=:99')
            logging.info("仮想ディスプレイ :99 を使用します")
        
        # WebDriverの検出を回避
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # ChromeDriverを自動インストール・設定
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # WebDriverであることを隠す
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # ページ読み込みタイムアウト設定（CLAUDE.md要件: 10秒）
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(10)
        
        logging.info("Chrome WebDriver 初期化成功")
        return driver
        
    except Exception as e:
        logging.error(f"WebDriver設定エラー: {str(e)}")
        logging.error("解決方法:")
        logging.error("1. ./setup_gce.sh を実行してセットアップ")
        logging.error("2. export DISPLAY=:99 でディスプレイを設定")
        logging.error("3. Xvfb :99 -screen 0 1920x1080x24 & で仮想ディスプレイ起動")
        raise

def read_input_file(filepath):
    """CSVまたはExcelファイルを読み込む"""
    try:
        _, ext = os.path.splitext(filepath)
        
        if ext.lower() == '.csv':
            # CSVファイルの場合（エンコーディング自動判定）
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(filepath, encoding='shift_jis')
                except UnicodeDecodeError:
                    df = pd.read_csv(filepath, encoding='cp932')
        else:
            # Excelファイルの場合
            df = pd.read_excel(filepath)
        
        logging.info(f"ファイル読み込み成功: {len(df)}行のデータ")
        return df
    except Exception as e:
        logging.error(f"ファイル読み込みエラー: {str(e)}")
        raise

def get_target_urls(df):
    """対象URLを抽出 (httpから始まるURLのみ)"""
    urls = []
    
    # contact_url列を優先、なければE-mail列を使用
    url_column = None
    if 'contact_url' in df.columns:
        url_column = 'contact_url'
        logging.info("対象列: contact_url")
    elif 'E-mail' in df.columns:
        url_column = 'E-mail'  
        logging.info("対象列: E-mail")
    elif 'url' in df.columns:
        url_column = 'url'
        logging.info("対象列: url")
    else:
        available_columns = list(df.columns)
        logging.error(f"利用可能な列: {available_columns}")
        raise ValueError("contact_url、E-mail、url列のいずれかが必要です")
    
    total_rows = 0
    valid_urls = 0
    
    for idx, row in df.iterrows():
        total_rows += 1
        url = str(row[url_column]).strip()
        
        # httpから始まるURLのみを対象とする
        if url and url != 'nan' and url.lower().startswith('http'):
            valid_urls += 1
            urls.append({
                'index': idx,
                'url': url,
                'company': row.get('company', row.get('会社名', f'行{idx+1}'))
            })
            logging.debug(f"有効URL: {url} ({row.get('company', row.get('会社名', '不明'))})")
        else:
            logging.debug(f"無効URL (行{idx+1}): {url}")
    
    logging.info(f"全行数: {total_rows}, 有効URL数: {valid_urls}")
    logging.info(f"対象URL例: {urls[:3] if urls else '無し'}")
    
    return urls

def find_form_fields(driver):
    """フォーム入力欄を検出 - CLAUDE.md要件に準拠"""
    fields = {}
    
    # フィールド検出パターン（優先度順）
    field_patterns = {
        'name': ['name', 'お名前', '氏名', '名前', 'your-name', 'customer-name', 'fullname', 'contact-name'],
        'company': ['company', '会社名', '会社', 'organization', 'corp', 'your-company', 'corp-name'],
        'email': ['email', 'mail', 'メール', 'e-mail', 'your-email', 'address', 'mailaddress'],
        'phone': ['phone', 'tel', '電話', '電話番号', 'your-phone', 'telephone', 'contact-phone'],
        'message': ['message', 'content', 'body', 'inquiry', 'comment', 'お問い合わせ', 'your-message', 'textarea', '内容', 'details']
    }
    
    for field_type, patterns in field_patterns.items():
        element = None
        
        # name属性で検索
        for pattern in patterns:
            try:
                if field_type == 'message':
                    # メッセージ欄はtextareaも検索
                    element = driver.find_element(By.CSS_SELECTOR, 
                        f'input[name*="{pattern}"], textarea[name*="{pattern}"]')
                else:
                    element = driver.find_element(By.CSS_SELECTOR, f'input[name*="{pattern}"]')
                break
            except NoSuchElementException:
                continue
        
        # id属性で検索
        if not element:
            for pattern in patterns:
                try:
                    if field_type == 'message':
                        element = driver.find_element(By.CSS_SELECTOR,
                            f'input[id*="{pattern}"], textarea[id*="{pattern}"]')
                    else:
                        element = driver.find_element(By.CSS_SELECTOR, f'input[id*="{pattern}"]')
                    break
                except NoSuchElementException:
                    continue
        
        # placeholder属性で検索
        if not element:
            for pattern in patterns:
                try:
                    if field_type == 'message':
                        element = driver.find_element(By.CSS_SELECTOR,
                            f'input[placeholder*="{pattern}"], textarea[placeholder*="{pattern}"]')
                    else:
                        element = driver.find_element(By.CSS_SELECTOR, f'input[placeholder*="{pattern}"]')
                    break
                except NoSuchElementException:
                    continue
        
        if element:
            fields[field_type] = element
    
    return fields

def fill_form_fields(driver, fields):
    """フォーム欄に情報を入力"""
    try:
        # 各フィールドに値を入力
        if 'name' in fields:
            fields['name'].clear()
            fields['name'].send_keys(COMPANY_INFO['full_name'])
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
        
        return True
    except Exception as e:
        logging.error(f"フォーム入力エラー: {str(e)}")
        return False

def handle_select_elements(driver):
    """プルダウンとラジオボタンを処理 - CLAUDE.md要件に準拠"""
    try:
        # プルダウン（select）の処理 - 一番上の選択肢を選択
        selects = driver.find_elements(By.TAG_NAME, 'select')
        for i, select in enumerate(selects):
            try:
                select_obj = Select(select)
                options = select_obj.options
                
                if len(options) > 1:
                    # 最初の空白選択肢をスキップして一番上の有効な選択肢を選択
                    selected = False
                    for idx in range(1, len(options)):
                        option_text = options[idx].text.strip()
                        if option_text and option_text not in ['選択してください', 'Please select', '--']:
                            select_obj.select_by_index(idx)
                            logging.info(f"プルダウン選択: {option_text}")
                            selected = True
                            break
                    
                    if not selected and len(options) > 1:
                        # それでも選択されない場合は2番目の選択肢を選択
                        select_obj.select_by_index(1)
                        logging.info(f"プルダウン選択（デフォルト）: {options[1].text}")
                
                time.sleep(0.5)
            except Exception as e:
                logging.warning(f"プルダウン{i+1}処理エラー: {str(e)}")
        
        # ラジオボタンの処理 - 各グループの最初の選択肢を選択
        radios = driver.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        radio_groups = {}
        for radio in radios:
            name = radio.get_attribute('name')
            if name and name not in radio_groups and radio.is_displayed():
                try:
                    if radio.is_enabled():
                        radio.click()
                        radio_groups[name] = True
                        logging.info(f"ラジオボタン選択: {name}")
                        time.sleep(0.5)
                except Exception as e:
                    logging.warning(f"ラジオボタン処理エラー ({name}): {str(e)}")
        
    except Exception as e:
        logging.error(f"選択要素処理エラー: {str(e)}")

def find_submit_button(driver):
    """送信ボタンを検出 - CLAUDE.md要件に準拠"""
    # type="submit"を最優先で検索
    submit_selectors = [
        'input[type="submit"]',
        'button[type="submit"]'
    ]
    
    # value/textによる検索パターン
    button_texts = ['送信', 'Submit', '確認', '次へ', 'send', 'contact', 'submit']
    
    # まずtype="submit"で検索
    for selector in submit_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    return element
        except Exception:
            continue
    
    # value属性でテキスト検索
    for text in button_texts:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, f'input[value*="{text}"]')
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    return element
        except Exception:
            continue
    
    # ボタンタグのテキストで検索
    try:
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        for button in buttons:
            button_text = button.text.strip().lower()
            for text in button_texts:
                if text.lower() in button_text:
                    if button.is_displayed() and button.is_enabled():
                        return button
    except Exception:
        pass
    
    # aタグ（リンクボタン）でも検索
    try:
        links = driver.find_elements(By.TAG_NAME, 'a')
        for link in links:
            link_text = link.text.strip().lower()
            for text in button_texts:
                if text.lower() in link_text:
                    if link.is_displayed():
                        return link
    except Exception:
        pass
    
    return None

def handle_confirmation_page(driver):
    """確認画面の処理 - CLAUDE.md要件に準拠"""
    try:
        # 確認画面のボタンテキスト（優先度順）
        confirmation_texts = ['送信', '確定', '送る', 'Submit', 'OK', 'はい', 'send', 'confirm']
        
        # type="submit"を最優先で検索
        try:
            submit_elements = driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
            for element in submit_elements:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    time.sleep(3)  # 送信後の待機時間を延長
                    return True
        except Exception:
            pass
        
        # テキストベースで検索
        for text in confirmation_texts:
            try:
                # ボタンタグから検索
                buttons = driver.find_elements(By.TAG_NAME, 'button')
                for button in buttons:
                    button_text = button.text.strip().lower()
                    if text.lower() in button_text and button.is_displayed() and button.is_enabled():
                        logging.info(f"確認ボタンクリック: {button.text}")
                        button.click()
                        time.sleep(3)
                        return True
                
                # input要素のvalue属性から検索
                inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="submit"], input[type="button"]')
                for input_elem in inputs:
                    value = input_elem.get_attribute('value') or ''
                    if text.lower() in value.lower() and input_elem.is_displayed() and input_elem.is_enabled():
                        logging.info(f"確認ボタンクリック: {value}")
                        input_elem.click()
                        time.sleep(3)
                        return True
                        
                # aタグ（リンクボタン）からも検索
                links = driver.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    link_text = link.text.strip().lower()
                    if text.lower() in link_text and link.is_displayed():
                        logging.info(f"確認リンククリック: {link.text}")
                        link.click()
                        time.sleep(3)
                        return True
            except Exception as e:
                logging.debug(f"確認ボタン検索エラー ({text}): {str(e)}")
                continue
        
        return False
    except Exception as e:
        logging.error(f"確認画面処理エラー: {str(e)}")
        return False

def check_success(driver):
    """送信成功を判定 - CLAUDE.md要件に準拠（5秒待機後判定）"""
    try:
        # 5秒待機してから判定
        time.sleep(5)
        
        # URL確認（ありがとうページ）
        current_url = driver.current_url.lower()
        success_url_patterns = ['thanks', 'complete', 'success', 'finish', 'done', 'thankyou', 'sent']
        
        for pattern in success_url_patterns:
            if pattern in current_url:
                logging.info(f"成功URL検出: {current_url} (パターン: {pattern})")
                return True
        
        # ページ内容確認（成功メッセージ）
        success_messages = [
            '送信しました', 'ありがとう', '受け付けました', '完了', '送信完了',
            'thank you', 'success', 'submitted', 'received', 'sent successfully',
            'お問い合わせありがとう', 'メッセージを送信', '正常に送信'
        ]
        
        try:
            page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
            for msg in success_messages:
                if msg.lower() in page_text:
                    logging.info(f"成功メッセージ検出: {msg}")
                    return True
        except Exception as e:
            logging.debug(f"ページテキスト取得エラー: {str(e)}")
        
        # ページタイトルでも確認
        try:
            title = driver.title.lower()
            title_success_patterns = ['thanks', 'thank you', 'complete', 'success', '完了', 'ありがとう']
            for pattern in title_success_patterns:
                if pattern in title:
                    logging.info(f"成功タイトル検出: {title}")
                    return True
        except Exception as e:
            logging.debug(f"タイトル取得エラー: {str(e)}")
        
        logging.info(f"成功判定: 失敗 - URL: {current_url}")
        return False
        
    except Exception as e:
        logging.error(f"成功判定エラー: {str(e)}")
        return False

def process_single_url(driver, url_info):
    """単一URLを処理"""
    url = url_info['url']
    company = url_info['company']
    
    result = {
        'url': url,
        'company': company,
        'status': 'failed',
        'error': '',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    try:
        logging.info(f"処理開始: {company} - {url}")
        
        # ページアクセス
        driver.get(url)
        time.sleep(3)  # ページ読み込み待機
        
        # フォーム欄を検出
        fields = find_form_fields(driver)
        if not fields:
            result['error'] = 'フォーム欄が見つかりません'
            logging.warning(f"フォーム欄未検出: {url}")
            return result
        
        logging.info(f"検出フィールド数: {len(fields)}")
        
        # フォーム入力
        if not fill_form_fields(driver, fields):
            result['error'] = 'フォーム入力に失敗しました'
            return result
        
        # 選択要素の処理
        handle_select_elements(driver)
        
        # 送信ボタンを検出・クリック
        submit_button = find_submit_button(driver)
        if not submit_button:
            result['error'] = '送信ボタンが見つかりません'
            logging.warning(f"送信ボタン未検出: {url}")
            return result
        
        logging.info(f"送信ボタンクリック: {submit_button.text if hasattr(submit_button, 'text') else 'N/A'}")
        submit_button.click()
        time.sleep(3)  # 送信後の待機
        
        # 確認画面の処理（より包括的に検出）
        page_source = driver.page_source.lower()
        current_url = driver.current_url.lower()
        
        # 確認画面検出パターン
        confirmation_patterns = ['確認', 'confirm', 'preview', 'check', '内容確認', 'verification']
        is_confirmation_page = any(pattern in page_source or pattern in current_url for pattern in confirmation_patterns)
        
        if is_confirmation_page:
            logging.info("確認画面を検出 - 確認ボタンを探します")
            if handle_confirmation_page(driver):
                logging.info("確認画面で送信ボタンをクリックしました")
            else:
                logging.warning("確認画面で送信ボタンが見つかりませんでした")
        
        # 成功判定（5秒待機を含む）
        if check_success(driver):
            result['status'] = 'success'
            result['error'] = '送信成功'
            logging.info(f"✅ 送信成功: {company} - {url}")
        else:
            result['error'] = '送信結果の確認ができませんでした'
            logging.warning(f"❌ 送信結果不明: {company} - {url}")
    
    except TimeoutException:
        result['error'] = 'ページの読み込みがタイムアウトしました'
        logging.error(f"タイムアウト: {url}")
    except Exception as e:
        result['error'] = f'エラー: {str(e)}'
        logging.error(f"処理エラー {url}: {str(e)}")
    
    return result

def save_results(df, results, output_filepath):
    """結果をファイルに保存"""
    try:
        # 結果を元のデータフレームに追加
        df['processing_status'] = 'not_processed'
        df['processing_error'] = ''
        df['processing_timestamp'] = ''
        
        for result in results:
            idx = result.get('index', -1)
            if idx >= 0 and idx < len(df):
                df.loc[idx, 'processing_status'] = result['status']
                df.loc[idx, 'processing_error'] = result['error']
                df.loc[idx, 'processing_timestamp'] = result['timestamp']
        
        # ファイル保存
        _, ext = os.path.splitext(output_filepath)
        if ext.lower() == '.csv':
            df.to_csv(output_filepath, index=False, encoding='utf-8-sig')
        else:
            df.to_excel(output_filepath, index=False)
        
        logging.info(f"結果保存完了: {output_filepath}")
        return True
    except Exception as e:
        logging.error(f"結果保存エラー: {str(e)}")
        return False

def process_urls(input_filepath, status_dict, callback_func, driver_callback=None):
    """メイン処理関数 - 1行ずつブラウザでURL処理"""
    driver = None
    results = []
    
    try:
        logging.info("=== 自動フォーム送信処理開始 ===")
        
        # ファイル読み込み
        df = read_input_file(input_filepath)
        urls = get_target_urls(df)
        
        if not urls:
            return {'success': False, 'error': '処理対象のURLが見つかりません'}
        
        status_dict['total_urls'] = len(urls)
        logging.info(f"処理対象URL数: {len(urls)}")
        
        # WebDriver設定とテスト
        logging.info("Chrome WebDriver を初期化中...")
        driver = setup_chrome_driver()
        
        # WebDriverのコールバック実行（アプリから参照できるよう）
        if driver_callback:
            driver_callback(driver)
        
        # Google アクセステスト
        try:
            logging.info("ブラウザ動作テスト中...")
            driver.get('https://www.google.com')
            time.sleep(2)
            logging.info("ブラウザ動作テスト成功")
        except Exception as e:
            logging.error(f"ブラウザ動作テスト失敗: {str(e)}")
            raise
        
        # 各URLを1行ずつ新しいタブで処理
        for i, url_info in enumerate(urls):
            if not status_dict['is_running']:
                logging.info("処理停止要求を受信")
                break
            
            logging.info(f"=== 処理中 {i+1}/{len(urls)}: {url_info['company']} ===")
            
            # ステータス更新
            status_dict['current_url'] = url_info['url']
            callback_func(
                url_info['url'],
                i,
                status_dict['success'],
                status_dict['failed'],
                len(urls),
                results
            )
            
            # 新しいタブでURL処理
            try:
                # 現在のタブハンドル数を記録
                original_handles = driver.window_handles
                original_count = len(original_handles)
                logging.info(f"現在のタブ数: {original_count}")
                
                # 新しいタブを開く（JavaScriptで確実に開く）
                driver.execute_script("window.open('about:blank', '_blank');")
                
                # 新しいタブが開かれるまで待機（最大5秒）
                new_tab_handle = None
                for attempt in range(10):
                    time.sleep(0.5)
                    current_handles = driver.window_handles
                    if len(current_handles) > original_count:
                        # 新しいタブのハンドルを特定
                        new_tab_handle = list(set(current_handles) - set(original_handles))[0]
                        break
                    logging.debug(f"新しいタブ待機中... 試行{attempt+1}")
                
                if new_tab_handle:
                    # 新しいタブに切り替え
                    driver.switch_to.window(new_tab_handle)
                    logging.info(f"新しいタブに切り替え成功 (ハンドル: {new_tab_handle})")
                    logging.info(f"新しいタブで処理開始: {url_info['url']}")
                else:
                    raise Exception("新しいタブの作成に失敗しました")
                
                # URL処理
                result = process_single_url(driver, url_info)
                result['index'] = url_info['index']
                results.append(result)
                
                # 結果集計と対応
                if result['status'] == 'success':
                    status_dict['success'] += 1
                    logging.info(f"✅ 成功: {url_info['company']} - タブを閉じます")
                    
                    # 成功した場合はタブを閉じる
                    driver.close()
                    # メインタブ（最初のタブ）に戻る
                    if driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
                else:
                    status_dict['failed'] += 1
                    logging.warning(f"❌ 失敗: {url_info['company']} - {result['error']} - タブを開いたまま残します")
                    
                    # 失敗した場合はタブを開いたまま残す
                    # メインタブ（最初のタブ）に戻る
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[0])
                
                status_dict['processed'] = i + 1
                
                # 次のURL処理まで2秒間隔で待機
                if i < len(urls) - 1:
                    logging.info("2秒待機中...")
                    time.sleep(2)
                    
            except Exception as e:
                logging.error(f"URL処理エラー {url_info['url']}: {str(e)}")
                result = {
                    'index': url_info['index'],
                    'url': url_info['url'],
                    'company': url_info['company'],
                    'status': 'failed',
                    'error': f'処理エラー: {str(e)}',
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                results.append(result)
                status_dict['failed'] += 1
                status_dict['processed'] = i + 1
                
                # エラー時は現在のタブを閉じてメインタブに戻る
                try:
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception as close_error:
                    logging.warning(f"タブクローズエラー: {str(close_error)}")
                    # メインタブに強制的に戻る
                    if driver.window_handles:
                        driver.switch_to.window(driver.window_handles[0])
        
        # 結果保存
        name, ext = os.path.splitext(input_filepath)
        output_filepath = f"{name}_result{ext}"
        
        logging.info("=== 処理結果の保存中 ===")
        if save_results(df, results, output_filepath):
            logging.info(f"結果保存成功: {output_filepath}")
            return {
                'success': True,
                'output_file': output_filepath,
                'total': len(urls),
                'success_count': status_dict['success'],
                'failed_count': status_dict['failed']
            }
        else:
            return {'success': False, 'error': '結果保存に失敗しました'}
    
    except Exception as e:
        logging.error(f"メイン処理エラー: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}
    
    finally:
        logging.info("=== 処理終了・リソース解放 ===")
        if driver:
            try:
                driver.quit()
                logging.info("WebDriver終了完了")
            except Exception as e:
                logging.error(f"WebDriver終了エラー: {str(e)}")