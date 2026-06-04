from sqlalchemy import create_engine as _create_engine
from dotenv import load_dotenv
import os

load_dotenv()

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_host = os.getenv('DB_HOST', '127.0.0.1')
        db_port = os.getenv('DB_PORT', '3306')
        db_user = os.getenv('DB_USER', 'neuralshelf')
        db_password = os.getenv('DB_PASSWORD', 'neuralshelf_pass')
        _engine = _create_engine(
            f"mysql+pymysql://{db_user}:{db_password}"
            f"@{db_host}:{db_port}/neuralshelf_db",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine
