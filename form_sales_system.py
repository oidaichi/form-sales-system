#!/usr/bin/env python3
"""
フォーム営業システム - 完全復元版
バックアップシステムをベースに完全に動作するシステムを構築
"""

import asyncio
import os
import sqlite3
from datetime import datetime, timedelta
import logging
import time
import random
import re
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from urllib.parse import urljoin, urlparse
import socket
import base64
import json

# オプショナル依存関係
try:
    import pandas as pd
    import openpyxl
    from openpyxl.styles import PatternFill, Font
    import requests
    from bs4 import BeautifulSoup
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 一部ライブラリが不足: {e}")
    print("完全な機能を使用するには: pip install pandas openpyxl requests beautifulsoup4 playwright")
    DEPENDENCIES_AVAILABLE = False

# =============================================================================
# ポート管理クラス
# =============================================================================

class PortManager:
    """動的ポート割り当て管理"""
    
    _used_ports = set()
    _port_assignments = {}
    
    @classmethod
    def get_free_port(cls, preferred_port=None):
        """利用可能なポートを取得"""
        if preferred_port and preferred_port not in cls._used_ports:
            if cls._is_port_available(preferred_port):
                cls._used_ports.add(preferred_port)
                return preferred_port
        
        # 動的ポート割り当て
        for port in range(9222, 9300):
            if port not in cls._used_ports and cls._is_port_available(port):
                cls._used_ports.add(port)
                return port
        
        raise RuntimeError("利用可能なポートが見つかりません")
    
    @classmethod
    def _is_port_available(cls, port):
        """ポートが利用可能かチェック"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return True
        except OSError:
            return False
    
    @classmethod
    def release_port(cls, port):
        """ポートを解放"""
        cls._used_ports.discard(port)
    
    @classmethod
    def assign_port(cls, component_name, preferred_port=None):
        """コンポーネントにポートを割り当て"""
        if component_name in cls._port_assignments:
            return cls._port_assignments[component_name]
        
        port = cls.get_free_port(preferred_port)
        cls._port_assignments[component_name] = port
        return port
    
    @classmethod
    def get_assigned_port(cls, component_name):
        """割り当て済みポートを取得"""
        return cls._port_assignments.get(component_name)
    
    @classmethod
    def release_assignment(cls, component_name):
        """コンポーネントのポート割り当てを解放"""
        if component_name in cls._port_assignments:
            port = cls._port_assignments.pop(component_name)
            cls.release_port(port)

# =============================================================================
# ログ管理クラス
# =============================================================================

class FormSalesLogger:
    """フォーム営業システム専用ログ管理"""
    
    def __init__(self, log_file=None, db_path='form_sales.db'):
        self.db_path = db_path
        self.log_file = log_file or f'form_sales_{datetime.now().strftime("%Y%m%d")}.log'
        
        # Pythonログの設定
        self.logger = logging.getLogger('form_sales')
        self.logger.setLevel(logging.INFO)
        
        # ログハンドラの重複を避ける
        if not self.logger.handlers:
            # ファイルハンドラ
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # コンソールハンドラ
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # フォーマッタ
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        # データベース初期化
        self._init_database()
    
    def _init_database(self):
        """データベーステーブルの初期化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT (datetime('now')),
                        level TEXT,
                        action_type TEXT,
                        status TEXT,
                        result TEXT,
                        message TEXT,
                        company_name TEXT,
                        url TEXT,
                        details TEXT
                    )
                ''')
                conn.commit()
        except Exception as e:
            print(f"データベース初期化エラー: {e}")
    
    def log_activity(self, level, action_type, status, result, message, company_name='', url='', details=''):
        """活動をデータベースに記録"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO activity_logs 
                    (timestamp, level, action_type, status, result, message, company_name, url, details)
                    VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (level, action_type, status, result, message, company_name, url, details))
                conn.commit()
        except Exception as e:
            self.logger.error(f"データベース記録エラー: {e}")
    
    def info(self, message, **kwargs):
        """情報ログ"""
        self.logger.info(message)
        self.log_activity('INFO', kwargs.get('action_type', 'general'), 
                         kwargs.get('status', 'success'), kwargs.get('result', ''),
                         message, kwargs.get('company_name', ''), kwargs.get('url', ''),
                         kwargs.get('details', ''))
    
    def warning(self, message, **kwargs):
        """警告ログ"""
        self.logger.warning(message)
        self.log_activity('WARNING', kwargs.get('action_type', 'general'),
                         kwargs.get('status', 'warning'), kwargs.get('result', ''),
                         message, kwargs.get('company_name', ''), kwargs.get('url', ''),
                         kwargs.get('details', ''))
    
    def error(self, message, **kwargs):
        """エラーログ"""
        self.logger.error(message)
        self.log_activity('ERROR', kwargs.get('action_type', 'general'),
                         kwargs.get('status', 'error'), kwargs.get('result', ''),
                         message, kwargs.get('company_name', ''), kwargs.get('url', ''),
                         kwargs.get('details', ''))
    
    def get_recent_logs(self, limit=100):
        """最近のログを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM activity_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"ログ取得エラー: {e}")
            return []

# =============================================================================
# Excel処理クラス
# =============================================================================

class ExcelProcessor:
    """Excel ファイル処理の統合クラス"""
    
    def __init__(self, db_path='form_sales.db'):
        self.db_path = db_path
        self.logger = FormSalesLogger()
        
    def process_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> List[Dict]:
        """Excelファイルから企業データを読み取る"""
        try:
            if not DEPENDENCIES_AVAILABLE:
                self.logger.error("必要なライブラリが不足しています（pandas, openpyxl）")
                return []
            
            self.logger.info(f"Excelファイル読み込み開始: {file_path}")
            
            # Excelファイルを読み込み
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            companies = []
            
            for index, row in df.iterrows():
                # 必要な列を動的に検出
                company_data = {'index': index + 2}  # Excelの行番号（ヘッダー考慮）
                
                # 列名の正規化とマッピング
                for col in df.columns:
                    col_lower = str(col).lower()
                    value = row[col]
                    
                    # 値が NaN の場合は空文字列に
                    if pd.isna(value):
                        value = ''
                    else:
                        value = str(value).strip()
                    
                    # 列名による自動マッピング（URL検出を優先）
                    if any(keyword in col_lower for keyword in ['url', 'ホームページ', 'hp', 'サイト', 'リンク']):
                        company_data['url'] = value
                    elif any(keyword in col_lower for keyword in ['会社', 'company', '企業']):
                        company_data['company_name'] = value
                    elif any(keyword in col_lower for keyword in ['本文', 'メッセージ', 'message', '内容']):
                        company_data['message'] = value
                    elif any(keyword in col_lower for keyword in ['メール', 'email', 'mail']):
                        company_data['email'] = value
                    elif any(keyword in col_lower for keyword in ['電話', 'tel', 'phone']):
                        company_data['phone'] = value
                    else:
                        # その他の列も保持
                        company_data[col] = value
                
                # 必須項目のデフォルト値設定
                if 'company_name' not in company_data:
                    company_data['company_name'] = company_data.get('企業名', f'企業{index+1}')
                
                if 'url' not in company_data:
                    company_data['url'] = company_data.get('URL', company_data.get('ホームページ', ''))
                
                if 'message' not in company_data:
                    company_data['message'] = company_data.get('メッセージ', 
                        'お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。')
                
                # URLが存在する場合のみリストに追加
                if company_data['url']:
                    companies.append(company_data)
            
            self.logger.info(f"企業データ読み込み完了: {len(companies)}社")
            return companies
            
        except Exception as e:
            self.logger.error(f"Excelファイル処理エラー: {str(e)}")
            return []
    
    def save_results_to_excel(self, original_file_path: str, sheet_name: str, results: List[Dict]) -> str:
        """処理結果をExcelファイルに保存"""
        try:
            # 出力ファイルパスを生成
            base_name = os.path.splitext(original_file_path)[0]
            output_file = f"{base_name}_結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # 元のExcelファイルを読み込み
            workbook = openpyxl.load_workbook(original_file_path)
            worksheet = workbook[sheet_name]
            
            # 結果列のヘッダーを追加
            headers = ['処理状況', 'フォーム発見', '送信試行', '送信成功', '入力フィールド数', 'ステータスメッセージ']
            
            # ヘッダー行の最後の列を取得
            max_col = worksheet.max_column
            for i, header in enumerate(headers, 1):
                cell = worksheet.cell(row=1, column=max_col + i)
                cell.value = header
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
            
            # 結果をExcelに書き込み
            for result in results:
                row_index = result.get('row_index', 0)
                if row_index > 0:
                    # 処理状況
                    status_cell = worksheet.cell(row=row_index, column=max_col + 1)
                    if result.get('submit_success'):
                        status_cell.value = "送信完了"
                        status_cell.fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
                    elif result.get('form_found'):
                        status_cell.value = "フォーム発見"
                        status_cell.fill = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")
                    else:
                        status_cell.value = "処理失敗"
                        status_cell.fill = PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid")
                    
                    # その他の情報
                    worksheet.cell(row=row_index, column=max_col + 2).value = "はい" if result.get('form_found') else "いいえ"
                    worksheet.cell(row=row_index, column=max_col + 3).value = "はい" if result.get('submit_attempted') else "いいえ"
                    worksheet.cell(row=row_index, column=max_col + 4).value = "はい" if result.get('submit_success') else "いいえ"
                    worksheet.cell(row=row_index, column=max_col + 5).value = result.get('filled_fields_count', 0)
                    worksheet.cell(row=row_index, column=max_col + 6).value = result.get('status_message', '')
            
            # ファイルを保存
            workbook.save(output_file)
            self.logger.info(f"結果ファイル保存完了: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"結果保存エラー: {str(e)}")
            return None

# =============================================================================
# 統合ブラウザ管理クラス
# =============================================================================

class UnifiedBrowserManager:
    """統合ブラウザ管理クラス"""
    
    def __init__(self, headless=True, timeout=30, enable_screenshots=False, component_name="browser"):
        self.headless = headless
        self.timeout = timeout
        self.enable_screenshots = enable_screenshots
        self.component_name = component_name
        self.screenshot_callback = None
        
        # Playwright関連
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # ポート管理
        self.cdp_port = None
        
        # ログ
        self.logger = FormSalesLogger()
        
        # 拡張されたフィールドパターン（実際のサイト調査結果を反映）
        self.field_patterns = {
            'company': {
                'japanese': ['会社名', '企業名', '法人名', '団体名', '組織名'],
                'english': ['company', 'corporation', 'organization'],
                'selectors': ['input[name*="company"]', 'input[id*="company"]']
            },
            'name': {
                'japanese': ['お名前', '氏名', '名前', '担当者', '代表者'],
                'english': ['name', 'your name', 'full name', 'contact name'],
                'selectors': ['input[name*="name"]', 'input[id*="name"]', 'input[placeholder*="名前"]']
            },
            'furigana': {
                'japanese': ['ふりがな', 'フリガナ', 'よみがな', '読み方'],
                'english': ['furigana', 'reading'],
                'selectors': ['input[name*="furigana"]', 'input[id*="furigana"]']
            },
            'email': {
                'japanese': ['メール', 'eメール', 'メールアドレス', '電子メール'],
                'english': ['email', 'mail', 'e-mail', 'email address'],
                'selectors': ['input[type="email"]', 'input[name*="email"]', 'input[id*="email"]']
            },
            'email_confirm': {
                'japanese': ['メール確認', 'メールアドレス確認', '確認用メール'],
                'english': ['email confirm', 'confirm email'],
                'selectors': ['input[name*="email_confirm"]', 'input[name*="email2"]']
            },
            'phone': {
                'japanese': ['電話', '電話番号', 'tel', 'TEL', 'お電話番号'],
                'english': ['phone', 'telephone', 'tel', 'mobile'],
                'selectors': ['input[type="tel"]', 'input[name*="phone"]', 'input[name*="tel"]']
            },
            'zip': {
                'japanese': ['郵便番号', '〒', 'zip'],
                'english': ['postal', 'zip', 'postcode'],
                'selectors': ['input[name*="zip"]', 'input[name*="postal"]']
            },
            'address': {
                'japanese': ['住所', 'ご住所', '所在地'],
                'english': ['address', 'location'],
                'selectors': ['input[name*="address"]', 'input[id*="address"]']
            },
            'prefecture': {
                'japanese': ['都道府県', '県', '都府県'],
                'english': ['prefecture', 'state'],
                'selectors': ['select[name*="prefecture"]', 'select[name*="pref"]']
            },
            'message': {
                'japanese': ['メッセージ', '内容', 'お問い合わせ内容', 'ご相談内容', '詳細', 'ご要望'],
                'english': ['message', 'content', 'inquiry', 'details', 'comment'],
                'selectors': ['textarea', 'input[name*="message"]', 'input[name*="content"]']
            },
            'consultation_type': {
                'japanese': ['ご相談内容', '問い合わせ種別', 'お問い合わせ内容'],
                'english': ['consultation', 'inquiry type'],
                'selectors': ['select[name*="consultation"]', 'input[name*="inquiry"]']
            },
            'privacy_policy': {
                'japanese': ['個人情報', 'プライバシー', '利用規約', '同意'],
                'english': ['privacy', 'policy', 'agreement', 'consent'],
                'selectors': ['input[type="checkbox"][name*="privacy"]', 'input[type="checkbox"][name*="agree"]']
            },
            'date_first': {
                'japanese': ['第一希望', '希望日', '第1希望'],
                'patterns': [r'.*第一希望.*', r'.*希望日.*']
            },
            'date_second': {
                'japanese': ['第二希望', '第2希望'],
                'patterns': [r'.*第二希望.*', r'.*第2希望.*']
            },
            'date_third': {
                'japanese': ['第三希望', '第3希望'],
                'patterns': [r'.*第三希望.*', r'.*第3希望.*']
            }
        }
        
        # フィールド値
        self.field_values = {
            'company': '株式会社サンプル',
            'name': '田中太郎',
            'email': 'sample@example.com',
            'phone': '03-1234-5678',
            'message': 'お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。',
            'date_first': self._generate_date_string(7, include_time=True),
            'date_second': self._generate_date_string(8, include_time=True),
            'date_third': self._generate_date_string(9, include_time=True)
        }
    
    def _generate_date_string(self, days_offset: int, include_time: bool = False) -> str:
        """指定日数後の日付文字列を生成（平日のみ）"""
        target_date = datetime.now() + timedelta(days=days_offset)
        
        # 土日を避ける
        while target_date.weekday() >= 5:
            target_date += timedelta(days=1)
        
        year = target_date.year
        month = target_date.month
        day = target_date.day
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        weekday = weekday_names[target_date.weekday()]
        
        if include_time:
            return f"{year}年{month}月{day}日（{weekday}） 13:00"
        else:
            return f"{year}年{month}月{day}日（{weekday}）"
    
    async def initialize_browser(self) -> bool:
        """ブラウザの初期化"""
        try:
            if not DEPENDENCIES_AVAILABLE:
                self.logger.error("Playwrightが利用できません")
                return False
            
            self.logger.info(f"ブラウザ初期化開始: {self.component_name}")
            
            # Playwrightの初期化
            self.playwright = await async_playwright().start()
            
            # CDPポートの割り当て
            self.cdp_port = PortManager.assign_port(self.component_name, 9222)
            
            # ブラウザ起動オプション
            browser_args = [
                f'--remote-debugging-port={self.cdp_port}',
                '--remote-debugging-address=0.0.0.0',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-dev-shm-usage',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--single-process',
                '--no-sandbox',
                '--disable-gpu-sandbox',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images'
            ]
            
            # ブラウザ起動
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args,
                timeout=60000
            )
            
            self.logger.info(f"ブラウザ起動完了: CDP={self.cdp_port}")
            
            # コンテキストの作成
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True,
                java_script_enabled=True,
                accept_downloads=False
            )
            
            # ページの作成
            self.page = await self.context.new_page()
            
            # タイムアウト設定
            self.page.set_default_timeout(self.timeout * 1000)
            
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザ初期化エラー: {str(e)}")
            return False
    
    async def navigate_to_url(self, url: str) -> bool:
        """URLにナビゲート"""
        try:
            self.logger.info(f"ページナビゲート開始: {url}")
            
            if not self.page:
                if not await self.initialize_browser():
                    return False
            
            # URLの正規化
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # ページロード
            response = await self.page.goto(url, wait_until='networkidle', timeout=self.timeout * 1000)
            
            if response and response.status < 400:
                self.logger.info(f"ページロード成功: {url}")
                await self._take_screenshot("ページロード完了")
                return True
            else:
                self.logger.error(f"ページロード失敗: {url} (Status: {response.status if response else 'None'})")
                return False
                
        except Exception as e:
            self.logger.error(f"ナビゲートエラー: {str(e)}")
            return False
    
    async def _take_screenshot(self, step_name=""):
        """スクリーンショットを撮影"""
        if self.enable_screenshots and self.screenshot_callback and self.page:
            try:
                screenshot_data = await self.page.screenshot(full_page=True)
                screenshot_base64 = base64.b64encode(screenshot_data).decode('utf-8')
                
                screenshot_info = {
                    'timestamp': datetime.now().isoformat(),
                    'step': step_name,
                    'url': self.page.url,
                    'image': f"data:image/png;base64,{screenshot_base64}"
                }
                
                self.screenshot_callback(screenshot_info)
                
            except Exception as e:
                self.logger.warning(f"スクリーンショット撮影エラー: {str(e)}")
    
    def set_screenshot_callback(self, callback):
        """スクリーンショットコールバック関数を設定"""
        self.screenshot_callback = callback
    
    async def close_browser(self):
        """ブラウザを終了"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            # ポート解放
            if self.cdp_port:
                PortManager.release_assignment(self.component_name)
            
            self.logger.info(f"ブラウザ終了完了: {self.component_name}")
            
        except Exception as e:
            self.logger.error(f"ブラウザ終了エラー: {str(e)}")

# =============================================================================
# 人間らしい操作システム（自動操作検出回避）
# =============================================================================

class HumanLikeInteraction:
    """人間らしいマウス・キーボード操作を実現するクラス"""
    
    def __init__(self, page, logger=None):
        self.page = page
        self.logger = logger or FormSalesLogger()
    
    async def human_like_click(self, element, delay_range=(0.5, 2.0)):
        """人間らしいクリック操作"""
        try:
            # 要素が見える位置までスクロール
            await element.scroll_into_view_if_needed()
            await self.random_delay(0.3, 0.8)
            
            # 要素の境界ボックスを取得
            box = await element.bounding_box()
            if not box:
                return False
            
            # クリック位置をランダムに選択（要素の中央付近）
            x = box['x'] + box['width'] * (0.3 + random.random() * 0.4)
            y = box['y'] + box['height'] * (0.3 + random.random() * 0.4)
            
            # マウス移動（人間らしい軌跡）
            await self.page.mouse.move(x, y)
            await self.random_delay(0.1, 0.3)
            
            # クリック
            await self.page.mouse.click(x, y)
            await self.random_delay(*delay_range)
            
            return True
            
        except Exception as e:
            self.logger.warning(f"人間らしいクリック失敗: {str(e)}")
            return False
    
    async def human_like_type(self, element, text, typing_speed_range=(50, 150)):
        """人間らしいタイピング操作（実際のマウス・キーボード）"""
        try:
            # 要素を画面内に表示
            await element.scroll_into_view_if_needed()
            await self.random_delay(0.3, 0.8)
            
            # 実際のマウスクリック（要素の境界内のランダム位置）
            box = await element.bounding_box()
            if not box:
                return False
            
            # クリック位置をランダムに選択
            click_x = box['x'] + box['width'] * (0.2 + random.random() * 0.6)
            click_y = box['y'] + box['height'] * (0.2 + random.random() * 0.6)
            
            # マウス移動してクリック
            await self.page.mouse.move(click_x, click_y)
            await self.random_delay(0.1, 0.3)
            await self.page.mouse.click(click_x, click_y)
            await self.random_delay(0.2, 0.5)
            
            # 既存テキストを選択してクリア（Ctrl+A → Delete）
            await self.page.keyboard.press('Control+a')
            await self.random_delay(0.1, 0.2)
            await self.page.keyboard.press('Delete')
            await self.random_delay(0.1, 0.3)
            
            # 一文字ずつタイピング（人間らしい速度）
            for char in text:
                await self.page.keyboard.type(char)
                # ランダムな入力間隔
                delay = random.uniform(typing_speed_range[0], typing_speed_range[1]) / 1000
                await asyncio.sleep(delay)
            
            # 入力完了後の自然な一息
            await self.random_delay(0.3, 0.8)
            return True
            
        except Exception as e:
            self.logger.warning(f"人間らしいタイピング失敗: {str(e)}")
            return False
    
    async def human_like_select(self, element, value_or_text):
        """人間らしい選択操作（ドロップダウン、ラジオボタン等）"""
        try:
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            input_type = await element.get_attribute('type') or 'text'
            
            # ラジオボタンの場合
            if tag_name == 'input' and input_type == 'radio':
                return await self.handle_radio_button(element, value_or_text)
            
            # チェックボックスの場合
            elif tag_name == 'input' and input_type == 'checkbox':
                return await self.handle_checkbox(element, value_or_text)
            
            # select要素の場合
            elif tag_name == 'select':
                return await self.handle_select_dropdown(element, value_or_text)
            
            # カスタムドロップダウンの場合
            else:
                return await self.handle_custom_dropdown(element, value_or_text)
            
        except Exception as e:
            self.logger.warning(f"人間らしい選択失敗: {str(e)}")
            return False
    
    async def handle_radio_button(self, element, value_or_text):
        """ラジオボタンの処理"""
        try:
            # 対応する値のラジオボタンを探す
            name = await element.get_attribute('name')
            if name:
                # 同じname属性を持つラジオボタンを全て取得
                radio_buttons = await self.page.query_selector_all(f'input[type="radio"][name="{name}"]')
                
                for radio in radio_buttons:
                    radio_value = await radio.get_attribute('value') or ''
                    
                    # ラベルテキストもチェック
                    label_text = await self.get_label_text_for_input(radio)
                    
                    # 値またはラベルが一致する場合
                    if (value_or_text.lower() in radio_value.lower() or 
                        value_or_text.lower() in label_text.lower()):
                        return await self.human_like_click(radio)
            
            return False
            
        except Exception as e:
            self.logger.warning(f"ラジオボタン処理失敗: {str(e)}")
            return False
    
    async def handle_checkbox(self, element, value_or_text):
        """チェックボックスの処理（実際のマウスクリック）"""
        try:
            # "はい"、"yes"、"true"、"on"等の場合はチェック
            positive_values = ['はい', 'yes', 'true', 'on', '1', 'ok', 'agree', '同意']
            
            if any(val in value_or_text.lower() for val in positive_values):
                # 既にチェックされているかを確認
                is_checked = await element.is_checked()
                if not is_checked:
                    # 実際のマウスクリック
                    await element.scroll_into_view_if_needed()
                    await self.random_delay(0.2, 0.5)
                    
                    box = await element.bounding_box()
                    if box:
                        click_x = box['x'] + box['width'] / 2
                        click_y = box['y'] + box['height'] / 2
                        await self.page.mouse.move(click_x, click_y)
                        await self.random_delay(0.1, 0.3)
                        await self.page.mouse.click(click_x, click_y)
                        await self.random_delay(0.2, 0.5)
                        return True
                return True  # 既にチェック済み
            
            return False
            
        except Exception as e:
            self.logger.warning(f"チェックボックス処理失敗: {str(e)}")
            return False
    
    async def handle_select_dropdown(self, element, value_or_text):
        """標準のselectドロップダウンの処理（実際のマウス操作）"""
        try:
            # ドロップダウンを実際にクリックして開く
            await element.scroll_into_view_if_needed()
            await self.random_delay(0.3, 0.7)
            
            box = await element.bounding_box()
            if box:
                # ドロップダウンの右側（矢印部分）をクリック
                click_x = box['x'] + box['width'] * 0.9
                click_y = box['y'] + box['height'] / 2
                await self.page.mouse.move(click_x, click_y)
                await self.random_delay(0.1, 0.3)
                await self.page.mouse.click(click_x, click_y)
                await self.random_delay(0.5, 1.0)  # ドロップダウンが開くまで待機
                
                # オプションを検索してクリック
                options = await element.query_selector_all('option')
                for option in options:
                    option_text = await option.inner_text()
                    option_value = await option.get_attribute('value') or ''
                    
                    if (value_or_text.lower() in option_text.lower() or 
                        value_or_text == option_value or
                        (value_or_text == '東京都' and ('東京' in option_text or 'tokyo' in option_value.lower()))):
                        
                        # オプションをマウスクリック
                        option_box = await option.bounding_box()
                        if option_box:
                            option_x = option_box['x'] + option_box['width'] / 2
                            option_y = option_box['y'] + option_box['height'] / 2
                            await self.page.mouse.move(option_x, option_y)
                            await self.random_delay(0.1, 0.2)
                            await self.page.mouse.click(option_x, option_y)
                            await self.random_delay(0.3, 0.6)
                            return True
            
            # フォールバック: キーボード操作
            try:
                await element.click()
                await self.random_delay(0.2, 0.4)
                # 東京都の場合、'T'キーを押して東京都に移動
                if value_or_text == '東京都':
                    await self.page.keyboard.press('KeyT')
                    await self.random_delay(0.2, 0.4)
                await self.page.keyboard.press('Enter')
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            self.logger.warning(f"selectドロップダウン処理失敗: {str(e)}")
            return False
    
    async def handle_custom_dropdown(self, element, value_or_text):
        """カスタムドロップダウンの処理"""
        try:
            # カスタムドロップダウンを開く
            await self.human_like_click(element)
            await self.random_delay(0.3, 0.8)
            
            # ドロップダウンが開くのを待つ
            await self.page.wait_for_timeout(500)
            
            # 一般的なドロップダウン選択肢のセレクタ
            option_selectors = [
                'li[role="option"]',
                '.dropdown-item',
                '.select-option',
                '.option',
                'ul li',
                '[data-value]',
                '.menu-item'
            ]
            
            for selector in option_selectors:
                try:
                    options = await self.page.query_selector_all(selector)
                    for option in options:
                        if await option.is_visible():
                            option_text = await option.inner_text()
                            option_value = await option.get_attribute('data-value') or ''
                            
                            if (value_or_text.lower() in option_text.lower() or 
                                value_or_text.lower() in option_value.lower()):
                                return await self.human_like_click(option)
                                
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.warning(f"カスタムドロップダウン処理失敗: {str(e)}")
            return False
    
    async def get_label_text_for_input(self, input_element):
        """入力要素に対応するラベルテキストを取得"""
        try:
            # id属性からlabel要素を探す
            input_id = await input_element.get_attribute('id')
            if input_id:
                label = await self.page.query_selector(f'label[for="{input_id}"]')
                if label:
                    return await label.inner_text()
            
            # 親要素にラベルがあるかチェック
            parent = await input_element.query_selector('..')
            if parent:
                label_text = await parent.inner_text()
                return label_text.replace(await input_element.inner_text(), '').strip()
            
            return ''
            
        except Exception:
            return ''
    
    async def random_delay(self, min_seconds=0.1, max_seconds=1.0):
        """ランダムな遅延"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
    
    async def detect_captcha_or_verification(self):
        """CAPTCHA や人間検証の検出"""
        try:
            # 一般的なCAPTCHA/検証要素を検索
            captcha_selectors = [
                'div[class*="captcha"]',
                'div[class*="recaptcha"]', 
                'iframe[src*="recaptcha"]',
                'div[class*="hcaptcha"]',
                'div[class*="verification"]',
                'div[class*="challenge"]',
                'canvas', # Canvas-based CAPTCHA
                'input[placeholder*="認証"]',
                'input[placeholder*="確認"]'
            ]
            
            for selector in captcha_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    self.logger.warning(f"CAPTCHA/検証要素を検出: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"CAPTCHA検出エラー: {str(e)}")
            return False
    
    async def wait_for_page_stability(self, timeout=5000):
        """ページの安定化を待つ"""
        try:
            await self.page.wait_for_load_state('networkidle', timeout=timeout)
            await self.random_delay(0.5, 1.5)
            return True
        except:
            return False

class ImprovedFormFiller:
    """改善されたフォーム入力クラス"""
    
    def __init__(self, page, logger=None):
        self.page = page
        self.logger = logger or FormSalesLogger()
        self.human_interaction = HumanLikeInteraction(page, logger)
    
    async def fill_form_intelligently(self, form_data, company_data):
        """インテリジェントなフォーム入力（強化版）"""
        try:
            filled_count = 0
            input_elements = form_data.get('input_elements', [])
            
            self.logger.info(f"フォーム入力開始: {len(input_elements)}個のフィールドを検出")
            
            # フィールドタイプ別の分類
            field_summary = {}
            for input_info in input_elements:
                field_type = input_info.get('field_type', 'unknown')
                field_summary[field_type] = field_summary.get(field_type, 0) + 1
            
            valid_fields = sum(count for field_type, count in field_summary.items() if field_type != 'unknown')
            self.logger.info(f"認識済みフィールド: {valid_fields}個 ({field_summary})")
            
            # CAPTCHA検出
            if await self.human_interaction.detect_captcha_or_verification():
                self.logger.warning("🔒 CAPTCHA/人間検証を検出しました。人間による操作が必要です。")
                return {'success': False, 'filled_count': 0, 'requires_human': True}
            
            # ページの安定化を待つ
            await self.human_interaction.wait_for_page_stability(timeout=3000)
            
            # フィールドを優先順位に従って処理
            prioritized_fields = self.prioritize_fields(input_elements)
            
            for i, input_info in enumerate(prioritized_fields):
                try:
                    element = input_info['element']
                    field_type = input_info.get('field_type', 'unknown')
                    
                    # unknown フィールドはスキップ
                    if field_type == 'unknown':
                        self.logger.info(f"スキップ: unknown フィールド")
                        continue
                    
                    # 要素が表示されているかチェック
                    is_visible = await element.is_visible()
                    is_enabled = await element.is_enabled()
                    
                    if not is_visible:
                        self.logger.warning(f"スキップ: {field_type} - 要素が非表示")
                        continue
                    if not is_enabled:
                        self.logger.warning(f"スキップ: {field_type} - 要素が無効")
                        continue
                    
                    # フィールドタイプに応じた入力
                    self.logger.info(f"🎯 入力試行: {field_type}")
                    success = await self.fill_field_by_type(element, field_type, company_data)
                    
                    if success:
                        filled_count += 1
                        await self.human_interaction.random_delay(0.5, 1.0)
                        self.logger.info(f"✅ フィールド入力成功: {field_type}")
                    else:
                        self.logger.warning(f"❌ フィールド入力失敗: {field_type}")
                    
                except Exception as e:
                    self.logger.error(f"フィールド処理エラー: {field_type} - {str(e)}")
                    continue
            
            result_success = filled_count > 0
            self.logger.info(f"フォーム入力完了: {filled_count}フィールド")
            
            return {
                'success': result_success, 
                'filled_count': filled_count, 
                'requires_human': not result_success
            }
            
        except Exception as e:
            self.logger.error(f"❌ フォーム入力エラー: {str(e)}")
            return {'success': False, 'filled_count': 0, 'requires_human': True}
    
    def prioritize_fields(self, input_elements):
        """フィールドを優先順位でソート"""
        # 優先順位の定義
        priority_order = {
            'name': 1,
            'company': 2,
            'furigana': 3,
            'email': 4,
            'email_confirm': 5,
            'phone': 6,
            'zip': 7,
            'prefecture': 8,
            'address': 9,
            'consultation_type': 10,
            'message': 11,
            'privacy_policy': 12,
            'checkbox_other': 13,
            'unknown': 99
        }
        
        return sorted(input_elements, key=lambda x: priority_order.get(x.get('field_type', 'unknown'), 99))
    
    async def fill_field_by_type(self, element, field_type, company_data):
        """フィールドタイプに応じた入力（JavaScript直接実行で確実に）"""
        try:
            # 入力値を決定
            input_value = self.get_input_value_for_field(field_type, company_data)
            if not input_value and field_type not in ['privacy_policy', 'checkbox_other']:
                return False
            
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            input_type = await element.get_attribute('type') or 'text'
            
            self.logger.info(f"入力開始: {field_type} = '{input_value[:30]}...' ({tag_name}, {input_type})")
            
            # 要素を表示領域に移動
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            
            # テキスト入力フィールド
            if tag_name in ['input', 'textarea'] and input_type not in ['checkbox', 'radio', 'submit', 'button']:
                return await self.force_text_input(element, input_value)
            
            # チェックボックス
            elif input_type == 'checkbox':
                if field_type == 'privacy_policy':
                    return await self.force_checkbox_check(element)
                return False
            
            # ドロップダウン
            elif tag_name == 'select':
                return await self.force_select_option(element, input_value)
            
            # ラジオボタン
            elif input_type == 'radio':
                return await self.force_radio_select(element, input_value)
            
            return False
            
        except Exception as e:
            self.logger.warning(f"フィールド入力エラー: {str(e)}")
            return False
    
    async def force_text_input(self, element, text):
        """JavaScript直接実行でテキスト入力を強制"""
        try:
            # 方法1: 直接値を設定
            await element.evaluate(f'''
                (element) => {{
                    element.focus();
                    element.value = "{text}";
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            ''')
            await asyncio.sleep(0.3)
            
            # 確認: 実際に値が設定されたか
            current_value = await element.get_attribute('value')
            if current_value == text:
                self.logger.info(f"JavaScript入力成功: '{text[:20]}...'")
                return True
            
            # 方法2: フォーカス + キーボード入力
            await element.click()
            await asyncio.sleep(0.2)
            await element.clear()
            await asyncio.sleep(0.2)
            await element.type(text)
            await asyncio.sleep(0.3)
            
            # 再確認
            current_value = await element.get_attribute('value')
            if current_value == text:
                self.logger.info(f"キーボード入力成功: '{text[:20]}...'")
                return True
                
            # 方法3: 最後の手段 - fill()
            await element.fill(text)
            await asyncio.sleep(0.3)
            
            final_value = await element.get_attribute('value')
            success = final_value == text
            
            if success:
                self.logger.info(f"fill()入力成功: '{text[:20]}...'")
            else:
                self.logger.warning(f"全ての入力方法が失敗: 期待値='{text}', 実際値='{final_value}'")
            
            return success
            
        except Exception as e:
            self.logger.error(f"強制テキスト入力失敗: {str(e)}")
            return False
    
    async def force_checkbox_check(self, element):
        """JavaScript直接実行でチェックボックスを強制チェック"""
        try:
            # 方法1: JavaScript直接操作
            await element.evaluate('''
                (element) => {
                    element.checked = true;
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
            ''')
            await asyncio.sleep(0.3)
            
            # 確認
            is_checked = await element.is_checked()
            if is_checked:
                self.logger.info("JavaScript チェック成功")
                return True
            
            # 方法2: クリック
            await element.click()
            await asyncio.sleep(0.3)
            
            is_checked = await element.is_checked()
            if is_checked:
                self.logger.info("クリック チェック成功")
                return True
            
            # 方法3: check()
            await element.check()
            is_checked = await element.is_checked()
            
            if is_checked:
                self.logger.info("check() 成功")
            else:
                self.logger.warning("全てのチェック方法が失敗")
            
            return is_checked
            
        except Exception as e:
            self.logger.error(f"強制チェックボックス操作失敗: {str(e)}")
            return False
    
    async def force_select_option(self, element, value):
        """JavaScript直接実行でドロップダウン選択を強制"""
        try:
            # 方法1: JavaScript直接選択
            result = await element.evaluate(f'''
                (element) => {{
                    const options = element.options;
                    for (let i = 0; i < options.length; i++) {{
                        const option = options[i];
                        if (option.text.includes("{value}") || option.value === "{value}") {{
                            element.selectedIndex = i;
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}
                    }}
                    return false;
                }}
            ''')
            
            if result:
                self.logger.info(f"JavaScript選択成功: {value}")
                return True
            
            # 方法2: 東京都特別処理
            if value == '東京都':
                result = await element.evaluate('''
                    (element) => {
                        const options = element.options;
                        for (let i = 0; i < options.length; i++) {
                            const option = options[i];
                            if (option.text.includes("東京") || option.value.includes("tokyo") || option.value === "13") {
                                element.selectedIndex = i;
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                        }
                        return false;
                    }
                ''')
                
                if result:
                    self.logger.info("東京都選択成功")
                    return True
            
            # 方法3: Playwright標準
            try:
                await element.select_option(label=value)
                self.logger.info(f"select_option成功: {value}")
                return True
            except:
                pass
            
            self.logger.warning(f"全ての選択方法が失敗: {value}")
            return False
            
        except Exception as e:
            self.logger.error(f"強制ドロップダウン選択失敗: {str(e)}")
            return False
    
    async def force_radio_select(self, element, value):
        """JavaScript直接実行でラジオボタン選択を強制"""
        try:
            # 方法1: 直接選択
            await element.evaluate('''
                (element) => {
                    element.checked = true;
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
            ''')
            await asyncio.sleep(0.3)
            
            is_checked = await element.is_checked()
            if is_checked:
                self.logger.info("ラジオボタン選択成功")
                return True
            
            # 方法2: クリック
            await element.click()
            await asyncio.sleep(0.3)
            
            is_checked = await element.is_checked()
            if is_checked:
                self.logger.info("ラジオボタンクリック成功")
            else:
                self.logger.warning("ラジオボタン選択失敗")
            
            return is_checked
            
        except Exception as e:
            self.logger.error(f"強制ラジオボタン選択失敗: {str(e)}")
            return False
    
    def get_input_value_for_field(self, field_type, company_data):
        """フィールドタイプに応じた入力値を取得（要件定義書準拠）"""
        # エクセルから読み取った企業名と本文を確実に使用
        target_company_name = company_data.get('company_name', '企業名不明')
        message_content = company_data.get('message', 'お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。')
        
        field_mapping = {
            # ターゲット企業情報（エクセルデータ使用）
            'company': target_company_name,
            'company_name': target_company_name,
            
            # 自社情報（要件定義書準拠）
            'name': '富安　朱',
            'furigana': 'とみやす　あや',
            'furigana_katakana': 'トミヤス　アヤ',
            'sei': 'とみやす',
            'mei': 'あや',
            'sei_katakana': 'トミヤス',
            'mei_katakana': 'アヤ',
            'family_name': '富安',
            'first_name': '朱',
            
            # 自社連絡先（要件定義書準拠）
            'email': 'minefujiko.honbu@gmail.com',
            'email_confirm': 'minefujiko.honbu@gmail.com',
            'phone': '08036855092',
            
            # 自社住所（要件定義書準拠）
            'zip': '107-0062',
            'address': '東京都港区南青山3丁目1番36号青山丸竹ビル6F',
            'prefecture': '東京都',
            
            # 自社名（要件定義書準拠）
            'our_company': '株式会社みねふじこ',
            'sender_company': '株式会社みねふじこ',
            
            # メッセージ・相談内容（エクセル本文使用）
            'message': message_content,
            'consultation_type': 'お問い合わせ',
            'inquiry_type': 'その他',
            
            # その他
            'subject': '業務提携のご相談',
            'date': '2025-01-15',
            'date_first': '2025-01-15',
            'date_second': '2025-01-16',
            'date_third': '2025-01-17',
            
            # チェックボックス・ラジオボタン
            'privacy_policy': 'はい',
            'checkbox_other': 'はい'
        }
        
        result = field_mapping.get(field_type, '')
        
        # デバッグ: 実際に使用される値をログ出力
        if result and field_type in ['company', 'company_name', 'message', 'name', 'email']:
            self.logger.info(f"入力値設定: {field_type} = '{result[:50]}{'...' if len(result) > 50 else ''}'")
        
        return result

# =============================================================================
# タブベース半自動処理システム
# =============================================================================

class TabBasedFormProcessor:
    """タブベースでの半自動フォーム処理システム"""
    
    def __init__(self, logger=None):
        self.logger = logger or FormSalesLogger()
        self.browser = None
        self.context = None
        self.cdp_port = None
        self.active_tabs = {}  # {tab_id: {company_data, page, status}}
        self.completed_companies = []
        self.failed_companies = []
    
    async def initialize_browser(self):
        """GUI Chromeブラウザの初期化"""
        try:
            # CDP付きでGUI Chromeを起動
            self.cdp_port = PortManager.assign_port('tab_processor', 9222)
            
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=False,  # GUI表示
                args=[
                    f'--remote-debugging-port={self.cdp_port}',
                    '--remote-debugging-address=0.0.0.0',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-web-security'
                ]
            )
            
            self.context = await self.browser.new_context()
            self.logger.info(f"GUI Chrome起動完了: CDP={self.cdp_port}")
            return True
            
        except Exception as e:
            self.logger.error(f"ブラウザ初期化エラー: {str(e)}")
            return False
    
    async def process_companies_with_tabs(self, companies_list: List[Dict]):
        """企業リストをタブベースで処理（自動的に次の行に移動）"""
        try:
            self.logger.info(f"タブベース処理開始: {len(companies_list)}社")
            
            for i, company in enumerate(companies_list):
                try:
                    company_name = company.get('company_name', f'企業{i+1}')
                    self.logger.info(f"🏢 [{i+1}/{len(companies_list)}] 処理開始: {company_name}")
                    
                    # 企業処理を実行
                    await self.process_single_company_tab(company, i + 1)
                    
                    # 処理結果を確認
                    if len(self.completed_companies) > 0 and self.completed_companies[-1] == company:
                        self.logger.info(f"✅ [{i+1}/{len(companies_list)}] 成功: {company_name} → 次の企業へ")
                    else:
                        self.logger.warning(f"⚠️ [{i+1}/{len(companies_list)}] 要手動作業: {company_name} → 次の企業へ")
                    
                    # 次の企業処理前に少し待機
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    self.logger.error(f"❌ [{i+1}/{len(companies_list)}] 処理エラー: {company.get('company_name', 'Unknown')} - {str(e)} → 次の企業へ")
                    continue
            
            # 最終結果をログ出力
            self.logger.info(f"🎯 全社処理完了: 成功{len(self.completed_companies)}社, 人間作業待ち{len(self.failed_companies)}社")
            
            if len(self.active_tabs) > 0:
                self.logger.info(f"📋 手動作業が必要なタブ: {len(self.active_tabs)}個")
                for tab_id, tab_info in self.active_tabs.items():
                    company_name = tab_info['company_data'].get('company_name', 'Unknown')
                    self.logger.info(f"  - {company_name}: {tab_info['status']}")
            
            return {
                'total_processed': len(companies_list),
                'completed': len(self.completed_companies),
                'pending_manual': len(self.failed_companies),
                'active_tabs': len(self.active_tabs)
            }
            
        except Exception as e:
            self.logger.error(f"タブベース処理エラー: {str(e)}")
            return None
    
    async def process_single_company_tab(self, company_data: Dict, company_index: int):
        """単一企業を新しいタブで処理"""
        try:
            company_name = company_data.get('company_name', f'企業{company_index}')
            url = company_data.get('url', '')
            
            self.logger.info(f"🏢 タブ処理開始 [{company_index}]: {company_name} - {url}")
            
            # 新しいタブ（ページ）を作成
            page = await self.context.new_page()
            tab_id = f"tab_{company_index}_{int(time.time())}"
            
            # タブ情報を記録
            self.active_tabs[tab_id] = {
                'company_data': company_data,
                'page': page,
                'status': 'processing',
                'company_index': company_index
            }
            
            # ページタイトルを設定（識別しやすくするため）
            await page.set_extra_http_headers({'User-Agent': f'FormSales-{company_name}'})
            
            # URLにナビゲート
            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)
                self.logger.info(f"ページロード成功 [{company_index}]: {url}")
            except Exception as e:
                self.logger.warning(f"ページロードエラー [{company_index}]: {str(e)}")
                self.active_tabs[tab_id]['status'] = 'navigation_failed'
                self.failed_companies.append(company_data)
                return
            
            # フォーム処理を実行
            success = await self.process_form_in_tab(page, company_data, company_index)
            
            if success:
                # フォーム送信成功 → タブを閉じる
                self.logger.info(f"✅ フォーム送信成功 [{company_index}]: {company_name} → タブクローズ")
                await page.close()
                del self.active_tabs[tab_id]
                self.completed_companies.append(company_data)
            else:
                # フォーム送信失敗 → タブを残す
                self.logger.warning(f"⚠️ フォーム送信失敗 [{company_index}]: {company_name} → タブ保持（人間作業待ち）")
                self.active_tabs[tab_id]['status'] = 'manual_required'
                self.failed_companies.append(company_data)
            
        except Exception as e:
            self.logger.error(f"タブ処理エラー [{company_index}]: {str(e)}")
            if tab_id in self.active_tabs:
                self.active_tabs[tab_id]['status'] = 'error'
                self.failed_companies.append(company_data)
    
    async def process_form_in_tab(self, page, company_data: Dict, company_index: int) -> bool:
        """タブ内でフォーム処理を実行（人間らしい操作で）"""
        try:
            company_name = company_data.get('company_name', f'企業{company_index}')
            current_url = page.url
            
            # 🎯 1. フォームページ判定（URL + 内容 + 入力要素）
            form_page_detector = FormPageDetector(page, self.logger)
            page_check = await form_page_detector.is_form_page()
            
            if page_check['is_form_page']:
                self.logger.info(f"✅ フォームページ確認 [{company_index}]: {company_name} - スコア{page_check['total_score']:.1f}")
                # フォームページと判定されたら即座に入力処理へ
                return await self.fill_and_submit_form_immediately(page, company_data, company_index)
            else:
                self.logger.info(f"❓ フォームページではない [{company_index}]: {company_name} - お問い合わせページを探索")
                # フォームページでない場合は従来の探索処理
                return await self.search_and_process_forms(page, company_data, company_index)
                
        except Exception as e:
            self.logger.error(f"フォーム処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def fill_and_submit_form_immediately(self, page, company_data: Dict, company_index: int) -> bool:
        """フォームページで即座に入力・送信処理"""
        try:
            company_name = company_data.get('company_name', f'企業{company_index}')
            
            # 🔍 ページ内のフォーム要素を検出
            comprehensive_detector = ComprehensiveFormDetector(page, self.logger)
            forms = await comprehensive_detector.detect_all_forms()
            
            if not forms:
                self.logger.warning(f"入力要素未発見 [{company_index}]: {company_name} - フォームページだが入力要素なし")
                return False
            
            # 最初のフォームで処理
            form_data = forms[0]
            self.logger.info(f"📝 フォーム入力開始 [{company_index}]: {company_name} - {len(form_data.get('input_elements', []))}個の入力要素")
            
            # 人間らしいフォーム入力
            improved_filler = ImprovedFormFiller(page, self.logger)
            await improved_filler.human_interaction.wait_for_page_stability()
            
            # 🎯 まず最初の入力欄にカーソルを合わせる（基本動作）
            cursor_result = await self.focus_first_input_field(page, form_data, company_index)
            
            if not cursor_result:
                self.logger.warning(f"⚠️ 入力欄検出失敗 [{company_index}]: {company_name} - 基本的な入力欄が見つからない")
                return False
            
            # 🎯 汎用フォーム入力システム（新方式）を先に試行
            universal_fill_result = await self.universal_form_filler(page, form_data, company_data, company_index)
            
            if universal_fill_result['success'] and universal_fill_result['filled_count'] > 0:
                self.logger.info(f"✅ 汎用入力成功 [{company_index}]: {company_name} - {universal_fill_result['filled_count']}フィールド入力")
                fill_result = universal_fill_result
            else:
                # フォールバック: 既存のImprovedFormFillerを使用
                self.logger.info(f"🔄 既存システムでフォールバック試行 [{company_index}]: {company_name}")
                fill_result = await improved_filler.fill_form_intelligently(form_data, company_data)
                
                if fill_result.get('requires_human'):
                    self.logger.warning(f"人間検証必要 [{company_index}]: {company_name} - CAPTCHA等検出")
                    return False
            
            if fill_result['success'] and fill_result['filled_count'] > 0:
                # 人間らしい遅延
                await improved_filler.human_interaction.random_delay(1.0, 3.0)
                
                # フォーム送信
                submit_result = await self.submit_form_human_like(page, form_data, company_index)
                
                if submit_result['success']:
                    self.logger.info(f"🎉 完了 [{company_index}]: {company_name} - 入力{fill_result['filled_count']}フィールド, 送信成功")
                    return True
                else:
                    self.logger.warning(f"送信失敗 [{company_index}]: {company_name} - {submit_result['message']}")
                    return False
            else:
                self.logger.warning(f"入力失敗 [{company_index}]: {company_name} - 入力可能フィールドなし")
                return False
                
        except Exception as e:
            self.logger.error(f"即座入力処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def focus_first_input_field(self, page, form_data: Dict, company_index: int) -> bool:
        """最初の入力欄にカーソルを合わせる（基本動作）"""
        try:
            company_name = form_data.get('company_name', f'企業{company_index}')
            self.logger.info(f"🎯 最初の入力欄検索開始 [{company_index}]: {company_name}")
            
            # 🔍 1. より簡単な方法で入力欄を検索
            input_selectors = [
                'input[type="text"]',
                'input[type="email"]', 
                'input[type="tel"]',
                'input:not([type])',  # type属性なし
                'textarea',
                'input[name*="name"]',
                'input[name*="company"]',
                'input[name*="mail"]',
                'input[placeholder*="名前"]',
                'input[placeholder*="会社"]',
                'input[placeholder*="メール"]'
            ]
            
            first_input = None
            found_selector = None
            
            # 順番に試して最初に見つかった入力欄を使用
            for selector in input_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        if await element.is_visible() and await element.is_enabled():
                            first_input = element
                            found_selector = selector
                            break
                    if first_input:
                        break
                except Exception as e:
                    self.logger.warning(f"セレクタ検索エラー [{company_index}] {selector}: {str(e)}")
                    continue
            
            if not first_input:
                # 🔍 2. より積極的に検索
                self.logger.info(f"標準検索失敗、積極的検索実行 [{company_index}]")
                try:
                    # すべてのinput要素を取得
                    all_inputs = await page.query_selector_all('input')
                    for element in all_inputs:
                        if await element.is_visible() and await element.is_enabled():
                            input_type = await element.get_attribute('type') or 'text'
                            if input_type not in ['hidden', 'submit', 'button', 'reset', 'image']:
                                first_input = element
                                found_selector = f'input[type="{input_type}"]'
                                break
                except Exception as e:
                    self.logger.warning(f"積極的検索エラー [{company_index}]: {str(e)}")
            
            if not first_input:
                # 🔍 3. 最終手段：textareaを検索
                try:
                    textareas = await page.query_selector_all('textarea')
                    for element in textareas:
                        if await element.is_visible() and await element.is_enabled():
                            first_input = element
                            found_selector = 'textarea'
                            break
                except Exception as e:
                    self.logger.warning(f"textarea検索エラー [{company_index}]: {str(e)}")
            
            if first_input:
                # 入力欄にカーソルを合わせる
                try:
                    # まずスクロールして表示領域に移動
                    await first_input.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    
                    # フォーカス
                    await first_input.focus()
                    await asyncio.sleep(0.3)
                    
                    # クリック（フォーカスが確実に移るように）
                    await first_input.click()
                    await asyncio.sleep(0.3)
                    
                    # 入力欄の詳細情報を取得
                    tag_name = await first_input.evaluate('el => el.tagName.toLowerCase()')
                    input_type = await first_input.get_attribute('type') or 'text'
                    name = await first_input.get_attribute('name') or ''
                    placeholder = await first_input.get_attribute('placeholder') or ''
                    
                    self.logger.info(f"✅ 最初の入力欄にカーソル合わせ成功 [{company_index}]: {tag_name}[{input_type}] name='{name}' placeholder='{placeholder}' (セレクタ: {found_selector})")
                    return True
                    
                except Exception as e:
                    self.logger.error(f"カーソル合わせエラー [{company_index}]: {str(e)}")
                    return False
            else:
                self.logger.error(f"❌ 入力欄が見つからない [{company_index}]: ページに入力可能なフィールドがない")
                return False
                
        except Exception as e:
            self.logger.error(f"最初の入力欄検索エラー [{company_index}]: {str(e)}")
            return False
    
    async def universal_form_filler(self, page, form_data: Dict, company_data: Dict, company_index: int) -> Dict:
        """汎用性の高いフォーム入力システム（新方式）"""
        try:
            company_name = company_data.get('company_name', f'企業{company_index}')
            self.logger.info(f"🎯 汎用フォーム入力開始 [{company_index}]: {company_name}")
            
            # 入力する情報を準備（要件定義書準拠）
            input_data = self.prepare_input_data(company_data)
            
            input_elements = form_data.get('input_elements', [])
            filled_count = 0
            total_attempts = 0
            
            for element_info in input_elements:
                try:
                    total_attempts += 1
                    
                    # 要素の詳細情報を取得
                    element = element_info.get('element')
                    field_type = element_info.get('field_type', 'unknown')
                    tag = element_info.get('tag', 'unknown')
                    input_type = element_info.get('type', 'text')
                    label = element_info.get('label', '')
                    name = element_info.get('name', '')
                    
                    self.logger.info(f"入力試行 [{company_index}]: {tag}[{input_type}] ラベル='{label}' name='{name}' フィールドタイプ={field_type}")
                    
                    # 入力値を決定
                    input_value = self.get_input_value_for_field_type(field_type, input_data, element_info)
                    
                    if not input_value and input_type not in ['checkbox', 'radio', 'submit', 'button']:
                        self.logger.warning(f"入力値なし [{company_index}]: フィールドタイプ={field_type} をスキップ")
                        continue
                    
                    # 🎯 複数の入力方法を試行
                    success = await self.try_multiple_input_methods(element, input_value, input_type, company_index)
                    
                    if success:
                        filled_count += 1
                        self.logger.info(f"✅ 入力成功 [{company_index}]: {field_type} = '{input_value[:30]}...'")
                        # 人間らしい遅延
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                    else:
                        self.logger.warning(f"❌ 入力失敗 [{company_index}]: {field_type}")
                        
                except Exception as e:
                    self.logger.error(f"要素処理エラー [{company_index}]: {str(e)}")
                    continue
            
            success_rate = filled_count / max(total_attempts, 1) * 100
            self.logger.info(f"汎用入力完了 [{company_index}]: {filled_count}/{total_attempts}個成功 ({success_rate:.1f}%)")
            
            return {
                'success': filled_count > 0,
                'filled_count': filled_count,
                'total_attempts': total_attempts,
                'success_rate': success_rate
            }
            
        except Exception as e:
            self.logger.error(f"汎用フォーム入力エラー [{company_index}]: {str(e)}")
            return {'success': False, 'filled_count': 0, 'total_attempts': 0}
    
    def prepare_input_data(self, company_data: Dict) -> Dict:
        """入力データを準備（要件定義書準拠）"""
        # エクセルから読み取った企業名と本文を使用
        target_company_name = company_data.get('company_name', '企業名不明')
        message_content = company_data.get('message', 'お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。')
        
        return {
            # ターゲット企業情報（エクセルデータ）
            'company': target_company_name,
            'company_name': target_company_name,
            
            # 自社情報（要件定義書準拠）
            'name': '富安　朱',
            'furigana': 'とみやす　あや',
            'furigana_katakana': 'トミヤス　アヤ',
            'sei': 'とみやす',
            'mei': 'あや',
            'sei_katakana': 'トミヤス',
            'mei_katakana': 'アヤ',
            'family_name': '富安',
            'first_name': '朱',
            
            # 自社連絡先（要件定義書準拠）
            'email': 'minefujiko.honbu@gmail.com',
            'email_confirm': 'minefujiko.honbu@gmail.com',
            'phone': '08036855092',
            
            # 自社住所（要件定義書準拠）
            'zip': '107-0062',
            'address': '東京都港区南青山3丁目1番36号青山丸竹ビル6F',
            'prefecture': '東京都',
            
            # 自社名（要件定義書準拠）
            'our_company': '株式会社みねふじこ',
            'sender_company': '株式会社みねふじこ',
            
            # メッセージ（エクセル本文）
            'message': message_content,
            'consultation_type': 'お問い合わせ',
            'inquiry_type': 'その他',
            'subject': '業務提携のご相談',
            
            # その他
            'privacy_policy': True,
            'agree': True,
            'newsletter': False
        }
    
    def get_input_value_for_field_type(self, field_type: str, input_data: Dict, element_info: Dict) -> str:
        """フィールドタイプに応じた入力値を取得"""
        # 直接マッピング
        if field_type in input_data:
            value = input_data[field_type]
            return str(value) if value is not None else ''
        
        # フォールバック: ラベルやname属性から推測
        label = element_info.get('label', '').lower()
        name = element_info.get('name', '').lower()
        combined_text = f"{label} {name}"
        
        # より詳細なマッピング
        if any(word in combined_text for word in ['名前', 'name', '氏名', 'お名前']):
            if 'ふりがな' in combined_text or 'フリガナ' in combined_text:
                return input_data.get('furigana', '')
            elif 'せい' in combined_text or '姓' in combined_text:
                return input_data.get('sei', '')
            elif 'めい' in combined_text or '名' in combined_text:
                return input_data.get('mei', '')
            return input_data.get('name', '')
        elif any(word in combined_text for word in ['会社', 'company', '企業']):
            return input_data.get('company', '')
        elif any(word in combined_text for word in ['メール', 'mail', 'email']):
            return input_data.get('email', '')
        elif any(word in combined_text for word in ['電話', 'tel', 'phone']):
            return input_data.get('phone', '')
        elif any(word in combined_text for word in ['メッセージ', '内容', '相談', 'message', 'inquiry']):
            return input_data.get('message', '')
        elif any(word in combined_text for word in ['住所', 'address']):
            return input_data.get('address', '')
        elif any(word in combined_text for word in ['郵便', 'zip', '〒']):
            return input_data.get('zip', '')
        
        return ''
    
    async def try_multiple_input_methods(self, element, input_value: str, input_type: str, company_index: int) -> bool:
        """複数の入力方法を試行"""
        try:
            # チェックボックス・ラジオボタンの処理
            if input_type in ['checkbox', 'radio']:
                return await self.handle_checkbox_radio(element, input_value, company_index)
            
            # セレクトボックスの処理
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            if tag_name == 'select':
                return await self.handle_select(element, input_value, company_index)
            
            # テキスト入力の処理
            if input_type in ['text', 'email', 'tel', 'url', 'password', 'search', 'number'] or tag_name == 'textarea':
                return await self.handle_text_input(element, input_value, company_index)
            
            return False
            
        except Exception as e:
            self.logger.error(f"入力方法試行エラー [{company_index}]: {str(e)}")
            return False
    
    async def handle_text_input(self, element, value: str, company_index: int) -> bool:
        """テキスト入力の処理（5つの方法を試行）"""
        try:
            # 方法1: JavaScript直接設定（最も確実）
            self.logger.info(f"方法1: JavaScript直接設定 [{company_index}]")
            try:
                await element.evaluate(f'''
                    (el) => {{
                        el.focus();
                        el.value = "{value}";
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }}
                ''')
                await asyncio.sleep(0.2)
                
                # 検証
                current_value = await element.evaluate('el => el.value')
                if current_value == value:
                    self.logger.info(f"✅ JavaScript直接設定成功 [{company_index}]")
                    return True
            except Exception as e:
                self.logger.warning(f"JavaScript直接設定失敗 [{company_index}]: {str(e)}")
            
            # 方法2: フォーカス後にJavaScript設定
            self.logger.info(f"方法2: フォーカス後JavaScript設定 [{company_index}]")
            try:
                await element.click()
                await asyncio.sleep(0.1)
                await element.evaluate(f'''
                    (el) => {{
                        el.value = "{value}";
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                ''')
                await asyncio.sleep(0.2)
                
                current_value = await element.evaluate('el => el.value')
                if current_value == value:
                    self.logger.info(f"✅ フォーカス後JavaScript成功 [{company_index}]")
                    return True
            except Exception as e:
                self.logger.warning(f"フォーカス後JavaScript失敗 [{company_index}]: {str(e)}")
            
            # 方法3: クリア後に一文字ずつ入力
            self.logger.info(f"方法3: 一文字ずつ入力 [{company_index}]")
            try:
                await element.click()
                await asyncio.sleep(0.1)
                
                # フィールドをクリア
                await element.evaluate('el => el.value = ""')
                await asyncio.sleep(0.1)
                
                # 一文字ずつ入力
                for char in value:
                    await element.type(char)
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                await asyncio.sleep(0.2)
                current_value = await element.evaluate('el => el.value')
                if current_value == value:
                    self.logger.info(f"✅ 一文字ずつ入力成功 [{company_index}]")
                    return True
            except Exception as e:
                self.logger.warning(f"一文字ずつ入力失敗 [{company_index}]: {str(e)}")
            
            # 方法4: Playwright標準のfill()
            self.logger.info(f"方法4: Playwright fill() [{company_index}]")
            try:
                await element.fill(value)
                await asyncio.sleep(0.2)
                
                current_value = await element.evaluate('el => el.value')
                if current_value == value:
                    self.logger.info(f"✅ Playwright fill()成功 [{company_index}]")
                    return True
            except Exception as e:
                self.logger.warning(f"Playwright fill()失敗 [{company_index}]: {str(e)}")
            
            # 方法5: キーボードエミュレーション
            self.logger.info(f"方法5: キーボードエミュレーション [{company_index}]")
            try:
                await element.click()
                await asyncio.sleep(0.1)
                
                # 全選択してクリア
                await element.press('Control+a')
                await asyncio.sleep(0.1)
                await element.press('Delete')
                await asyncio.sleep(0.1)
                
                # タイピング
                await element.type(value)
                await asyncio.sleep(0.2)
                
                current_value = await element.evaluate('el => el.value')
                if current_value == value:
                    self.logger.info(f"✅ キーボードエミュレーション成功 [{company_index}]")
                    return True
            except Exception as e:
                self.logger.warning(f"キーボードエミュレーション失敗 [{company_index}]: {str(e)}")
            
            self.logger.error(f"❌ 全ての入力方法が失敗 [{company_index}]: '{value}'")
            return False
            
        except Exception as e:
            self.logger.error(f"テキスト入力処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def handle_checkbox_radio(self, element, value, company_index: int) -> bool:
        """チェックボックス・ラジオボタンの処理"""
        try:
            input_type = await element.get_attribute('type')
            
            if input_type == 'checkbox':
                # チェックボックスは基本的にチェックする
                await element.evaluate('el => el.checked = true; el.dispatchEvent(new Event("change", { bubbles: true }));')
                self.logger.info(f"✅ チェックボックスをチェック [{company_index}]")
                return True
                
            elif input_type == 'radio':
                # ラジオボタンは選択する
                await element.evaluate('el => { el.checked = true; el.dispatchEvent(new Event("change", { bubbles: true })); }')
                self.logger.info(f"✅ ラジオボタンを選択 [{company_index}]")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"チェックボックス/ラジオボタン処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def handle_select(self, element, value: str, company_index: int) -> bool:
        """セレクトボックスの処理"""
        try:
            # 選択肢を取得
            options = await element.query_selector_all('option')
            
            for option in options:
                option_text = await option.inner_text()
                option_value = await option.get_attribute('value') or ''
                
                # 値またはテキストがマッチするかチェック
                if (value.lower() in option_text.lower() or 
                    value.lower() == option_value.lower() or
                    option_text.lower() in value.lower()):
                    
                    await element.select_option(value=option_value)
                    self.logger.info(f"✅ セレクトボックス選択成功 [{company_index}]: '{option_text}'")
                    return True
            
            # 特別処理: 都道府県
            if '東京' in value:
                for option in options:
                    option_text = await option.inner_text()
                    if '東京' in option_text:
                        option_value = await option.get_attribute('value') or ''
                        await element.select_option(value=option_value)
                        self.logger.info(f"✅ 都道府県選択成功 [{company_index}]: '{option_text}'")
                        return True
            
            self.logger.warning(f"❌ セレクトボックス選択失敗 [{company_index}]: '{value}' に対応する選択肢なし")
            return False
            
        except Exception as e:
            self.logger.error(f"セレクトボックス処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def search_and_process_forms(self, page, company_data: Dict, company_index: int) -> bool:
        """フォームページでない場合の探索処理（従来ロジック）"""
        try:
            # 簡易ブラウザマネージャーを作成
            temp_manager = UnifiedBrowserManager(headless=False, timeout=30)
            temp_manager.page = page
            temp_manager.logger = self.logger
            
            # 包括的フォーム探索
            forms = await discover_forms_comprehensive(temp_manager)
            
            if not forms:
                self.logger.warning(f"フォーム探索失敗 [{company_index}]: フォームが見つかりませんでした")
                return False
            
            # 最初のフォームで処理
            form_data = forms[0]
            
            # フォームページに移動（必要な場合）
            if form_data.get('source_type') == 'contact_page':
                form_url = form_data.get('source_url')
                if form_url and form_url != page.url:
                    await page.goto(form_url, wait_until='networkidle', timeout=15000)
                    self.logger.info(f"フォームページに移動 [{company_index}]: {form_url}")
                    # 移動後にフォームページ判定を再実行
                    form_page_detector = FormPageDetector(page, self.logger)
                    moved_page_check = await form_page_detector.is_form_page()
                    if moved_page_check['is_form_page']:
                        self.logger.info(f"✅ 移動先がフォームページ確認 [{company_index}]: スコア{moved_page_check['total_score']:.1f}")
                        return await self.fill_and_submit_form_immediately(page, company_data, company_index)
            
            # 人間らしいフォーム入力クラスを使用
            improved_filler = ImprovedFormFiller(page, self.logger)
            
            # ページの安定化を待つ
            await improved_filler.human_interaction.wait_for_page_stability()
            
            # CAPTCHA検出とフォーム入力
            fill_result = await improved_filler.fill_form_intelligently(form_data, company_data)
            
            # 人間検証が必要な場合はタブを残す
            if fill_result.get('requires_human'):
                self.logger.warning(f"人間検証必要 [{company_index}]: CAPTCHA等を検出、手動操作が必要です")
                return False
            
            if fill_result['success'] and fill_result['filled_count'] > 0:
                # 人間らしい遅延を追加
                await improved_filler.human_interaction.random_delay(1.0, 3.0)
                
                # フォーム送信試行（改良版送信機能を使用）
                submit_result = await self.submit_form_human_like(page, form_data, company_index)
                
                if submit_result['success']:
                    self.logger.info(f"フォーム送信成功 [{company_index}]: {fill_result['filled_count']}フィールド入力")
                    return True
                else:
                    self.logger.warning(f"フォーム送信失敗 [{company_index}]: {submit_result['message']}")
                    return False
            else:
                self.logger.warning(f"フォーム入力失敗 [{company_index}]: 入力可能フィールドがありませんでした")
                return False
                
        except Exception as e:
            self.logger.error(f"フォーム処理エラー [{company_index}]: {str(e)}")
            return False
    
    async def submit_form_human_like(self, page, form_data: Dict, company_index: int) -> Dict:
        """人間らしいフォーム送信処理"""
        try:
            human_interaction = HumanLikeInteraction(page, self.logger)
            
            # 拡張された送信ボタンパターン
            enhanced_submit_patterns = [
                # 基本的な送信ボタン
                'input[type="submit"]',
                'button[type="submit"]',
                'input[value*="送信"]',
                'button:contains("送信")',
                
                # 確認系ボタン（ユーザーリクエストに対応）
                'input[value*="確認"]',
                'button:contains("確認")',
                'input[value*="確認する"]',
                'button:contains("確認する")',
                'input[value*="確認画面"]',
                'button:contains("確認画面")',
                'input[value*="確認画面へ"]',
                'button:contains("確認画面へ")',
                'input[value*="内容確認"]',
                'button:contains("内容確認")',
                
                # その他のパターン
                'input[value*="申し込み"]',
                'button:contains("申し込み")',
                'input[value*="お申込み"]',
                'button:contains("お申込み")',
                'input[value*="問い合わせ"]',
                'button:contains("問い合わせ")',
                'input[value*="Submit"]',
                'button:contains("Submit")',
                'button[class*="submit"]',
                'input[class*="submit"]'
            ]
            
            # 送信ボタンを検索
            submit_button = None
            for pattern in enhanced_submit_patterns:
                try:
                    if ':contains(' in pattern:
                        # jQuery風のセレクタを処理
                        tag = pattern.split(':')[0]
                        text = pattern.split('"')[1]
                        elements = await page.query_selector_all(tag)
                        for element in elements:
                            element_text = await element.inner_text()
                            if text in element_text:
                                submit_button = element
                                break
                    else:
                        submit_button = await page.query_selector(pattern)
                    
                    if submit_button and await submit_button.is_visible():
                        self.logger.info(f"送信ボタン発見 [{company_index}]: {pattern}")
                        break
                        
                except Exception:
                    continue
            
            if not submit_button:
                return {'success': False, 'attempted': False, 'message': '送信ボタンが見つかりませんでした'}
            
            # 人間らしいクリックで送信
            self.logger.info(f"フォーム送信開始 [{company_index}]: 人間らしい操作で送信中...")
            
            click_success = await human_interaction.human_like_click(submit_button, delay_range=(0.5, 1.5))
            
            if not click_success:
                return {'success': False, 'attempted': True, 'message': '送信ボタンのクリックに失敗しました'}
            
            # 送信後の遷移/応答を待機
            await human_interaction.random_delay(2.0, 5.0)
            
            # 成功判定
            success_indicators = [
                'ありがとう', '送信完了', '受け付け', '完了', 'thank', 'success',
                'complete', 'received', '送信され', '確認いたしました', '受信',
                'submitted', 'sent', 'delivered'
            ]
            
            try:
                page_content = await page.content()
                current_url = page.url
                
                # 成功キーワードをチェック
                for keyword in success_indicators:
                    if keyword in page_content.lower():
                        self.logger.info(f"成功キーワード発見 [{company_index}]: {keyword}")
                        return {
                            'success': True,
                            'attempted': True,
                            'message': f'フォーム送信成功 (キーワード: {keyword})',
                            'final_url': current_url
                        }
                
                # URLが変わった場合も成功の可能性
                form_url = form_data.get('source_url', '')
                if form_url and current_url != form_url:
                    self.logger.info(f"URL変化を検出 [{company_index}]: {form_url} → {current_url}")
                    return {
                        'success': True,
                        'attempted': True,
                        'message': 'フォーム送信成功 (URL遷移確認)',
                        'final_url': current_url
                    }
                
                return {
                    'success': False,  # 確証がないので失敗扱い
                    'attempted': True,
                    'message': '送信完了の確認ができませんでした',
                    'final_url': current_url
                }
                
            except Exception as e:
                return {
                    'success': False,
                    'attempted': True,
                    'message': f'送信後の確認エラー: {str(e)}'
                }
                
        except Exception as e:
            self.logger.error(f"フォーム送信エラー [{company_index}]: {str(e)}")
            return {'success': False, 'attempted': False, 'message': f'送信エラー: {str(e)}'}
    
    async def close_browser(self):
        """ブラウザ終了"""
        try:
            if self.browser:
                await self.browser.close()
                self.logger.info("ブラウザ終了完了")
                
                # 残ったタブの情報をログ出力
                if self.active_tabs:
                    self.logger.info(f"人間作業待ちタブ: {len(self.active_tabs)}個")
                    for tab_id, tab_info in self.active_tabs.items():
                        company_name = tab_info['company_data'].get('company_name', 'Unknown')
                        self.logger.info(f"  - {company_name}: {tab_info['status']}")
        except Exception as e:
            self.logger.error(f"ブラウザ終了エラー: {str(e)}")
    
    def get_status_summary(self):
        """処理状況のサマリーを取得"""
        return {
            'completed_count': len(self.completed_companies),
            'pending_manual_count': len(self.failed_companies),
            'active_tabs_count': len(self.active_tabs),
            'completed_companies': self.completed_companies,
            'failed_companies': self.failed_companies,
            'active_tabs_info': [
                {
                    'company_name': tab_info['company_data'].get('company_name'),
                    'url': tab_info['company_data'].get('url'),
                    'status': tab_info['status'],
                    'company_index': tab_info['company_index']
                }
                for tab_info in self.active_tabs.values()
            ]
        }

# =============================================================================
# フォーム検出・処理関数
# =============================================================================

async def find_contact_links(browser_manager: UnifiedBrowserManager) -> List[Dict]:
    """お問い合わせページへのリンクを検索"""
    try:
        browser_manager.logger.info("お問い合わせリンク検索開始")
        
        # お問い合わせ系のキーワード
        contact_patterns = [
            'お問い合わせ', '相談', 'contact', 'inquiry', 'お問合せ',
            'Contact Us', 'Get in Touch', 'お申し込み', '申込み',
            'ご相談', '問い合わせ', 'コンタクト', '連絡', 'Contact',
            'Form', 'フォーム', '見積', '資料請求', '無料相談',
            'ご予約', '予約', 'reservation', 'booking', 'お見積り',
            'お申込み', '申し込む', 'apply', 'register', '登録'
        ]
        
        contact_links = []
        
        # テキストベースでリンクを検索
        for pattern in contact_patterns:
            try:
                # リンクテキストで検索
                links = await browser_manager.page.query_selector_all(f'a:has-text("{pattern}")')
                for link in links:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and text:
                        # 相対URLを絶対URLに変換
                        if href.startswith('/'):
                            current_url = browser_manager.page.url
                            base_url = '/'.join(current_url.split('/')[:3])
                            href = base_url + href
                        elif not href.startswith('http'):
                            current_url = browser_manager.page.url
                            base_url = '/'.join(current_url.split('/')[:-1])
                            href = base_url + '/' + href.lstrip('./')
                        
                        contact_links.append({
                            'url': href,
                            'text': text.strip(),
                            'pattern': pattern
                        })
            except Exception as e:
                browser_manager.logger.warning(f"リンク検索エラー ({pattern}): {str(e)}")
                continue
        
        # URLパターンでも検索
        url_patterns = [
            'contact', 'inquiry', 'form', 'consultation', 'consult',
            'reservation', 'booking', 'apply', 'request'
        ]
        
        for pattern in url_patterns:
            try:
                links = await browser_manager.page.query_selector_all(f'a[href*="{pattern}"]')
                for link in links:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and text:
                        # 相対URLを絶対URLに変換
                        if href.startswith('/'):
                            current_url = browser_manager.page.url
                            base_url = '/'.join(current_url.split('/')[:3])
                            href = base_url + href
                        elif not href.startswith('http'):
                            current_url = browser_manager.page.url
                            base_url = '/'.join(current_url.split('/')[:-1])
                            href = base_url + '/' + href.lstrip('./')
                        
                        contact_links.append({
                            'url': href,
                            'text': text.strip(),
                            'pattern': f'url:{pattern}'
                        })
            except Exception as e:
                browser_manager.logger.warning(f"URLパターン検索エラー ({pattern}): {str(e)}")
                continue
        
        # 重複を除去
        unique_links = []
        seen_urls = set()
        for link in contact_links:
            if link['url'] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link['url'])
        
        browser_manager.logger.info(f"お問い合わせリンク発見: {len(unique_links)}個")
        return unique_links
        
    except Exception as e:
        browser_manager.logger.error(f"お問い合わせリンク検索エラー: {str(e)}")
        return []

async def discover_forms_comprehensive(browser_manager: UnifiedBrowserManager, max_pages=3) -> List[Dict]:
    """包括的なフォーム検索（複数ページを探索）"""
    try:
        all_forms = []
        visited_urls = set()
        current_url = browser_manager.page.url
        
        browser_manager.logger.info("包括的フォーム検索開始")
        
        # 1. 現在のページで包括的フォーム検索
        comprehensive_detector = ComprehensiveFormDetector(browser_manager.page, browser_manager.logger)
        main_forms = await comprehensive_detector.detect_all_forms()
        for form in main_forms:
            form['source_url'] = current_url
            form['source_type'] = 'main_page'
        all_forms.extend(main_forms)
        visited_urls.add(current_url)
        
        browser_manager.logger.info(f"メインページフォーム: {len(main_forms)}個")
        
        # 2. お問い合わせリンクを検索
        contact_links = await find_contact_links(browser_manager)
        
        # 3. お問い合わせページでフォームを検索
        pages_checked = 0
        for link in contact_links:
            if pages_checked >= max_pages:
                break
                
            link_url = link['url']
            if link_url in visited_urls:
                continue
                
            try:
                browser_manager.logger.info(f"お問い合わせページ確認: {link['text']} ({link_url})")
                
                # ページに移動
                await browser_manager.page.goto(link_url, wait_until='networkidle', timeout=15000)
                await browser_manager.page.wait_for_timeout(2000)
                
                # 包括的フォーム検索
                page_detector = ComprehensiveFormDetector(browser_manager.page, browser_manager.logger)
                page_forms = await page_detector.detect_all_forms()
                for form in page_forms:
                    form['source_url'] = link_url
                    form['source_type'] = 'contact_page'
                    form['link_text'] = link['text']
                all_forms.extend(page_forms)
                
                browser_manager.logger.info(f"お問い合わせページフォーム: {len(page_forms)}個")
                
                visited_urls.add(link_url)
                pages_checked += 1
                
            except Exception as e:
                browser_manager.logger.warning(f"お問い合わせページエラー ({link_url}): {str(e)}")
                continue
        
        browser_manager.logger.info(f"包括的フォーム検索完了: 合計{len(all_forms)}個のフォーム発見")
        return all_forms
        
    except Exception as e:
        browser_manager.logger.error(f"包括的フォーム検索エラー: {str(e)}")
        return all_forms if 'all_forms' in locals() else []

class FormPageDetector:
    """フォームページ判定システム"""
    
    def __init__(self, page, logger=None):
        self.page = page
        self.logger = logger or FormSalesLogger()
    
    async def is_form_page(self) -> Dict:
        """現在のページがフォームページかどうかを判定"""
        try:
            current_url = self.page.url
            self.logger.info(f"🔍 フォームページ判定開始: {current_url}")
            
            # URLパターンでの判定
            url_score = self.check_url_patterns(current_url)
            
            # ページ内容での判定
            content_score = await self.check_page_content()
            
            # 入力要素の存在確認
            input_score = await self.check_input_elements()
            
            # 総合スコア計算
            total_score = url_score + content_score + input_score
            is_form_page = total_score >= 2.0  # しきい値
            
            result = {
                'is_form_page': is_form_page,
                'total_score': total_score,
                'url_score': url_score,
                'content_score': content_score,
                'input_score': input_score,
                'url': current_url
            }
            
            self.logger.info(f"{'✅ フォームページ判定: 成功' if is_form_page else '❌ フォームページ判定: 非対象'} (スコア: {total_score:.1f})")
            return result
            
        except Exception as e:
            self.logger.error(f"フォームページ判定エラー: {str(e)}")
            return {'is_form_page': False, 'total_score': 0, 'error': str(e)}
    
    def check_url_patterns(self, url: str) -> float:
        """URLパターンでフォームページを判定（ディレクトリ・ファイル名強化）"""
        url_lower = url.lower()
        
        # URLからパス部分を抽出
        from urllib.parse import urlparse
        parsed = urlparse(url_lower)
        path = parsed.path
        
        # ディレクトリ名・ファイル名を個別に分析
        path_parts = [part for part in path.split('/') if part]
        filename = path_parts[-1] if path_parts else ''
        directories = path_parts[:-1] if len(path_parts) > 1 else path_parts
        
        self.logger.info(f"URL分析: パス={path}, ディレクトリ={directories}, ファイル名={filename}")
        
        # 確実にフォームページとわかるパターン
        definitive_patterns = [
            'contact', 'inquiry', 'form', 'お問い合わせ', '問合せ',
            'consultation', 'consult', 'toiawase', 'soudan',
            'contact.php', 'contact.html', 'inquiry.php', 'form.php'
        ]
        
        # 可能性が高いパターン
        likely_patterns = [
            'apply', 'request', 'booking', 'reservation', 'estimate',
            '申込', '申し込み', '見積', '相談', '予約', 'moushikomi',
            'enquiry', 'info', 'mail'
        ]
        
        score = 0.0
        found_patterns = []
        
        # パス全体での確定パターンチェック
        for pattern in definitive_patterns:
            if pattern in url_lower:
                score += 1.5
                found_patterns.append(f"全体:{pattern}")
                break
        
        # ディレクトリ名での確定パターンチェック（追加ボーナス）
        if score == 0:  # 全体で見つからない場合
            for directory in directories:
                for pattern in definitive_patterns:
                    if pattern == directory or pattern in directory:
                        score += 1.5
                        found_patterns.append(f"ディレクトリ:{pattern}")
                        break
                if score > 0:
                    break
        
        # ファイル名での確定パターンチェック（追加ボーナス）
        if score == 0 and filename:  # まだ見つからない場合
            for pattern in definitive_patterns:
                if pattern == filename or pattern in filename:
                    score += 1.5
                    found_patterns.append(f"ファイル名:{pattern}")
                    break
        
        # 可能性パターンチェック（確定パターンがない場合のみ）
        if score == 0:
            for pattern in likely_patterns:
                if pattern in url_lower:
                    score += 1.0
                    found_patterns.append(f"可能性:{pattern}")
                    break
        
        # URLの末尾がスラッシュで終わる場合（ディレクトリ構造）のボーナス
        if url_lower.endswith('/') and any(pattern in url_lower for pattern in definitive_patterns[:6]):
            score += 0.3
            found_patterns.append("ディレクトリ構造ボーナス")
        
        if found_patterns:
            self.logger.info(f"URLパターン発見: {found_patterns}")
        
        return min(score, 2.0)  # 最大2.0
    
    async def check_page_content(self) -> float:
        """ページ内容でフォームページを判定"""
        try:
            # ページのテキスト内容を取得
            page_text = await self.page.inner_text('body')
            page_text_lower = page_text.lower()
            
            # フォーム関連キーワード
            form_keywords = [
                'お問い合わせ', '問合せ', 'contact', 'inquiry',
                'フォーム', 'form', '相談', 'consultation',
                '申込', '申し込み', 'apply', '見積', 'estimate',
                '必須', 'required', '入力', 'input',
                '送信', 'submit', '確認', 'confirm'
            ]
            
            score = 0.0
            found_keywords = []
            
            for keyword in form_keywords:
                if keyword in page_text_lower:
                    score += 0.3
                    found_keywords.append(keyword)
            
            # タイトルでも確認
            try:
                title = await self.page.title()
                title_lower = title.lower()
                for keyword in form_keywords[:8]:  # 主要キーワードのみ
                    if keyword in title_lower:
                        score += 0.5
                        found_keywords.append(f"title:{keyword}")
            except:
                pass
            
            if found_keywords:
                self.logger.info(f"コンテンツキーワード発見: {found_keywords[:5]}")
            
            return min(score, 2.0)  # 最大2.0
            
        except Exception as e:
            self.logger.warning(f"ページ内容チェックエラー: {str(e)}")
            return 0.0
    
    async def check_input_elements(self) -> float:
        """入力要素の存在でフォームページを判定（強化版）"""
        try:
            # 🔍 包括的な入力要素検出
            all_input_elements = await self.detect_all_input_elements()
            
            total_inputs = all_input_elements['total_count']
            submit_count = all_input_elements['submit_count']
            checkbox_count = all_input_elements['checkbox_count']
            radio_count = all_input_elements['radio_count']
            
            score = 0.0
            
            # 入力要素の数に応じてスコア
            if total_inputs >= 5:
                score += 2.0
            elif total_inputs >= 3:
                score += 1.5
            elif total_inputs >= 2:
                score += 1.0
            elif total_inputs >= 1:
                score += 0.5
            
            # 送信ボタンがあればボーナス
            if submit_count > 0:
                score += 0.5
            
            # チェックボックス・ラジオボタンがあればボーナス（フォームらしさ）
            if checkbox_count > 0:
                score += 0.3
            if radio_count > 0:
                score += 0.3
            
            self.logger.info(f"入力要素詳細: 総計{total_inputs}個 (送信{submit_count}, チェック{checkbox_count}, ラジオ{radio_count})")
            
            return min(score, 2.0)  # 最大2.0
            
        except Exception as e:
            self.logger.warning(f"入力要素チェックエラー: {str(e)}")
            return 0.0
    
    async def detect_all_input_elements(self) -> Dict:
        """あらゆる方法で入力要素を検出"""
        try:
            elements = {
                'text_inputs': [],
                'textareas': [],
                'selects': [],
                'checkboxes': [],
                'radios': [],
                'submit_buttons': [],
                'other_inputs': []
            }
            
            # 🔍 方法1: 標準的なHTMLセレクタ
            # テキスト系入力
            text_selectors = [
                'input[type="text"]',
                'input[type="email"]', 
                'input[type="tel"]',
                'input[type="url"]',
                'input[type="password"]',
                'input[type="search"]',
                'input[type="number"]',
                'input[type="date"]',
                'input[type="datetime-local"]',
                'input:not([type])',  # type属性なし（デフォルトtext）
                'input[type=""]'      # type属性が空
            ]
            
            for selector in text_selectors:
                found = await self.page.query_selector_all(selector)
                elements['text_inputs'].extend([el for el in found if await el.is_visible()])
            
            # テキストエリア
            textareas = await self.page.query_selector_all('textarea')
            elements['textareas'] = [el for el in textareas if await el.is_visible()]
            
            # セレクトボックス
            selects = await self.page.query_selector_all('select')
            elements['selects'] = [el for el in selects if await el.is_visible()]
            
            # チェックボックス
            checkboxes = await self.page.query_selector_all('input[type="checkbox"]')
            elements['checkboxes'] = [el for el in checkboxes if await el.is_visible()]
            
            # ラジオボタン
            radios = await self.page.query_selector_all('input[type="radio"]')
            elements['radios'] = [el for el in radios if await el.is_visible()]
            
            # 🔍 方法2: 送信ボタンの包括的検出
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("送信")',
                'button:has-text("確認")',
                'button:has-text("申し込み")',
                'button:has-text("問い合わせ")',
                'button:has-text("Submit")',
                'button:has-text("Send")',
                'input[value*="送信"]',
                'input[value*="確認"]',
                'input[value*="申込"]',
                'input[value*="Submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    found = await self.page.query_selector_all(selector)
                    elements['submit_buttons'].extend([el for el in found if await el.is_visible()])
                except:
                    continue
            
            # 🔍 方法3: JavaScript/動的要素の検出
            dynamic_inputs = await self.detect_dynamic_inputs()
            elements['other_inputs'].extend(dynamic_inputs)
            
            # 重複削除
            all_unique_inputs = set()
            for category, input_list in elements.items():
                unique_list = []
                for input_el in input_list:
                    try:
                        element_id = await input_el.evaluate('el => el.outerHTML')
                        if element_id not in all_unique_inputs:
                            all_unique_inputs.add(element_id)
                            unique_list.append(input_el)
                    except:
                        unique_list.append(input_el)
                elements[category] = unique_list
            
            # カウント計算
            total_count = (len(elements['text_inputs']) + 
                          len(elements['textareas']) + 
                          len(elements['selects']) +
                          len(elements['checkboxes']) +
                          len(elements['radios']) +
                          len(elements['other_inputs']))
            
            result = {
                'elements': elements,
                'total_count': total_count,
                'submit_count': len(elements['submit_buttons']),
                'checkbox_count': len(elements['checkboxes']),
                'radio_count': len(elements['radios'])
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"包括的入力要素検出エラー: {str(e)}")
            return {'total_count': 0, 'submit_count': 0, 'checkbox_count': 0, 'radio_count': 0}
    
    async def detect_dynamic_inputs(self) -> List:
        """JavaScript/動的に生成された入力要素を検出"""
        try:
            # JavaScriptで動的要素を検索
            dynamic_elements = await self.page.evaluate('''
                () => {
                    const inputs = [];
                    
                    // contenteditable要素（リッチテキストエディタ）
                    document.querySelectorAll('[contenteditable="true"]').forEach(el => {
                        if (el.offsetParent !== null) inputs.push(el);
                    });
                    
                    // カスタムinput要素（data-*属性やクラス名で判定）
                    document.querySelectorAll('[data-input], [data-field], .input-field, .form-control').forEach(el => {
                        if (el.offsetParent !== null && !el.matches('input, textarea, select')) {
                            inputs.push(el);
                        }
                    });
                    
                    // 見た目がinputっぽい要素
                    document.querySelectorAll('div, span').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.border && style.border !== 'none' && 
                            (style.backgroundColor === 'rgb(255, 255, 255)' || 
                             style.backgroundColor === 'white') &&
                            el.offsetParent !== null) {
                            inputs.push(el);
                        }
                    });
                    
                    return inputs.length;
                }
            ''')
            
            self.logger.info(f"動的要素検出: {dynamic_elements}個")
            return []  # 実際の要素は後で必要に応じて取得
            
        except Exception as e:
            self.logger.warning(f"動的要素検出エラー: {str(e)}")
            return []

class ComprehensiveFormDetector:
    """包括的フォーム検出システム"""
    
    def __init__(self, page, logger=None):
        self.page = page
        self.logger = logger or FormSalesLogger()
    
    async def detect_all_forms(self) -> List[Dict]:
        """あらゆる手段でフォームを検出"""
        self.logger.info("🔍 包括的フォーム検出開始")
        all_forms = []
        
        # 方法1: 標準的なformタグ検出
        forms_by_tag = await self.detect_forms_by_tag()
        all_forms.extend(forms_by_tag)
        self.logger.info(f"formタグ検出: {len(forms_by_tag)}個")
        
        # 方法2: 入力フィールドグループ検出（formタグなし）
        forms_by_inputs = await self.detect_forms_by_input_groups()
        all_forms.extend(forms_by_inputs)
        self.logger.info(f"入力グループ検出: {len(forms_by_inputs)}個")
        
        # 方法3: コンタクト系キーワード近辺検出
        forms_by_keywords = await self.detect_forms_by_keywords()
        all_forms.extend(forms_by_keywords)
        self.logger.info(f"キーワード近辺検出: {len(forms_by_keywords)}個")
        
        # 方法4: 送信ボタン周辺検出
        forms_by_submit = await self.detect_forms_by_submit_buttons()
        all_forms.extend(forms_by_submit)
        self.logger.info(f"送信ボタン周辺検出: {len(forms_by_submit)}個")
        
        # 方法5: iframe内検出
        forms_in_iframe = await self.detect_forms_in_iframes()
        all_forms.extend(forms_in_iframe)
        self.logger.info(f"iframe内検出: {len(forms_in_iframe)}個")
        
        # 重複削除とスコアリング
        unique_forms = self.deduplicate_and_score_forms(all_forms)
        
        self.logger.info(f"✅ 総検出数: {len(unique_forms)}個のフォーム")
        return unique_forms
    
    async def detect_forms_by_tag(self) -> List[Dict]:
        """標準的なformタグでフォーム検出（強化版）"""
        try:
            forms = await self.page.query_selector_all('form')
            form_list = []
            
            for i, form in enumerate(forms):
                # 🔍 包括的な入力要素検出
                inputs = await self.find_all_inputs_in_element(form)
                
                if len(inputs) >= 1:  # 1つでも入力要素があれば対象
                    form_data = await self.analyze_form_elements(form, inputs, f'form_tag_{i}')
                    if form_data:
                        form_data['detection_method'] = 'form_tag'
                        form_data['confidence'] = 0.9
                        form_list.append(form_data)
            
            return form_list
        except Exception as e:
            self.logger.error(f"formタグ検出エラー: {str(e)}")
            return []
    
    async def find_all_inputs_in_element(self, element):
        """要素内のあらゆる入力要素を検出（強化版）"""
        try:
            # 包括的なセレクタリスト
            input_selectors = [
                'input[type="text"]', 'input[type="email"]', 'input[type="tel"]',
                'input[type="url"]', 'input[type="password"]', 'input[type="search"]',
                'input[type="number"]', 'input[type="date"]', 'input[type="datetime-local"]',
                'input[type="time"]', 'input[type="month"]', 'input[type="week"]',
                'input[type="color"]', 'input[type="range"]', 'input[type="file"]',
                'input[type="checkbox"]', 'input[type="radio"]',
                'input:not([type])', 'input[type=""]',  # type属性なし/空
                'textarea', 'select',
                # カスタム要素
                '[contenteditable="true"]',
                '[data-input]', '[data-field]', '.input-field', '.form-control'
            ]
            
            all_inputs = []
            
            for selector in input_selectors:
                try:
                    found = await element.query_selector_all(selector)
                    for input_el in found:
                        if await input_el.is_visible():
                            all_inputs.append(input_el)
                except:
                    continue
            
            # 重複削除
            unique_inputs = []
            seen_elements = set()
            
            for input_el in all_inputs:
                try:
                    element_html = await input_el.evaluate('el => el.outerHTML')
                    if element_html not in seen_elements:
                        seen_elements.add(element_html)
                        unique_inputs.append(input_el)
                except:
                    unique_inputs.append(input_el)
            
            return unique_inputs
            
        except Exception as e:
            self.logger.warning(f"包括的入力検出エラー: {str(e)}")
            return []
    
    async def detect_forms_by_input_groups(self) -> List[Dict]:
        """入力フィールドのグループ化でフォーム検出（強化版）"""
        try:
            # 🔍 包括的に全ての入力要素を取得
            all_inputs = await self.find_all_inputs_in_element(self.page)
            self.logger.info(f"全入力要素: {len(all_inputs)}個")
            
            if len(all_inputs) < 2:
                return []
            
            # 入力要素をグループ化（近い位置にあるものをまとめる）
            groups = await self.group_nearby_inputs(all_inputs)
            form_list = []
            
            for i, group in enumerate(groups):
                if len(group) >= 2:  # 2つ以上の入力要素があるグループ
                    # 共通の親要素を見つける
                    parent = await self.find_common_parent(group)
                    if parent:
                        form_data = await self.analyze_form_elements(parent, group, f'input_group_{i}')
                        if form_data:
                            form_data['detection_method'] = 'input_group'
                            form_data['confidence'] = 0.7
                            form_list.append(form_data)
            
            return form_list
        except Exception as e:
            self.logger.error(f"入力グループ検出エラー: {str(e)}")
            return []
    
    async def detect_forms_by_keywords(self) -> List[Dict]:
        """コンタクト系キーワード周辺のフォーム検出"""
        try:
            contact_keywords = [
                'お問い合わせ', 'contact', 'inquiry', '相談', '申し込み',
                'お申込み', 'メッセージ', 'message', 'フォーム', 'form',
                '連絡', '問合せ', '見積', 'estimate', '資料請求'
            ]
            
            form_list = []
            
            for keyword in contact_keywords:
                # キーワードを含む要素を検索
                keyword_elements = await self.page.query_selector_all(f'text="{keyword}"')
                
                for element in keyword_elements:
                    # キーワード周辺の入力要素を検索
                    nearby_inputs = await self.find_nearby_inputs(element, radius=500)
                    
                    if len(nearby_inputs) >= 2:
                        parent = await self.find_common_parent(nearby_inputs)
                        if parent:
                            form_data = await self.analyze_form_elements(parent, nearby_inputs, f'keyword_{keyword}')
                            if form_data:
                                form_data['detection_method'] = 'keyword'
                                form_data['confidence'] = 0.8
                                form_data['trigger_keyword'] = keyword
                                form_list.append(form_data)
            
            return form_list
        except Exception as e:
            self.logger.error(f"キーワード検出エラー: {str(e)}")
            return []
    
    async def detect_forms_by_submit_buttons(self) -> List[Dict]:
        """送信ボタン周辺のフォーム検出"""
        try:
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("送信")',
                'button:has-text("確認")',
                'button:has-text("申し込み")',
                'button:has-text("問い合わせ")',
                'input[value*="送信"]',
                'input[value*="確認"]',
                'input[value*="申込"]'
            ]
            
            form_list = []
            
            for selector in submit_selectors:
                try:
                    buttons = await self.page.query_selector_all(selector)
                    
                    for button in buttons:
                        # ボタン周辺の入力要素を検索
                        nearby_inputs = await self.find_nearby_inputs(button, radius=800)
                        
                        if len(nearby_inputs) >= 1:
                            parent = await self.find_common_parent(nearby_inputs + [button])
                            if parent:
                                form_data = await self.analyze_form_elements(parent, nearby_inputs, f'submit_button')
                                if form_data:
                                    form_data['detection_method'] = 'submit_button'
                                    form_data['confidence'] = 0.8
                                    form_data['submit_button'] = button
                                    form_list.append(form_data)
                except:
                    continue
            
            return form_list
        except Exception as e:
            self.logger.error(f"送信ボタン検出エラー: {str(e)}")
            return []
    
    async def detect_forms_in_iframes(self) -> List[Dict]:
        """iframe内のフォーム検出"""
        try:
            iframes = await self.page.query_selector_all('iframe')
            form_list = []
            
            for iframe in iframes:
                try:
                    # iframe内のフォームを検索（セキュリティ制限があるため限定的）
                    iframe_forms = await iframe.content_frame()
                    if iframe_forms:
                        iframe_inputs = await iframe_forms.query_selector_all('input, textarea, select')
                        if len(iframe_inputs) >= 1:
                            form_data = {
                                'form_index': len(form_list),
                                'input_elements': [],
                                'form_element': iframe,
                                'detection_method': 'iframe',
                                'confidence': 0.6,
                                'is_iframe': True
                            }
                            form_list.append(form_data)
                except:
                    continue
            
            return form_list
        except Exception as e:
            self.logger.error(f"iframe検出エラー: {str(e)}")
            return []
    
    async def find_nearby_inputs(self, reference_element, radius=500):
        """指定要素の近くにある入力要素を検索"""
        try:
            ref_box = await reference_element.bounding_box()
            if not ref_box:
                return []
            
            all_inputs = await self.page.query_selector_all('input, textarea, select')
            nearby_inputs = []
            
            for input_elem in all_inputs:
                try:
                    input_box = await input_elem.bounding_box()
                    if not input_box:
                        continue
                    
                    # 距離計算
                    distance = ((ref_box['x'] - input_box['x']) ** 2 + 
                               (ref_box['y'] - input_box['y']) ** 2) ** 0.5
                    
                    if distance <= radius:
                        nearby_inputs.append(input_elem)
                except:
                    continue
            
            return nearby_inputs
        except Exception as e:
            self.logger.error(f"近隣入力要素検索エラー: {str(e)}")
            return []
    
    async def find_common_parent(self, elements):
        """要素群の共通親要素を見つける"""
        try:
            if not elements:
                return None
            
            # 最初の要素から親を辿る
            current = elements[0]
            for _ in range(10):  # 最大10階層まで
                parent = await current.query_selector('..')
                if not parent:
                    break
                
                # 他の全要素がこの親の子孫かチェック
                is_common = True
                for elem in elements[1:]:
                    try:
                        is_descendant = await parent.query_selector(f'* >> {await elem.evaluate("el => el.tagName")}')
                        if not is_descendant:
                            is_common = False
                            break
                    except:
                        is_common = False
                        break
                
                if is_common:
                    return parent
                
                current = parent
            
            return await elements[0].query_selector('..') or self.page
        except:
            return self.page
    
    async def group_nearby_inputs(self, inputs, max_distance=300):
        """入力要素を位置に基づいてグループ化"""
        try:
            groups = []
            used = set()
            
            for i, input1 in enumerate(inputs):
                if i in used:
                    continue
                
                group = [input1]
                used.add(i)
                
                try:
                    box1 = await input1.bounding_box()
                    if not box1:
                        continue
                    
                    for j, input2 in enumerate(inputs[i+1:], i+1):
                        if j in used:
                            continue
                        
                        try:
                            box2 = await input2.bounding_box()
                            if not box2:
                                continue
                            
                            distance = ((box1['x'] - box2['x']) ** 2 + 
                                       (box1['y'] - box2['y']) ** 2) ** 0.5
                            
                            if distance <= max_distance:
                                group.append(input2)
                                used.add(j)
                        except:
                            continue
                except:
                    continue
                
                if len(group) >= 2:
                    groups.append(group)
            
            return groups
        except Exception as e:
            self.logger.error(f"入力要素グループ化エラー: {str(e)}")
            return []
    
    async def analyze_form_elements(self, form_element, input_elements, form_id):
        """フォーム要素の詳細分析"""
        try:
            analyzed_inputs = []
            
            for input_element in input_elements:
                try:
                    if not await input_element.is_visible():
                        continue
                    
                    tag_name = await input_element.evaluate('el => el.tagName.toLowerCase()')
                    input_type = await input_element.get_attribute('type') or 'text'
                    name = await input_element.get_attribute('name') or ''
                    id_attr = await input_element.get_attribute('id') or ''
                    placeholder = await input_element.get_attribute('placeholder') or ''
                    class_attr = await input_element.get_attribute('class') or ''
                    
                    # 包括的なラベル検索
                    label_text = await find_label_text_comprehensive(self.page, input_element)
                    
                    # フィールドタイプを識別
                    field_type = identify_field_type_enhanced({
                        'tag': tag_name,
                        'type': input_type,
                        'name': name,
                        'id': id_attr,
                        'placeholder': placeholder,
                        'class': class_attr,
                        'label': label_text
                    })
                    
                    input_info = {
                        'tag': tag_name,
                        'type': input_type,
                        'name': name,
                        'id': id_attr,
                        'placeholder': placeholder,
                        'class': class_attr,
                        'label': label_text.strip(),
                        'field_type': field_type,
                        'element': input_element
                    }
                    
                    analyzed_inputs.append(input_info)
                except Exception as e:
                    self.logger.warning(f"要素分析エラー: {str(e)}")
                    continue
            
            if len(analyzed_inputs) >= 1:
                return {
                    'form_index': form_id,
                    'input_elements': analyzed_inputs,
                    'form_element': form_element,
                    'valid_field_count': len([inp for inp in analyzed_inputs if inp['field_type'] != 'unknown'])
                }
            
            return None
        except Exception as e:
            self.logger.error(f"フォーム分析エラー: {str(e)}")
            return None
    
    def deduplicate_and_score_forms(self, forms):
        """フォームの重複削除とスコアリング"""
        try:
            # 重複削除: 同じ入力要素を含むフォームを統合
            unique_forms = []
            
            for form in forms:
                is_duplicate = False
                
                for existing_form in unique_forms:
                    # 入力要素の重複チェック
                    overlap = 0
                    for inp1 in form['input_elements']:
                        for inp2 in existing_form['input_elements']:
                            if inp1['element'] == inp2['element']:
                                overlap += 1
                    
                    # 50%以上重複している場合は重複とみなす
                    if overlap >= len(form['input_elements']) * 0.5:
                        is_duplicate = True
                        # より信頼性の高い方を残す
                        if form['confidence'] > existing_form['confidence']:
                            unique_forms.remove(existing_form)
                            unique_forms.append(form)
                        break
                
                if not is_duplicate:
                    unique_forms.append(form)
            
            # スコアでソート（信頼性の高い順）
            return sorted(unique_forms, key=lambda x: x.get('confidence', 0), reverse=True)
        except Exception as e:
            self.logger.error(f"重複削除エラー: {str(e)}")
            return forms

async def search_forms_on_page(browser_manager: UnifiedBrowserManager) -> List[Dict]:
    """ページ上のフォームを検索（強化版）"""
    try:
        browser_manager.logger.info("フォーム検索開始")
        
        # フォーム要素を取得（フォームタグがない場合も考慮）
        forms = await browser_manager.page.query_selector_all('form')
        
        # フォームタグがない場合は、ページ全体から入力要素を検索
        if not forms:
            browser_manager.logger.info("form要素なし - ページ全体から入力要素を検索")
            forms = [await browser_manager.page.query_selector('body')]
        
        form_data_list = []
        
        for i, form in enumerate(forms):
            if not form:
                continue
                
            try:
                # フォーム内の入力要素を取得（すべての入力要素）
                inputs = await form.query_selector_all(
                    'input, textarea, select'
                )
                
                input_data = []
                for input_element in inputs:
                    try:
                        # 非表示要素をスキップ
                        if not await input_element.is_visible():
                            continue
                            
                        # 要素情報を取得
                        tag_name = await input_element.evaluate('el => el.tagName.toLowerCase()')
                        input_type = await input_element.get_attribute('type') or 'text'
                        name = await input_element.get_attribute('name') or ''
                        id_attr = await input_element.get_attribute('id') or ''
                        placeholder = await input_element.get_attribute('placeholder') or ''
                        class_attr = await input_element.get_attribute('class') or ''
                        value = await input_element.get_attribute('value') or ''
                        
                        # より包括的なラベル検索
                        label_text = await find_label_text_comprehensive(browser_manager.page, input_element)
                        
                        # フィールドタイプを識別
                        field_type = identify_field_type_enhanced({
                            'tag': tag_name,
                            'type': input_type,
                            'name': name,
                            'id': id_attr,
                            'placeholder': placeholder,
                            'class': class_attr,
                            'label': label_text,
                            'value': value
                        })
                        
                        input_info = {
                            'tag': tag_name,
                            'type': input_type,
                            'name': name,
                            'id': id_attr,
                            'placeholder': placeholder,
                            'class': class_attr,
                            'label': label_text.strip(),
                            'value': value,
                            'field_type': field_type,
                            'element': input_element
                        }
                        
                        input_data.append(input_info)
                        
                    except Exception as e:
                        browser_manager.logger.warning(f"入力要素情報取得エラー: {str(e)}")
                
                # フォームが有効かチェック（より柔軟に）
                valid_inputs = [inp for inp in input_data if inp['field_type'] != 'unknown']
                
                if len(input_data) >= 1:  # 1つでも入力フィールドがあれば対象とする
                    form_info = {
                        'form_index': i,
                        'input_elements': input_data,  # ImprovedFormFillerに合わせて変更
                        'form_element': form,
                        'valid_field_count': len(valid_inputs)
                    }
                    form_data_list.append(form_info)
                    browser_manager.logger.info(f"フォーム発見: {len(input_data)}個の入力フィールド（{len(valid_inputs)}個認識済み）")
            
            except Exception as e:
                browser_manager.logger.warning(f"フォーム解析エラー: {str(e)}")
        
        browser_manager.logger.info(f"フォーム検索完了: {len(form_data_list)}個のフォーム発見")
        return form_data_list
        
    except Exception as e:
        browser_manager.logger.error(f"フォーム検索エラー: {str(e)}")
        return []

async def find_label_text_comprehensive(page, input_element):
    """包括的なラベルテキスト検索"""
    try:
        label_text = ''
        
        # 方法1: id属性からlabel要素を探す
        input_id = await input_element.get_attribute('id')
        if input_id:
            label = await page.query_selector(f'label[for="{input_id}"]')
            if label:
                label_text = await label.text_content()
                if label_text and label_text.strip():
                    return label_text.strip()
        
        # 方法2: 親要素のテキストを探す
        parent = await input_element.query_selector('..')
        if parent:
            parent_text = await parent.text_content()
            if parent_text:
                # 入力要素自体のテキストを除去
                input_text = await input_element.text_content() or ''
                clean_text = parent_text.replace(input_text, '').strip()
                if clean_text:
                    label_text = clean_text
        
        # 方法3: 近くの要素からラベルっぽいテキストを探す
        if not label_text:
            # 前の兄弟要素を確認
            try:
                prev_sibling = await input_element.evaluate_handle('el => el.previousElementSibling')
                if prev_sibling:
                    prev_text = await prev_sibling.text_content()
                    if prev_text and len(prev_text.strip()) < 50:  # 短いテキストのみ
                        label_text = prev_text.strip()
            except:
                pass
        
        # 方法4: placeholder や name属性から推測
        if not label_text:
            placeholder = await input_element.get_attribute('placeholder')
            if placeholder:
                label_text = placeholder
            else:
                name = await input_element.get_attribute('name')
                if name:
                    label_text = name
        
        return label_text.strip() if label_text else ''
        
    except Exception:
        return ''

def identify_field_type_enhanced(field_info: Dict) -> str:
    """簡素化されたフィールドタイプ識別"""
    # すべてのテキスト情報を結合
    text_info = ' '.join([
        field_info.get('name', ''),
        field_info.get('id', ''),
        field_info.get('placeholder', ''),
        field_info.get('label', ''),
        field_info.get('class', ''),
        field_info.get('value', '')
    ]).lower()
    
    # input type による判定を最優先
    input_type = field_info.get('type', '').lower()
    tag = field_info.get('tag', '').lower()
    
    if input_type == 'email':
        return 'email'
    elif input_type == 'tel':
        return 'phone'
    elif tag == 'textarea':
        return 'message'
    elif tag == 'select':
        if '都道府県' in text_info or 'prefecture' in text_info or '県' in text_info:
            return 'prefecture'
        return 'consultation_type'
    elif input_type == 'checkbox':
        if any(word in text_info for word in ['プライバシー', '個人情報', '同意', 'privacy', 'agree']):
            return 'privacy_policy'
        return 'checkbox_other'
    elif input_type == 'radio':
        return 'consultation_type'
    
    # テキスト内容で判定
    if any(word in text_info for word in ['名前', 'name', '氏名']):
        if 'ふりがな' in text_info or 'フリガナ' in text_info:
            return 'furigana'
        elif 'せい' in text_info or '姓' in text_info:
            return 'sei'
        elif 'めい' in text_info or '名' in text_info:
            return 'mei'
        return 'name'
    elif any(word in text_info for word in ['会社', 'company', '企業', '企業名']):
        # エクセルから読み取った企業名を入力（ターゲット企業名）
        return 'company'
    elif any(word in text_info for word in ['メール', 'mail', 'email']):
        return 'email'
    elif any(word in text_info for word in ['電話', 'tel', 'phone']):
        return 'phone'
    elif any(word in text_info for word in ['郵便', 'zip', '〒']):
        return 'zip'
    elif any(word in text_info for word in ['住所', 'address']):
        return 'address'
    elif any(word in text_info for word in ['メッセージ', '内容', '相談', 'message', 'inquiry']):
        return 'message'
    
    return 'unknown'

def _identify_field_type(field_info: Dict) -> Optional[str]:
    """フィールドタイプを識別"""
    # テキスト情報を結合
    text_info = ' '.join([
        field_info.get('name', ''),
        field_info.get('id', ''),
        field_info.get('placeholder', ''),
        field_info.get('label', '')
    ]).lower()
    
    # フィールドパターンでマッチング
    field_patterns = {
        'company': ['会社', 'company', '企業', '法人'],
        'name': ['名前', 'name', '氏名', '担当者'],
        'email': ['mail', 'メール', 'email'],
        'phone': ['電話', 'phone', 'tel'],
        'message': ['message', 'メッセージ', '内容', '問い合わせ'],
        'date_first': ['第一希望', '第1希望', '希望日'],
        'date_second': ['第二希望', '第2希望'],
        'date_third': ['第三希望', '第3希望']
    }
    
    for field_type, patterns in field_patterns.items():
        for pattern in patterns:
            if pattern in text_info:
                return field_type
    
    return None

async def fill_form_fields(browser_manager: UnifiedBrowserManager, form_data: Dict, company_data: Dict) -> Dict:
    """フォームフィールドに入力"""
    result = {
        'filled_fields_count': 0,
        'errors': []
    }
    
    try:
        browser_manager.logger.info("フォーム入力開始")
        
        inputs = form_data.get('inputs', [])
        
        for field_info in inputs:
            try:
                field_type = _identify_field_type(field_info)
                
                if field_type:
                    # 入力値を決定
                    fill_value = ''
                    if field_type == 'company':
                        fill_value = company_data.get('company_name', '株式会社サンプル')
                    elif field_type == 'name':
                        fill_value = '田中太郎'
                    elif field_type == 'email':
                        fill_value = company_data.get('email', 'sample@example.com')
                    elif field_type == 'phone':
                        fill_value = company_data.get('phone', '03-1234-5678')
                    elif field_type == 'message':
                        fill_value = company_data.get('message', 'お世話になっております。弊社サービスについてご紹介させていただきたく、ご連絡いたします。')
                    elif field_type.startswith('date_'):
                        # 日付フィールドの処理
                        days_offset = {'date_first': 7, 'date_second': 8, 'date_third': 9}[field_type]
                        fill_value = _generate_date_string(days_offset, include_time=True)
                    
                    if fill_value:
                        # フィールドに入力
                        element = field_info['element']
                        success = await _fill_field_with_multiple_methods(browser_manager, element, fill_value)
                        
                        if success:
                            result['filled_fields_count'] += 1
                            browser_manager.logger.info(f"フィールド入力成功: {field_type} = {fill_value}")
                        else:
                            result['errors'].append(f"フィールド入力失敗: {field_type}")
                
            except Exception as e:
                error_msg = f"フィールド処理エラー: {str(e)}"
                result['errors'].append(error_msg)
                browser_manager.logger.warning(error_msg)
        
        browser_manager.logger.info(f"フォーム入力完了: {result['filled_fields_count']}フィールド")
        return result
        
    except Exception as e:
        error_msg = f"フォーム入力エラー: {str(e)}"
        result['errors'].append(error_msg)
        browser_manager.logger.error(error_msg)
        return result

def _generate_date_string(days_offset: int, include_time: bool = False) -> str:
    """指定日数後の日付文字列を生成"""
    target_date = datetime.now() + timedelta(days=days_offset)
    
    # 土日を避ける
    while target_date.weekday() >= 5:
        target_date += timedelta(days=1)
    
    year = target_date.year
    month = target_date.month
    day = target_date.day
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']
    weekday = weekday_names[target_date.weekday()]
    
    if include_time:
        return f"{year}年{month}月{day}日（{weekday}） 13:00"
    else:
        return f"{year}年{month}月{day}日（{weekday}）"

async def _fill_field_with_multiple_methods(browser_manager: UnifiedBrowserManager, element, value: str) -> bool:
    """複数の方法でフィールドに入力"""
    try:
        # 方法1: クリック + キーボード入力
        try:
            await element.click()
            await browser_manager.page.wait_for_timeout(100)
            # 既存値をクリア
            await browser_manager.page.keyboard.press('Control+a')
            await browser_manager.page.keyboard.press('Delete')
            await browser_manager.page.wait_for_timeout(100)
            # 新しい値を入力
            await browser_manager.page.keyboard.type(value)
            await browser_manager.page.wait_for_timeout(300)
            
            # 入力確認
            current_value = await element.input_value()
            if value in current_value:
                return True
        except:
            pass
        
        # 方法2: fill メソッド
        try:
            await element.fill(value)
            await browser_manager.page.wait_for_timeout(300)
            
            current_value = await element.input_value()
            if value in current_value:
                return True
        except:
            pass
        
        # 方法3: JavaScript直接設定
        try:
            await element.evaluate("""
                (element, value) => {
                    element.value = value;
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                }
            """, value)
            await browser_manager.page.wait_for_timeout(300)
            
            current_value = await element.input_value()
            if value in current_value:
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        browser_manager.logger.warning(f"フィールド入力エラー: {str(e)}")
        return False

async def submit_form(browser_manager: UnifiedBrowserManager, form_data: Dict) -> Dict:
    """フォームを送信"""
    result = {
        'attempted': False,
        'success': False,
        'message': ''
    }
    
    try:
        browser_manager.logger.info("フォーム送信開始")
        
        # 送信ボタンを探す
        submit_patterns = [
            '送信', 'submit', '送る', '確認', 'send', 'go', 'next',
            '申し込み', '問い合わせ', 'contact', 'inquiry',
            '確認画面', '確認画面へ', '確認する', '次へ', 'continue', '進む',
            '入力確認', '内容確認', '確認ページ', '確認ページへ',
            'check', 'confirm', 'verify', 'review', 'proceed',
            '申込', '申し込む', 'apply', 'register', '登録',
            'この内容で', 'この内容', '内容で送信', '送信する'
        ]
        
        form_element = form_data.get('form_element')
        submit_button = None
        
        # フォーム内から送信ボタンを探す
        for pattern in submit_patterns:
            selectors = [
                f"input[type='submit']",
                f"button[type='submit']",
                f"button:has-text('{pattern}')",
                f"input[value*='{pattern}']",
                f"button:text-is('{pattern}')",
                f"button:text-matches('.*{pattern}.*', 'i')"
            ]
            
            for selector in selectors:
                try:
                    if form_element:
                        elements = await form_element.query_selector_all(selector)
                    else:
                        elements = await browser_manager.page.query_selector_all(selector)
                    
                    for element in elements:
                        if await element.is_visible() and await element.is_enabled():
                            submit_button = element
                            break
                    
                    if submit_button:
                        break
                except:
                    continue
            
            if submit_button:
                break
        
        if submit_button:
            result['attempted'] = True
            
            # 送信前のスクリーンショット
            await browser_manager._take_screenshot("フォーム送信前")
            
            # 送信実行
            await submit_button.click()
            
            # 送信後の処理を待機
            await browser_manager.page.wait_for_timeout(3000)
            
            # 送信後のスクリーンショット
            await browser_manager._take_screenshot("フォーム送信後")
            
            # 送信成功の確認
            success = await _verify_submission_success(browser_manager)
            
            if success:
                result['success'] = True
                result['message'] = 'フォーム送信が完了しました'
                browser_manager.logger.info("✅ フォーム送信成功")
            else:
                result['message'] = 'フォーム送信でエラーが発生しました'
                browser_manager.logger.warning("⚠️ フォーム送信の完了が確認できませんでした")
        else:
            result['message'] = '送信ボタンが見つかりませんでした'
            browser_manager.logger.warning("送信ボタンが見つかりませんでした")
        
        return result
        
    except Exception as e:
        result['message'] = f'送信エラー: {str(e)}'
        browser_manager.logger.error(result['message'])
        return result

async def _verify_submission_success(browser_manager: UnifiedBrowserManager) -> bool:
    """送信成功の確認"""
    try:
        # 成功キーワードの検索
        success_keywords = [
            '送信完了', '受付完了', 'ありがとうございました', '送信しました',
            'submitted', 'sent successfully', 'thank you', 'confirmation',
            '受け付けました', '送信が完了', 'complete', 'success'
        ]
        
        # ページコンテンツの確認
        page_content = await browser_manager.page.content()
        page_text = page_content.lower()
        
        for keyword in success_keywords:
            if keyword.lower() in page_text:
                browser_manager.logger.info(f"成功キーワード発見: {keyword}")
                return True
        
        # URLの確認
        current_url = browser_manager.page.url.lower()
        url_success_keywords = ['thank', 'success', 'complete', 'confirm']
        
        for keyword in url_success_keywords:
            if keyword in current_url:
                browser_manager.logger.info(f"成功URL検出: {keyword} in {current_url}")
                return True
        
        return False
        
    except Exception as e:
        browser_manager.logger.error(f"送信成功確認エラー: {str(e)}")
        return False

# =============================================================================
# メイン処理関数
# =============================================================================

async def process_company_complete(company_data: Dict, enable_screenshots=False, screenshot_callback=None) -> Dict:
    """企業の完全処理"""
    result = {
        'company_name': company_data.get('company_name', ''),
        'url': company_data.get('url', ''),
        'form_found': False,
        'submit_attempted': False,
        'submit_success': False,
        'filled_fields_count': 0,
        'status_message': '',
        'errors': [],
        'forms_discovered': 0,
        'form_source_type': '',
        'form_source_url': ''
    }
    
    browser_manager = None
    
    try:
        logger = FormSalesLogger()
        logger.info(f"🏢 企業処理開始: {company_data.get('company_name')} - {company_data.get('url')}")
        
        # ブラウザマネージャーの初期化
        browser_manager = UnifiedBrowserManager(
            headless=True,  # CDP埋め込み表示のためヘッドレス
            timeout=30,
            enable_screenshots=enable_screenshots,
            component_name="form_processor"
        )
        
        if screenshot_callback:
            browser_manager.set_screenshot_callback(screenshot_callback)
        
        # ブラウザ初期化
        if not await browser_manager.initialize_browser():
            result['status_message'] = 'ブラウザの初期化に失敗しました'
            result['errors'].append('ブラウザ初期化失敗')
            return result
        
        # URLにナビゲート
        if not await browser_manager.navigate_to_url(company_data.get('url', '')):
            result['status_message'] = 'URLにアクセスできませんでした'
            result['errors'].append('URL アクセス失敗')
            return result
        
        # フォーム検索（包括的な検索でお問い合わせページも探索）
        forms = await discover_forms_comprehensive(browser_manager)
        
        if not forms:
            result['status_message'] = 'フォームが見つかりませんでした（メインページ・お問い合わせページ共に確認済み）'
            result['errors'].append('フォーム未発見')
            return result
        
        result['form_found'] = True
        result['forms_discovered'] = len(forms)
        
        # 最初のフォームを処理
        form_data = forms[0]
        
        # フォームの発見場所を記録
        result['form_source_type'] = form_data.get('source_type', 'main_page')
        result['form_source_url'] = form_data.get('source_url', company_data.get('url', ''))
        
        form_source = form_data.get('source_type', 'main_page')
        if form_source == 'contact_page':
            logger.info(f"お問い合わせページでフォーム発見: {form_data.get('link_text', '')} ({form_data.get('source_url', '')})")
            
            # お問い合わせページのフォームの場合、そのページに移動する必要がある
            form_page_url = form_data.get('source_url', '')
            if form_page_url and browser_manager.page.url != form_page_url:
                logger.info(f"フォームページに移動: {form_page_url}")
                if not await browser_manager.navigate_to_url(form_page_url):
                    result['status_message'] = 'フォームページにアクセスできませんでした'
                    result['errors'].append('フォームページアクセス失敗')
                    return result
        
        # フォーム入力
        fill_result = await fill_form_fields(browser_manager, form_data, company_data)
        result['filled_fields_count'] = fill_result['filled_fields_count']
        result['errors'].extend(fill_result['errors'])
        
        if result['filled_fields_count'] > 0:
            # フォーム送信
            submit_result = await submit_form(browser_manager, form_data)
            result['submit_attempted'] = submit_result['attempted']
            result['submit_success'] = submit_result['success']
            
            if result['submit_success']:
                form_location = "お問い合わせページ" if form_data.get('source_type') == 'contact_page' else "メインページ"
                result['status_message'] = f'フォーム送信完了（{form_location}、{result["filled_fields_count"]}フィールド入力）'
            else:
                form_location = "お問い合わせページ" if form_data.get('source_type') == 'contact_page' else "メインページ"
                result['status_message'] = f'フォーム入力完了、送信失敗（{form_location}、{result["filled_fields_count"]}フィールド入力）: {submit_result["message"]}'
        else:
            result['status_message'] = 'フィールドに入力できませんでした'
        
        return result
        
    except Exception as e:
        error_msg = f'処理エラー: {str(e)}'
        result['status_message'] = error_msg
        result['errors'].append(error_msg)
        return result
        
    finally:
        if browser_manager:
            await browser_manager.close_browser()

def run_in_new_loop(coro):
    """新しいイベントループで非同期関数を実行"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    except Exception as e:
        logger = FormSalesLogger()
        logger.error(f"イベントループエラー: {str(e)}")
        return {
            'company_name': '',
            'url': '',
            'form_found': False,
            'submit_attempted': False,
            'submit_success': False,
            'filled_fields_count': 0,
            'status_message': f'処理エラー: {str(e)}',
            'errors': [str(e)]
        }

def process_single_company_advanced(company_data: Dict, enable_screenshots=False, screenshot_callback=None) -> Dict:
    """外部インターフェース用の関数（旧システム互換性用）"""
    return run_in_new_loop(
        process_company_complete(company_data, enable_screenshots, screenshot_callback)
    )

async def process_companies_tab_based(companies_list: List[Dict]) -> Dict:
    """タブベース半自動処理システムの非同期版"""
    processor = TabBasedFormProcessor()
    
    try:
        # ブラウザ初期化
        if not await processor.initialize_browser():
            return {
                'success': False,
                'error': 'ブラウザの初期化に失敗しました',
                'completed_count': 0,
                'pending_manual_count': 0,
                'active_tabs_count': 0
            }
        
        # 企業リスト処理
        result = await processor.process_companies_with_tabs(companies_list)
        
        if result is None:
            return {
                'success': False,
                'error': 'タブベース処理に失敗しました',
                'completed_count': 0,
                'pending_manual_count': 0,
                'active_tabs_count': 0
            }
        
        # 処理状況サマリーを取得
        status_summary = processor.get_status_summary()
        
        # 注意: ブラウザは閉じずに残す（人間が手動操作できるように）
        # await processor.close_browser()
        
        return {
            'success': True,
            'total_processed': result['total_processed'],
            'completed_count': result['completed'],
            'pending_manual_count': result['pending_manual'],
            'active_tabs_count': result['active_tabs'],
            'completed_companies': status_summary['completed_companies'],
            'failed_companies': status_summary['failed_companies'],
            'active_tabs_info': status_summary['active_tabs_info'],
            'message': f'処理完了: 自動送信成功{result["completed"]}社, 人間作業待ち{result["pending_manual"]}社'
        }
        
    except Exception as e:
        # エラー時はブラウザを閉じる
        await processor.close_browser()
        return {
            'success': False,
            'error': f'処理エラー: {str(e)}',
            'completed_count': 0,
            'pending_manual_count': 0,
            'active_tabs_count': 0
        }

def process_companies_tab_based_sync(companies_list: List[Dict]) -> Dict:
    """タブベース半自動処理システムの外部インターフェース"""
    return run_in_new_loop(process_companies_tab_based(companies_list))

# =============================================================================
# 互換性クラス
# =============================================================================

class EmailSender:
    """メール送信クラス"""
    def __init__(self):
        self.logger = FormSalesLogger()
    
    def send_email(self, to_email=None, subject="", content="", company_name=""):
        """メール送信（現在は記録のみ）"""
        self.logger.info(f"メール記録: 宛先={to_email}, 件名={subject}, 企業={company_name}")
        return True

class AdvancedWebCrawler:
    def __init__(self, *args, **kwargs):
        self.manager = UnifiedBrowserManager(*args, **kwargs)
    
    async def find_contact_forms_advanced(self, url):
        if await self.manager.navigate_to_url(url):
            return await search_forms_on_page(self.manager)
        return []
    
    async def close_playwright(self):
        await self.manager.close_browser()

class AdvancedFormFiller:
    def __init__(self, *args, **kwargs):
        self.manager = UnifiedBrowserManager(*args, **kwargs)
    
    async def fill_and_submit_form_advanced(self, form_data):
        fill_result = await fill_form_fields(self.manager, form_data, {})
        submit_result = await submit_form(self.manager, form_data)
        
        return {
            'filled_fields_count': fill_result['filled_fields_count'],
            'submit_attempted': submit_result['attempted'],
            'submit_success': submit_result['success'],
            'errors': fill_result['errors'] + [submit_result['message']] if not submit_result['success'] else fill_result['errors']
        }
    
    async def close_playwright(self):
        await self.manager.close_browser()

if __name__ == "__main__":
    # テスト用のサンプル実行
    test_company = {
        'company_name': 'テスト企業',
        'url': 'https://fujino-gyosei.jp/contact/',
        'message': 'テストメッセージ'
    }
    
    result = process_single_company_advanced(test_company, enable_screenshots=True)
    print(f"処理結果: {result}")