#!/usr/bin/env python3
"""
CDP接続テスト - ブラウザ埋め込み表示用
"""

import asyncio
import time
import requests
from playwright.async_api import async_playwright

async def start_browser_with_cdp():
    """CDP付きブラウザを起動して維持"""
    playwright = await async_playwright().start()
    
    try:
        print("🚀 CDPブラウザ起動中...")
        
        # CDPポート付きでブラウザを起動
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--remote-debugging-port=9222',
                '--remote-debugging-address=0.0.0.0',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        print('✅ ブラウザ起動成功（CDP=9222）')
        
        # テストページにアクセス
        await page.goto('https://www.google.com')
        print(f'✅ ページアクセス成功: {page.url}')
        
        # CDP接続をテスト
        print("\n🔗 CDP接続テスト中...")
        
        for i in range(5):
            try:
                response = requests.get('http://localhost:9222/json', timeout=2)
                if response.status_code == 200:
                    tabs = response.json()
                    print(f"✅ CDP接続成功: {len(tabs)}個のタブ検出")
                    for tab in tabs[:2]:  # 最初の2個だけ表示
                        print(f"   - {tab.get('title', 'タイトルなし')}: {tab.get('url', '')}")
                    break
                else:
                    print(f"⚠️ CDP応答エラー: {response.status_code}")
            except Exception as e:
                print(f"⚠️ CDP接続試行 {i+1}/5: {str(e)}")
                time.sleep(1)
        
        print(f"\n📱 Webアプリケーションで http://localhost:5000 にアクセスして")
        print(f"📱 ブラウザ埋め込み表示をテストしてください")
        print(f"\n⏱️ 30秒間ブラウザを維持します...")
        
        # 30秒間維持
        for i in range(30):
            await asyncio.sleep(1)
            if i % 5 == 0:
                print(f"⏱️ {30-i}秒残り...")
        
        await browser.close()
        await playwright.stop()
        print('✅ ブラウザ終了')
        
    except Exception as e:
        print(f'❌ エラー: {e}')

if __name__ == "__main__":
    asyncio.run(start_browser_with_cdp())