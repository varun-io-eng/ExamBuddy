🎓 Exam Buddy Pro
An AI-powered adaptive exam preparation platform with Deep Knowledge Tracing, RAG-based doubt solving, prerequisite gap detection, and personalized study coaching — built for JEE, NEET, GATE, and College Exams.

📌 Table of Contents
Overview
Features
Architecture
Tech Stack
Project Structure
Installation
Configuration
Usage
Module Reference
Exam Support
Deployment


Overview
Exam Buddy Pro is a research-grade adaptive learning system that goes beyond flashcards and quizzes. It tracks how a student learns — not just what they score — using Bayesian Knowledge Tracking (BKT) and Deep Knowledge Tracing (LSTM-based DKT) to model mastery at the concept level.
When a student gets a question wrong, the system does not just mark it incorrect. It identifies the root cause — a prerequisite topic that was never properly understood — using a directed acyclic graph (DAG) of 80+ topic dependencies, and redirects practice to fix the foundation first.
The doubt solver uses Retrieval-Augmented Generation (RAG) to answer questions from subject-specific reference books (HC Verma for Physics, RD Sharma for Maths, NCERT for Chemistry/Biology, CLRS for CS) rather than generating answers from general LLM knowledge.

Features
🧠 Core Intelligence

Bayesian Knowledge Tracking (BKT) — models per-topic mastery probability using a 4-parameter HMM, updated after every answer
Deep Knowledge Tracing (DKT) — LSTM neural network that models learning across sequences of attempts, detecting cross-topic dependencies
Prerequisite DAG Engine — 80+ topic dependency graph across Physics, Chemistry, Mathematics, Biology, and Computer Science; detects root-cause gaps and pivots practice to fix foundations
ML Difficulty Predictor — XGBoost model that adapts question difficulty based on recent performance history

📚 Doubt Solver

Subject-aware RAG — auto-detects subject from question text using scored keyword matching; Physics question → retrieves from HC Verma, Maths → RD Sharma, never cross-contaminates
Multi-modal input — text, audio (transcribed), image (OCR-extracted)
4-layer JSON parser — handles malformed LLM output with aggressive fallback strategies
Confusion type detection — identifies concept gaps, formula confusion, sign errors, unit errors, and overthinking patterns
Multi-view explanations — Intuition, Mathematical, Analogy, Shortcut, and Visual modes per question

🎯 Adaptive Practice

3 practice modes — MCQ (Competitive), Tutorial/Descriptive, Numerical/Problem Solving
Spaced repetition queue — daily review schedule driven by forgetting curve mathematics
Meta-cognitive tracker — detects answer-switching patterns and confidence calibration
Time-pressure intelligence — speed vs accuracy profiling, hesitation detection
Root-cause analysis — categorizes mistakes as concept gaps, formula confusion, calculation slips, sign errors, or overthinking

📝 Exam Mode

PDF upload — extracts MCQ questions from uploaded PYQ PDFs using multi-chunk processing
Custom exam creator — generates exams by subject, topic, difficulty, and question count
Full exam interface — timer, question navigation, mark for review, negative marking
Detailed results — score card, question-by-question review, auto-saved to database

🎓 AI Study Coach

Video Lectures — subject-filtered YouTube lecture library (Gate Smashers, Abdul Bari, Jenny's, Khan Academy, Physics Wallah, 3Blue1Brown, Amoeba Sisters, Crash Course)
Pomodoro timer — integrated focus/break timer with motivational prompts
Study Plan Generator (unlocks after 10 sessions) — day-by-day plan with PDF export
Exam Readiness (unlocks after 3 exams) — overall readiness score with gap analysis
Exam Strategy (coming soon) — time allocation and subject-wise approach

🕸️ Knowledge Graph

Visual mastery map across all subjects and topics
Prerequisite chain overlay — shows exactly which foundation is causing a weakness
One-click "Fix Now" buttons that redirect practice to root-cause topics
Correctly handles topics not in DAG — flags all low-mastery topics as gaps

🏆 Competitive Intelligence

Percentile ranking across all users
ML-predicted exam rank
Topic-wise benchmarking vs top performers
Strategic weakest-link analysis


Architecture
┌─────────────────────────────────────────────────────────┐
│                        app.py                           │
│              (Streamlit UI — 8 tabs)                    │
└────────────┬────────────────────────┬───────────────────┘
             │                        │
    ┌────────▼────────┐    ┌──────────▼──────────┐
    │  gemini_service │    │   database_auth     │
    │  (Groq LLM API) │    │   (SQLite + Auth)   │
    └────────┬────────┘    └─────────────────────┘
             │
    ┌────────▼────────┐    ┌─────────────────────┐
    │  rag_retriever  │    │  prerequisite_engine│
    │  (TF-IDF/Chroma)│    │  (DAG + mastery)    │
    └─────────────────┘    └─────────────────────┘

    ┌─────────────────────────────────────────────┐
    │           ML / Knowledge Tracking           │
    │  deep_knowledge_tracker  (BKT + DKT LSTM)   │
    │  ml_difficulty_predictor (XGBoost)          │
    │  ml_trainer              (data pipeline)    │
    │  ml_integration          (background only)  │
    └─────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────┐
    │               Feature Modules               │
    │  metacognitive_tracker  (switching + SRS)   │
    │  intelligent_question_generator             │
    │  competitive_intelligence                   │
    │  ai_study_coach         (videos + Pomodoro) │
    │  advanced_features_ui   (concept coverage)  │
    │  analytics              (knowledge graph)   │
    └─────────────────────────────────────────────┘

Tech Stack
LayerTechnologyFrontendStreamlitLLMGroq API (Gemma / LLaMA models)Knowledge TrackingCustom BKT (HMM), PyTorch LSTM (DKT)Difficulty PredictionXGBoost (via scikit-learn)RAG RetrievalTF-IDF (sklearn) + ChromaDB (optional)EmbeddingsSentenceTransformers (optional, for ChromaDB)DatabaseSQLite via AuthDatabasePDF ProcessingPyPDF2PDF ExportReportLabAudio TranscriptionGroq Whisper APIImage OCRTesseract / PILVisualizationPlotlyStylingCustom CSS via ui_professional.py

Project Structure
exam-buddy-pro/
│
├── app.py                          # Main Streamlit app — all 8 tabs, routing, onboarding
├── config.py                       # API keys (not committed — see Configuration)
│
├── database_auth.py                # SQLite DB, user auth, onboarding, attempt recording
├── gemini_service.py               # Groq LLM wrapper, RAG-powered doubt answering
├── rag_retriever.py                # Subject-aware RAG with TF-IDF + optional ChromaDB
├── prerequisite_engine.py          # DAG engine — gap detection + knowledge graph UI
│
├── deep_knowledge_tracker.py       # BKT (HMM) + DKT (LSTM) knowledge models
├── ml_difficulty_predictor.py      # XGBoost adaptive difficulty
├── ml_trainer.py                   # ML training data pipeline
├── ml_integration.py               # Background ML initializer (no UI)
│
├── metacognitive_tracker.py        # Answer-switching tracker + spaced repetition queue
├── intelligent_question_generator.py  # Context-aware MCQ/tutorial/numerical generation
├── advanced_features_ui.py         # Concept coverage tab renderer
├── analytics.py                    # Basic knowledge graph renderer (fallback)
│
├── ai_study_coach.py               # Video lectures, Pomodoro, study plan, exam strategy
├── competitive_intelligence.py     # Percentile ranking and benchmarking
│
├── ui_professional.py              # Dark/light theme CSS, metric cards, progress bars
│
├── requirements.txt                # All dependencies
└── README.md

Installation
Prerequisites

Python 3.10 or higher
A Groq API key (free tier available)

Steps
bash# 1. Clone the repository
git clone https://github.com/yourusername/exam-buddy-pro.git
cd exam-buddy-pro

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key (see Configuration section)

# 5. Run the app
streamlit run app.py
requirements.txt
streamlit>=1.35.0
groq>=0.9.0
numpy>=1.24.0
pandas>=2.0.0
plotly>=5.18.0
scikit-learn>=1.3.0
torch>=2.0.0
xgboost>=2.0.0
reportlab>=4.0.0
PyPDF2>=3.0.0
Pillow>=10.0.0
sentence-transformers>=2.2.0
chromadb>=0.4.0

Note: torch, chromadb, and sentence-transformers are optional. The system gracefully falls back to BKT (instead of DKT) and TF-IDF (instead of ChromaDB) if they are unavailable.


Configuration
Create a config.py file in the project root:
python# config.py
GROQ_API_KEY = "gsk_your_api_key_here"
Never commit config.py to version control. Add it to .gitignore:
config.py
*.db
__pycache__/
.venv/

Usage
First Launch

Open the app and register a new account
On first login, the onboarding screen appears:

Step 1 — Select your target exam (JEE Main, JEE Advanced, NEET, GATE CS, College Exams, etc.)
Step 2 — Select your current level (Beginner / Average / Strong)


Subjects are auto-assigned based on your exam:

JEE → Physics, Chemistry, Mathematics
NEET → Physics, Chemistry, Biology
GATE CS / College Exams → DSA, DBMS, Operating Systems, Computer Networks, OOPs



Taking an Exam
Go to 📝 Upload & Take Exam tab:

Upload a PDF of previous year questions, or
Create a custom exam by selecting subject, topic, difficulty, and count

Asking Doubts
Go to 🧠 Doubt Solver tab:

Type your question, upload an audio file, or take a photo of a problem
The system auto-detects the subject from your question and retrieves the correct reference material

Watching Video Lectures
Go to 🎓 AI Study Coach → 🎥 Video Lectures:

Subject dropdown shows only subjects relevant to your exam
Built-in Pomodoro timer tracks your study session


Module Reference
ModuleResponsibilityapp.pyTab routing, onboarding, session state, sidebardatabase_auth.pyUser registration/login, attempt recording, onboarding preferencesgemini_service.pyLLM calls, question generation, RAG-powered answering, 4-layer JSON parsingrag_retriever.pySubject detection (scored keywords), TF-IDF retrieval, ChromaDB fallbackprerequisite_engine.pyDAG traversal, gap detection, intervention card, knowledge graphdeep_knowledge_tracker.pyBKT (4-param HMM), DKT (LSTM), mastery estimation, review schedulingml_difficulty_predictor.pyXGBoost difficulty prediction, feature engineeringmetacognitive_tracker.pyAnswer-switching detection, spaced repetition queue, review badgesintelligent_question_generator.pyContext-aware question generation across 3 modesai_study_coach.pyYouTube video library, Pomodoro timer, study plan, PDF exportcompetitive_intelligence.pyPercentile ranking, benchmarking, strategic gap analysis

Exam Support
ExamSubjectsJEE Main / AdvancedPhysics, Chemistry, MathematicsNEETPhysics, Chemistry, BiologyGATE CSComputer Science, MathematicsGATE ECEPhysics, Mathematics, ElectronicsCollege ExamsDSA, DBMS, Operating Systems, Computer Networks, OOPsCATMathematics, Verbal Ability, Logical ReasoningUPSCGeneral Studies, Mathematics, Science

Deployment
The app is deployed on Render as a web service.
Render Setup

Connect your GitHub repository to Render
Set Build Command: pip install -r requirements.txt
Set Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
Add environment variable: GROQ_API_KEY = your_key_here
Use a persistent disk mounted at /opt/render/project/src for the SQLite database

Cold Start Optimization
The app is optimized for cold starts on free-tier hosting:

ML models initialize lazily on first use
BKT falls back to simple priors if DKT LSTM is not yet trained
ChromaDB falls back to TF-IDF if vector store is empty


Acknowledgements
Video lectures sourced from the YouTube channels of:
Gate Smashers · Abdul Bari · Jenny's Lectures · Khan Academy · Physics Wallah · 3Blue1Brown · Amoeba Sisters · Crash Course · freeCodeCamp · Neso Academy · Organic Chemistry Tutor
Reference knowledge base built from:
HC Verma (Physics) · RD Sharma / SL Loney (Mathematics) · NCERT (Chemistry, Biology) · Morrison Boyd (Organic Chemistry) · CLRS (Algorithms) · Galvin (Operating Systems)
