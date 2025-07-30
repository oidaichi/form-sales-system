import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 30))
    PROCESSING_INTERVAL = int(os.environ.get('PROCESSING_INTERVAL', 2))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///form_sales_simple.db')
    DATABASE_TIMEOUT = 30
    BROWSER_HEADLESS = os.environ.get('BROWSER_HEADLESS', 'false').lower() == 'true'
    BROWSER_TIMEOUT = int(os.environ.get('BROWSER_TIMEOUT', 30))
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 30))
