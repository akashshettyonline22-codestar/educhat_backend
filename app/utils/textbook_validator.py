from openai import OpenAI
import os
from dotenv import load_dotenv
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def validate_textbook(extracted_text: str, claimed_subject: str, claimed_grade: str) -> dict:
    """
    Validate if uploaded textbook matches claimed subject and grade
    
    Args:
        extracted_text: Full text extracted from PDF
        claimed_subject: What user says the subject is (e.g., "Mathematics")
        claimed_grade: What user says the grade is (e.g., "5")
    
    Returns:
        {
            "valid": bool,
            "confidence": float,
            "detected_subject": str,
            "detected_grade": str,
            "message": str
        }
    """
    
    # Get text sample (first 2000 chars + middle 1000 chars)
    text_length = len(extracted_text)
    if text_length > 3000:
        sample = extracted_text[:2000] + "\n...\n" + extracted_text[text_length//2:text_length//2+1000]
    else:
        sample = extracted_text
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"""
                Analyze this textbook content and determine the actual subject and grade level.
                
                Content Sample:
                {sample[:2500]}
                
                User Claims:
                Subject: {claimed_subject}
                Grade: {claimed_grade}
                
                Respond in this exact format:
                SUBJECT: [detected subject - Mathematics/Science/English/Social Studies/etc]
                GRADE: [number 1-12 or K]
                MATCH: [YES if both match, CLOSE if grade within 1-2 levels, NO if mismatch]
                CONFIDENCE: [0.0-1.0]
                REASON: [brief explanation]
                """
            }],
            temperature=0.2,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse response
        subject_match = re.search(r'SUBJECT:\s*(.+)', result_text, re.IGNORECASE)
        grade_match = re.search(r'GRADE:\s*(.+)', result_text, re.IGNORECASE)
        match_status = re.search(r'MATCH:\s*(\w+)', result_text, re.IGNORECASE)
        confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', result_text, re.IGNORECASE)
        reason_match = re.search(r'REASON:\s*(.+)', result_text, re.IGNORECASE)
        
        detected_subject = subject_match.group(1).strip() if subject_match else claimed_subject
        detected_grade = grade_match.group(1).strip() if grade_match else claimed_grade
        match = match_status.group(1).upper() if match_status else "UNKNOWN"
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        reason = reason_match.group(1).strip() if reason_match else "Validation completed"
        
        # Determine if valid
        is_valid = match in ["YES", "CLOSE"] and confidence >= 0.6
        
        if is_valid:
            message = f"✅ Validated: {detected_subject} Grade {detected_grade}"
        else:
            message = f"❌ Mismatch: Expected {claimed_subject} Grade {claimed_grade}, but detected {detected_subject} Grade {detected_grade}"
        
        return {
            "valid": is_valid,
            "confidence": confidence,
            "detected_subject": detected_subject,
            "detected_grade": detected_grade,
            "claimed_subject": claimed_subject,
            "claimed_grade": claimed_grade,
            "message": message,
            "reason": reason
        }
        
    except Exception as e:
        print(f"Validation error: {e}")
        return {
            "valid": True,  # Default to valid on error to not block upload
            "confidence": 0.5,
            "detected_subject": claimed_subject,
            "detected_grade": claimed_grade,
            "claimed_subject": claimed_subject,
            "claimed_grade": claimed_grade,
            "message": "⚠️ Could not validate, proceeding with upload",
            "reason": f"Validation error: {str(e)}"
        }
