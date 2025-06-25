#!/usr/bin/env python3
"""
フォーム営業システム起動スクリプト
"""

import subprocess
import sys
import time
import os

def check_conda_environment():
    """conda環境をチェック"""
    try:
        result = subprocess.run(['conda', 'info', '--envs'], capture_output=True, text=True)
        if 'base' in result.stdout and '*' in result.stdout:
            print("✅ conda base環境が有効です")
            return True
        else:
            print("❌ conda base環境が無効です")
            print("🚨 実行前に以下を実行してください:")
            print("   eval \"$(conda shell.bash hook)\"")
            print("   conda activate base")
            return False
    except:
        print("❌ condaが見つかりません")
        return False

def check_dependencies():
    """依存関係をチェック"""
    required_modules = ['pandas', 'openpyxl', 'requests', 'bs4', 'playwright', 'flask']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            missing.append(module)
    
    if missing:
        print(f"\n🚨 不足している依存関係: {', '.join(missing)}")
        print("インストールコマンド:")
        print("pip install pandas openpyxl requests beautifulsoup4 playwright flask flask-socketio")
        print("playwright install chromium")
        return False
    
    return True

def start_flask_app():
    """Flaskアプリケーションを起動"""
    print("\n🚀 Flaskアプリケーション起動中...")
    print("📱 ブラウザで http://localhost:5000 にアクセスしてください")
    print("🛑 停止するには Ctrl+C を押してください")
    print("-" * 50)
    
    try:
        # Flaskアプリを起動
        os.system("python app.py")
    except KeyboardInterrupt:
        print("\n🛑 アプリケーションを停止しました")

def main():
    print("🚀 フォーム営業システム起動スクリプト")
    print("=" * 50)
    
    # conda環境チェック
    if not check_conda_environment():
        sys.exit(1)
    
    print("\n📦 依存関係チェック:")
    if not check_dependencies():
        sys.exit(1)
    
    print("\n✅ 全ての依存関係が揃っています")
    
    # Flaskアプリケーション起動
    start_flask_app()

if __name__ == "__main__":
    main()