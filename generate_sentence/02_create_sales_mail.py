"""
営業メール自動生成システム
ExcelからURLを取得し、企業情報を分析して「俺のクローン」サービスの営業メールを生成
"""

import os
import sys
import time
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from openai import OpenAI

# =============================================================================
# 設定とグローバル変数
# =============================================================================

# ファイルパスとシート設定
CSV_FILE_PATH = "./uploads/新築一戸建て住宅建設list1.csv"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL_COLUMN = "url" # URLが記載されている列名
SUBJECT_COLUMN = "件名"  # 件名出力列
BODY_COLUMN = "本文"     # 本文出力列
SPLIT_SYMBOL = "###SPLIT###"  # 件名と本文の分割記号

# 処理設定
OPEN_INTERVAL = 3  # タブを開く間隔（秒）
MAX_PAGES_PER_SITE = 10  # サイトあたりの最大回遊ページ数
PAGE_LOAD_TIMEOUT = 10  # ページ読み込みタイムアウト（秒）
REQUEST_TIMEOUT = 10  # リクエストタイムアウト（秒）

# 処理範囲
start_row_number = 0
end_row_number = 121

# OpenAI設定
OPENAI_MODEL = "gpt-4.1-mini-2025-04-14" # "gpt-4.1-nano"  # 使用モデル
MAX_TOKENS = 1000  # 営業メール生成時の最大トークン数

# 弊社サービス情報
OUR_SERVICE_INFO = """
1. サービス概要
  1.1 「俺のクローン」は、社長や社員の姿・声・表情をAIで完全コピーした動画（AI分身）を生成し、
      24時間365日SNSやWebサイトで自動集客・採用を実現するサービス。

2. 主な特徴
  2.1 AI分身動画の自動生成
    2.1.1 初回約1時間の撮影後は、追加撮影不要であらゆるシナリオ・表情の動画を生成。
  2.2 マルチプラットフォーム対応
    2.2.1 YouTubeショート、Instagramリール、TikTok、Xなど主要SNS向けに一括制作。
  2.3 丸ごと代行サービス
    2.3.1 企画・台本作成、撮影、編集、投稿までプロがワンストップで実施。

3. 解決できる経営課題＆効果指標
  3.1 解決できる課題
    3.1.1 動画制作に10～15時間かかる工数を大幅削減。
    3.1.2 投稿頻度不足による反応・問い合わせの低迷を解消。
    3.1.3 魅力的なコンテンツ不足での応募数減少を防止。
  3.2 実績指標
    3.2.1 認知者数：50%増
    3.2.2 応募者数：30%増
    3.2.3 撮影時間：90%減

4. 導入までの流れ
  4.1 Zoomでのヒアリングと日程調整
  4.2 無料オンライン打ち合わせ（活用提案）
  4.3 台本作成方法の決定
  4.4 契約締結・初期費用支払い確認
  4.5 初回撮影（弊社訪問）＆AIクローン作成
  4.6 納品・運用サポート開始

5. 活用事例
  5.1 セミナー動画：社長不在でも自動集客で参加者50%増
  5.2 SNS動画：クロスプラットフォーム投稿で認知大量獲得
  5.3 社内研修動画：属人性排除＆台本作成負荷低減
  5.4 多言語動画：海外向けプロモーション・インバウンド対応

6. FAQ要点
  6.1 撮影時間は初回約1時間のみ
  6.2 特別な機材不要（服装・場所のみ準備）
  6.3 企画～投稿まで丸投げOK

"""

# =============================================================================
# ログ設定
# =============================================================================

def setup_logging() -> logging.Logger:
    """
    ログ設定を初期化する
    
    Returns:
        logging.Logger: 設定されたロガー
    """
    # ログディレクトリを作成
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイル名（日時付き）
    log_filename = f"sales_email_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"ログファイルを作成しました: {log_filepath}")
    return logger


def setup_openai_client() -> OpenAI:
    """
    OpenAIクライアントを設定する
    
    Returns:
        OpenAI: 設定されたOpenAIクライアント
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
    
    try:
        client = OpenAI(api_key=api_key)
        # 接続テスト（簡単なAPIコールを実行）
        test_response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print(f"OpenAI API接続テスト成功（モデル: {OPENAI_MODEL}）")
        return client
    except Exception as e:
        raise ValueError(f"OpenAI API接続エラー: {str(e)}")

# =============================================================================
# ユーティリティ関数
# =============================================================================

def check_environment_variables() -> bool:
    """
    必要な環境変数が設定されているかチェックする
    
    Returns:
        bool: すべての環境変数が設定されている場合True
    """
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"エラー: 以下の環境変数が設定されていません: {missing_vars}")
        return False
    
    print("必要な環境変数がすべて設定されています ✓")
    return True

def is_valid_url(url: str) -> bool:
    """
    URLが有効かどうかをチェックする
    
    Args:
        url (str): チェックするURL
        
    Returns:
        bool: 有効なURLの場合True
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)
    except Exception:
        return False

def normalize_url(url: str) -> str:
    """
    URLを正規化する（httpスキームを追加など）
    
    Args:
        url (str): 正規化するURL
        
    Returns:
        str: 正規化されたURL
    """
    if not url:
        return ""
    
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url

# =============================================================================
# Excel操作関数
# =============================================================================

def load_csv_data() -> Tuple[pd.DataFrame, bool]:
    """
    CSVファイルからデータを読み込む
    
    Returns:
        Tuple[pd.DataFrame, bool]: DataFrameと成功フラグ
    """
    try:
        if not os.path.exists(CSV_FILE_PATH):
            print(f"エラー: CSVファイルが見つかりません: {CSV_FILE_PATH}")
            return pd.DataFrame(), False
        
        df = pd.read_csv(CSV_FILE_PATH)
        
        # 件名列と本文列が存在しない場合は作成
        if SUBJECT_COLUMN not in df.columns:
            df[SUBJECT_COLUMN] = ""
            print(f"'{SUBJECT_COLUMN}'列を作成しました")
        
        if BODY_COLUMN not in df.columns:
            df[BODY_COLUMN] = ""
            print(f"'{BODY_COLUMN}'列を作成しました")
        
        print(f"CSVファイルを読み込みました: {len(df)}行")
        return df, True
        
    except Exception as e:
        print(f"CSV読み込みエラー: {str(e)}")
        return pd.DataFrame(), False

def save_email_to_csv(df: pd.DataFrame, row_index: int, subject: str, body: str) -> bool:
    """
    生成した営業メールをCSVファイルに保存する
    
    Args:
        df (pd.DataFrame): DataFrame
        row_index (int): 行インデックス
        subject (str): 件名
        body (str): 本文
        
    Returns:
        bool: 保存成功フラグ
    """
    try:
        # 件名列と本文列に値を設定
        df.loc[row_index, SUBJECT_COLUMN] = subject
        df.loc[row_index, BODY_COLUMN] = body
        
        # CSVファイルに保存
        df.to_csv(CSV_FILE_PATH, index=False, encoding='utf-8')
        
        return True
        
    except Exception as e:
        print(f"CSV保存エラー (行{row_index}): {str(e)}")
        return False

def split_email_content(email_content: str) -> Tuple[str, str]:
    """
    メール内容を件名と本文に分割する
    
    Args:
        email_content (str): 分割記号で区切られたメール内容
        
    Returns:
        Tuple[str, str]: (件名, 本文)
    """
    try:
        if SPLIT_SYMBOL in email_content:
            parts = email_content.split(SPLIT_SYMBOL, 1)
            subject = parts[0].strip()
            body = parts[1].strip()
            return subject, body
        else:
            # 分割記号が見つからない場合、全体を件名として扱う
            return email_content.strip(), ""
    except Exception as e:
        # エラーが発生した場合、全体を件名として扱う
        return email_content.strip(), ""

# =============================================================================
# Webスクレイピング関数
# =============================================================================

def create_chrome_driver() -> webdriver.Chrome:
    """
    Chromeヘッドレスドライバーを作成する
    
    Returns:
        webdriver.Chrome: 設定されたChromeドライバー
    """
    options = Options()
    options.add_argument('--headless')  # ヘッドレスモード
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # JavaScript無効化（高速化のため）
    prefs = {"profile.managed_default_content_settings.javascript": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    return driver

def extract_text_from_page(driver: webdriver.Chrome, url: str) -> str:
    """
    指定URLからテキストを抽出する
    
    Args:
        driver (webdriver.Chrome): Webドライバー
        url (str): 抽出するURL
        
    Returns:
        str: 抽出されたテキスト
    """
    try:
        driver.get(url)
        
        # ページ読み込み待機
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # ページのテキストを取得
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text
        
        # 改行とスペースを整理
        text = ' '.join(text.split())
        
        return text
        
    except TimeoutException:
        return f"タイムアウト: {url}"
    except WebDriverException as e:
        return f"ドライバーエラー: {str(e)}"
    except Exception as e:
        return f"ページ抽出エラー: {str(e)}"

def get_internal_links(driver: webdriver.Chrome, base_url: str) -> List[str]:
    """
    ページから内部リンクを取得する
    
    Args:
        driver (webdriver.Chrome): Webドライバー
        base_url (str): ベースURL
        
    Returns:
        List[str]: 内部リンクのリスト
    """
    try:
        links = []
        base_domain = urlparse(base_url).netloc
        
        # aタグのhref属性を取得
        link_elements = driver.find_elements(By.TAG_NAME, "a")
        
        for element in link_elements:
            href = element.get_attribute("href")
            if href:
                # 絶対URLに変換
                full_url = urljoin(base_url, href)
                
                # 同一ドメインかチェック
                if urlparse(full_url).netloc == base_domain:
                    links.append(full_url)
        
        # 重複を除去
        return list(set(links))
        
    except Exception as e:
        print(f"リンク取得エラー: {str(e)}")
        return []

def scrape_company_info(url: str, logger: logging.Logger) -> str:
    """
    企業サイトから情報を収集する
    
    Args:
        url (str): 企業サイトのURL
        logger (logging.Logger): ロガー
        
    Returns:
        str: 収集した企業情報
    """
    if not is_valid_url(url):
        error_msg = f"無効なURL: {url}"
        logger.error(error_msg)
        return error_msg
    
    url = normalize_url(url)
    logger.info(f"企業情報収集開始: {url}")
    
    driver = None
    try:
        driver = create_chrome_driver()
        
        # メインページのテキストを取得
        main_text = extract_text_from_page(driver, url)
        
        if "エラー" in main_text:
            logger.warning(f"メインページ取得失敗: {main_text}")
            return f"サイト接続エラー: {main_text}"
        
        all_text = f"メインページ: {main_text}\n\n"
        
        # 内部リンクを取得
        internal_links = get_internal_links(driver, url)
        logger.info(f"内部リンク取得: {len(internal_links)}件")
        
        # 最大ページ数まで回遊
        visited_count = 1  # メインページをカウント
        
        for link in internal_links[:MAX_PAGES_PER_SITE - 1]:  # メインページ分を引く
            if visited_count >= MAX_PAGES_PER_SITE:
                break
            
            logger.info(f"ページ回遊 {visited_count + 1}/{MAX_PAGES_PER_SITE}: {link}")
            
            page_text = extract_text_from_page(driver, link)
            
            if not page_text.startswith(("タイムアウト", "エラー")):
                all_text += f"ページ{visited_count + 1}: {page_text}\n\n"
                visited_count += 1
                
                # 間隔を空ける
                time.sleep(1)
            else:
                logger.warning(f"ページ取得スキップ: {page_text}")
        
        logger.info(f"企業情報収集完了: {visited_count}ページ取得")
        return all_text
        
    except Exception as e:
        error_msg = f"スクレイピングエラー: {str(e)}"
        logger.error(error_msg)
        return error_msg
        
    finally:
        if driver:
            driver.quit()

# =============================================================================
# OpenAI API関数
# =============================================================================

def generate_sales_email(company_info: str, openai_client: OpenAI, logger: logging.Logger) -> str:
    """
    企業情報をもとに営業メールを生成する
    
    Args:
        company_info (str): 企業情報
        openai_client (OpenAI): OpenAIクライアント
        logger (logging.Logger): ロガー
        
    Returns:
        str: 生成された営業メール（件名###SPLIT###本文の形式）
    """
    try:
        # 企業情報の長さを制限（APIの制限を考慮）
        max_company_info_length = 8000  # 文字数制限
        
        if len(company_info) > max_company_info_length:
            company_info = company_info[:max_company_info_length] + "..."
            logger.info(f"企業情報を{max_company_info_length}文字に制限しました")
        
        prompt = f"""
以下の企業情報をもとに、「俺のクローン」のサービスサイトとても閲覧したくなるようメールの本文内容を作成してください。

【企業情報】
{company_info}

【弊社サービス情報】
{OUR_SERVICE_INFO}

【注意】
改行を使って読みやすさを意識してください。
必ず{SPLIT_SYMBOL}で件名と本文を区切ってください。

【サービスサイトを見たくするメール作成指示】
1. 件名と本文を作成してください
2. 本文は500文字程度で作成してください
3. この企業はYouTube等のSNSの活用に力を入れています。
4. この企業の集客やSNS戦略、採用方法を具体的に調べてください。ただし明文化されていないので企業情報を元にメタ思考で考えてください。
5. そのうえで弊社サービスがこの企業にぴったりであることを論理的に誠実なトーンでメール本文を書いてください。
6. 件名と本文の間に{SPLIT_SYMBOL}を入れて、以下の形式で出力してください：

件名内容{SPLIT_SYMBOL}

先方の企業名
代表取締役社長の苗字 様

株式会社みねふじこ 代表 冨安朱と申します。
芸能事務所を経営後、現在クローン動画の受託事業をしております。

突然のご連絡失礼いたします。

本文内容

サービスサイトはこちら
https://ore-no-clone.jp

30分の無料zoomで、御社がより楽に、お客様数・採用者数を増やす方法
をご説明しますので、お手すきの時間を下記ページよりご選択ください。
（効率化のため、失礼ではありますがシステムでの日程調整とさせていただいております。）
https://timerex.net/s/lovantvictoria01_a930/8e8d634c

ご多忙のところとは存じますが、何卒よろしくお願いいたします。

株式会社みねふじこ
代表取締役社長 冨安朱
https://www.minefujiko.jp

"""
        logger.info("OpenAI API呼び出し開始")
        
        # システムプロンプト
        system_prompt = "あなたは優秀な営業担当者です。企業の特徴を理解し、サービスサイトを閲覧したくなる最適なメール本文を作成します。"
        
        # OpenAI APIを呼び出し
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
            top_p=1.0,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        email_content = response.choices[0].message.content.strip()
        logger.info("営業メール生成完了")
        
        return email_content
        
    except Exception as e:
        error_msg = f"営業メール生成エラー: {str(e)}"
        logger.error(error_msg)
        return error_msg

# =============================================================================
# メイン処理関数
# =============================================================================

def process_single_company(df: pd.DataFrame, row_index: int, openai_client: OpenAI, logger: logging.Logger) -> bool:
    """
    単一企業の処理を実行する
    
    Args:
        df (pd.DataFrame): DataFrame
        row_index (int): 処理する行のインデックス
        openai_client (OpenAI): OpenAIクライアント
        logger (logging.Logger): ロガー
        
    Returns:
        bool: 処理成功フラグ
    """
    try:
        # URLを取得
        url = df.loc[row_index, URL_COLUMN]
        
        if pd.isna(url) or not url:
            error_msg = "URLが空です"
            logger.warning(f"行{row_index + 2}: {error_msg}")
            save_email_to_csv(df, row_index, f"エラー: {error_msg}", "")
            return False
        
        company_name = df.loc[row_index, df.columns[0]] if len(df.columns) > 0 else "企業名不明"
        logger.info(f"行{row_index + 2}: {company_name} - {url}")
        
        # 企業情報を収集
        print(f"  企業情報収集中...")
        company_info = scrape_company_info(url, logger)
        
        # エラーチェック
        if company_info.startswith(("エラー", "無効", "サイト接続エラー")):
            logger.error(f"行{row_index + 2}: 企業情報収集失敗 - {company_info}")
            save_email_to_csv(df, row_index, f"エラー: {company_info}", "")
            return False
        
        # 営業メールを生成
        print(f"  営業メール生成中...")
        email_content = generate_sales_email(company_info, openai_client, logger)
        
        # エラーチェック
        if email_content.startswith("営業メール生成エラー"):
            logger.error(f"行{row_index + 2}: 営業メール生成失敗 - {email_content}")
            save_email_to_csv(df, row_index, f"エラー: {email_content}", "")
            return False
        
        # 件名と本文に分割
        subject, body = split_email_content(email_content)
        
        # Excelに保存
        success = save_email_to_csv(df, row_index, subject, body)
        
        if success:
            logger.info(f"行{row_index + 2}: 処理完了")
            print(f"  ✓ 営業メール生成完了 (件名: {len(subject)}文字, 本文: {len(body)}文字)")
            return True
        else:
            logger.error(f"行{row_index + 2}: Excel保存失敗")
            return False
            
    except Exception as e:
        error_msg = f"処理エラー: {str(e)}"
        logger.error(f"行{row_index + 2}: {error_msg}")
        save_email_to_csv(df, row_index, f"エラー: {error_msg}", "")
        return False

def main():
    """
    メイン処理関数
    """
    print("=== 営業メール自動生成システム ===")
    print("開始時刻:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # ログ設定
    logger = setup_logging()
    
    try:
        # 環境変数チェック
        if not check_environment_variables():
            return
        
        # OpenAIクライアント設定
        openai_client = setup_openai_client()
        logger.info("OpenAIクライアント設定完了")
        
        # CSVデータ読み込み
        df, success = load_csv_data()
        if not success:
            return
        
        # 処理範囲の確認
        total_rows = min(end_row_number, len(df))
        actual_start = max(0, start_row_number)
        
        print(f"\n処理範囲: 行{actual_start + 2}～{total_rows + 1} ({total_rows - actual_start}件)")
        print(f"使用モデル: {OPENAI_MODEL}")
        print(f"最大回遊ページ数: {MAX_PAGES_PER_SITE}")
        print(f"出力先: {SUBJECT_COLUMN}列（件名）、{BODY_COLUMN}列（本文）")
        
        # 処理統計
        stats = {
            'total': total_rows - actual_start,
            'success': 0,
            'failed': 0,
            'start_time': datetime.now()
        }
        
        # 各企業を処理
        for i in range(actual_start, total_rows):
            current = i - actual_start + 1
            
            print(f"\n--- {current}/{stats['total']} 件目の処理 ---")
            
            success = process_single_company(df, i, openai_client, logger)
            
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
            
            # 進捗表示
            progress = (current / stats['total']) * 100
            print(f"進捗: {progress:.1f}% (成功: {stats['success']}, 失敗: {stats['failed']})")
            
            # API制限を考慮して間隔を空ける
            if current < stats['total']:  # 最後の処理でない場合
                print(f"  {OPEN_INTERVAL}秒待機中...")
                time.sleep(OPEN_INTERVAL)
        
        # 処理結果サマリー
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']
        
        print("\n=== 処理完了 ===")
        print(f"総件数: {stats['total']}")
        print(f"成功: {stats['success']}")
        print(f"失敗: {stats['failed']}")
        print(f"処理時間: {stats['duration']}")
        print(f"終了時刻: {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        logger.info(f"全処理完了 - 成功: {stats['success']}, 失敗: {stats['failed']}")
        
    except KeyboardInterrupt:
        print("\n処理が中断されました")
        logger.warning("ユーザーによって処理が中断されました")
        
    except Exception as e:
        print(f"\nシステムエラー: {str(e)}")
        logger.error(f"システムエラー: {str(e)}")

if __name__ == "__main__":
    main()