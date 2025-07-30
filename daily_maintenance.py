import sqlite3
import os
from datetime import datetime, timedelta
from logger_config import setup_logging
from database import init_db # Import init_db
from flask import Flask # Import Flask to create a dummy app context

# ロギング設定
logger = setup_logging(log_level="INFO")

class DailyMaintenance:
    def __init__(self, db_path, log_retention_days):
        self.db_path = db_path
        self.log_retention_days = log_retention_days

    def delete_old_logs(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 古い履歴の自動削除
            threshold_date = datetime.now() - timedelta(days=self.log_retention_days)
            threshold_date_str = threshold_date.strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("DELETE FROM processing_logs WHERE timestamp < ?", (threshold_date_str,))
            conn.commit()
            logger.info(f"Deleted processing logs older than {self.log_retention_days} days.")
            
        except sqlite3.Error as e:
            logger.error(f"Database error during log deletion: {e}")
        finally:
            if conn:
                conn.close()

    def run_maintenance(self):
        logger.info("Starting daily maintenance tasks...")
        
        # Ensure database schema is initialized
        # Create a dummy Flask app context for init_db to work
        app = Flask(__name__)
        app.config['DATABASE_URL'] = self.db_path # Set the database URL for the dummy app
        with app.app_context():
            init_db()
            logger.info("Database schema initialized (if not already).")

        self.delete_old_logs()
        logger.info("Daily maintenance tasks completed.")

if __name__ == "__main__":
    DB_PATH = os.environ.get('DATABASE_URL', 'sqlite:///form_sales.db').replace('sqlite:///', '')
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 30))

    maintenance = DailyMaintenance(DB_PATH, LOG_RETENTION_DAYS)
    maintenance.run_maintenance()
