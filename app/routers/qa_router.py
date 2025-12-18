from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse
from typing import Optional
from datetime import datetime

# Import our proper schemas and database functions
from app.schemas.chat_schemas import (
    MessageType, ChatBotResponse, ChatMessageSend, 
    ChatConversationResponse, ChatSessionListResponse
)
from app.models.chat_database import (
    create_chat_session_db, save_chat_message_db,
    get_recent_chat_messages_db, get_chat_messages_db, 
    get_user_chat_sessions_db, get_chat_session_db
)

# Import existing utilities
from app.utils.vector_processor import search_similar_chunks
import fitz  # PyMuPDF
import base64
import os
import re
import requests
import time
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/qa", tags=["Question & Answer Chatbot"])
security = HTTPBearer()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/ask", response_model=ChatBotResponse)
async def ask_question_chatbot(
    request: Request,
    textbook_id: str,
    question: str,
    session_id: Optional[str] = None,
    token: str = Depends(security)
):
    """Complete chatbot endpoint with enhanced conversational context handling"""
    user_email = request.state.current_user_email
    
    try:
        print(f"🤖 Chatbot Question: {question}")
        print(f"📋 Session ID: {session_id}")
        print(f"📚 Textbook ID: {textbook_id}")
        print(f"👤 User: {user_email}")
        
        # Step 1: Handle session management
        if not session_id:
            session_id = await create_chat_session_db(user_email, textbook_id)
            print(f"✅ Created new session: {session_id}")
        else:
            # Verify session exists and belongs to user
            existing_session = await get_chat_session_db(session_id, user_email)
            if not existing_session:
                return ChatBotResponse(
                    success=False,
                    session_id=session_id,
                    user_message_id="",
                    bot_message_id="",
                    question=question,
                    answer="Invalid or expired session ID. Please start a new conversation.",
                    answer_type="error",
                    context_used=False,
                    out_of_context=False,
                    error="Invalid session"
                )
        
        # Step 2: Save user message to conversation
        user_message_id = await save_chat_message_db(
            session_id=session_id,
            user_email=user_email,
            message_type=MessageType.USER,
            content=question
        )
        print(f"💾 Saved user message: {user_message_id}")
        
        # Step 3: Get conversation history for context
        conversation_history = await get_recent_chat_messages_db(session_id, user_email, limit=10)
        conversation_context = build_conversation_context(conversation_history)
        
        print(f"📖 Retrieved {len(conversation_history)} previous messages")
        print(f"🔗 Context length: {len(conversation_context)} characters")
        
        # Step 4: Enhanced search with conversation context
        search_results = await enhanced_context_search(
            user_email, textbook_id, question, conversation_history, top_k=3
        )
        
        if not search_results:
            # Check if it's a follow-up question that can be answered from conversation alone
            if is_followup_question(question, conversation_context) and conversation_context:
                print("🔗 No textbook results, but handling as conversation follow-up")
                
                # Get textbook metadata for grade-appropriate response
                textbook_info = await get_textbook_metadata(user_email, textbook_id)
                grade = textbook_info.get("grade", "1") if textbook_info else "1"
                
                bot_response = generate_followup_response(question, conversation_context, "", grade)
                
                bot_message_id = await save_chat_message_db(
                    session_id=session_id,
                    user_email=user_email,
                    message_type=MessageType.BOT,
                    content=bot_response,
                    metadata={"answer_type": "conversation_followup", "textbook_content_used": False}
                )
                
                return ChatBotResponse(
                    success=True,
                    session_id=session_id,
                    user_message_id=user_message_id,
                    bot_message_id=bot_message_id,
                    question=question,
                    answer=bot_response,
                    answer_type="conversation_followup",
                    context_used=True,
                    out_of_context=False,
                    educational_image=None,
                    reference_pages=[],
                    page_image_used=False,
                    conversation_length=len(conversation_history) + 2
                )
            
            # Regular no content found response
            bot_response = "I couldn't find any relevant information in your textbook to answer this question. Please ask questions related to the content in your uploaded textbook."
            
            bot_message_id = await save_chat_message_db(
                session_id=session_id,
                user_email=user_email,
                message_type=MessageType.BOT,
                content=bot_response,
                metadata={"out_of_context": True, "no_content_found": True}
            )
            
            return ChatBotResponse(
                success=True,
                session_id=session_id,
                user_message_id=user_message_id,
                bot_message_id=bot_message_id,
                question=question,
                answer=bot_response,
                answer_type="no_content_found",
                context_used=bool(conversation_context),
                out_of_context=True,
                educational_image=None,
                reference_pages=[],
                page_image_used=False,
                conversation_length=len(conversation_history) + 2
            )
        
        # Step 5: Build textbook context and extract page info
        textbook_context = ""
        page_numbers = set()
        similarity_scores = []
        
        for chunk_content, score in search_results:
            textbook_context += chunk_content + "\n\n"
            similarity_scores.append(score)
            
            # Extract page numbers
            page_match = re.search(r'=== Page (\d+)', chunk_content)
            if page_match:
                page_numbers.add(int(page_match.group(1)))
        
        print(f"📄 Found content from pages: {sorted(list(page_numbers))}")
        print(f"🎯 Similarity scores: {[round(s, 3) for s in similarity_scores]}")
        
        # Step 6: Enhanced relevance check considering conversation context
        is_relevant, relevance_reason = enhanced_relevance_check(
            question, textbook_context, similarity_scores, conversation_context
        )
        
        if not is_relevant:
            bot_response = f"This question seems to be outside the scope of your textbook. {relevance_reason} Please ask questions related to the topics covered in your textbook."
            
            bot_message_id = await save_chat_message_db(
                session_id=session_id,
                user_email=user_email,
                message_type=MessageType.BOT,
                content=bot_response,
                metadata={
                    "out_of_context": True, 
                    "relevance_reason": relevance_reason,
                    "similarity_scores": similarity_scores
                }
            )
            
            return ChatBotResponse(
                success=True,
                session_id=session_id,
                user_message_id=user_message_id,
                bot_message_id=bot_message_id,
                question=question,
                answer=bot_response,
                answer_type="out_of_context",
                context_used=bool(conversation_context),
                out_of_context=True,
                educational_image=None,
                reference_pages=[],
                page_image_used=False,
                conversation_length=len(conversation_history) + 2
            )
        
        print("✅ Question is relevant to textbook content")
        
        # Step 7: Get textbook metadata for grade-appropriate responses
        textbook_info = await get_textbook_metadata(user_email, textbook_id)
        grade = textbook_info.get("grade", "1") if textbook_info else "1"
        
        # Step 8: Extract page image if available
        best_page = min(page_numbers) if page_numbers else 1
        pdf_path = await get_pdf_path_from_db(user_email, textbook_id)
        page_image_base64 = None
        
        if pdf_path:
            page_image_base64 = extract_page_as_base64(pdf_path, best_page)
            print(f"📸 Extracted page {best_page} image: {bool(page_image_base64)}")
        
        # Step 9: Generate context-aware response
        if is_followup_question(question, conversation_context):
            print("🔗 Generating follow-up response with enhanced context")
            bot_response = generate_followup_response(question, conversation_context, textbook_context, grade)
            answer_type = "contextual_followup"
        elif page_image_base64:
            bot_response = generate_multimodal_response_with_context(
                question, textbook_context, page_image_base64, conversation_context, grade
            )
            answer_type = "multimodal_with_context"
            print("🖼️ Generated multimodal response with page image")
        else:
            bot_response = generate_text_response_with_context(
                question, textbook_context, conversation_context, grade
            )
            answer_type = "text_with_context"
            print("📝 Generated text-only response")
        
        # Step 10: Generate educational image if helpful
        educational_image = None
        if should_generate_educational_image(question, bot_response, conversation_context):
            print("🎨 Generating educational image...")
            try:
                image_prompt = generate_image_prompt_with_llm(question, bot_response, grade)
                if image_prompt:
                    educational_image = await generate_image_huggingface(image_prompt)
                    if educational_image:
                        print(f"✅ Generated educational image: {educational_image}")
                    else:
                        print("❌ Educational image generation failed")
            except Exception as e:
                print(f"❌ Image generation error: {e}")
        
        # Step 11: Save bot response with comprehensive metadata
        bot_message_metadata = {
            "answer_type": answer_type,
            "educational_image": educational_image,
            "reference_pages": sorted(list(page_numbers)),
            "context_used": bool(conversation_context),
            "page_image_used": bool(page_image_base64),
            "similarity_scores": similarity_scores,
            "textbook_grade": grade,
            "is_followup": is_followup_question(question, conversation_context),
            "response_tokens": len(bot_response.split())
        }
        
        bot_message_id = await save_chat_message_db(
            session_id=session_id,
            user_email=user_email,
            message_type=MessageType.BOT,
            content=bot_response,
            metadata=bot_message_metadata
        )
        
        print(f"💾 Saved bot response: {bot_message_id}")
        print("🎉 Chatbot response completed successfully")
        
        return ChatBotResponse(
            success=True,
            session_id=session_id,
            user_message_id=user_message_id,
            bot_message_id=bot_message_id,
            question=question,
            answer=bot_response,
            answer_type=answer_type,
            context_used=bool(conversation_context),
            out_of_context=False,
            educational_image=educational_image,
            reference_pages=sorted(list(page_numbers)),
            page_image_used=bool(page_image_base64),
            conversation_length=len(conversation_history) + 2
        )
        
    except Exception as e:
        print(f"❌ Chatbot error: {e}")
        
        # Try to save error message if we have session info
        error_message = "I'm sorry, I encountered an error while processing your question. Please try again."
        
        if session_id and 'user_message_id' in locals():
            try:
                await save_chat_message_db(
                    session_id=session_id,
                    user_email=user_email,
                    message_type=MessageType.BOT,
                    content=error_message,
                    metadata={"error": str(e), "error_type": "processing_error"}
                )
            except:
                pass  # Don't fail twice
        
        return ChatBotResponse(
            success=False,
            session_id=session_id or "",
            user_message_id=locals().get('user_message_id', ""),
            bot_message_id="",
            question=question,
            answer=error_message,
            answer_type="error",
            context_used=False,
            out_of_context=False,
            educational_image=None,
            reference_pages=[],
            page_image_used=False,
            conversation_length=0,
            error=str(e)
        )

@router.get("/conversations/{session_id}", response_model=ChatConversationResponse)
async def get_conversation_history(
    session_id: str,
    request: Request,
    limit: int = 50,
    token: str = Depends(security)
):
    """Get complete conversation history for a session"""
    user_email = request.state.current_user_email
    
    try:
        # Get session info
        session_info = await get_chat_session_db(session_id, user_email)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = await get_chat_messages_db(session_id, user_email, limit=limit)
        
        # Format messages for response
        formatted_messages = []
        for msg in messages:
            formatted_msg = {
                "message_id": msg["_id"],
                "session_id": msg["session_id"],
                "message_type": msg["message_type"],
                "content": msg["content"],
                "timestamp": msg["timestamp"],
                "metadata": msg.get("metadata", {})
            }
            formatted_messages.append(formatted_msg)
        
        return ChatConversationResponse(
            success=True,
            session_id=session_id,
            messages=formatted_messages,
            total_messages=len(formatted_messages),
            session_info={
                "created_at": session_info["created_at"].isoformat(),
                "last_active": session_info["last_active"].isoformat(),
                "message_count": session_info.get("message_count", 0),
                "textbook_id": session_info["textbook_id"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return ChatConversationResponse(
            success=False,
            session_id=session_id,
            messages=[],
            total_messages=0,
            session_info=None
        )

@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_user_chat_sessions(
    request: Request,
    limit: int = 20,
    token: str = Depends(security)
):
    """List user's chat sessions"""
    user_email = request.state.current_user_email
    
    try:
        sessions = await get_user_chat_sessions_db(user_email, limit=limit)
        
        formatted_sessions = []
        for session in sessions:
            formatted_session = {
                "session_id": session["_id"],
                "textbook_id": session["textbook_id"],
                "created_at": session["created_at"],
                "last_active": session["last_active"],
                "message_count": session.get("message_count", 0),
                "status": session.get("status", "active"),
                "preview_message": session.get("preview_message", "New conversation")
            }
            formatted_sessions.append(formatted_session)
        
        return ChatSessionListResponse(
            success=True,
            sessions=formatted_sessions,
            total=len(formatted_sessions)
        )
        
    except Exception as e:
        return ChatSessionListResponse(
            success=False,
            sessions=[],
            total=0
        )

# ENHANCED CONVERSATION CONTEXT PROCESSING

def build_conversation_context(conversation_history: list) -> str:
    """Build conversation context from message history"""
    
    if not conversation_history or len(conversation_history) < 2:
        return ""
    
    # Get last 8 messages (4 exchanges max) for better context
    recent_messages = conversation_history[-8:]
    
    context_parts = []
    for message in recent_messages:
        role = "Student" if message["message_type"] == "user" else "Teacher"
        content = message["content"][:200]  # Limit content length but allow more
        context_parts.append(f"{role}: {content}")
    
    return "\n".join(context_parts)

def extract_context_keywords(conversation_history: list, current_question: str) -> str:
    """Extract keywords from recent conversation to enhance search"""
    
    if not conversation_history:
        return current_question
    
    # Get last few user questions and bot responses to extract topic keywords
    recent_topics = []
    
    for message in conversation_history[-6:]:  # Last 6 messages
        content = message["content"].lower()
        
        # Extract important nouns and concepts
        words = re.findall(r'\b[a-z]{4,}\b', content)  # Words 4+ chars
        
        # Filter out common words
        common_words = {
            "what", "when", "where", "which", "have", "will", "that", "this", 
            "they", "with", "from", "about", "could", "would", "should", "like",
            "just", "more", "some", "very", "good", "well", "much", "many"
        }
        
        topic_words = [word for word in words if word not in common_words]
        recent_topics.extend(topic_words[:3])  # Take top 3 from each message
    
    # Combine current question with recent topic keywords
    if recent_topics:
        unique_topics = list(set(recent_topics))[:5]  # Top 5 unique keywords
        enhanced_query = f"{current_question} {' '.join(unique_topics)}"
        print(f"🔍 Enhanced search query: {current_question} + keywords: {unique_topics}")
        return enhanced_query
    
    return current_question

def is_followup_question(question: str, conversation_context: str) -> bool:
    """Determine if this is a follow-up question that needs previous context"""
    
    question_lower = question.lower().strip()
    
    # Clear follow-up indicators
    followup_phrases = [
        "explain it", "explain that", "tell me more", "more about", "elaborate",
        "what about", "how about", "clarify", "expand on", "go deeper", 
        "can you explain", "please explain", "more clearly", "better explanation", 
        "simpler way", "in detail", "further", "additionally", "also"
    ]
    
    # Pronouns that usually refer to previous context
    context_pronouns = ["it", "that", "this", "them", "they", "those", "these"]
    
    # Very short questions that likely need context
    is_very_short = len(question.split()) <= 3
    
    # Questions that start with certain words and are short
    context_starters = ["why", "how", "when", "where", "what if", "can you", "could you"]
    
    # Specific follow-up question patterns
    followup_patterns = [
        r'\bexplain\b.*\b(it|that|this)\b',
        r'\btell me more\b',
        r'\bwhat about\b',
        r'\bhow about\b',
        r'\bmore\s+(about|on|detail)',
        r'\bclarify\b',
        r'\belaborate\b'
    ]
    
    has_followup_phrase = any(phrase in question_lower for phrase in followup_phrases)
    has_context_pronoun = any(f" {pronoun} " in f" {question_lower} " for pronoun in context_pronouns)
    starts_with_context = any(question_lower.startswith(starter) for starter in context_starters)
    matches_pattern = any(re.search(pattern, question_lower) for pattern in followup_patterns)
    
    is_followup = (has_followup_phrase or 
                   matches_pattern or
                   (has_context_pronoun and conversation_context) or 
                   (is_very_short and conversation_context and starts_with_context))
    
    if is_followup:
        print(f"🔗 Detected follow-up question: '{question}'")
        print(f"   - Has followup phrase: {has_followup_phrase}")
        print(f"   - Matches pattern: {matches_pattern}")
        print(f"   - Has context pronoun: {has_context_pronoun}")
        print(f"   - Is very short with context: {is_very_short and bool(conversation_context)}")
    
    return is_followup

async def enhanced_context_search(user_email: str, textbook_id: str, question: str, conversation_history: list, top_k: int = 3):
    """Enhanced search that considers conversation context for follow-up questions"""
    
    # First try regular search
    regular_results = search_similar_chunks(user_email, textbook_id, question, top_k=top_k)
    
    print(f"🔍 Regular search results: {len(regular_results)} chunks found")
    if regular_results:
        print(f"🎯 Regular search scores: {[round(score, 3) for _, score in regular_results]}")
    
    # If it's a follow-up question and regular search yields poor results, enhance with context
    conversation_context = build_conversation_context(conversation_history)
    
    if is_followup_question(question, conversation_context):
        
        if not regular_results or (regular_results and max([score for _, score in regular_results]) < 0.4):
            print("🔍 Regular search insufficient for follow-up question, enhancing with context...")
            
            # Extract keywords from conversation history
            enhanced_query = extract_context_keywords(conversation_history, question)
            
            # Search again with enhanced query
            context_results = search_similar_chunks(user_email, textbook_id, enhanced_query, top_k=top_k)
            
            if context_results:
                print(f"✅ Context-enhanced search found {len(context_results)} results")
                print(f"🎯 Enhanced search scores: {[round(score, 3) for _, score in context_results]}")
                
                # Use enhanced results if they're significantly better
                if max([score for _, score in context_results]) > max([score for _, score in regular_results]) * 1.2:
                    return context_results
    
    return regular_results

def enhanced_relevance_check(question: str, textbook_context: str, similarity_scores: list, conversation_context: str) -> tuple[bool, str]:
    """Enhanced relevance check that considers conversation context"""
    
    # If this is clearly a follow-up question, be more lenient with relevance
    if is_followup_question(question, conversation_context):
        print("🔗 Follow-up question detected - using lenient relevance check")
        
        # For follow-up questions, lower the similarity threshold significantly
        if similarity_scores and max(similarity_scores) > 0.2:  # Much lower threshold
            return True, "Follow-up question with adequate context match."
        
        # If we have conversation context, try to determine if it relates to the current textbook content
        if conversation_context:
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "user", 
                        "content": f"""
                        This is a follow-up question in an educational conversation.
                        
                        Current Question: "{question}"
                        Previous Conversation: "{conversation_context[-400:]}"
                        Available Textbook Content: "{textbook_context[:500]}..."
                        
                        The student is asking a follow-up question that likely refers to our previous discussion about educational topics.
                        
                        Can this follow-up question be reasonably answered using:
                        1. The previous conversation context (what we were just discussing), AND/OR
                        2. The available textbook content
                        
                        Even if the textbook content isn't a perfect match, if the conversation context provides enough information to give a helpful educational answer, consider it RELEVANT.
                        
                        For educational follow-up questions like "explain it clearly", "tell me more", "how about that" - these should almost always be RELEVANT if we were just discussing an educational topic.
                        
                        Respond: "RELEVANT" or "NOT_RELEVANT: [reason]"
                        """
                    }],
                    temperature=0.2,
                    max_tokens=50
                )
                
                llm_response = response.choices[0].message.content.strip()
                
                if "NOT_RELEVANT" in llm_response.upper():
                    reason = llm_response.split("NOT_RELEVANT:", 1)[1].strip() if ":" in llm_response else "Follow-up question cannot be answered with available context."
                    return False, reason
                else:
                    return True, "Follow-up question can be answered using conversation and textbook context."
                    
            except Exception as e:
                print(f"Enhanced relevance check failed: {e}")
                # For follow-up questions, strongly default to relevant to avoid breaking conversation flow
                return True, "Could not verify relevance, but treating as valid educational follow-up."
    
    # Use regular relevance check for non-follow-up questions
    return check_question_relevance(question, textbook_context, similarity_scores)

def generate_followup_response(question: str, conversation_context: str, textbook_context: str, grade: str) -> str:
    """Generate response specifically for follow-up questions"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                You are a friendly teacher continuing an educational conversation with a Grade {grade} student.
                
                Previous Conversation:
                {conversation_context}
                
                Student's Follow-up Question: "{question}"
                
                Additional Textbook Content: {textbook_context}
                
                Instructions:
                - This is clearly a follow-up to our previous educational discussion
                - Refer back to what we were just talking about
                - Use the conversation context as your primary source
                - Supplement with textbook content if relevant and helpful
                - Provide the clarification, explanation, or additional detail the student is asking for
                - Use simple, engaging language appropriate for Grade {grade}
                - Be encouraging and build on the learning momentum
                - If they asked to "explain clearly" or "tell me more", provide a more detailed, step-by-step explanation
                
                Answer the student's follow-up question by building naturally on our previous conversation.
                """
            }],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Follow-up response generation failed: {e}")
        return f"Let me explain more about what we were just discussing. {conversation_context[-200:]}..."

def needs_conversation_context(question: str, conversation_context: str) -> bool:
    """Determine if question likely refers to previous conversation"""
    
    if not conversation_context:
        return False
    
    question_lower = question.lower()
    
    context_indicators = [
        "what did", "we just", "that", "this", "remember", "before", 
        "earlier", "previous", "last time", "again", "also", "more about",
        "tell me more", "explain that", "what was", "it", "they", "them",
        "can you", "could you", "please", "how about", "what about"
    ]
    
    return any(indicator in question_lower for indicator in context_indicators)

# RESPONSE GENERATION WITH ENHANCED CONTEXT

def generate_multimodal_response_with_context(question: str, textbook_context: str, page_image_base64: str, conversation_context: str, grade: str) -> str:
    """Generate response using both textbook page image and conversation context"""
    
    try:
        context_instruction = ""
        if conversation_context and needs_conversation_context(question, conversation_context):
            context_instruction = f"""
            
            Previous Conversation Context:
            {conversation_context}
            
            Note: The student may be referring to our previous discussion. Consider the conversation history when answering.
            """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            You are a friendly, patient educational assistant having a conversation with a Grade {grade} student.
                            {context_instruction}
                            
                            Student's Question: {question}
                            Textbook Content: {textbook_context}
                            
                            Instructions:
                            - Look at the textbook page image and describe relevant visual elements
                            - If this relates to our previous conversation, acknowledge it naturally
                            - Use simple, engaging language appropriate for Grade {grade} (ages {int(grade)+5}-{int(grade)+6})
                            - Be conversational and encouraging like a real teacher
                            - Keep responses helpful but concise (2-3 paragraphs max)
                            - Reference specific visual elements from the page when relevant
                            - Reply with just answer
                            
                            Answer the student's question in a warm, supportive way.
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
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Multimodal response generation failed: {e}")
        return f"I can see your textbook page! Based on what I can see and the content: {textbook_context[:200]}..."

def generate_text_response_with_context(question: str, textbook_context: str, conversation_context: str, grade: str) -> str:
    """Generate text-only response with conversation context"""
    
    try:
        context_instruction = ""
        if conversation_context and needs_conversation_context(question, conversation_context):
            context_instruction = f"""
            
            Previous Conversation Context:
            {conversation_context}
            
            Build upon our previous discussion naturally if the question relates to it.
            """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                You are a friendly, patient educational assistant having a conversation with a Grade {grade} student.
                {context_instruction}
                
                Student's Question: {question}
                Textbook Content: {textbook_context}
                
                Instructions:
                - If this relates to our previous conversation, reference it naturally
                - Use simple, engaging language appropriate for Grade {grade} (ages {int(grade)+5}-{int(grade)+6})
                - Be conversational and encouraging like a real teacher
                - Keep responses helpful but concise (2-3 paragraphs max)
                - Provide clear explanations with examples when possible
                
                Answer the student's question in a warm, supportive way.
                """
            }],
            temperature=0.7,
            max_tokens=250
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Text response generation failed: {e}")
        return f"Based on your textbook: {textbook_context[:200]}..."

# RELEVANCE AND IMAGE GENERATION

def check_question_relevance(question: str, textbook_context: str, similarity_scores: list) -> tuple[bool, str]:
    """Check if question is relevant to textbook content"""
    
    # Check similarity scores first
    if similarity_scores and max(similarity_scores) < 0.25:
        return False, "The question doesn't seem to match any content in your textbook."
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                Determine if this question can be reasonably answered using the textbook content provided.
                
                Question: "{question}"
                Textbook Content Sample: "{textbook_context[:600]}..."
                
                Consider the question RELEVANT if it:
                - Asks about topics mentioned or closely related to the textbook content
                - Can be answered using the educational material provided
                - Is within the scope of the subject matter
                
                Consider it NOT_RELEVANT if it:
                - Asks about completely different subjects
                - Is about current events, personal matters, or non-educational topics
                - Cannot be answered using the textbook content
                
                Respond with: "RELEVANT" or "NOT_RELEVANT: [brief reason]"
                """
            }],
            temperature=0.2,
            max_tokens=50
        )
        
        llm_response = response.choices[0].message.content.strip()
        
        if "NOT_RELEVANT" in llm_response.upper():
            reason = llm_response.split("NOT_RELEVANT:", 1)[1].strip() if ":" in llm_response else "Question not related to textbook content."
            return False, reason
        else:
            return True, "Question is relevant to textbook content."
            
    except Exception as e:
        print(f"Relevance check failed: {e}")
        # Default to relevant to avoid false negatives
        return True, "Could not verify relevance, proceeding with answer."

def should_generate_educational_image(question: str, answer: str, conversation_context: str) -> bool:
    """Determine if educational image would be helpful"""
    
    combined_text = f"{question} {answer} {conversation_context}".lower()
    
    visual_indicators = [
        # Spatial concepts
        "bottom", "top", "up", "down", "left", "right", "inside", "outside",
        "over", "under", "above", "below", "beside", "between", "middle",
        
        # Size and comparison
        "big", "small", "large", "tiny", "bigger", "smaller", "tall", "short",
        
        # Shapes and math
        "circle", "square", "triangle", "rectangle", "add", "subtract", 
        "count", "number", "plus", "minus", "equal", "total", "rolling",
        
        # Visual learning words
        "see", "look", "show", "picture", "image", "draw", "color", 
        "imagine", "example", "demonstrate", "illustrate"
    ]
    
    has_visual_concept = any(indicator in combined_text for indicator in visual_indicators)
    
    # Also check if question is asking for visual explanation
    visual_requests = ["show me", "can you draw", "what does", "how does", "picture"]
    has_visual_request = any(req in combined_text for req in visual_requests)
    
    return has_visual_concept or has_visual_request

# IMAGE GENERATION FUNCTIONS

def generate_image_prompt_with_llm(question: str, answer: str, grade: str) -> Optional[str]:
    """Generate educational image prompt using LLM"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user", 
                "content": f"""
                Create an image generation prompt for an educational illustration for Grade {grade} children.
                
                Student's Question: "{question}"
                Teacher's Answer: "{answer}"
                
                Create a detailed DALL-E prompt for a simple, colorful, cartoon-style educational image that:
                1. Visually demonstrates the key concepts from the answer
                2. Is appropriate for Grade {grade} children (ages {int(grade)+5}-{int(grade)+6})
                3. Uses bright, cheerful colors and simple shapes
                4. Includes specific visual elements mentioned in the answer
                5. Is educational but fun and engaging
                6. Has no text overlays - purely visual learning aid
                
                Focus on making abstract concepts concrete and visual for young learners.
                
                Return ONLY the image generation prompt, nothing else.
                """
            }],
            temperature=0.7,
            max_tokens=120
        )
        
        generated_prompt = response.choices[0].message.content.strip()
        
        # Enhance prompt with consistent style requirements
        enhanced_prompt = f"{generated_prompt}, cartoon illustration style, bright primary colors, simple and clear, child-friendly, educational diagram, no text or words"
        
        return enhanced_prompt
        
    except Exception as e:
        print(f"Image prompt generation failed: {e}")
        return f"Simple colorful cartoon illustration for Grade {grade} children about {question}, bright colors, educational, fun, no text, cartoon style"

async def generate_image_huggingface(prompt: str) -> Optional[str]:
    """Generate educational image using Hugging Face API"""
    
    try:
        hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        
        if not hf_token:
            print("HUGGINGFACE_API_TOKEN not found")
            return None
        
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        
        # Try FLUX model first
        API_URL_NEW = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 4,
                "guidance_scale": 1.0,
                "width": 1024,
                "height": 1024
            }
        }
        
        response = requests.post(API_URL_NEW, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            # Save image
            timestamp = int(time.time())
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', prompt[:20])
            filename = f"edu_{safe_name}_{timestamp}.png"
            file_path = f"data/educational_images/{filename}"
            
            os.makedirs("data/educational_images", exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return f"/qa/images/{filename}"
            
        else:
            # Fallback to Stable Diffusion
            API_URL_OLD = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
            
            payload_old = {
                "inputs": prompt,
                "parameters": {
                    "num_inference_steps": 20,
                    "guidance_scale": 7.0
                }
            }
            
            response_old = requests.post(API_URL_OLD, headers=headers, json=payload_old, timeout=30)
            
            if response_old.status_code == 200:
                timestamp = int(time.time())
                safe_name = re.sub(r'[^a-zA-Z0-9]', '_', prompt[:20])
                filename = f"edu_sd_{safe_name}_{timestamp}.png"
                file_path = f"data/educational_images/{filename}"
                
                os.makedirs("data/educational_images", exist_ok=True)
                
                with open(file_path, 'wb') as f:
                    f.write(response_old.content)
                
                return f"/qa/images/{filename}"
        
        return None
        
    except Exception as e:
        print(f"HF image generation error: {e}")
        return None

# UTILITY FUNCTIONS

async def get_pdf_path_from_db(user_email: str, textbook_id: str) -> Optional[str]:
    """Get original PDF file path from database"""
    from app.database import database
    
    try:
        chunk = await database.textbook_chunks.find_one({
            "textbook_id": textbook_id,
            "user_email": user_email
        })
        
        return chunk.get("file_path") if chunk else None
        
    except Exception as e:
        print(f"Error getting PDF path: {e}")
        return None

def extract_page_as_base64(pdf_path: str, page_number: int) -> Optional[str]:
    """Extract PDF page as base64 encoded image"""
    
    try:
        if not pdf_path or not os.path.exists(pdf_path):
            return None
            
        pdf_document = fitz.open(pdf_path)
        
        if page_number <= len(pdf_document):
            page = pdf_document.load_page(page_number - 1)  # 0-indexed
            
            # High quality rendering
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale for clarity
            pix = page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            pdf_document.close()
            
            return base64.b64encode(img_data).decode('utf-8')
        
        pdf_document.close()
        return None
        
    except Exception as e:
        print(f"Page extraction failed: {e}")
        return None

async def get_textbook_metadata(user_email: str, textbook_id: str) -> Optional[dict]:
    """Get textbook metadata from database"""
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

# IMAGE SERVING ENDPOINT

@router.get("/images/{filename}")
async def serve_educational_image(filename: str):
    """Serve generated educational images"""
    file_path = f"data/educational_images/{filename}"
    
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Educational image not found")

# HEALTH CHECK

@router.get("/health")
async def chatbot_health_check():
    """Health check for chatbot system"""
    return {
        "status": "healthy",
        "service": "Educational Chatbot with Enhanced Context",
        "features": [
            "Conversational Q&A with memory",
            "Enhanced follow-up question handling",
            "Context-aware textbook search",
            "Multimodal responses with page images", 
            "FREE educational image generation",
            "Intelligent out-of-context detection",
            "Grade-appropriate responses"
        ],
        "integrations": {
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
            "huggingface_configured": bool(os.getenv("HUGGINGFACE_API_TOKEN")),
            "database_connected": True
        }
    }
