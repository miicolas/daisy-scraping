from typing import Union
from datetime import datetime
from sqlmodel import Field, SQLModel
from enum import Enum


# Enum pour le statut du crawl
class CrawlStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

# Modèle pour le log du crawl
class CrawlLog(SQLModel, table=True):
    id: Union[int, None] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    spider_name: str = Field(index=True)
    status: str = Field(index=True)
    error_message: Union[str, None] = None
    items_scraped: Union[int, None] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Union[datetime, None] = None

