from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse
from app.utils.vector_processor import search_similar_chunks
import fitz  # PyMuPDF
import base64
import os
import re
import requests
import time
from openai import OpenAI
from typing import Optional

router = APIRouter(prefix="/qa", tags=["Question & Answer"])
security = HTTPBearer()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/ask")
async def ask_question_multimodal(
    request: Request,
    textbook_id: str,
    question: str,
    token: str = Depends(security)
):
    """Q&A with PDF page image extraction and educational image generation"""
    user_email = request.state.current_user_email
    
    try:
        # Step 1: Search similar chunks
        results = search_similar_chunks(user_email, textbook_id, question, top_k=3)
        
        if not results:
            return {
                "success": False,
                "message": "No relevant content found", 
                "question": question
            }
        
        # Step 2: Extract context and find best page number
        context = ""
        page_numbers = set()
        
        for chunk_content, score in results:
            context += chunk_content + "\n\n"
            
            # Extract page number from chunk content
            page_match = re.search(r'=== Page (\d+)', chunk_content)
            if page_match:
                page_numbers.add(int(page_match.group(1)))
        
        # Get most relevant page (first found)
        best_page = min(page_numbers) if page_numbers else 1
        
        # Step 3: Get PDF path and extract page image
        pdf_path = await get_pdf_path_from_db(user_email, textbook_id)
        page_image_base64 = extract_page_as_base64(pdf_path, best_page)
        
        # Step 4: Generate multimodal answer
        if page_image_base64:
            answer = generate_multimodal_answer(question, context, page_image_base64)
            answer_type = "multimodal_with_page_image"
        else:
            answer = generate_text_only_answer(question, context)
            answer_type = "text_only_fallback"
        
        # Step 5: Generate educational image using LLM-generated prompt
        educational_image = await generate_educational_image_smart(
            question, answer, context, user_email, textbook_id
        )
        
        return {
            "success": True,
            "question": question,
            "answer": answer,
            "answer_type": answer_type,
            "educational_image": educational_image,
            "reference_page": best_page,
            "page_image_used": page_image_base64 is not None,
            "found_results": len(results),
            "all_reference_pages": sorted(list(page_numbers)),
            "textbook_id": textbook_id
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e), 
            "question": question,
            "textbook_id": textbook_id
        }

async def get_pdf_path_from_db(user_email: str, textbook_id: str) -> Optional[str]:
    """Get original PDF file path from database"""
    from app.database import database
    
    try:
        chunk = await database.textbook_chunks.find_one({
            "textbook_id": textbook_id,
            "user_email": user_email
        })
        
        if chunk and "file_path" in chunk:
            return chunk["file_path"]
            
        return None
        
    except Exception as e:
        print(f"Error getting PDF path: {e}")
        return None

def extract_page_as_base64(pdf_path: str, page_number: int) -> Optional[str]:
    """Extract specific PDF page as base64 encoded image"""
    try:
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"PDF file not found: {pdf_path}")
            return None
            
        pdf_document = fitz.open(pdf_path)
        
        if page_number <= len(pdf_document):
            page = pdf_document.load_page(page_number - 1)  # 0-indexed
            
            # High quality rendering for better LLM vision
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for clarity
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to base64
            img_data = pix.tobytes("png")
            pdf_document.close()
            
            return base64.b64encode(img_data).decode('utf-8')
        
        pdf_document.close()
        print(f"Page {page_number} not found in PDF")
        return None
        
    except Exception as e:
        print(f"Page extraction failed: {e}")
        return None

def generate_multimodal_answer(question: str, context: str, page_image_base64: str) -> str:
    """Generate answer using GPT-4 Vision with both text and page image"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Use gpt-4o for vision
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            You are a friendly teacher. Answer this question using both the textbook content and what you can see in the page image.
                            
                            Question: {question}
                            
                            Textbook Content: {context}
                            
                            Please look at the page image and reference specific visual elements (diagrams, numbers, pictures, examples) you can see. Explain in simple, child-friendly language.
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=350,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Multimodal answer generation failed: {e}")
        return f"I can see the page from your textbook, but I had trouble generating a response. The textbook says: {context[:200]}..."

def generate_text_only_answer(question: str, context: str) -> str:
    """Fallback text-only answer generation"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                You are a friendly teacher. Answer this question using the textbook content.
                
                Question: {question}
                Textbook Content: {context}
                
                Answer in simple, child-friendly language:
                """
            }],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Text answer generation failed: {e}")
        return f"Based on your textbook: {context[:300]}..."

async def generate_educational_image_smart(question: str, answer: str, context: str, user_email: str, textbook_id: str) -> Optional[str]:
    """Generate educational image using LLM-created prompts"""
    
    # Get textbook metadata
    textbook_info = await get_textbook_metadata(user_email, textbook_id)
    
    if not textbook_info:
        return None
    
    grade = textbook_info.get("grade", "1")
    
    # Check if visual aid would be helpful
    if is_visual_concept(question, answer, context):
        try:
            # Step 1: Use LLM to generate perfect image prompt
            image_prompt = generate_image_prompt_with_llm(question, answer, grade)
            
            print(f"Generated prompt: {image_prompt}")  # For debugging
            
            # Step 2: Generate image using the LLM-created prompt
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            saved_path = await save_educational_image(image_url, question)
            return saved_path
            
        except Exception as e:
            print(f"Educational image generation failed: {e}")
            return None
    
    return None

def generate_image_prompt_with_llm(question: str, answer: str, grade: str) -> str:
    """Use LLM to generate the perfect DALL-E prompt based on the answer"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                You are an expert at creating image prompts for educational illustrations.
                
                Create a detailed DALL-E prompt for an educational image that will help a Grade {grade} child understand this concept.
                
                Question: "{question}"
                Answer given: "{answer}"
                
                Based on the answer above, create a DALL-E prompt that will generate a perfect educational illustration. The image should:
                
                1. Visually demonstrate the key concepts mentioned in the answer
                2. Be appropriate for Grade {grade} children  
                3. Use bright, colorful, cartoon-style illustrations
                4. Include specific visual elements that match the answer's examples
                5. Be simple, clear, and educational
                6. Have no text - purely visual
                
                Focus on the specific examples in the answer to create the most relevant visual aid.
                
                Return ONLY the DALL-E prompt, nothing else.
                """
            }],
            temperature=0.7,
            max_tokens=200
        )
        
        generated_prompt = response.choices[0].message.content.strip()
        
        # Add consistent style requirements
        final_prompt = f"""
        {generated_prompt}
        
        Style: Bright, colorful, simple cartoon illustration for Grade {grade} children. 
        Clean background, large clear objects, no text overlays. Educational and age-appropriate.
        """
        
        return final_prompt.strip()
        
    except Exception as e:
        print(f"LLM prompt generation failed: {e}")
        return f"Create a simple, bright, colorful cartoon illustration for Grade {grade} children that explains: {question}. Use large, clear objects and bright colors. No text."

def is_visual_concept(question: str, answer: str, context: str) -> bool:
    """Check if concept would benefit from visual illustration"""
    
    combined_text = f"{question} {answer} {context}".lower()
    
    visual_indicators = [
        # Spatial concepts
        "bottom", "top", "up", "down", "left", "right", "inside", "outside",
        "over", "under", "above", "below", "beside", "between",
        
        # Size and comparison  
        "big", "small", "large", "tiny", "bigger", "smaller", "tall", "short",
        
        # Shapes and objects
        "circle", "square", "triangle", "rectangle", "round", "straight",
        "pot", "block", "stack", "pile", "flower", "plant",
        
        # Visual descriptions
        "see", "look", "show", "picture", "image", "diagram", "example",
        "imagine", "think of", "like this", "for instance"
    ]
    
    return any(indicator in combined_text for indicator in visual_indicators)

async def get_textbook_metadata(user_email: str, textbook_id: str) -> Optional[dict]:
    """Get textbook grade and subject info from database"""
    from app.database import database
    
    try:
        chunk = await database.textbook_chunks.find_one({
            "textbook_id": textbook_id,
            "user_email": user_email
        })
        
        if chunk:
            return {
                "grade": chunk.get("grade", "1"),
                "subject": chunk.get("subject", ""),
                "textbook_name": chunk.get("textbook_name", "")
            }
        return {"grade": "1", "subject": "general"}
        
    except Exception as e:
        print(f"Error getting textbook metadata: {e}")
        return {"grade": "1", "subject": "general"}

async def save_educational_image(image_url: str, question: str) -> Optional[str]:
    """Download and save the generated image locally"""
    try:
        os.makedirs("data/educational_images", exist_ok=True)
        
        # Download image
        response = requests.get(image_url)
        if response.status_code == 200:
            # Create safe filename
            timestamp = int(time.time())
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', question[:15])
            filename = f"{safe_name}_{timestamp}.png"
            
            file_path = f"data/educational_images/{filename}"
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return f"/qa/images/{filename}"
            
    except Exception as e:
        print(f"Error saving image: {e}")
        return None

@router.get("/images/{filename}")
async def serve_educational_image(filename: str):
    """Serve generated educational images"""
    file_path = f"data/educational_images/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Educational image not found")
