from datetime import date
from typing import Optional

from pydantic import BaseModel


class ReportCreate(BaseModel):
    title: str
    slug: str
    summary: str
    category: str
    publish_date: date
    pdf_url: Optional[str] = None
    status: str = "draft"
    content: str = ""
    analyst: str = "Ang Capital"
    reading_time: str = ""
    cover_image: Optional[str] = None
    is_featured: bool = False


class FrontendUserCreate(BaseModel):
    username: str
    email: str
    password_hash: str
    level: str = "User"
