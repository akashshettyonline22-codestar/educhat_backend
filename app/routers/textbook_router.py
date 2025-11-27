from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from app.models.textbook_model import create_textbook_metadata, update_textbook_processing_status
from app.models.chunk_model import create_textbook_chunks
from app.utils.pdf_processor import extract_text_hybrid, chunk_text_smart, get_text_preview
from typing import Optional
import os
import uuid
from datetime import datetime
from app.utils.vector_processor import process_chunks_to_vectors
from app.utils.textbook_validator import validate_textbook




router = APIRouter(prefix="/textbooks", tags=["textbooks"])
security = HTTPBearer()

@router.post("/upload")
async def upload_textbook(
    request: Request,
    name: str = Form(...),
    subject: str = Form(...), 
    grade: str = Form(...),
    description: Optional[str] = Form(None),
    textbook: Optional[UploadFile] = File(None),
    token: str = Depends(security)
):
    # Get current user from middleware
    print("textbook")
    user_email = request.state.current_user_email

    
    # Basic validation
    if not name or not subject or not grade:
        raise HTTPException(status_code=400, detail="Name, subject, and grade are required")
    
    if not textbook:
        raise HTTPException(status_code=400, detail="Please upload a textbook file")
    
    # Check file type
    if not textbook.filename.lower().endswith(('.pdf')):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Create uploads directory
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_extension = os.path.splitext(textbook.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    try:
        # Read and save file
        content = await textbook.read()
        file_size = len(content)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"File saved: {file_path} ({file_size} bytes)")
        
        # Extract text from PDF
        print("Extracting text from PDF...")
        extraction_result = extract_text_hybrid(content)
        extracted_text = extraction_result["combined_text"]

        validation = validate_textbook(extracted_text, subject, grade)
    
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["message"],
                "validation": validation
            }
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract meaningful text from PDF")
        
        print(f"Extracted {len(extracted_text)} characters of text")
        
        # Split text into chunks (NO FULL TEXT STORAGE)
        print("Creating text chunks...")
        chunks = chunk_text_smart(extracted_text, chunk_size=800, overlap=100)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to create text chunks")
        
        print(f"Created {len(chunks)} chunks")
        
        # Prepare textbook metadata (NO extracted_text field)
        textbook_metadata = {
            "name": name,
            "subject": subject,
            "grade": grade,
            "description": description or "",
            "user_email": user_email,
            "file_path": file_path,
            "file_size": file_size,
            "original_filename": textbook.filename,
            "processing_status": "processing"
        }
        
        # Save textbook metadata first
        textbook_id = await create_textbook_metadata(textbook_metadata)
        print(f"Textbook metadata saved with ID: {textbook_id}")
        
        # Save chunks to database
        chunk_ids = await create_textbook_chunks(
            textbook_id=textbook_id,
            user_email=user_email, 
            chunks=chunks,
            textbook_metadata=textbook_metadata
        )
        print(f"Saved {len(chunk_ids)} chunks to database")
        
        # Update textbook with processing results
        total_words = sum(chunk["word_count"] for chunk in chunks)
        await update_textbook_processing_status(textbook_id, len(chunks), total_words)
        
        # Get preview from chunks
        text_preview = get_text_preview(chunks)

        # Save chunks to database
        chunk_ids = await create_textbook_chunks(
            textbook_id=textbook_id,
            user_email=user_email, 
            chunks=chunks,
            textbook_metadata=textbook_metadata
        )
        print(f"Saved {len(chunk_ids)} chunks to database")

        # NEW: Create vector embeddings and FAISS index
        print("Creating vector embeddings...")
        try:
            index_path, chunks_path = process_chunks_to_vectors(
                user_email=user_email,
                textbook_id=textbook_id, 
                chunks=chunks
            )
            print(f"Vectors created successfully: {index_path}")
            vector_created = True
        except Exception as e:
            print(f"Vector creation failed: {e}")
            vector_created = False

        
        result = {
            "message": "Textbook uploaded and processed successfully!",
            "textbook_id": textbook_id,
            "success": True,
            "data": {
                "name": name,
                "subject": subject,
                "grade": grade,
                "description": description,
                "user_email": user_email,
                "file_uploaded": textbook.filename,
                "file_size": file_size,
                "chunk_count": len(chunks),
                "total_words": total_words,
                "vectors_created": vector_created,  # NEW
                "text_preview": text_preview,
                "processing_status": "completed"
            }
        }

        
        return result
        
    except HTTPException:
        # Clean up file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        print("exception",e)
        # Clean up file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error processing textbook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process textbook: {str(e)}")
