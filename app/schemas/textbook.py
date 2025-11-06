from pydantic import BaseModel
from typing import Optional


class TextbookUpload(BaseModel):
    title: str
    subject: Optional[str] = None
    description: Optional[str] = None
    # No changes needed here ✅


class TextbookResponse(BaseModel):
    id: str
    title: str
    subject: Optional[str]
    description: Optional[str]
    file_path: str
    total_chunks: int
    upload_date: str
    message: str
    # ADD THESE OPTIONAL FIELDS:
    chunks_with_pages: Optional[int] = 0  # Count of chunks with page numbers
    original_filename: Optional[str] = None  # Original PDF filename
