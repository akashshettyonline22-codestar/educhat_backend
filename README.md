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

graph TB
    subgraph Client["Client Layer"]
        A[Web App<br/>React/Vue]
        B[Mobile App<br/>Future]
    end
    
    subgraph API["API Gateway Layer"]
        C[FastAPI Server]
        D[CORS Middleware]
        E[JWT Auth]
    end
    
    subgraph App["Application Layer"]
        F[Auth Router]
        G[Textbook Router]
        H[Q&A Router]
        I[Bots Router]
        J[Analytics Router]
    end
    
    subgraph Logic["Business Logic Layer"]
        K[PDF Processor]
        L[Vector Search<br/>FAISS]
        M[Chat Manager]
        N[Image Generator<br/>Hugging Face]
        O[Validator<br/>GPT-4]
    end
    
    subgraph Storage["Storage Layer"]
        P[(MongoDB)]
        Q[FAISS Indexes]
        R[File System<br/>PDFs & Images]
    end
    
    subgraph External["External Services"]
        S[OpenAI API<br/>GPT-4 Vision]
        T[Hugging Face<br/>FLUX Model]
    end
    
    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    E --> G
    E --> H
    E --> I
    E --> J
    
    G --> K
    G --> O
    H --> L
    H --> M
    H --> N
    
    K --> P
    L --> Q
    M --> P
    N --> R
    O --> S
    N --> T
    
    style Client fill:#e1f5ff
    style API fill:#fff3e0
    style App fill:#f3e5f5
    style Logic fill:#e8f5e9
    style Storage fill:#fff9c4
    style External fill:#ffebee


📊 Textbook Upload Workflow
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant PDF as PDF Processor
    participant VAL as Validator GPT
    participant CHUNK as Chunker
    participant VEC as Vector Engine
    participant DB as MongoDB
    participant FAISS as FAISS Index

    U->>API: Upload PDF + Metadata
    API->>PDF: Extract Text (Hybrid)
    PDF-->>API: Extracted Text
    
    API->>VAL: Validate Subject & Grade
    VAL->>VAL: Check with GPT-4
    
    alt Validation Failed
        VAL-->>API: ❌ Mismatch
        API-->>U: Reject Upload
    else Validation Passed
        VAL-->>API: ✅ Valid
        API->>CHUNK: Smart Chunking
        CHUNK-->>API: 50-200 Chunks
        
        API->>VEC: Generate Embeddings
        VEC->>VEC: SentenceTransformer
        VEC->>FAISS: Store Vectors
        VEC->>DB: Store Chunks
        
        FAISS-->>API: Index Created
        DB-->>API: Chunks Saved
        API-->>U: ✅ Upload Success
    end


💬 Chat Flow with Multimodal AI

flowchart TD
    Start([Student Asks Question]) --> Session{Session<br/>Exists?}
    
    Session -->|No| CreateSession[Create New Session]
    Session -->|Yes| LoadHistory[Load Conversation History]
    
    CreateSession --> SaveMsg[Save User Message]
    LoadHistory --> SaveMsg
    
    SaveMsg --> Context[Build Context<br/>Last 8 Messages]
    Context --> Followup{Is Follow-up<br/>Question?}
    
    Followup -->|Yes| Extract[Extract Keywords<br/>from History]
    Followup -->|No| DirectSearch[Direct Search]
    
    Extract --> EnhancedSearch[Enhanced Search<br/>Question + Context]
    DirectSearch --> EnhancedSearch
    
    EnhancedSearch --> FAISS[FAISS Vector Search]
    FAISS --> Results{Found<br/>Results?}
    
    Results -->|No| OutOfContext[Out of Context Response]
    Results -->|Yes| ExtractPage[Extract Page Screenshot]
    
    ExtractPage --> GPT4[Send to GPT-4 Vision<br/>Text + Image + Context]
    GPT4 --> CheckVisual{Visual<br/>Concept?}
    
    CheckVisual -->|Yes| GenImage[Generate Educational Image<br/>Hugging Face FLUX]
    CheckVisual -->|No| Response[Assemble Response]
    
    GenImage --> Response
    Response --> SaveBot[Save Bot Response]
    SaveBot --> End([Return to User])
    OutOfContext --> End
    
    style Start fill:#4caf50,color:#fff
    style End fill:#2196f3,color:#fff
    style FAISS fill:#ff9800,color:#fff
    style GPT4 fill:#9c27b0,color:#fff
    style GenImage fill:#e91e63,color:#fff



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

 
---

### 📝 File Descriptions

#### **Core Application (`app/`)**

| File/Directory | Purpose |
|----------------|---------|
| `routers/` | API endpoint handlers organized by feature |
| `models/` | Pydantic schemas and database operations |
| `utils/` | Helper functions for PDF, vectors, validation |
| `middleware/` | Custom FastAPI middleware (auth, logging) |
| `auth_utils.py` | JWT token creation and verification |
| `database.py` | MongoDB connection and initialization |

#### **API Routers**

| Router | Endpoints | Description |
|--------|-----------|-------------|
| `auth_router.py` | `/register`, `/login` | User authentication |
| `textbook_router.py` | `/textbooks/upload`, `/textbooks/list` | Textbook management |
| `qa_router.py` | `/qa/ask`, `/qa/images/{filename}` | Chatbot Q&A |
| `bots_router.py` | `/bots/`, `/bots/{id}` | Bot management |
| `analytics_router.py` | `/analytics/` | Dashboard statistics |

#### **Data Storage**

| Directory | Contents | Purpose |
|-----------|----------|---------|
| `data/indexes/` | `*.index` files | FAISS vector embeddings |
| `data/chunks/` | `*.pkl` files | Chunk text mappings |
| `data/educational_images/` | `*.png` files | AI-generated educational images |
| `uploads/` | `*.pdf` files | Original textbook PDFs |

#### **Configuration Files**

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app setup, CORS, middleware |
| `requirements.txt` | Python package dependencies |
| `.env` | Environment variables (secrets) |
| `.gitignore` | Files to exclude from git |
| `README.md` | Project documentation |

---

### 🗄️ Database Collections (MongoDB)



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

  
