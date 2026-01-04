📚 EduChat - AI-Powered Educational Chatbot
An intelligent educational assistant that transforms textbooks into interactive learning experiences using multimodal AI, vector embeddings, and conversational memory.

[
[
[
[

🎯 Overview
EduChat is a cutting-edge educational platform that allows students to upload their textbooks and interact with an AI tutor that:

🧠 Remembers entire conversation context

👀 Sees and references actual textbook pages (GPT-4 Vision)

🎨 Generates custom educational illustrations (FREE via Hugging Face)

✅ Validates textbook content for subject and grade accuracy

📊 Provides analytics on learning progress

✨ Key Features
1. Intelligent Textbook Processing
Hybrid Text Extraction: Combines PDFPlumber + OCR for 95%+ accuracy
​

Smart Chunking: Breaks content into optimal 1000-word chunks with 150-word overlap

Vector Embeddings: Uses FAISS for lightning-fast semantic search

Content Validation: AI verifies subject and grade level accuracy

2. Multimodal AI Conversations
GPT-4 Vision Integration: Bot "sees" textbook pages and references diagrams

Conversational Memory: Remembers last 8-10 messages for context

Follow-up Intelligence: Understands "explain it clearly" without losing context

Page Screenshots: Extracts and displays actual textbook pages

3. Educational Image Generation
FREE AI Images: Hugging Face FLUX model (no API costs)

Smart Prompts: GPT generates perfect image descriptions

Visual Learning: Creates custom diagrams for concepts

4. Complete Bot Management
Multiple Bots: Each textbook = one specialized chatbot

Analytics Dashboard: Track usage, conversations, and progress

Session Management: Separate conversations per topic

🏗️ System Architecture

┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│              (React/Vue/Your UI Framework)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (JWT Auth)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Router  │  │Textbook      │  │  QA Router   │      │
│  │ /register    │  │ Router       │  │  /qa/ask     │      │
│  │ /login       │  │ /upload      │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Bots Router  │  │ Analytics    │                         │
│  │ /bots/       │  │ Router       │                         │
│  └──────────────┘  └──────────────┘                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   MongoDB    │ │    FAISS     │ │  File System │
│              │ │              │ │              │
│ • Users      │ │ • Vector     │ │ • PDF Files  │
│ • Chunks     │ │   Indexes    │ │ • Images     │
│ • Sessions   │ │ • Embeddings │ │              │
│ • Messages   │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │
        └───────────────┐
                        ↓
                ┌──────────────┐
                │  External    │
                │    APIs      │
                │              │
                │ • OpenAI     │
                │ • Hugging    │
                │   Face       │
                └──────────────┘

📊 Textbook Upload Workflow

┌─────────────────────────────────────────────────────┐
│         STEP 1: File Upload                         │
│  User uploads PDF + metadata (subject, grade)       │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│         STEP 2: Text Extraction (Hybrid)            │
│  ┌──────────────┐      ┌──────────────┐            │
│  │  PDFPlumber  │  +   │  OCR         │            │
│  │  (Digital)   │      │  (Scanned)   │            │
│  └──────┬───────┘      └──────┬───────┘            │
│         └──────────┬───────────┘                    │
│                    ↓                                │
│         Combined Clean Text                         │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│         STEP 3: Content Validation (GPT-4)          │
│  • Check subject match (Math vs Science)            │
│  • Verify grade level (5 vs 8)                      │
│  • Confidence score > 60%                           │
│                                                     │
│  ✅ PASS → Continue  |  ❌ FAIL → Reject            │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│         STEP 4: Smart Chunking                      │
│  • 1000-word chunks                                 │
│  • 150-word overlap                                 │
│  • Preserve page numbers                            │
│  Result: ~50-200 chunks                             │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│         STEP 5: Vector Embeddings (FAISS)           │
│  Each chunk → 384-dim vector                        │
│  Model: all-MiniLM-L6-v2                           │
│  Storage: data/indexes/ + data/chunks/              │
└────────────────┬────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────┐
│         STEP 6: Storage                             │
│  • MongoDB: chunks, metadata                        │
│  • FAISS: vector index                              │
│  • File: original PDF                               │
│                                                     │
│  ✅ Ready for Q&A                                   │
└─────────────────────────────────────────────────────┘

💬 Chat Flow with Multimodal AI

Student Question: "What are rolling objects?"
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  1. Save User Message → MongoDB                     │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  2. Retrieve Conversation History (last 8 msgs)     │
│     Build Context for Follow-up Detection           │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  3. Enhanced Context Search                         │
│     • Is follow-up? Extract keywords from history   │
│     • Search FAISS: "rolling objects [context]"     │
│     • Find: "Page 12 about rolling objects"         │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  4. Extract Page 12 Screenshot (PyMuPDF)            │
│     • Render at 2x resolution                       │
│     • Convert to base64 PNG                         │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  5. Send to GPT-4 Vision                            │
│     Inputs:                                         │
│     • Text: "Rolling objects are shapes..."         │
│     • Image: [Page 12 screenshot]                   │
│     • Context: Previous conversation                │
│                                                     │
│     GPT Response:                                   │
│     "Looking at page 12, I see a ball,              │
│      cylinder, and cube. The ball and               │
│      cylinder roll because..."                      │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  6. Check: Should Generate Educational Image?       │
│     • Contains visual keywords? ✓ (rolling)         │
│     • Generate prompt with GPT                      │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  7. Hugging Face Image Generation (FREE)            │
│     Prompt: "Cartoon of ball rolling, cylinder      │
│              rolling, cube not rolling..."          │
│     Model: FLUX.1-schnell (2-5 sec)                 │
│     Save: data/educational_images/edu_123.png       │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  8. Return Complete Response                        │
│     {                                               │
│       "answer": "Looking at page 12...",            │
│       "reference_page": 12,                         │
│       "educational_image": "/qa/images/edu_123.png" │
│     }                                               │
└────────────────┬────────────────────────────────────┘
        │
        ↓
┌─────────────────────────────────────────────────────┐
│  9. Save Bot Response → MongoDB                     │
│     Update session activity                         │
└─────────────────────────────────────────────────────┘


🚀 Quick Start
 Prerequisites

    Python 3.9+
    MongoDB 4.4+
    Tesseract OCR (for scanned PDFs)

1. Clone Repository
       
   git clone https://github.com/akashshettyonline22-codestar/educhat_backend
   cd educhat_backend

2. Install Dependencies

   pip install -r requirements.txt
   
4. Setup Environment Variables
    Create .env file:

    text
    # Database
    MONGODB_URL=mongodb://localhost:27017/educhat

    # Authentication
    JWT_SECRET_KEY=your-super-secret-key-change-this-in-production

    # OpenAI API
    OPENAI_API_KEY=sk-your-openai-api-key-here

    # Hugging Face (FREE)
    HUGGINGFACE_API_TOKEN=hf_your-huggingface-token-here

5. Start MongoDB
   
   mongod --dbpath /path/to/data

6. Run Application

   uvicorn main:app --reload --host 0.0.0.0 --port 8000

7. Access API Documentation

   Open browser: http://localhost:8000/docs   

📁 Project Structure

   educhat/
│
├── app/
│   ├── routers/
│   │   ├── auth_router.py          # User registration & login
│   │   ├── textbook_router.py      # Textbook upload & management
│   │   ├── qa_router.py            # Q&A chatbot endpoints
│   │   ├── bots_router.py          # Bot listing & deletion
│   │   └── analytics_router.py     # Dashboard analytics
│   │
│   ├── models/
│   │   ├── chat_schemas.py         # Pydantic models for chat
│   │   ├── chat_database.py        # Chat MongoDB operations
│   │   ├── textbook_schemas.py     # Textbook models
│   │   └── chunk_model.py          # Chunk operations
│   │
│   ├── utils/
│   │   ├── pdf_processor.py        # PDF text extraction
│   │   ├── vector_processor.py     # FAISS embeddings
│   │   └── textbook_validator.py   # Content validation
│   │
│   ├── middleware/
│   │   └── auth_middleware.py      # JWT authentication
│   │
│   ├── auth_utils.py               # JWT helper functions
│   └── database.py                 # MongoDB connection
│
├── data/
│   ├── indexes/                    # FAISS vector indexes
│   ├── chunks/                     # Chunk text mappings
│   └── educational_images/         # Generated images
│
├── uploads/                        # User-uploaded PDFs
│
├── main.py                         # FastAPI application
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
└── README.md                       # This file


🔌 API Endpoints
   Authentication

   | Method | Endpoint  | Description             |
| ------ | --------- | ----------------------- |
| POST   | /register | Register new user       |
| POST   | /login    | Login and get JWT token |

Textbooks

| Method | Endpoint          | Description                         |
| ------ | ----------------- | ----------------------------------- |
| POST   | /textbooks/upload | Upload textbook PDF with validation |
| GET    | /textbooks/list   | List all user's textbooks           |
| GET    | /textbooks/{id}   | Get textbook details                |
| DELETE | /textbooks/{id}   | Delete textbook and data            |

Q&A Chatbot

| Method | Endpoint              | Description            |
| ------ | --------------------- | ---------------------- |
| POST   | /qa/ask               | Ask question to bot    |
| GET    | /qa/images/{filename} | Serve generated images |

Bots Management

| Method | Endpoint   | Description   |
| ------ | ---------- | ------------- |
| GET    | /bots/     | List all bots |
| DELETE | /bots/{id} | Delete bot    |

Analytics

| Method | Endpoint    | Description              |
| ------ | ----------- | ------------------------ |
| GET    | /analytics/ | Get dashboard statistics |


🛠️ Technologies Used

   | Technology           | Purpose                                |
| -------------------- | -------------------------------------- |
| FastAPI              | Modern Python web framework            |
| MongoDB              | Document database for chat & textbooks |
| FAISS                | Vector similarity search               |
| OpenAI GPT-4         | Text generation & vision               |
| Hugging Face FLUX    | FREE image generation                  |
| SentenceTransformers | Text embeddings                        |
| PyMuPDF              | PDF page extraction                    |
| PDFPlumber           | PDF text extraction                    |
| Tesseract OCR        | Scanned text recognition               |
| JWT                  | Authentication                         |


🔒 Security Features
✅ JWT-based authentication

✅ Password hashing (bcrypt)

✅ User-isolated data storage

✅ API rate limiting ready

✅ Input validation (Pydantic)

✅ CORS configuration

🎓 Educational Benefits
For Students:
📖 Interactive textbook learning

💡 Visual explanations with diagrams

🔄 Follow-up questions supported


🤝 Contributing
Contributions welcome! Please follow these steps:

Fork the repository

Create feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add AmazingFeature')

Push to branch (git push origin feature/AmazingFeature)

Open Pull Request

📝 License
MIT License - feel free to use for educational purposes.

👨‍💻 Author
Your Name

GitHub: @yakashshettyonline22-codestar

Email: akashshettyonline22@gmail.com

🙏 Acknowledgments
OpenAI for GPT-4 API

Hugging Face for free image generation

FastAPI community

MongoDB team

📞 Support
For issues or questions:

🐛 Open an issue on GitHub

📧 Email: akashshettyonline22@gmail.com


Built with ❤️ for education

  