import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_level='INFO', log_file='app.log', max_bytes=10*1024*1024, backup_count=5):
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    log_filepath = os.path.join(log_directory, log_file)

    # ルートロガーの設定
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 既存のハンドラをクリア
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    # ファイルハンドラ
    file_handler = RotatingFileHandler(
        log_filepath, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # コンソールハンドラ
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger
