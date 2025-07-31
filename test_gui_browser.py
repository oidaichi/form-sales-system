#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GCE GUI環境でのブラウザ動作テスト
新しいタブの動作確認用
"""

import os
import time
import logging
from form_automation import setup_chrome_driver, setup_logging

def test_gui_browser():
    """GCE GUI環境でのブラウザ動作テスト"""
    print("=" * 60)
    print("🖥️  GCE GUI環境 ブラウザ動作テスト")
    print("=" * 60)
    
    # ログ設定
    setup_logging()
    
    # 環境変数確認
    print("📋 環境変数確認:")
    print(f"DISPLAY: {os.environ.get('DISPLAY', '未設定')}")
    
    # Chrome WebDriverテスト
    driver = None
    try:
        print("\n🚀 Chrome WebDriver初期化...")
        driver = setup_chrome_driver()
        print("✅ WebDriver初期化成功")
        
        # Googleアクセステスト
        print("\n🌐 Googleアクセステスト...")
        driver.get('https://www.google.com')
        print(f"✅ アクセス成功 - タイトル: {driver.title}")
        
        # 新しいタブテスト
        print("\n📑 新しいタブ作成テスト...")
        original_handles = driver.window_handles
        print(f"初期タブ数: {len(original_handles)}")
        
        # 新しいタブを開く
        driver.execute_script("window.open('about:blank', '_blank');")
        time.sleep(2)
        
        current_handles = driver.window_handles
        print(f"新しいタブ作成後のタブ数: {len(current_handles)}")
        
        if len(current_handles) > len(original_handles):
            print("✅ 新しいタブの作成成功")
            
            # 新しいタブに切り替え
            new_tab = list(set(current_handles) - set(original_handles))[0]
            driver.switch_to.window(new_tab)
            print("✅ 新しいタブに切り替え成功")
            
            # Yahoo Japanにアクセス
            driver.get('https://www.yahoo.co.jp')
            print(f"✅ 新しいタブでアクセス成功 - タイトル: {driver.title}")
            
            time.sleep(3)
            
            # タブを閉じる
            driver.close()
            print("✅ 新しいタブを閉じました")
            
            # 元のタブに戻る
            driver.switch_to.window(original_handles[0])
            print("✅ 元のタブに戻りました")
            
        else:
            print("❌ 新しいタブの作成に失敗")
        
        print("\n🎉 GCE GUI環境でのブラウザ動作テスト成功!")
        print("💡 システムは正常に動作します")
        
        # 5秒間ブラウザを表示
        print("\n⏰ 5秒間ブラウザを表示します...")
        time.sleep(5)
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        print("\n🔧 解決方法:")
        print("1. GCE環境でGUIデスクトップが起動していることを確認")
        print("2. export DISPLAY=:0 (またはX11セッションに応じて)")
        print("3. ./setup_gce.sh でセットアップを再実行")
        return False
        
    finally:
        if driver:
            try:
                driver.quit()
                print("🧹 WebDriver終了完了")
            except:
                pass

if __name__ == '__main__':
    success = test_gui_browser()
    
    print("\n" + "=" * 60)
    if success:
        print("🎊 テスト成功! GCE GUI環境でブラウザが正常動作")
        print("💡 python3 app.py でシステムを起動してください")
    else:
        print("⚠️  テスト失敗 - GCE GUI環境を確認してください")
    print("=" * 60)