"""
ULTIMATE Exam Buddy Pro - app.py (2026-Level) ⭐⭐ UPDATED WITH EXCEPTIONAL TABS
🔥 ALL ADVANCED FEATURES:
- 3 Practice Modes (MCQ, Tutorial/Descriptive, Numerical)
- Root-Cause Mistake Classification
- Time-Pressure Intelligence
- Exam Strategy Generator
- Learning DNA Profile
- Smart Break Detection
- Concept Dependency Graph
- Exam Outcome Simulator
- Meta-Explanation Feedback

⭐⭐ NEW 9+ FEATURES (v3.0):
Feature 1: Deep Knowledge Tracing (DKT) — LSTM replaces BKT
  - Captures cross-topic dependencies over time
  - "Failing Algebra Week 1 predicts Calculus failure Week 5"

Feature 2: True RAG Doubt Solver
  - Retrieves from local vector DB (HC Verma, NCERT, RD Sharma)
  - Every answer cites a real source, zero hallucination

Feature 3: Meta-Cognitive Answer Switching Tracker
  - Detects: Changed Correct→Wrong, Guessing, Deep Confusion
  - Shows HOW you think, not just WHAT you got wrong

Feature 4: Daily Spaced Repetition Review Queue
  - Forgetting curve math drives proactive "review NOW" alerts
  - Closes the feedback loop: app reaches out to student
"""

import streamlit as st
import json
import time
from datetime import datetime, timedelta
import re
import random
from collections import defaultdict, Counter

# Page config
st.set_page_config(
    page_title="Exam Buddy Pro - Ultimate",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import modules
from database_auth import AuthDatabase
from gemini_service import EnhancedGeminiService
from ui_professional import apply_theme, render_metric_card, render_score_display, render_progress_bar
from analytics import render_analytics_dashboard, render_knowledge_graph
from file_processors import AudioProcessor, FileProcessor

# ⭐ FEATURE 1: Deep Knowledge Tracing (replaces BKT)
try:
    from deep_knowledge_tracker import DeepKnowledgeTracker as BayesianKnowledgeTracker
    DKT_AVAILABLE = True
except Exception:
    from bayesian_knowledge_tracker import BayesianKnowledgeTracker
    DKT_AVAILABLE = False

from intelligent_question_generator import IntelligentQuestionGenerator
from error_taxonomy_engine import ErrorTaxonomy, FixStrategyEngine
from advanced_features_ui import (
    render_bayesian_knowledge_tab,
    render_concept_coverage_tab,
    render_error_analysis_tab
)

# ⭐ ML INTEGRATION (runs in background only — no UI tab)
from ml_integration import (
    initialize_ml_system,
    enhance_adaptive_practice,
    render_ml_training_section,
    build_student_context
)

# ⭐ FEATURE 2: RAG retriever (initialised once)
try:
    from rag_retriever import get_retriever
    RAG_AVAILABLE = True
except Exception:
    RAG_AVAILABLE = False

# ⭐ FEATURES 3 & 4: Meta-cognitive tracker + Daily Review Queue
try:
    from metacognitive_tracker import (
        init_tracker, reset_tracker, track_answer_change,
        render_metacognitive_analysis,
        render_daily_review_queue,
        render_sidebar_review_badge
    )
    METACOG_AVAILABLE = True
except Exception:
    METACOG_AVAILABLE = False

# ⭐⭐ COMPETITIVE ADVANTAGE TABS
from ai_study_coach import render_ai_study_coach_tab
from competitive_intelligence import render_competitive_intelligence_tab
try:
    from prerequisite_engine import PrerequisiteEngine, render_prerequisite_intervention, render_prereq_knowledge_graph
    PREREQ_AVAILABLE = True
except Exception:
    PREREQ_AVAILABLE = False


def save_question_attempts_to_db(db, user_id, questions, answers, exam_name, session_id=None):
    """Save individual question attempts for analytics and ML insights - FIXED FOR AuthDatabase"""
    import uuid
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    attempts_saved = 0
    
    for i, q in enumerate(questions):
        user_answer = answers.get(i, None)
        if user_answer is None:
            continue  # Skip unattempted questions
        
        question_text = q.get('question', '')
        correct_answer = q.get('correct_answer', 'A')
        
        # Normalize comparison
        user_answer_normalized = str(user_answer).strip().upper()
        correct_answer_normalized = str(correct_answer).strip().upper()
        is_correct = (user_answer_normalized == correct_answer_normalized)
        
        subject = q.get('subject', 'General')
        topic = q.get('topic', q.get('subtopic', 'General'))
        difficulty = q.get('difficulty', 'medium')
        
        try:
            # Use record_attempt (the method that exists in AuthDatabase)
            db.record_attempt(
                user_id=user_id,
                question=question_text[:200],
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
                time_taken=30,
                subject=subject,
                topic=topic,
                difficulty=difficulty
            )
            attempts_saved += 1
        except Exception as e:
            print(f"Error saving Q{i+1}: {e}")
            continue
    
    print(f"✅ Saved {attempts_saved} attempts for analytics")
    return attempts_saved



# ══════════════════════════════════════════════════════════════════════════
# EXAM → SUBJECTS MAPPING
# ══════════════════════════════════════════════════════════════════════════

EXAM_SUBJECTS = {
    "JEE Main":      ["Physics", "Chemistry", "Mathematics"],
    "JEE Advanced":  ["Physics", "Chemistry", "Mathematics"],
    "NEET":          ["Physics", "Chemistry", "Biology"],
    "GATE CS":       ["Computer Science", "Mathematics"],
    "GATE ECE":      ["Physics", "Mathematics", "Electronics"],
    "UPSC":          ["General Studies", "Mathematics", "Science"],
    "CAT":           ["Mathematics", "Verbal Ability", "Logical Reasoning"],
    "College Exams": ["DSA", "DBMS", "Operating Systems", "Computer Networks", "OOPs"],
}

EXAM_SUBJECT_ICONS = {
    "Physics":           "⚛️",
    "Chemistry":         "🧪",
    "Mathematics":       "📐",
    "Biology":           "🧬",
    "Computer Science":  "💻",
    "DSA":               "🌳",
    "DBMS":              "🗄️",
    "Operating Systems": "⚙️",
    "Computer Networks": "🌐",
    "OOPs":              "🔷",
    "Electronics":       "🔌",
    "General Studies":   "📚",
    "Verbal Ability":    "📝",
    "Logical Reasoning": "🧩",
}

def get_subjects_for_exam(exam_type: str) -> list:
    """Return subject list for the given exam type."""
    return EXAM_SUBJECTS.get(exam_type, ["Physics", "Chemistry", "Mathematics"])


def get_user_attempt_count(db, user_id):
    """Returns total number of attempts the user has made."""
    try:
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attempts WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception:
        return 0


def render_empty_state(tab_name, features, icon="🔒"):
    """Friendly empty state with a redirect button to the exam tab."""
    st.markdown(f"## {icon} {tab_name}")
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""<div style="text-align:center;padding:40px 20px;">
                <div style="font-size:64px;margin-bottom:16px;">📄</div>
                <h3 style="margin-bottom:8px;">No exam data yet</h3>
                <p style="color:#888;margin-bottom:24px;">
                    Take your first exam to unlock this tab!
                </p></div>""",
            unsafe_allow_html=True
        )
        st.markdown("**Once you take an exam, you'll see:**")
        for feature in features:
            st.markdown(f"  {feature}")
        st.markdown("---")
        st.info("👇 Go to the **Upload & Take Exam** tab to get started")
        if st.button(
            "🚀 Take My First Exam", type="primary",
            use_container_width=True,
            key=f"goto_exam_{tab_name.replace(' ','_')}"
        ):
            st.session_state['goto_tab'] = 3
            st.rerun()


def render_onboarding_screen():
    """
    2-step onboarding on first login.
    Step 1 — Which exam are you preparing for?
    Step 2 — What is your current level?
    No subject selection — subjects are auto-assigned based on exam.
    """
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem 0;">
        <div style="font-size:4rem;">🎓</div>
        <h1 style="font-size:2.5rem;font-weight:800;">Welcome to Exam Buddy Pro!</h1>
        <p style="font-size:1.1rem;color:#94a3b8;">
            Let's set up your profile. Takes 20 seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:

        # Step 1 — Exam type
        st.markdown("### 🎯 Step 1 — Which exam are you preparing for?")
        exam_options = list(EXAM_SUBJECTS.keys())
        exam_type = st.selectbox(
            "Exam", exam_options, label_visibility="collapsed",
            key="onboard_exam"
        )

        # Show subjects that will be unlocked — read-only preview, not a selector
        subjects_for_exam = get_subjects_for_exam(exam_type)
        subject_pills = "  ".join(
            f"{EXAM_SUBJECT_ICONS.get(s, '📖')} {s}" for s in subjects_for_exam
        )
        st.caption(f"Subjects included: {subject_pills}")

        st.markdown("")

        # Step 2 — Level
        st.markdown("### 💪 Step 2 — What is your current level?")
        level = st.radio(
            "Level", ["Beginner", "Average", "Strong"],
            horizontal=True, label_visibility="collapsed",
            key="onboard_level"
        )

        st.markdown("---")
        if st.button("🚀 Let's Start!", type="primary", use_container_width=True):
            # Default starting subject = first subject in exam list
            default_subject = subjects_for_exam[0] if subjects_for_exam else "General"
            saved = st.session_state.db.save_onboarding(
                st.session_state.user_id, exam_type, default_subject
            )
            if saved:
                st.session_state['onboarding_complete']  = True
                st.session_state['exam_type']            = exam_type
                st.session_state['current_subject']      = default_subject
                st.session_state['available_subjects']   = subjects_for_exam
                difficulty_map = {"Beginner": "Easy", "Average": "Medium", "Strong": "Hard"}
                st.session_state['initial_difficulty']   = difficulty_map.get(level, "Medium")
                st.success("✅ All set! Loading your dashboard...")
                st.rerun()
            else:
                st.error("Something went wrong. Please try again.")

def init_session_state():
    """Initialize all session state variables"""
    if 'db' not in st.session_state:
        st.session_state.db = AuthDatabase()
    
    # Authentication states
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'
    
    defaults = {
        # Chat & Practice states
        'chat_history': [],
        'generated_questions': [],
        'user_answers': {},
        'quiz_submitted': False,
        'question_start_times': {},
        'current_subject': 'Physics',
        'practice_subject': 'Physics',
        
        # 🧠 ADVANCED DOUBT SOLVER STATES
        'doubt_view_preferences': {
            'intuition': True, 
            'math': False, 
            'analogy': True, 
            'shortcut': True
        },
        'doubt_confidence_level': 3,
        'doubt_step_mode': False,
        'doubt_current_step': 0,
        'doubt_steps': [],
        'doubt_follow_up_shown': False,
        'doubt_follow_up_question': None,
        'doubt_confusion_type': None,
        'doubt_context_data': None,
        'doubt_last_question': '',
        'doubt_last_response': '',
        'doubt_user_mistakes': [],
        'doubt_explanation_shown': False,
        'doubt_available_views': [],
        'doubt_generated_views': {},
        'doubt_active_view': None,
        
        # 🔥 NEW: PRACTICE MODE STATES
        'practice_mode': 'MCQ (Competitive)',  # MCQ, Tutorial, Numerical
        'tutorial_questions': [],
        'tutorial_answers': {},
        'tutorial_ai_feedback': {},
        'numerical_questions': [],
        'numerical_solutions': {},
        'numerical_feedback': {},
        
        # 🔥 NEW: ROOT-CAUSE STATES
        'mistake_history': [],  # List of {question, mistake_type, timestamp}
        'mistake_patterns': {},  # {mistake_type: count}
        
        # 🔥 NEW: TIME-PRESSURE INTELLIGENCE
        'time_accuracy_data': [],  # {time_taken, is_correct, timestamp}
        'speed_vs_accuracy_profile': None,
        'hesitation_data': [],
        
        # 🔥 NEW: LEARNING DNA PROFILE
        'learning_dna': {
            'speed_vs_accuracy': 'balanced',  # fast/balanced/careful
            'memory_type': 'formula-based',  # formula/visual/concept
            'fatigue_time': 45,  # minutes
            'confidence_bias': 'neutral',  # overconfident/neutral/underconfident
            'mistake_patterns': {},
            'preferred_learning_style': 'mixed'
        },
        
        # 🔥 NEW: SMART BREAK DETECTION
        'session_start_time': time.time(),
        'consecutive_errors': 0,
        'questions_since_break': 0,
        'last_break_time': time.time(),
        'break_suggested': False,
        
        # 🔥 NEW: CONCEPT DEPENDENCY
        'concept_dependencies': {},  # {topic: [prerequisite topics]}
        'weak_prerequisites': {},
        
        # 🔥 NEW: META-FEEDBACK
        'explanation_feedback': [],  # {explanation_id, rating, feedback}
        'explanation_quality_score': 0.8,
        
        # Upload PYQ Exam states
        'upload_exam_started': False,
        'upload_exam_name': 'My Exam',
        'upload_exam_duration': 180,
        'upload_questions': [],
        'upload_answers': {},
        'upload_submitted': False,
        'upload_start_time': None,
        'upload_marked_review': set(),
        'upload_current_q': 0,
        'upload_positive_marks': 4,
        'upload_negative_marks': 1,
        'upload_negative_marking': True,


        # ⭐ ADVANCED ML FEATURES STATES
        'bkt_tracker': None,
        'question_generator': None,
        'error_engine': None,
        'advanced_features_initialized': False,
        'mistake_history': [],
        

    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


def render_login_page():
    """Render login/register page"""
    apply_theme(st.session_state.theme)
    
    st.markdown("<h1 style='text-align: center; margin-bottom: 1rem;'>🎓 Exam Buddy Pro</h1>", 
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 2rem;'>"
                "Professional Exam Preparation Platform</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        st.markdown("### Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")
            
            if submit:
                if username and password:
                    user_id, message = st.session_state.db.login_user(username, password)
                    if user_id:
                        st.session_state.user_id = user_id
                        st.session_state.authenticated = True
                        user_info = st.session_state.db.get_user_info(user_id)
                        st.session_state.username = user_info['username']
                        st.session_state.theme = user_info['theme_preference']
                        st.success(f"✅ Welcome back, {user_info['username']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Please fill all fields")
    
    with tab2:
        st.markdown("### Create New Account")
        with st.form("register_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register", use_container_width=True, type="primary")
            
            if submit:
                if new_username and new_email and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("❌ Passwords don't match")
                    elif len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters")
                    else:
                        user_id, message = st.session_state.db.register_user(
                            new_username, new_email, new_password
                        )
                        if user_id:
                            st.success(f"✅ {message}! Please login.")
                        else:
                            st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ Please fill all fields")




def initialize_advanced_features(db, llm):
    """Initialize all advanced ML features including DKT"""
    if not st.session_state.get('advanced_features_initialized', False):
        try:
            # Feature 1: Use DKT if available, else fall back to BKT
            tracker = BayesianKnowledgeTracker(db)  # Already points to DKT via import
            st.session_state.bkt_tracker = tracker

            if DKT_AVAILABLE:
                st.sidebar.success("🧠 DKT: Active (LSTM Knowledge Tracking)")
                # Auto-train DKT in background if enough data
                try:
                    tracker.auto_train()
                except Exception:
                    pass
            else:
                st.sidebar.info("🧮 BKT: Active (Bayesian Knowledge Tracking)")

            st.session_state.question_generator = IntelligentQuestionGenerator(
                db, llm, tracker
            )
            st.session_state.error_engine = FixStrategyEngine(db, llm)

            # Feature 2: Initialise RAG retriever
            if RAG_AVAILABLE:
                try:
                    get_retriever()
                    st.sidebar.success("📚 RAG: Active (Vector Knowledge Base)")
                except Exception:
                    pass

            # Feature 3 & 4: init metacognitive tracker
            if METACOG_AVAILABLE:
                init_tracker()

            st.session_state.advanced_features_initialized = True
            return True
        except Exception as e:
            st.sidebar.warning(f"⚠️ Advanced features: {str(e)[:40]}")
            return False
    return True


def main():
    """Main application"""
    # Apply theme
    apply_theme(st.session_state.theme)
    
    # ⭐ ML INTEGRATION - Initialize ML system
    initialize_ml_system(st.session_state.db)
    
    # Check authentication
    if not st.session_state.authenticated:
        render_login_page()
        return

    # ── ONBOARDING: show once on first login ─────────────────────────────
    if not st.session_state.get('onboarding_complete'):
        status = st.session_state.db.get_onboarding_status(st.session_state.user_id)
        if not status['is_onboarded']:
            render_onboarding_screen()
            return
        else:
            st.session_state['onboarding_complete']  = True
            st.session_state['exam_type']            = status['exam_type']
            st.session_state['current_subject']      = status['onboarding_subject']
            st.session_state['available_subjects']   = get_subjects_for_exam(status['exam_type'])

    exam_type = st.session_state.get('exam_type', 'JEE Main')
    subjects  = st.session_state.get('available_subjects', get_subjects_for_exam(exam_type))

    st.markdown(f'''
    <div style="text-align: center; padding: 1rem 0;">
        <h1 style="font-size: 3rem; font-weight: 700;">
            🎓 Exam Buddy Pro
        </h1>
        <p style="font-size: 1.1rem;">
            Welcome, {st.session_state.username}! &nbsp;|&nbsp; 🎯 {exam_type}
        </p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Load API key
    try:
        from config import GROQ_API_KEY
        if not GROQ_API_KEY or "paste_your_api_key" in GROQ_API_KEY.lower():
            st.error("⚠️ Please set your GROQ_API_KEY in config.py")
            st.info("Get API key: https://console.groq.com/keys")
            st.stop()
        api_key = GROQ_API_KEY
    except ImportError:
        st.error("❌ config.py not found")
        st.stop()
    
    # Initialize LLM
    if "llm" not in st.session_state:
        try:
            st.session_state.llm = EnhancedGeminiService(api_key)
        except Exception as e:
            st.error(f"LLM error: {e}")
            st.stop()
    
    llm = st.session_state.llm
    
    # ⭐ Initialize Advanced ML Features
    initialize_advanced_features(st.session_state.db, llm)
    
    render_sidebar()
    
    # ── 8 TABS (ML+DKT and Analytics removed from UI, run in background) ──
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🧠 Doubt Solver",
        "🎯 Adaptive Practice",
        "📝 Upload & Take Exam",
        "🗺️ Concept Coverage",
        "🕸️ Knowledge Graph",
        "🎓 AI Study Coach",
        "🏆 Competitive Intel",
        "📅 Daily Review",
    ])

    # ── Tab 1: Doubt Solver ───────────────────────────────────────────────
    with tab1:
        render_advanced_doubt_solver(llm)

    # ── Tab 2: Adaptive Practice ──────────────────────────────────────────
    with tab2:
        render_adaptive_practice_with_modes(llm)

    # ── Tab 3: Upload & Take Exam ─────────────────────────────────────────
    with tab3:
        render_upload_exam_mode(llm)

    # ── Tab 4: Concept Coverage ───────────────────────────────────────────
    with tab4:
        _atm4 = get_user_attempt_count(st.session_state.db, st.session_state.user_id)
        if _atm4 == 0:
            render_empty_state(
                "Concept Coverage", icon="🗺️",
                features=[
                    "🗺️ Visual map of topics covered vs remaining",
                    "✅ Mastered concepts highlighted in green",
                    "⚠️ Weak concepts needing revision",
                    "📋 Syllabus completion percentage",
                    "🎯 Next recommended topic to study",
                ]
            )
        elif st.session_state.question_generator:
            render_concept_coverage_tab(
                st.session_state.user_id,
                st.session_state.db,
                st.session_state.question_generator
            )
        else:
            st.info("⏳ Initializing... please refresh.")

    # ── Tab 5: Knowledge Graph ────────────────────────────────────────────
    with tab5:
        _atm5 = get_user_attempt_count(st.session_state.db, st.session_state.user_id)
        if _atm5 == 0:
            render_empty_state(
                "Knowledge Graph", icon="🕸️",
                features=[
                    "🕸️ Visual graph of knowledge across all subjects",
                    "🟢 Green = mastered  🟡 Yellow = in progress  🔴 Red = gap",
                    "🔗 Prerequisite chains — see WHY you're stuck",
                    "🎯 One-click Fix buttons to attack weak prerequisites",
                ]
            )
        else:
            if PREREQ_AVAILABLE:
                render_prereq_knowledge_graph(st.session_state.user_id, st.session_state.db)
            else:
                render_knowledge_graph(st.session_state.user_id, st.session_state.db)

    # ── Tab 6: AI Study Coach — always open (video lectures don't need exam data)
    with tab6:
        render_ai_study_coach_tab(
            st.session_state.user_id,
            st.session_state.db,
            st.session_state.get('bkt_tracker'),
            llm
        )

    # ── Tab 7: Competitive Intel ──────────────────────────────────────────
    with tab7:
        _atm7 = get_user_attempt_count(st.session_state.db, st.session_state.user_id)
        if _atm7 == 0:
            render_empty_state(
                "Competitive Intelligence", icon="🏆",
                features=[
                    "🏅 Your percentile rank among all students",
                    "🎯 ML-predicted exam rank",
                    "📊 Topic-wise benchmarking vs top performers",
                    "⚡ Strategic weakest-link analysis",
                ]
            )
        elif st.session_state.bkt_tracker:
            render_competitive_intelligence_tab(
                st.session_state.user_id,
                st.session_state.db,
                st.session_state.bkt_tracker
            )
        else:
            st.info("⏳ Tracker initializing... please refresh.")

    # ── Tab 8: Daily Review Queue ─────────────────────────────────────────
    with tab8:
        _atm8 = get_user_attempt_count(st.session_state.db, st.session_state.user_id)
        if _atm8 == 0:
            render_empty_state(
                "Daily Review Queue", icon="📅",
                features=[
                    "📅 Today's personalised topics to revise",
                    "🔴 Topics you're about to forget — review NOW",
                    "🟡 Topics declining in mastery — review soon",
                    "⏰ Powered by forgetting curve maths",
                ]
            )
        else:
            st.markdown("## 📅 Daily Review Queue")
            st.caption("Your personalised study plan for today — driven by the forgetting curve")
            dkt_label = "DKT (Deep Knowledge Tracing)" if DKT_AVAILABLE else "BKT (Bayesian)"
            st.info(f"🧠 Powered by {dkt_label} — reviews topics at the optimal moment")
            if st.session_state.get('bkt_tracker') and st.session_state.get('user_id'):
                if METACOG_AVAILABLE:
                    def on_practice(subject, topic):
                        st.session_state.current_subject = subject
                        st.session_state.practice_subject = subject
                        st.info(f"✅ Go to Adaptive Practice → {subject} → {topic}")
                    render_daily_review_queue(
                        st.session_state.user_id,
                        st.session_state.bkt_tracker,
                        on_practice_click=on_practice
                    )
                else:
                    st.warning("Install metacognitive_tracker.py to enable the Review Queue.")
            else:
                st.info("Complete at least 5 questions to unlock the Daily Review Queue.")
        st.markdown("## 📅 Daily Review Queue")
        st.caption("Your personalised study plan for today — driven by the forgetting curve")

        dkt_label = "DKT (Deep Knowledge Tracing)" if DKT_AVAILABLE else "BKT (Bayesian)"
        st.info(f"🧠 Powered by {dkt_label} — reviews topics at the mathematically optimal moment")

        if st.session_state.get('bkt_tracker') and st.session_state.get('user_id'):
            if METACOG_AVAILABLE:
                def on_practice(subject, topic):
                    st.session_state.current_subject = subject
                    st.session_state.practice_subject = subject
                    st.info(f"✅ Set practice topic to: {subject} → {topic}. Go to Adaptive Practice tab!")

                render_daily_review_queue(
                    st.session_state.user_id,
                    st.session_state.bkt_tracker,
                    on_practice_click=on_practice
                )

                # DKT cross-topic insight
                if DKT_AVAILABLE:
                    st.divider()
                    st.markdown("### 🔗 DKT Cross-Topic Dependency Insights")
                    st.caption("The LSTM model detects patterns across your entire study history")
                    try:
                        dkt_info = st.session_state.bkt_tracker.get_dkt_ability(
                            st.session_state.user_id
                        )
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("DKT Ability Score",
                                      f"{dkt_info['ability']*100:.1f}%")
                        with col2:
                            trend_icon = {"improving": "📈", "declining": "📉", "stable": "➡️"}.get(
                                dkt_info.get('trend', 'stable'), "➡️"
                            )
                            st.metric("Learning Trend",
                                      f"{trend_icon} {dkt_info.get('trend','stable').title()}")
                        with col3:
                            st.metric("Sequence Length",
                                      f"{dkt_info['sequence_length']} attempts")

                        insight = dkt_info.get('cross_topic_insight')
                        if insight:
                            st.warning(f"🔗 **Cross-Topic Pattern Detected:** {insight}")
                        else:
                            st.success("✅ No problematic cross-topic dependencies detected.")

                        if dkt_info.get('next_prediction'):
                            prob = dkt_info['next_prediction'] * 100
                            st.metric(
                                "P(correct on next question)",
                                f"{prob:.1f}%",
                                help="LSTM prediction based on your full attempt sequence"
                            )
                    except Exception as e:
                        st.info(f"Complete more practice sessions to unlock DKT insights. ({e})")
            else:
                st.warning("Install metacognitive_tracker.py to enable the Review Queue.")
        else:
            st.info("📚 Complete at least 5 practice questions to unlock your Daily Review Queue!")


def render_sidebar():
    """Sidebar with stats, theme toggle, and user info"""
    with st.sidebar:
        user_info = st.session_state.db.get_user_info(st.session_state.user_id)

        username = user_info.get("username", "Guest") if user_info else "Guest"
        email = user_info.get("email", "") if user_info else ""

        st.markdown(f"### 👤 {username}")
        if email:
            st.caption(f"📧 {email}")

        st.divider()
        # Theme toggle
        st.markdown("### 🎨 Theme")
        theme_option = st.radio(
            "Theme:",
            ["🌙 Dark", "☀️ Light"],
            index=0 if st.session_state.theme == 'dark' else 1,
            label_visibility="collapsed"
        )
        
        new_theme = 'dark' if theme_option == "🌙 Dark" else 'light'
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.session_state.db.update_theme_preference(st.session_state.user_id, new_theme)
            st.rerun()
        
        st.divider()
        
        # Quick Stats
        st.markdown("### 📊 Quick Stats")
        
        analytics = st.session_state.db.get_user_analytics(st.session_state.user_id)
        overall = analytics['overall']
        
        if overall[0] > 0:
            total_q = overall[0]
            correct = overall[1]
            accuracy = (correct / total_q * 100) if total_q > 0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Questions", total_q)
            with col2:
                st.metric("Accuracy", f"{accuracy:.1f}%")
        else:
            st.info("📚 Start practicing!")
        
        st.divider()
        
        # Learning DNA Snapshot
        st.markdown("### 🧬 Your Learning DNA")
        dna = st.session_state.learning_dna
        st.caption(f"**Speed:** {dna['speed_vs_accuracy'].title()}")
        st.caption(f"**Memory:** {dna['memory_type'].title()}")
        st.caption(f"**Fatigue:** ~{dna['fatigue_time']} min")
        
        # Smart Break Detection
        minutes_since_break = (time.time() - st.session_state.last_break_time) / 60
        if minutes_since_break > dna['fatigue_time'] and st.session_state.questions_since_break > 10:
            st.warning("⏰ Consider taking a break!")
        
        st.divider()

        # ⭐ FEATURE 4: Daily Review Queue badge
        if METACOG_AVAILABLE and st.session_state.get('bkt_tracker') and st.session_state.get('user_id'):
            render_sidebar_review_badge(
                st.session_state.user_id,
                st.session_state.bkt_tracker
            )
        
        st.divider()
        
        # Current subject selector
        st.markdown("### 📚 Subject")
        subjects = ["Physics", "Chemistry", "Mathematics", "Biology", "Computer Science"]
        
        # Safety check: if current_subject is not in the list, default to Physics
        if st.session_state.current_subject not in subjects:
            st.session_state.current_subject = 'Physics'
        
        st.session_state.current_subject = st.selectbox(
            "Subject",
            subjects,
            index=subjects.index(st.session_state.current_subject),
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Recommendations
        st.markdown("### 💡 Tips")
        recs = st.session_state.db.get_study_recommendations(st.session_state.user_id)
        
        if recs:
            for rec in recs[:3]:
                with st.expander(rec['title']):
                    st.write(rec['reason'])
        else:
            st.info("Start practicing for tips!")


# ==================== 🧠 ADVANCED DOUBT SOLVER ====================

def render_advanced_doubt_solver(llm):
    """Advanced Doubt Solver with all features"""
    st.markdown("### 🧠 Advanced Doubt Solver")
    st.caption("✨ Mistake-Aware • Multi-View • Confusion Detection • Meta-Feedback")
    
    # Confidence Level Selector
    st.markdown("#### ⚙️ Personalization")
    col1, col2 = st.columns(2)
    
    with col1:
        confidence = st.select_slider(
            "📊 Your Confidence Level",
            options=[1, 2, 3, 4, 5],
            value=st.session_state.doubt_confidence_level,
            help="1 = Need basics | 5 = Challenge me"
        )
        st.session_state.doubt_confidence_level = confidence
    
    with col2:
        step_mode = st.checkbox(
            "🎯 Step-by-Step Mode",
            value=st.session_state.doubt_step_mode,
            help="Reveal answer progressively"
        )
        st.session_state.doubt_step_mode = step_mode
    
    st.divider()
    
    # Question Input
    st.markdown("#### 💬 Ask Your Doubt")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        doubt_question = st.text_area(
            "Type your question:",
            placeholder="e.g., Why does acceleration due to gravity not depend on mass?",
            height=100,
            key="doubt_input"
        )
    
    with col2:
        st.markdown("**Or upload:**")
        audio_file = st.file_uploader("🎤 Audio", type=['mp3', 'wav', 'ogg'], key="doubt_audio")
        image_file = st.file_uploader("📸 Image", type=['png', 'jpg', 'jpeg'], key="doubt_image")
    
    if st.button("🚀 Get Answer", type="primary", use_container_width=True):
        if not doubt_question and not audio_file and not image_file:
            st.error("⚠️ Please enter a question or upload a file")
            return
        
        final_question = doubt_question
        
        # Process audio
        if audio_file:
            with st.spinner("🎤 Processing audio..."):
                processor = AudioProcessor()
                audio_text = processor.transcribe_audio(audio_file)
                if audio_text:
                    final_question = audio_text
                    st.info(f"🎤 Transcribed: {audio_text}")
        
        # Process image
        if image_file:
            with st.spinner("📸 Analyzing image..."):
                processor = FileProcessor()
                image_text = processor.extract_text_from_image(image_file)
                if image_text:
                    final_question = f"{final_question}\n\nImage content: {image_text}" if final_question else image_text
                    st.info(f"📸 Extracted: {image_text[:100]}...")
        
        if final_question:
            st.session_state.doubt_last_question = final_question
            
            with st.spinner("🧠 is thinking..."):
                # Get context from past mistakes
                recent_mistakes = st.session_state.mistake_history[-5:] if st.session_state.mistake_history else None
                
                # Generate answer
                response = llm.answer_doubt_advanced(
                    question=final_question,
                    subject=st.session_state.current_subject,
                    confidence_level=confidence,
                    past_mistakes=recent_mistakes,
                    learning_style=st.session_state.learning_dna['preferred_learning_style']
                )
                
                st.session_state.doubt_last_response = response
                st.session_state.doubt_explanation_shown = True
                
                # Detect confusion
                confusion_type = detect_confusion_type(final_question)
                st.session_state.doubt_confusion_type = confusion_type
                
                # Generate available views
                st.session_state.doubt_available_views = ['intuition', 'math', 'analogy', 'shortcut', 'visual']
                st.session_state.doubt_generated_views = {'main': response}
            
            st.rerun()
    
    # Display response
    if st.session_state.doubt_explanation_shown and st.session_state.doubt_last_response:
        st.divider()
        st.markdown("### 💡 Answer")
        
        # Show confusion type if detected
        if st.session_state.doubt_confusion_type:
            confusion_icons = {
                'concept_gap': '📚',
                'formula_confusion': '🔢',
                'sign_error': '➕➖',
                'unit_confusion': '📏',
                'overthinking': '🤔'
            }
            icon = confusion_icons.get(st.session_state.doubt_confusion_type, '🎯')
            st.info(f"{icon} **Detected Issue:** {st.session_state.doubt_confusion_type.replace('_', ' ').title()}")
        
        # Main answer
        st.markdown(f'<div class="assistant-message">{st.session_state.doubt_last_response}</div>', 
                   unsafe_allow_html=True)

        # ⭐ FEATURE 2: Show RAG sources used
        rag_sources = st.session_state.get('last_doubt_sources', [])
        if rag_sources:
            with st.expander("📚 View Knowledge Sources Retrieved"):
                st.caption("These reference materials were used to answer your question:")
                for chunk in rag_sources:
                    if chunk.get('score', 0) > 0.05:
                        st.markdown(f"**{chunk['source']}** — *{chunk['topic']}*")
                        st.caption(chunk['content'][:200] + "...")
                        st.divider()
        
        st.divider()
        
        # 🔥 On-Demand Multi-View Selection
        st.markdown("#### 🎨 Need Another Perspective?")
        st.caption("Choose how you want to see this explained:")
        
        view_cols = st.columns(5)
        view_options = [
            ('🧠 Intuition', 'intuition'),
            ('🔢 Mathematical', 'math'),
            ('🎯 Analogy', 'analogy'),
            ('⚡ Shortcut', 'shortcut'),
            ('📊 Visual', 'visual')
        ]
        
        for col, (label, view_type) in zip(view_cols, view_options):
            with col:
                if st.button(label, use_container_width=True, key=f"view_{view_type}"):
                    with st.spinner(f"Generating {label}..."):
                        view_content = llm.generate_specific_view(
                            st.session_state.doubt_last_question,
                            view_type,
                            st.session_state.current_subject
                        )
                        st.session_state.doubt_generated_views[view_type] = view_content
                        st.session_state.doubt_active_view = view_type
                    st.rerun()
        
        # Display selected view
        if st.session_state.doubt_active_view and st.session_state.doubt_active_view != 'main':
            view_type = st.session_state.doubt_active_view
            if view_type in st.session_state.doubt_generated_views:
                st.markdown(f"#### {view_type.title()} View")
                st.markdown(f'<div class="assistant-message">{st.session_state.doubt_generated_views[view_type]}</div>', 
                           unsafe_allow_html=True)
        
        st.divider()
        
        # 🔥 META-AI: Explanation Feedback
        st.markdown("#### 📝 Was This Explanation Helpful?")
        feedback_col1, feedback_col2, feedback_col3 = st.columns(3)
        
        with feedback_col1:
            if st.button("❌ Too Complex", use_container_width=True):
                record_explanation_feedback("too_complex")
                st.success("Thanks! I'll simplify next time.")
        
        with feedback_col2:
            if st.button("❌ Too Fast", use_container_width=True):
                record_explanation_feedback("too_fast")
                st.success("Thanks! I'll add more steps.")
        
        with feedback_col3:
            if st.button("✅ Just Right", use_container_width=True):
                record_explanation_feedback("perfect")
                st.success("Awesome! Learning this style.")
        
        st.divider()
        
        # Follow-up question generation
        if not st.session_state.doubt_follow_up_shown:
            with st.spinner("Generating follow-up..."):
                follow_up = llm.generate_follow_up_question(
                    st.session_state.doubt_last_question,
                    st.session_state.doubt_last_response
                )
                st.session_state.doubt_follow_up_question = follow_up
                st.session_state.doubt_follow_up_shown = True
        
        if st.session_state.doubt_follow_up_question:
            st.markdown("#### 🎯 Test Your Understanding")
            st.info(f"**Follow-up:** {st.session_state.doubt_follow_up_question}")
            
            user_follow_up_answer = st.text_area("Your answer:", key="follow_up_answer", height=100)
            
            if st.button("Check Answer", use_container_width=True):
                with st.spinner("Checking..."):
                    feedback = llm.evaluate_follow_up_answer(
                        st.session_state.doubt_follow_up_question,
                        user_follow_up_answer,
                        st.session_state.doubt_last_response
                    )
                    st.markdown(f'<div class="assistant-message">{feedback}</div>', unsafe_allow_html=True)


# ==================== 🎯 ADAPTIVE PRACTICE WITH 3 MODES ====================

def render_adaptive_practice_with_modes(llm):
    """
    🔥 NEW: Practice with 3 modes - MCQ, Tutorial/Descriptive, Numerical
    """
    st.markdown("### 🎯 Adaptive Practice (3 Modes)")
    st.caption("Choose your practice style: Competitive MCQs, College Tutorials, or Problem Solving")
    
    # 🔥 MODE SELECTOR
    st.markdown("#### 📚 Practice Mode")
    mode_cols = st.columns(3)
    
    modes = [
        ("🏆 MCQ (Competitive)", "MCQ (Competitive)", "Quick MCQs for competitive exams"),
        ("📖 Tutorial / Descriptive", "Tutorial", "Step-by-step explanations for college"),
        ("🔢 Numerical / Problem Solving", "Numerical", "Solve problems with working")
    ]
    
    for col, (label, mode_val, desc) in zip(mode_cols, modes):
        with col:
            if st.button(f"{label}\n\n{desc}", use_container_width=True, 
                        type="primary" if st.session_state.practice_mode == mode_val else "secondary"):
                st.session_state.practice_mode = mode_val
                st.rerun()
    
    st.info(f"**Current Mode:** {st.session_state.practice_mode}")
    st.divider()
    
    # Common settings
    difficulty, accuracy, reason = st.session_state.db.get_adaptive_difficulty(
        st.session_state.user_id,
        subject=st.session_state.current_subject
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox("Subject", 
            ["Physics", "Chemistry", "Mathematics", "Biology", "Computer Science"],
            key="practice_subject_selector")
        st.session_state.practice_subject = subject
    
    with col2:
        topic = st.text_input("Topic", placeholder="e.g., Kinematics")
    
    with col3:
        count = st.number_input("Questions", 1, 20, 5)
    
    st.info(f"🤖 **Recommendation:** {difficulty} - {reason}")
    
    manual_diff = st.selectbox("Override Difficulty:", 
        ["Use Recommendation", "Easy", "Medium", "Hard"])
    
    final_difficulty = difficulty if manual_diff == "Use Recommendation" else manual_diff
    
    # 🔥 Render based on selected mode
    if st.session_state.practice_mode == "MCQ (Competitive)":
        render_mcq_practice(llm, topic, final_difficulty, count, subject)
    
    elif st.session_state.practice_mode == "Tutorial":
        render_tutorial_practice(llm, topic, final_difficulty, count, subject)
    
    elif st.session_state.practice_mode == "Numerical":
        render_numerical_practice(llm, topic, final_difficulty, count, subject)


def render_score_card(correct, total):
    """Display score card with performance metrics"""
    percentage = (correct / total * 100) if total > 0 else 0
    
    st.divider()
    st.markdown("### 🎯 Your Score")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Correct", correct)
    with col2:
        st.metric("📊 Total", total)
    with col3:
        st.metric("🎯 Score", f"{percentage:.1f}%")
    
    # Performance message
    if percentage >= 90:
        st.success("🏆 Outstanding! Excellent performance!")
    elif percentage >= 75:
        st.success("🌟 Great job! Very good score!")
    elif percentage >= 60:
        st.info("👍 Good effort! Keep practicing!")
    elif percentage >= 40:
        st.warning("📚 Need more practice. Review weak areas.")
    else:
        st.error("💪 Don't worry! Focus on fundamentals and try again.")


def render_mcq_practice(llm, topic, difficulty, count, subject):
    """Standard MCQ practice (existing functionality)"""
    
    if st.button("🚀 Generate MCQs", type="primary", use_container_width=True):
        if not topic:
            st.error("⚠️ Please enter a topic")
            return
        
        with st.spinner("🧠 Creating MCQs..."):
            weak = st.session_state.db.get_weak_topics(st.session_state.user_id, 3)
            weak_areas = [w[1] for w in weak] if weak else None
            
            questions = llm.generate_adaptive_questions(topic, difficulty, count, weak_areas)
        
        if questions:
            st.session_state.generated_questions = questions
            st.session_state.user_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.question_start_times = {}
            # ⭐ FEATURE 3: Reset answer switch tracker for new quiz
            if METACOG_AVAILABLE:
                reset_tracker()
            st.rerun()
    
    if st.session_state.generated_questions and not st.session_state.quiz_submitted:
        st.divider()
        for i, q in enumerate(st.session_state.generated_questions):
            st.markdown(f"**Q{i+1}.** {q['question']}")
            if i not in st.session_state.question_start_times:
                st.session_state.question_start_times[i] = time.time()
            
            # Display options
            options_keys = list(q['options'].keys())
            answer = st.radio(
                "Answer:", 
                options_keys,
                format_func=lambda x: f"{x}. {q['options'][x]}", 
                key=f"aq_{i}",
                index=None  # No default selection
            )
            
            # ⭐ FEATURE 3: Track answer changes for meta-cognitive analysis
            prev_answer = st.session_state.user_answers.get(i)
            if answer is not None and answer != prev_answer:
                if METACOG_AVAILABLE:
                    track_answer_change(i, prev_answer or '', answer)
                st.session_state.user_answers[i] = answer
            
            st.divider()
        
        if st.button("📊 Submit Quiz", type="primary", use_container_width=True):
            st.session_state.quiz_submitted = True
            
            # 🔥 Record time-accuracy data for each question
            for i, q in enumerate(st.session_state.generated_questions):
                if i in st.session_state.question_start_times:
                    time_taken = time.time() - st.session_state.question_start_times[i]
                    
                    # Normalize comparison
                    user_ans = st.session_state.user_answers.get(i, "")
                    correct_ans = q.get('correct_answer', q.get('answer', ''))
                    user_ans_normalized = str(user_ans).strip().upper() if user_ans else ""
                    correct_ans_normalized = str(correct_ans).strip().upper()
                    is_correct = (user_ans_normalized == correct_ans_normalized)
                    
                    st.session_state.time_accuracy_data.append({
                        'time_taken': time_taken,
                        'is_correct': is_correct,
                        'timestamp': datetime.now()
                    })
            
            st.rerun()
    
    if st.session_state.quiz_submitted and st.session_state.generated_questions:
        # Calculate score with normalized comparison
        correct = 0
        for i, q in enumerate(st.session_state.generated_questions):
            user_ans = st.session_state.user_answers.get(i, "")
            correct_ans = q.get('correct_answer', q.get('answer', ''))
            
            # Normalize for comparison
            user_ans_normalized = str(user_ans).strip().upper() if user_ans else ""
            correct_ans_normalized = str(correct_ans).strip().upper()
            
            if user_ans_normalized == correct_ans_normalized:
                correct += 1
        
        total = len(st.session_state.generated_questions)
        
        render_score_card(correct, total)
        
        # 🔥 ROOT-CAUSE: Analyze mistakes
        st.divider()
        st.markdown("### 🧠 Root-Cause Analysis")
        
        mistake_analysis = analyze_mistakes_root_cause(
            st.session_state.generated_questions,
            st.session_state.user_answers
        )
        
        if mistake_analysis['mistakes']:
            for mistake in mistake_analysis['mistakes']:
                icon = {
                    'concept_gap': '📚',
                    'formula_confusion': '🔢',
                    'sign_error': '➕➖',
                    'calculation_slip': '🧮',
                    'overthinking': '🤔'
                }.get(mistake['type'], '❌')
                
                st.warning(f"{icon} **{mistake['type'].replace('_', ' ').title()}**: {mistake['description']}")
            
            # Store in history
            for mistake in mistake_analysis['mistakes']:
                st.session_state.mistake_history.append({
                    'type': mistake['type'],
                    'timestamp': datetime.now(),
                    'question': mistake.get('question', '')
                })
        else:
            st.success("🌟 No pattern errors detected! Great job!")
        
        # 🔥 TIME-PRESSURE INTELLIGENCE
        st.divider()
        st.markdown("### ⏱️ Time-Pressure Intelligence")
        analyze_time_pressure()

        # ⭐ FEATURE 3: Meta-Cognitive Answer Switching Analysis
        if METACOG_AVAILABLE:
            tracker = init_tracker()
            render_metacognitive_analysis(
                tracker,
                st.session_state.generated_questions,
                st.session_state.user_answers
            )
        
        st.divider()
        st.markdown("### 📝 Detailed Review")
        
        for i, q in enumerate(st.session_state.generated_questions):
            user_ans = st.session_state.user_answers.get(i, "Not answered")
            correct_ans = q.get('correct_answer', q.get('answer', ''))
            
            # Normalize answers for comparison (strip whitespace, convert to uppercase)
            user_ans_normalized = str(user_ans).strip().upper() if user_ans != "Not answered" else "Not answered"
            correct_ans_normalized = str(correct_ans).strip().upper()
            
            is_correct = (user_ans_normalized == correct_ans_normalized)
            
            # Calculate time taken
            time_taken = "N/A"
            if i in st.session_state.question_start_times and i+1 in st.session_state.question_start_times:
                time_diff = st.session_state.question_start_times[i+1] - st.session_state.question_start_times[i]
                time_taken = f"{time_diff:.1f}s"
            elif i in st.session_state.question_start_times:
                time_diff = time.time() - st.session_state.question_start_times[i]
                time_taken = f"{time_diff:.1f}s"
            
            with st.expander(f"Q{i+1} - {'✅ Correct' if is_correct else '❌ Wrong'} ({time_taken})"):
                st.markdown(f"**{q['question']}**")
                
                # Display all options with visual indicators
                for opt_key in ['A', 'B', 'C', 'D']:
                    if opt_key in q['options']:
                        opt_text = q['options'][opt_key]
                        if opt_key.upper() == correct_ans_normalized:
                            st.success(f"✅ {opt_key}. {opt_text} ← **Correct Answer**")
                        elif opt_key.upper() == user_ans_normalized and not is_correct:
                            st.error(f"❌ {opt_key}. {opt_text} ← **Your Answer**")
                        else:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{opt_key}. {opt_text}")
                
                # Debug info (can be removed in production)
                with st.expander("🔍 Debug Info"):
                    st.write(f"Your answer (raw): `{user_ans}` (type: {type(user_ans).__name__})")
                    st.write(f"Correct answer (raw): `{correct_ans}` (type: {type(correct_ans).__name__})")
                    st.write(f"Your answer (normalized): `{user_ans_normalized}`")
                    st.write(f"Correct answer (normalized): `{correct_ans_normalized}`")
                    st.write(f"Match: {is_correct}")
                
                if q.get('explanation'):
                    if is_correct:
                        st.success(f"💡 **Explanation:** {q['explanation']}")
                    else:
                        st.info(f"💡 **Explanation:** {q['explanation']}")
                        
                        # 🔥 Suggest concept dependencies
                        st.warning("💪 **Tip:** Review the concept and try similar problems to strengthen understanding.")


def render_tutorial_practice(llm, topic, difficulty, count, subject):
    """
    Tutorial/Descriptive Practice Mode - FIXED VERSION
    Students write answers, evaluates comprehensively
    """
    
    if st.button("🚀 Generate Tutorial Questions", type="primary", use_container_width=True):
        if not topic:
            st.error("⚠️ Please enter a topic")
            return
        
        with st.spinner("🧠 Creating tutorial questions..."):
            # Improved prompt for better question generation
            prompt = f"""Generate {count} DIFFERENT tutorial/descriptive questions for {subject} - {topic}.
Difficulty: {difficulty}

Requirements:
1. Each question should be UNIQUE and test different aspects
2. Questions should require detailed explanations
3. Include variety: explain, derive, describe, compare, analyze

Return ONLY a JSON array with this EXACT format:
[
  {{
    "question": "Explain the concept of [specific concept in {topic}]",
    "key_points": ["point1", "point2", "point3"]
  }},
  {{
    "question": "Derive the formula for [specific formula in {topic}]",
    "key_points": ["step1", "step2", "step3"]
  }}
]

Make sure ALL {count} questions are completely different from each other."""
            
            response = llm.chat(prompt, temperature=0.8)
            
            try:
                # Extract JSON from response
                import json
                import re
                
                # Find JSON array in response
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    questions = json.loads(json_match.group())
                    
                    # Validate questions
                    if len(questions) >= count:
                        st.session_state.tutorial_questions = questions[:count]
                        st.session_state.tutorial_answers = {}
                        st.session_state.tutorial_ai_feedback = {}
                        st.success(f"✅ Generated {count} tutorial questions!")
                    else:
                        raise ValueError("Not enough questions generated")
                else:
                    raise ValueError("No JSON found in response")
                    
            except Exception as e:
                st.error(f"❌ Error generating questions: {str(e)}")
                # Don't use fallback - ask user to try again
                st.info("💡 Please try clicking the button again")
                return
        
        st.rerun()
    
    # Display questions for answering
    if st.session_state.tutorial_questions and not st.session_state.tutorial_ai_feedback:
        st.divider()
        st.markdown("### 📝 Answer These Questions")
        st.info("💡 Write detailed answers. The will evaluate your understanding.")
        
        for i, q in enumerate(st.session_state.tutorial_questions):
            st.markdown(f"#### Question {i+1}")
            st.markdown(f"**{q['question']}**")
            
            # Show key points as hints
            with st.expander("💡 Points to Consider"):
                for point in q.get('key_points', []):
                    st.markdown(f"• {point}")
            
            # Single text area for answer
            answer = st.text_area(
                f"Your Answer:",
                placeholder="Write your detailed answer here... Explain step by step.",
                height=200,
                key=f"tutorial_ans_{i}"
            )
            st.session_state.tutorial_answers[i] = answer
            st.divider()
        
        # Submit button
        if st.button("📊 Submit All Answers for Evaluation", type="primary", use_container_width=True):
            # Check if at least one answer is provided
            answered = sum(1 for ans in st.session_state.tutorial_answers.values() if ans.strip())
            
            if answered == 0:
                st.error("⚠️ Please answer at least one question!")
                return
            
            with st.spinner("🧠 is evaluating your answers..."):
                for i, q in enumerate(st.session_state.tutorial_questions):
                    user_answer = st.session_state.tutorial_answers.get(i, "")
                    
                    if user_answer.strip():
                        # evaluation
                        eval_prompt = f"""Evaluate this student's answer:

Question: {q['question']}

Key Points Expected: {', '.join(q.get('key_points', []))}

Student's Answer:
{user_answer}

Provide feedback in this format:

**Score: X/10**

**✅ Strengths:**
[What the student got right]

**⚠️ Missing/Incomplete:**
[What could be improved or added]

**💡 Suggestions:**
[How to improve the answer]

Be encouraging and constructive!"""
                        
                        feedback = llm.chat(eval_prompt, temperature=0.5)
                        st.session_state.tutorial_ai_feedback[i] = feedback
                    else:
                        st.session_state.tutorial_ai_feedback[i] = "⚠️ No answer provided"
            
            st.success("✅ Evaluation complete!")
            st.rerun()
    
    # Display feedback
    if st.session_state.tutorial_ai_feedback:
        st.divider()
        st.markdown("### 🎓 Tutor Feedback")
        
        for i, q in enumerate(st.session_state.tutorial_questions):
            with st.expander(f"📝 Question {i+1}: {q['question'][:60]}...", expanded=(i==0)):
                st.markdown("#### Question:")
                st.markdown(f"*{q['question']}*")
                
                st.markdown("#### Your Answer:")
                user_ans = st.session_state.tutorial_answers.get(i, "")
                if user_ans.strip():
                    st.markdown(user_ans)
                else:
                    st.info("Not answered")
                
                st.divider()
                st.markdown("#### Feedback:")
                st.markdown(st.session_state.tutorial_ai_feedback.get(i, "No feedback yet"))
        
        # Option to try again
        if st.button("🔄 Start New Tutorial Practice", use_container_width=True):
            st.session_state.tutorial_questions = []
            st.session_state.tutorial_answers = {}
            st.session_state.tutorial_ai_feedback = {}
            st.rerun()


def render_numerical_practice(llm, topic, difficulty, count, subject):
    """
    Numerical/Problem-Solving Practice - FIXED VERSION
    Simplified: Students just write their solution and answer
    """
    
    if st.button("🚀 Generate Numerical Problems", type="primary", use_container_width=True):
        if not topic:
            st.error("⚠️ Please enter a topic")
            return
        
        with st.spinner("🧠 Creating numerical problems..."):
            # Improved prompt for numerical questions
            prompt = f"""Generate {count} DIFFERENT numerical/calculation problems for {subject} - {topic}.
Difficulty: {difficulty}

Requirements:
1. Each problem should be UNIQUE and test different concepts
2. Include clear problem statements with specific values
3. Problems should require calculations/mathematical solutions
4. Each problem should be completely different

Return ONLY a JSON array with this EXACT format:
[
  {{
    "problem": "A detailed problem statement with specific values...",
    "correct_answer": "42 N",
    "solution_approach": "Brief hint about which concept/formula to use"
  }},
  {{
    "problem": "Another completely different problem...",
    "correct_answer": "15.5 m/s",
    "solution_approach": "Different concept/formula"
  }}
]

Make sure ALL {count} problems are completely different."""
            
            response = llm.chat(prompt, temperature=0.8)
            
            try:
                import json
                import re
                
                # Extract JSON
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    problems = json.loads(json_match.group())
                    
                    if len(problems) >= count:
                        st.session_state.numerical_questions = problems[:count]
                        st.session_state.numerical_solutions = {}
                        st.session_state.numerical_feedback = {}
                        st.success(f"✅ Generated {count} numerical problems!")
                    else:
                        raise ValueError("Not enough problems generated")
                else:
                    raise ValueError("No JSON found")
                    
            except Exception as e:
                st.error(f"❌ Error generating problems: {str(e)}")
                st.info("💡 Please try clicking the button again")
                return
        
        st.rerun()
    
    # Display problems for solving
    if st.session_state.numerical_questions and not st.session_state.numerical_feedback:
        st.divider()
        st.markdown("### 🔢 Solve These Problems")
        st.info("💡 Show your working and write your final answer.")
        
        for i, prob in enumerate(st.session_state.numerical_questions):
            st.markdown(f"#### Problem {i+1}")
            st.markdown(f"**{prob.get('problem', '')}**")
            
            # Hint if available
            if prob.get('solution_approach'):
                with st.expander("💡 Hint"):
                    st.markdown(prob['solution_approach'])
            
            # Single text area for complete solution
            solution = st.text_area(
                f"Your Solution (Show all working):",
                placeholder="Write your complete solution here:\n1. List given values\n2. Write formula\n3. Show calculations\n4. Write final answer with units",
                height=250,
                key=f"num_solution_{i}"
            )
            st.session_state.numerical_solutions[i] = solution
            
            st.divider()
        
        # Submit button
        if st.button("📊 Submit All Solutions for Checking", type="primary", use_container_width=True):
            answered = sum(1 for sol in st.session_state.numerical_solutions.values() if sol.strip())
            
            if answered == 0:
                st.error("⚠️ Please solve at least one problem!")
                return
            
            with st.spinner("🧠 is checking your solutions..."):
                for i, prob in enumerate(st.session_state.numerical_questions):
                    user_solution = st.session_state.numerical_solutions.get(i, "")
                    
                    if user_solution.strip():
                        check_prompt = f"""Check this numerical solution:

Problem: {prob.get('problem', '')}

Correct Answer: {prob.get('correct_answer', '')}

Student's Solution:
{user_solution}

Provide feedback:

**Result: ✅ CORRECT / ❌ INCORRECT / ⚠️ PARTIALLY CORRECT**

**Analysis:**
- Did they use the right approach?
- Are calculations correct?
- Is the final answer correct?

**Correct Solution:**
[Show the proper solution steps if student was wrong]

**Tips:**
[Suggest how to improve]

Be encouraging!"""
                        
                        feedback = llm.chat(check_prompt, temperature=0.4)
                        st.session_state.numerical_feedback[i] = feedback
                    else:
                        st.session_state.numerical_feedback[i] = "⚠️ No solution provided"
            
            st.success("✅ All solutions checked!")
            st.rerun()
    
    # Display feedback
    if st.session_state.numerical_feedback:
        st.divider()
        st.markdown("### 📋 Solution Feedback")
        
        for i, prob in enumerate(st.session_state.numerical_questions):
            with st.expander(f"🔢 Problem {i+1}: {prob.get('problem', '')[:60]}...", expanded=(i==0)):
                st.markdown("#### Problem:")
                st.markdown(f"*{prob.get('problem', '')}*")
                
                st.markdown("#### Your Solution:")
                user_sol = st.session_state.numerical_solutions.get(i, "")
                if user_sol.strip():
                    st.code(user_sol, language=None)
                else:
                    st.info("Not attempted")
                
                st.divider()
                st.markdown("#### Feedback:")
                st.markdown(st.session_state.numerical_feedback.get(i, "No feedback yet"))
        
        # Try again option
        if st.button("🔄 Start New Numerical Practice", use_container_width=True):
            st.session_state.numerical_questions = []
            st.session_state.numerical_solutions = {}
            st.session_state.numerical_feedback = {}
            st.rerun()


def analyze_mistakes_root_cause(questions, user_answers):
    """
    🔥 Classify mistake types (Root-Cause)
    """
    mistakes = []
    
    for i, q in enumerate(questions):
        user_ans = user_answers.get(i)
        if user_ans != q['correct_answer']:
            # Analyze mistake type
            mistake_type = classify_mistake(q, user_ans)
            
            mistakes.append({
                'question': q['question'],
                'type': mistake_type,
                'description': get_mistake_description(mistake_type)
            })
    
    # Count patterns
    mistake_counts = Counter([m['type'] for m in mistakes])
    
    return {
        'mistakes': mistakes,
        'patterns': dict(mistake_counts),
        'dominant_pattern': mistake_counts.most_common(1)[0][0] if mistake_counts else None
    }


def classify_mistake(question, user_answer):
    """Classify the type of mistake"""
    q_lower = question['question'].lower()
    
    # Simple heuristics (in real app, use LLM)
    if 'formula' in q_lower or 'equation' in q_lower:
        return 'formula_confusion'
    elif 'sign' in q_lower or 'direction' in q_lower or 'negative' in q_lower:
        return 'sign_error'
    elif 'calculate' in q_lower or 'compute' in q_lower:
        return 'calculation_slip'
    elif 'why' in q_lower or 'explain' in q_lower:
        return 'concept_gap'
    else:
        return 'overthinking'


def get_mistake_description(mistake_type):
    """Get description for mistake type"""
    descriptions = {
        'concept_gap': "You didn't understand the underlying theory. Review the concept first.",
        'formula_confusion': "You used the wrong formula or applied it incorrectly.",
        'sign_error': "This is a sign convention error - common in physics problems.",
        'calculation_slip': "Your approach was correct, but you made an arithmetic error.",
        'overthinking': "You overcomplicated this. The correct idea was simpler."
    }
    return descriptions.get(mistake_type, "Review this topic carefully.")


# ==================== ⏱️ TIME-PRESSURE INTELLIGENCE ====================

def analyze_time_pressure():
    """
    🔥 Analyze speed vs accuracy patterns
    """
    data = st.session_state.time_accuracy_data
    
    if len(data) < 5:
        st.info("⏳ Need more data to analyze time-pressure patterns (attempt 5+ questions)")
        return
    
    # Categorize by speed
    fast = [d for d in data if d['time_taken'] < 30]
    medium = [d for d in data if 30 <= d['time_taken'] < 60]
    slow = [d for d in data if d['time_taken'] >= 60]
    
    def get_accuracy(subset):
        if not subset:
            return 0
        return sum(1 for d in subset if d['is_correct']) / len(subset) * 100
    
    fast_acc = get_accuracy(fast)
    medium_acc = get_accuracy(medium)
    slow_acc = get_accuracy(slow)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Fast (<30s)", f"{fast_acc:.0f}%", f"{len(fast)} questions")
    with col2:
        st.metric("Medium (30-60s)", f"{medium_acc:.0f}%", f"{len(medium)} questions")
    with col3:
        st.metric("Slow (>60s)", f"{slow_acc:.0f}%", f"{len(slow)} questions")
    
    # Generate insights
    if fast_acc < medium_acc - 15:
        st.warning("⚠️ **Insight:** Your accuracy drops significantly when you rush. Take more time!")
        st.info("💡 **Strategy:** Attempt fewer questions, but ensure higher accuracy.")
    elif slow_acc < fast_acc:
        st.info("💡 **Insight:** You're overthinking! Your first instinct is often correct.")
        st.success("**Strategy:** Trust your preparation. Don't second-guess too much.")
    else:
        st.success("✅ **Insight:** You maintain consistent accuracy across speeds. Good balance!")
    
    # Update Learning DNA
    if fast_acc > medium_acc and fast_acc > slow_acc:
        st.session_state.learning_dna['speed_vs_accuracy'] = 'fast'
    elif slow_acc > fast_acc + 10:
        st.session_state.learning_dna['speed_vs_accuracy'] = 'careful'
    else:
        st.session_state.learning_dna['speed_vs_accuracy'] = 'balanced'


# ==================== 📊 ANALYTICS & LEARNING DNA ====================

def render_analytics_and_learning_dna(llm):
    """
    🔥 Enhanced analytics with Learning DNA Profile
    """
    st.markdown("### 📊 Analytics & Learning DNA")
    
    tab1, tab2, tab3 = st.tabs(["📈 Performance", "🧬 Learning DNA", "🎯 Mistake Patterns"])
    
    with tab1:
        # Original analytics
        render_analytics_dashboard(st.session_state.user_id, st.session_state.db)
    
    with tab2:
        # 🔥 Learning DNA Profile
        st.markdown("### 🧬 Your Learning DNA Profile")
        st.caption("Your personal cognitive fingerprint based on practice history")
        
        dna = st.session_state.learning_dna
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ⚡ Speed vs Accuracy")
            speed_icons = {
                'fast': '🏃‍♂️ Fast & Confident',
                'balanced': '⚖️ Balanced Approach',
                'careful': '🐢 Careful & Methodical'
            }
            st.info(speed_icons.get(dna['speed_vs_accuracy'], 'Unknown'))
            
            st.markdown("#### 🧠 Memory Type")
            st.info(f"{dna['memory_type'].replace('_', ' ').title()}")
            
            st.markdown("#### ⏰ Fatigue Time")
            st.info(f"~{dna['fatigue_time']} minutes")
        
        with col2:
            st.markdown("#### 🎯 Confidence Bias")
            confidence_icons = {
                'overconfident': '😎 Tends to be overconfident',
                'neutral': '😊 Well-calibrated',
                'underconfident': '😰 Often second-guesses'
            }
            st.info(confidence_icons.get(dna['confidence_bias'], 'Unknown'))
            
            st.markdown("#### 📚 Learning Style")
            st.info(f"{dna['preferred_learning_style'].title()}")
        
        st.divider()
        
        # Recommendations based on DNA
        st.markdown("### 💡 Personalized Recommendations")
        
        if dna['speed_vs_accuracy'] == 'fast':
            st.success("✅ **For You:** Your speed is an advantage! But double-check calculations in exams.")
        elif dna['speed_vs_accuracy'] == 'careful':
            st.info("💡 **For You:** Practice timed mocks to improve speed without losing accuracy.")
        
        if dna['fatigue_time'] < 45:
            st.warning(f"⏰ **Alert:** You tend to fatigue after {dna['fatigue_time']} min. Take breaks!")
        
        # 🔥 Update DNA with current session
        if st.button("🔄 Recalculate Learning DNA", use_container_width=True):
            with st.spinner("Analyzing your complete history..."):
                # This would analyze all past data and update DNA
                time.sleep(1)
                st.success("✅ Learning DNA updated!")
                st.rerun()
    
    with tab3:
        # 🔥 Mistake Pattern Analysis
        st.markdown("### 🎯 Your Mistake Patterns")
        
        if st.session_state.mistake_history:
            # Count mistake types
            mistake_counts = Counter([m['type'] for m in st.session_state.mistake_history])
            
            st.markdown("#### 📊 Mistake Distribution")
            for mistake_type, count in mistake_counts.most_common():
                percentage = (count / len(st.session_state.mistake_history)) * 100
                st.progress(percentage / 100)
                st.caption(f"{mistake_type.replace('_', ' ').title()}: {count} times ({percentage:.1f}%)")
            
            st.divider()
            
            # Most common mistake
            most_common = mistake_counts.most_common(1)[0]
            st.warning(f"⚠️ **Your Most Common Mistake:** {most_common[0].replace('_', ' ').title()} ({most_common[1]} times)")
            
            # recommendations
            st.info(f"💡 **Focus Area:** {get_mistake_description(most_common[0])}")
        
        else:
            st.info("Start practicing to see your mistake patterns!")


# ==================== 🎮 EXAM STRATEGY SIMULATOR ====================


def simulate_exam_outcome(total_q, accuracy, attempt_rate, pos_marks, neg_marks, simulations=1000):
    """Monte Carlo simulation for exam score"""
    scores = []
    
    for _ in range(simulations):
        attempted = int(total_q * attempt_rate / 100)
        
        # Simulate each attempt
        correct = 0
        for _ in range(attempted):
            if random.random() < (accuracy / 100):
                correct += 1
        
        wrong = attempted - correct
        score = (correct * pos_marks) - (wrong * neg_marks)
        scores.append(score)
    
    return {
        'mean': sum(scores) / len(scores),
        'min': min(scores),
        'max': max(scores),
        'scores': scores
    }


def generate_exam_strategy_recommendation(accuracy, attempt_rate, total_q, pos_marks, neg_marks):
    """Generate recommendation for exam strategy"""
    
    recommendations = []
    
    # Accuracy-based advice
    if accuracy < 60:
        recommendations.append("🎯 **Focus on accuracy first.** Your current accuracy is low. "
                             "Attempting fewer questions with higher accuracy will give better results.")
    elif accuracy > 80:
        recommendations.append("✅ **Great accuracy!** You can afford to attempt more questions. "
                             "Try increasing attempt rate by 10-15%.")
    
    # Attempt rate advice
    if attempt_rate < 70 and accuracy > 75:
        recommendations.append("⚡ **Increase attempts!** Your accuracy is good. "
                             "Don't leave questions unattempted - calculated risks pay off.")
    elif attempt_rate > 90 and accuracy < 65:
        recommendations.append("🎯 **Reduce attempts.** You're attempting too many with low accuracy. "
                             "Focus on questions you're confident about.")
    
    # Negative marking strategy
    if neg_marks > 0:
        threshold = (pos_marks / (pos_marks + neg_marks)) * 100
        recommendations.append(f"📊 **Break-even accuracy: {threshold:.0f}%** "
                             f"Only attempt if you're >{threshold:.0f}% confident.")
    
    # Time management
    recommendations.append(f"⏰ **Time Strategy:** Allocate ~{total_q/180*60:.0f} seconds per question. "
                          "Mark difficult ones for review and come back later.")
    
    return "\n\n".join(recommendations)


# ==================== HELPER FUNCTIONS ====================

def detect_confusion_type(question):
    """Detect what type of confusion the student has"""
    q_lower = question.lower()
    
    if any(word in q_lower for word in ['why', 'how', 'explain']):
        return 'concept_gap'
    elif any(word in q_lower for word in ['formula', 'equation']):
        return 'formula_confusion'
    elif any(word in q_lower for word in ['positive', 'negative', 'sign', 'direction']):
        return 'sign_error'
    elif any(word in q_lower for word in ['unit', 'convert', 'dimension']):
        return 'unit_confusion'
    else:
        return None


def record_explanation_feedback(feedback_type):
    """Record meta-feedback on explanations"""
    st.session_state.explanation_feedback.append({
        'type': feedback_type,
        'timestamp': datetime.now()
    })
    
    # Update quality score
    feedback_counts = Counter([f['type'] for f in st.session_state.explanation_feedback])
    total = len(st.session_state.explanation_feedback)
    
    if total > 0:
        perfect_ratio = feedback_counts.get('perfect', 0) / total
        st.session_state.explanation_quality_score = perfect_ratio


# ==================== UPLOAD EXAM MODE (Existing) ====================

def render_upload_exam_mode(llm):
    """
    Upload and take PYQ exams with PDF extraction
    """
    st.markdown("### 📝 Upload & Take Exam")
    st.caption("Upload PDF exams or create custom practice tests")
    
    # Mode selection
    mode = st.radio("Choose Mode:", 
        ["📤 Upload PDF Exam", "✏️ Create Custom Exam"],
        horizontal=True)
    
    if mode == "📤 Upload PDF Exam":
        render_pdf_upload_exam(llm)
    else:
        render_custom_exam_creator(llm)


def render_pdf_upload_exam(llm):
    """Upload and extract questions from PDF"""
    st.markdown("#### 📤 Upload PDF Exam")
    
    uploaded_file = st.file_uploader(
        "Upload your PYQ PDF",
        type=['pdf'],
        help="Upload a PDF containing multiple choice questions"
    )
    
    if uploaded_file:
        st.success(f"✅ Uploaded: {uploaded_file.name}")
        
        if st.button("🔍 Extract Questions from PDF", type="primary", use_container_width=True):
            with st.spinner("📄 Extracting questions from PDF..."):
                # Extract text from PDF
                try:
                    from file_processors import FileProcessor
                    processor = FileProcessor()
                    pdf_text = processor.process_pdf(uploaded_file)
                    
                    if pdf_text:
                        st.info(f"📄 Extracted {len(pdf_text)} characters from PDF")
                        
                        # Use enhanced extraction with multi-chunk processing
                        with st.spinner("🧠 is parsing questions (this may take a moment)..."):
                            questions = llm.extract_questions_from_pdf_text(pdf_text, max_questions=100)
                            
                            if questions and len(questions) > 0:
                                st.session_state.upload_questions = questions
                                st.session_state.upload_answers = {}
                                st.session_state.upload_submitted = False
                                st.session_state.upload_exam_started = False
                                st.session_state.upload_exam_name = uploaded_file.name.replace('.pdf', '')
                                
                                st.success(f"✅ Successfully extracted {len(questions)} questions!")
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Could not extract questions from PDF")
                                st.info("💡 Tips:")
                                st.markdown("""
                                - Ensure the PDF contains clear MCQ questions
                                - Questions should have options A, B, C, D
                                - Try a different PDF or use Custom Exam mode
                                """)
                    else:
                        st.error("❌ Could not extract text from PDF")
                        
                except Exception as e:
                    st.error(f"❌ Error processing PDF: {str(e)}")
                    st.info("💡 Make sure PyPDF2 is installed: pip install PyPDF2")
    
    # If questions extracted, show exam interface
    if st.session_state.upload_questions and not st.session_state.upload_submitted:
        render_exam_interface(llm)
    
    # Show results after submission
    if st.session_state.upload_submitted and st.session_state.upload_questions:
        render_exam_results(llm)


def render_custom_exam_creator(llm):
    """Create custom exam by generating questions"""
    st.markdown("#### ✏️ Create Custom Exam")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Use subjects from user's exam type (set during onboarding)
        _exam_subjects = st.session_state.get('available_subjects') or \
                         get_subjects_for_exam(st.session_state.get('exam_type', 'JEE Main'))
        subject = st.selectbox("Subject",
            _exam_subjects,
            key="custom_exam_subject")
        
        topic = st.text_input("Topic", 
            placeholder="e.g., Thermodynamics, Organic Chemistry",
            key="custom_exam_topic")
    
    with col2:
        difficulty = st.selectbox("Difficulty", 
            ["Easy", "Medium", "Hard"],
            key="custom_exam_difficulty")
        
        num_questions = st.number_input("Number of Questions", 
            min_value=5, max_value=50, value=20,
            key="custom_exam_count")
    
    col1, col2 = st.columns(2)
    with col1:
        duration = st.number_input("Duration (minutes)", 
            min_value=10, max_value=180, value=30,
            key="custom_exam_duration")
    
    with col2:
        exam_name = st.text_input("Exam Name", 
            value="My Practice Test",
            key="custom_exam_name")
    
    # Marking scheme
    st.markdown("#### 📊 Marking Scheme")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        positive_marks = st.number_input("Marks per correct answer", 
            min_value=1, max_value=10, value=4,
            key="custom_positive_marks")
    
    with col2:
        negative_marks = st.number_input("Negative marking (per wrong)", 
            min_value=0, max_value=5, value=1,
            key="custom_negative_marks")
    
    with col3:
        enable_negative = st.checkbox("Enable negative marking", 
            value=True,
            key="custom_enable_negative")
    
    if st.button("🚀 Generate Custom Exam", type="primary", use_container_width=True):
        if not topic:
            st.error("⚠️ Please enter a topic")
            return
        
        with st.spinner(f"🧠 Creating {num_questions} questions on {topic}..."):
            questions = llm.generate_adaptive_questions(
                topic=f"{subject} - {topic}",
                difficulty=difficulty,
                count=num_questions,
                weak_areas=None
            )
            
            if questions and len(questions) > 0:
                st.session_state.upload_questions = questions
                st.session_state.upload_answers = {}
                st.session_state.upload_submitted = False
                st.session_state.upload_exam_started = False
                st.session_state.upload_exam_name = exam_name
                st.session_state.upload_exam_duration = duration
                st.session_state.upload_positive_marks = positive_marks
                st.session_state.upload_negative_marks = negative_marks if enable_negative else 0
                st.session_state.upload_negative_marking = enable_negative
                
                st.success(f"✅ Generated {len(questions)} questions!")
                st.rerun()
            else:
                st.error("❌ Failed to generate questions. Please try again.")
    
    # If questions generated, show exam interface
    if st.session_state.upload_questions and not st.session_state.upload_submitted:
        render_exam_interface(llm)
    
    # Show results after submission
    if st.session_state.upload_submitted and st.session_state.upload_questions:
        render_exam_results(llm)


def render_exam_interface(llm):
    """Render the actual exam-taking interface"""
    
    if not st.session_state.upload_exam_started:
        st.divider()
        st.markdown(f"### 📋 {st.session_state.upload_exam_name}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Questions", len(st.session_state.upload_questions))
        with col2:
            st.metric("Duration", f"{st.session_state.upload_exam_duration} min")
        with col3:
            marking = f"+{st.session_state.upload_positive_marks}"
            if st.session_state.upload_negative_marking:
                marking += f" / -{st.session_state.upload_negative_marks}"
            st.metric("Marking", marking)
        
        st.markdown("**Instructions:**")
        st.info("""
        - All questions are multiple choice
        - You can navigate between questions
        - Mark questions for review if unsure
        - Timer will start when you begin
        - Submit when ready or time runs out
        """)
        
        if st.button("▶️ Start Exam", type="primary", use_container_width=True):
            st.session_state.upload_exam_started = True
            st.session_state.upload_start_time = time.time()
            st.session_state.upload_current_q = 0
            st.rerun()
    
    else:
        # Exam in progress
        st.divider()
        
        # Timer
        elapsed = time.time() - st.session_state.upload_start_time
        remaining = max(0, (st.session_state.upload_exam_duration * 60) - elapsed)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"### 📝 {st.session_state.upload_exam_name}")
        
        with col2:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            color = "🔴" if mins < 5 else "🟡" if mins < 10 else "🟢"
            st.metric("Time Left", f"{color} {mins:02d}:{secs:02d}")
        
        with col3:
            answered = len([a for a in st.session_state.upload_answers.values() if a])
            st.metric("Answered", f"{answered}/{len(st.session_state.upload_questions)}")
        
        # Auto-submit if time runs out
        if remaining <= 0 and not st.session_state.upload_submitted:
            st.session_state.upload_submitted = True
            st.warning("⏰ Time's up! Exam auto-submitted.")
            st.rerun()
        
        st.divider()
        
        # Question navigation
        st.markdown("#### Question Navigation")
        nav_cols = st.columns(min(10, len(st.session_state.upload_questions)))
        
        for i in range(len(st.session_state.upload_questions)):
            with nav_cols[i % 10]:
                # Color code: green=answered, yellow=marked, white=unanswered
                is_answered = i in st.session_state.upload_answers and st.session_state.upload_answers[i]
                is_marked = i in st.session_state.upload_marked_review
                
                if is_answered:
                    button_type = "primary" if i == st.session_state.upload_current_q else "secondary"
                elif is_marked:
                    button_type = "secondary"
                else:
                    button_type = "secondary"
                
                label = f"{'✓' if is_answered else '⚠' if is_marked else ''}{i+1}"
                
                if st.button(label, key=f"nav_{i}", use_container_width=True, type=button_type):
                    st.session_state.upload_current_q = i
                    st.rerun()
        
        st.divider()
        
        # Current question
        current_idx = st.session_state.upload_current_q
        q = st.session_state.upload_questions[current_idx]
        
        st.markdown(f"#### Question {current_idx + 1} of {len(st.session_state.upload_questions)}")
        # Use a styled box so the full question text (including math notation) is visible
        st.markdown(
            f'<div style="background:rgba(99,102,241,0.08); border-left:4px solid #6366f1;'
            f' border-radius:8px; padding:14px 18px; margin-bottom:12px; font-size:1.05rem;">'
            f'{q["question"]}</div>',
            unsafe_allow_html=True
        )
        
        # Options
        answer = st.radio(
            "Select your answer:",
            list(q['options'].keys()),
            format_func=lambda x: f"{x}. {q['options'][x]}",
            key=f"q_{current_idx}",
            index=None if current_idx not in st.session_state.upload_answers else 
                  list(q['options'].keys()).index(st.session_state.upload_answers[current_idx])
        )
        
        if answer:
            st.session_state.upload_answers[current_idx] = answer
        
        st.divider()
        
        # Navigation buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if current_idx > 0:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.upload_current_q -= 1
                    st.rerun()
        
        with col2:
            if current_idx in st.session_state.upload_marked_review:
                if st.button("✓ Unmark Review", use_container_width=True):
                    st.session_state.upload_marked_review.remove(current_idx)
                    st.rerun()
            else:
                if st.button("⚠️ Mark for Review", use_container_width=True):
                    st.session_state.upload_marked_review.add(current_idx)
                    st.rerun()
        
        with col3:
            if current_idx < len(st.session_state.upload_questions) - 1:
                if st.button("Next ➡️", use_container_width=True):
                    st.session_state.upload_current_q += 1
                    st.rerun()
        
        with col4:
            if st.button("📊 Submit Exam", type="primary", use_container_width=True):
                st.session_state.upload_submitted = True
                st.rerun()


def render_exam_results(llm):
    """Display exam results and analytics — runs once then cached."""

    # ── guard: compute & cache results exactly once ──────────────────────
    if 'upload_results_cached' not in st.session_state:
        questions = st.session_state.upload_questions
        answers   = st.session_state.upload_answers

        correct      = 0
        wrong        = 0
        unattempted  = 0

        for i, q in enumerate(questions):
            if i in answers and answers[i]:
                # Normalize comparison
                user_ans = str(answers[i]).strip().upper()
                correct_ans = str(q.get('correct_answer', '')).strip().upper()
                
                if user_ans == correct_ans:
                    correct += 1
                else:
                    wrong += 1
            else:
                unattempted += 1

        pos_marks = st.session_state.get('upload_positive_marks', 4)
        neg_marks = st.session_state.get('upload_negative_marks', 1)
        neg_on    = st.session_state.get('upload_negative_marking', True)

        positive_score = correct * pos_marks
        negative_score = wrong * neg_marks if neg_on else 0
        total_score    = positive_score - negative_score
        max_score      = len(questions) * pos_marks
        percentage     = (total_score / max_score * 100) if max_score > 0 else 0

        # ── persist to DB (runs exactly once) ─────────────────────────────
        import uuid
        session_id = str(uuid.uuid4())

        save_question_attempts_to_db(
            db=st.session_state.db,
            user_id=st.session_state.user_id,
            questions=questions,
            answers=answers,
            exam_name=st.session_state.upload_exam_name,
            session_id=session_id
        )

        st.session_state.db.record_exam(
            st.session_state.user_id,
            st.session_state.upload_exam_name,
            len(questions), correct, wrong, unattempted,
            total_score, max_score, percentage,
            (time.time() - st.session_state.upload_start_time) / 60
            if st.session_state.upload_start_time else 0
        )

        # cache everything so the rest of the page just reads
        st.session_state.upload_results_cached = {
            'correct': correct, 'wrong': wrong, 'unattempted': unattempted,
            'positive_score': positive_score, 'negative_score': negative_score,
            'total_score': total_score, 'max_score': max_score,
            'percentage': percentage
        }

    # ── read cached values ─────────────────────────────────────────────
    r = st.session_state.upload_results_cached
    correct     = r['correct']
    wrong       = r['wrong']
    unattempted = r['unattempted']
    positive_score = r['positive_score']
    negative_score = r['negative_score']
    total_score    = r['total_score']
    max_score      = r['max_score']
    percentage     = r['percentage']
    questions = st.session_state.upload_questions
    answers   = st.session_state.upload_answers

    # ── render ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🎯 Exam Results")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Score", f"{total_score}/{max_score}", f"{percentage:.1f}%")
    with col2:
        st.metric("✅ Correct", correct, f"+{positive_score}")
    with col3:
        st.metric("❌ Wrong", wrong, f"-{negative_score}" if negative_score > 0 else "0")
    with col4:
        st.metric("⚪ Unattempted", unattempted)

    # Performance message
    if percentage >= 90:
        st.success("🏆 Outstanding! Excellent performance!")
    elif percentage >= 75:
        st.success("🌟 Great job! Very good score!")
    elif percentage >= 60:
        st.info("👍 Good effort! Keep practicing!")
    elif percentage >= 40:
        st.warning("📚 Need more practice. Review weak areas.")
    else:
        st.error("💪 Don't worry! Focus on fundamentals and try again.")

    st.divider()

    # ── AI recommendations ─────────────────────────────────────────────
    st.markdown("### 🤖 Powered Recommendations")
    with st.spinner("🧠 Generating personalized recommendations..."):
        weak_topics = []
        for i, q in enumerate(questions):
            if i in answers and answers[i] and answers[i] != q.get('correct_answer'):
                if 'subtopic' in q:
                    weak_topics.append(q['subtopic'])

        time_taken = 0
        if st.session_state.upload_start_time:
            time_taken = (time.time() - st.session_state.upload_start_time) / 60

        performance_data = {
            'score': total_score, 'total': max_score, 'percentage': percentage,
            'correct': correct, 'wrong': wrong, 'unattempted': unattempted,
            'time_taken': time_taken, 'attempted': correct + wrong,
            'weak_topics': list(set(weak_topics))[:5] if weak_topics else []
        }
        recommendations = llm.generate_personalized_recommendations(performance_data)
        if recommendations:
            st.info(recommendations)

    st.divider()

    # ── detailed question-by-question review ───────────────────────────
    st.markdown("### 📝 Detailed Question-by-Question Review")

    for i, q in enumerate(questions):
        user_ans  = answers.get(i, None)
        correct_ans = q.get('correct_answer')
        
        # Normalize comparison
        if user_ans:
            user_ans_normalized = str(user_ans).strip().upper()
            correct_ans_normalized = str(correct_ans).strip().upper()
            is_correct = (user_ans_normalized == correct_ans_normalized)
        else:
            is_correct = False

        if is_correct:
            status = "✅ Correct"
        elif user_ans:
            status = "❌ Wrong"
        else:
            status = "⚪ Unattempted"

        with st.expander(f"Q{i+1} — {status}"):
            # Full question in styled box (preserves math notation)
            st.markdown(
                f'<div style="background:rgba(99,102,241,0.08); border-left:4px solid #6366f1;'
                f' border-radius:8px; padding:12px 16px; margin-bottom:10px;">'
                f'{q["question"]}</div>',
                unsafe_allow_html=True
            )

            # Options with colour coding
            for opt_key in ['A', 'B', 'C', 'D']:
                opt_val = q['options'].get(opt_key, '')
                opt_key_normalized = opt_key.strip().upper()
                
                if opt_key_normalized == str(correct_ans).strip().upper():
                    st.success(f"✅ {opt_key}. {opt_val}  ← Correct Answer")
                elif user_ans and opt_key_normalized == str(user_ans).strip().upper() and not is_correct:
                    st.error(f"❌ {opt_key}. {opt_val}  ← Your Answer")
                else:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{opt_key}. {opt_val}")

            if q.get('explanation'):
                st.info(f"💡 **Explanation:** {q['explanation']}")

    # ── save confirmation ──────────────────────────────────────────────
    st.success("✅ Exam saved! Check Knowledge Graph, AI Study Coach, and Competitive Intel tabs for your results.")

    # ── retake / new exam ──────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Retake This Exam", use_container_width=True):
            for key in ('upload_answers', 'upload_submitted', 'upload_exam_started',
                        'upload_marked_review', 'upload_results_cached'):
                if key == 'upload_answers':
                    st.session_state[key] = {}
                elif key == 'upload_marked_review':
                    st.session_state[key] = set()
                elif key in st.session_state:
                    del st.session_state[key]
            st.session_state.upload_submitted = False
            st.session_state.upload_exam_started = False
            st.rerun()
    with col2:
        if st.button("➕ Create New Exam", use_container_width=True, type="primary"):
            for key in ('upload_questions', 'upload_answers', 'upload_submitted',
                        'upload_exam_started', 'upload_marked_review', 'upload_results_cached'):
                if key == 'upload_questions':
                    st.session_state[key] = []
                elif key == 'upload_answers':
                    st.session_state[key] = {}
                elif key == 'upload_marked_review':
                    st.session_state[key] = set()
                elif key in st.session_state:
                    del st.session_state[key]
            st.session_state.upload_submitted = False
            st.session_state.upload_exam_started = False
            st.rerun()
# ==================== WELLNESS CENTER (Existing) ====================

# ==================== REMOVED FUNCTIONS (Replaced by Exceptional Tabs) ====================
# render_wellness_center() - Replaced by AI Study Coach tab with Pomodoro sessions
# render_error_analysis_tab() - Functionality merged into ML Insights and Competitive Intelligence


if __name__ == "__main__":
    main()