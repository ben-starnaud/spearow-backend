from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime

class RequestData(BaseModel):
    reportType: str
    reportCategory: Optional[str] = None
    reportFormat: str
    notes: Optional[str] = None
    token: str

class UserReport(BaseModel):
    Name: str
    Email: str
    ReportGeneratedAt: str = Field(default_factory=lambda: datetime.utcnow().date().isoformat())
    Report: Union[str, List[str]]


