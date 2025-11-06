import PyPDF2
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
import cv2
import numpy as np
from PIL import Image
import io
import re
from typing import List, Dict

def extract_text_hybrid(file_content: bytes) -> Dict[str, str]:
    """Hybrid extraction: Regular text + OCR for comprehensive content"""
    
    print("Starting hybrid text extraction...")
    
    # Method 1: Regular pdfplumber extraction
    print("Step 1: Regular text extraction...")
    regular_text = extract_regular_text(file_content)
    
    # Method 2: OCR extraction for images/scanned content
    print("Step 2: OCR extraction from images...")
    ocr_text = extract_text_with_ocr(file_content)
    
    # Method 3: Combine and deduplicate
    print("Step 3: Combining and cleaning text...")
    combined_text = combine_text_sources(regular_text, ocr_text)
    
    return {
        "regular_text": regular_text,
        "ocr_text": ocr_text,
        "combined_text": combined_text,
        "regular_chars": len(regular_text),
        "ocr_chars": len(ocr_text),
        "total_chars": len(combined_text)
    }

def extract_regular_text(file_content: bytes) -> str:
    """Extract regular text using pdfplumber"""
    try:
        pdf_file = io.BytesIO(file_content)
        text = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 20:
                    text += f"\n=== Page {i+1} ===\n" + page_text + "\n"
                    
        print(f"Regular extraction: {len(text)} characters from {len(pdf.pages)} pages")
        return clean_text(text)
        
    except Exception as e:
        print(f"Regular extraction failed: {e}")
        return ""

def extract_text_with_ocr(file_content: bytes, max_pages: int = 50) -> str:
    """Extract text from PDF using OCR on page images"""
    
    try:
        print("Converting PDF pages to images...")
        # Convert PDF to images (limit pages for performance)
        images = convert_from_bytes(file_content, dpi=200, first_page=1, last_page=max_pages)
        
        ocr_text = ""
        
        for i, image in enumerate(images):
            print(f"OCR processing page {i+1}/{len(images)}...")
            
            try:
                # Convert PIL to OpenCV
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Preprocess for better OCR
                processed = preprocess_for_ocr(opencv_image)
                
                # Extract text using Tesseract with configuration
                custom_config = r'--oem 3 --psm 6 -l eng'
                page_text = pytesseract.image_to_string(processed, config=custom_config)
                
                # Only add meaningful content
                if page_text.strip() and len(page_text.strip()) > 10:
                    ocr_text += f"\n=== Page {i+1} (OCR) ===\n" + page_text + "\n"
                    
            except Exception as page_error:
                print(f"OCR failed for page {i+1}: {page_error}")
                continue
        
        print(f"OCR extraction: {len(ocr_text)} characters")
        return clean_text(ocr_text)
        
    except Exception as e:
        print(f"OCR extraction failed: {e}")
        return ""

def preprocess_for_ocr(image):
    """Enhance image for better OCR accuracy"""
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Noise reduction
    denoised = cv2.medianBlur(gray, 3)
    
    # Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # Adaptive thresholding for text clarity
    thresh = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to clean up
    kernel = np.ones((1,1), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned

def combine_text_sources(regular_text: str, ocr_text: str) -> str:
    """Intelligently combine regular text and OCR text, removing duplicates"""
    
    if not regular_text and not ocr_text:
        return ""
    
    if not regular_text:
        return ocr_text
    
    if not ocr_text:
        return regular_text
    
    # Simple combination for now - can be enhanced with deduplication
    combined = regular_text + "\n\n" + "="*50 + "\n"
    combined += "ADDITIONAL OCR CONTENT (Images, Diagrams, Scanned Text)\n"
    combined += "="*50 + "\n\n" + ocr_text
    
    return combined

def clean_text(text: str) -> str:
    """Enhanced text cleaning"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Multiple newlines to double
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single
    
    # Remove common OCR artifacts
    text = re.sub(r'[^\w\s\-.,!?;:()\[\]{}"/\'+=*&%$#@<>|\\`~]', '', text)
    
    # Clean up page breaks
    text = re.sub(r'=== Page \d+ ===\s*=== Page \d+ \(OCR\) ===', '=== Page Combined ===', text)
    
    return text.strip()

def chunk_text_smart(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[Dict]:
    """Enhanced chunking with page number tracking"""
    
    # Split by page markers first
    page_sections = text.split('=== Page ')
    
    chunks = []
    chunk_number = 1
    
    for page_section in page_sections[1:]:  # Skip first empty split
        # Extract page number from section
        page_match = re.match(r'^(\d+)', page_section.strip())
        page_num = int(page_match.group(1)) if page_match else 1
        
        # Get content after page marker
        if '===' in page_section:
            page_content = page_section.split('===', 1)[1].strip()
        else:
            page_content = page_section.strip()
        
        # Create chunks for this page
        paragraphs = page_content.split('\n\n')
        current_chunk = ""
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            paragraph_length = len(paragraph.split())
            
            if current_length + paragraph_length > chunk_size and current_chunk:
                # Save chunk with page number
                chunks.append({
                    "chunk_number": chunk_number,
                    "content": current_chunk.strip(),
                    "word_count": current_length,
                    "char_count": len(current_chunk),
                    "content_type": "hybrid",
                    "page_number": page_num  # ADD THIS!
                })
                chunk_number += 1
                current_chunk = paragraph
                current_length = paragraph_length
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
                current_length += paragraph_length
        
        # Add final chunk for this page
        if current_chunk.strip():
            chunks.append({
                "chunk_number": chunk_number,
                "content": current_chunk.strip(),
                "word_count": current_length,
                "char_count": len(current_chunk),
                "content_type": "hybrid",
                "page_number": page_num  # ADD THIS!
            })
            chunk_number += 1
    
    return chunks

def get_overlap_text(text: str, overlap_words: int) -> str:
    """Get last N words for overlap"""
    words = text.split()
    if len(words) <= overlap_words:
        return text
    return " ".join(words[-overlap_words:])

def get_text_preview(chunks: List[Dict], max_length: int = 300) -> str:
    """Get a comprehensive preview from multiple chunks"""
    if not chunks:
        return "No content extracted"
    
    preview = f"📚 Extracted {len(chunks)} chunks from textbook\n\n"
    
    # Show preview from first chunk
    first_chunk = chunks[0]["content"]
    if len(first_chunk) <= max_length:
        preview += first_chunk
    else:
        preview += first_chunk[:max_length] + "..."
    
    return preview
