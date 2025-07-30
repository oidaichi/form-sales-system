CREATE TABLE processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    company_name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL,  -- success, failed, skipped
    message TEXT,
    processing_time INTEGER,  -- 処理時間（秒）
    form_fields_found INTEGER,  -- 検出フィールド数
    form_fields_filled INTEGER,  -- 入力成功フィールド数
    error_details TEXT,  -- エラー詳細
    page_title TEXT,  -- ページタイトル
    final_url TEXT   -- 最終到達URL
);
