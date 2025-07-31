#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCE環境テストスクリプト
Chrome WebDriverの動作確認用
"""

import os
import sys
import logging
from form_automation import setup_chrome_driver, setup_logging

def test_environment():
    """GCE環境の動作テスト"""
    print("=" * 60)
    print("🧪 GCE環境動作テスト開始")
    print("=" * 60)
    
    # ログ設定
    setup_logging()
    
    # 環境変数確認
    print("📋 環境変数確認:")
    print(f"DISPLAY: {os.environ.get('DISPLAY', '未設定')}")
    print(f"CHROME_BIN: {os.environ.get('CHROME_BIN', '未設定')}")
    
    # Chrome実行ファイル確認
    print("\n🔍 Chrome実行ファイル確認:")
    chrome_paths = [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium-browser',
        '/usr/bin/chromium'
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✅ 見つかりました: {path}")
        else:
            print(f"❌ 見つかりません: {path}")
    
    # WebDriver初期化テスト
    print("\n🚀 WebDriver初期化テスト:")
    driver = None
    try:
        driver = setup_chrome_driver()
        print("✅ WebDriver初期化成功")
        
        # Googleアクセステスト
        print("\n🌐 Googleアクセステスト:")
        driver.get('https://www.google.com')
        title = driver.title
        print(f"✅ アクセス成功 - タイトル: {title}")
        
        # ブラウザ情報取得
        user_agent = driver.execute_script("return navigator.userAgent;")
        print(f"📱 User Agent: {user_agent[:100]}...")
        
        # 簡単なフォーム操作テスト
        print("\n📝 フォーム操作テスト:")
        try:
            search_box = driver.find_element("name", "q")
            search_box.send_keys("test")
            print("✅ フォーム入力成功")
            search_box.clear()
            print("✅ フォームクリア成功")
        except Exception as e:
            print(f"⚠️ フォーム操作警告: {str(e)}")
        
        print("\n🎉 全テスト成功！システムは正常に動作します")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        print("\n🔧 解決方法:")
        print("1. ./setup_gce.sh を実行")
        print("2. export DISPLAY=:99")
        print("3. Xvfb :99 -screen 0 1920x1080x24 &")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                print("🧹 WebDriver終了完了")
            except:
                pass

def test_file_processing():
    """ファイル処理テスト"""
    print("\n📁 ファイル処理テスト:")
    
    # テストCSVファイル作成
    test_csv = """company,contact_url,address
テスト会社1,https://example.com/contact,東京都
テスト会社2,https://google.com,大阪府
テスト会社3,invalid_url,愛知県"""
    
    test_file = 'test_data.csv'
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_csv)
    
    try:
        from form_automation import read_input_file, get_target_urls
        
        df = read_input_file(test_file)
        print(f"✅ CSV読み込み成功: {len(df)}行")
        
        urls = get_target_urls(df)
        print(f"✅ URL抽出成功: {len(urls)}件")
        
        for url_info in urls:
            print(f"  - {url_info['company']}: {url_info['url']}")
        
        os.remove(test_file)
        print("✅ ファイル処理テスト成功")
        return True
        
    except Exception as e:
        print(f"❌ ファイル処理テスト失敗: {str(e)}")
        if os.path.exists(test_file):
            os.remove(test_file)
        return False

if __name__ == '__main__':
    success = True
    
    # 環境テスト
    if not test_environment():
        success = False
    
    # ファイル処理テスト
    if not test_file_processing():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎊 全テスト成功！システムは正常に動作します")
        print("💡 python3 app.py でシステムを起動してください")
    else:
        print("⚠️ 一部テストが失敗しました")
        print("💡 ./setup_gce.sh でセットアップを実行してください")
    print("=" * 60)
    
    sys.exit(0 if success else 1)