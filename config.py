import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    STREAM_API_SECRET: str = os.getenv("STREAM_API_SECRET", "")
    SPLUNK_HEC_URL: str = os.getenv("SPLUNK_HEC_URL", "https://localhost:8088/services/collector/event")
    SPLUNK_HEC_TOKEN: str = os.getenv("SPLUNK_HEC_TOKEN", "")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    WEBHOOK_QUEUE_NAME: str = os.getenv("WEBHOOK_QUEUE_NAME", "stream_webhooks")
    DEDUPLICATION_WINDOW_SECONDS: int = int(os.getenv("DEDUPLICATION_WINDOW_SECONDS", 300))

    if not STREAM_API_SECRET:
        raise ValueError("STREAM_API_SECRET not set in .env")
    if not SPLUNK_HEC_URL:
        raise ValueError("SPLUNK_HEC_URL not set in .env")
    if not SPLUNK_HEC_TOKEN:
        raise ValueError("SPLUNK_HEC_TOKEN not set in .env")

config = Config()