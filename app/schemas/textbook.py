from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TextbookValidationResult(BaseModel):
    is_valid: bool
    confidence: float
    detected_subject: str
    detected_grade: str
    claimed_subject: str
    claimed_grade: str
    message: str
    warnings: List[str] = []
    suggestions: List[str] = []

class TextbookUploadRequest(BaseModel):
    textbook_name: str
    subject: str
    grade: str
    description: Optional[str] = ""
    validate_content: bool = True

class TextbookUploadResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    textbook_id: Optional[str] = None
    textbook_name: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    chunks_created: Optional[int] = None
    embeddings_stored: Optional[int] = None
    char_count: Optional[int] = None
    validated: Optional[bool] = None
    validation: Optional[dict] = None

class TextbookListResponse(BaseModel):
    success: bool
    textbooks: List[dict] = []
    total: int = 0

class TextbookDetailsResponse(BaseModel):
    success: bool
    textbook_id: str
    textbook_name: str
    subject: str
    grade: str
    description: Optional[str] = None
    upload_date: datetime
    chunk_count: int
    validated: bool
    validation_confidence: Optional[float] = None
