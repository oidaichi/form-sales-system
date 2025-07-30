#!/usr/bin/env python3
"""
テスト用Excelファイル作成
"""

import pandas as pd

# テスト用データ
test_data = {
    '企業名': [
        '美容整体院もみツボ',
        'テスト企業2',
        'サンプル会社'
    ],
    'URL': [
        'https://fujino-gyosei.jp/contact/',
        'https://www.google.com',
        'https://souzoku-nagoya.net/otoiawase/'
    ],
    'メッセージ': [
        '弊社サービスについてご相談があります',
        'お問い合わせがあります',
        'ご提案したいサービスがあります'
    ]
}

# DataFrameを作成
df = pd.DataFrame(test_data)

# Excelファイルとして保存
excel_file = 'test_companies.xlsx'
df.to_excel(excel_file, index=False, sheet_name='Sheet1')

print(f"✅ テスト用Excelファイルを作成しました: {excel_file}")
print(f"📊 企業数: {len(df)}社")
print("\n📋 内容:")
for i, row in df.iterrows():
    print(f"  {i+1}. {row['企業名']} - {row['URL']}")