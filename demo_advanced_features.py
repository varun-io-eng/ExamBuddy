"""
demo_advanced_features.py - Standalone Demo of All 3 Advanced Features

Run this to see all features in action with sample data:
    streamlit run demo_advanced_features.py

🏆 DEMONSTRATES:
1. Bayesian Knowledge Tracing
2. Intelligent Question Generation
3. Error Taxonomy & Fix Strategy
"""

import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import random

# Set page config
st.set_page_config(
    page_title="Advanced ML Features Demo",
    page_icon="🚀",
    layout="wide"
)

st.title("🚀 Advanced Educational ML Features Demo")
st.markdown("---")

# Create temporary in-memory database with sample data
@st.cache_resource
def create_demo_database():
    """Create demo database with sample student data"""
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()
    
    # Create tables (simplified schema)
    cursor.execute("""
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            username TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE knowledge_nodes (
            node_id INTEGER PRIMARY KEY,
            subject TEXT,
            topic TEXT,
            subtopic TEXT,
            mastery_level REAL DEFAULT 0,
            confidence_score REAL DEFAULT 0,
            last_practiced TIMESTAMP,
            practice_count INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE attempts (
            attempt_id INTEGER PRIMARY KEY,
            user_id TEXT,
            node_id INTEGER,
            question TEXT,
            user_answer TEXT,
            correct_answer TEXT,
            is_correct BOOLEAN,
            time_taken INTEGER,
            difficulty TEXT,
            subject TEXT,
            topic TEXT,
            timestamp TIMESTAMP
        )
    """)
    
    # Insert demo user
    cursor.execute("INSERT INTO users VALUES ('demo_user', 'Demo Student')")
    
    # Insert sample knowledge nodes
    nodes = [
        ('Physics', 'Kinematics', 'Motion in 1D'),
        ('Physics', 'Kinematics', 'Motion in 2D'),
        ('Physics', 'Dynamics', 'Forces'),
        ('Physics', 'Work-Energy', 'Basic concepts'),
        ('Chemistry', 'Atomic Structure', 'Electronic config'),
        ('Mathematics', 'Calculus', 'Differentiation'),
    ]
    
    for i, (subj, topic, subtopic) in enumerate(nodes, 1):
        cursor.execute("""
            INSERT INTO knowledge_nodes 
            (node_id, subject, topic, subtopic, practice_count)
            VALUES (?, ?, ?, ?, ?)
        """, (i, subj, topic, subtopic, 0))
    
    # Insert sample attempts (simulating student practice)
    questions_data = [
        # Motion in 1D - improving performance
        ("A car accelerates from 0 to 20 m/s in 5s. Find acceleration.", False, 15, 1),
        ("A ball is dropped. What is its velocity after 2s? (g=10)", False, 20, 1),
        ("A car accelerates from 0 to 20 m/s in 5s. Find acceleration.", True, 12, 1),
        ("Distance covered by car at 10 m/s for 5s?", True, 8, 1),
        ("A ball is dropped. What is its velocity after 3s? (g=10)", True, 10, 1),
        
        # Motion in 2D - struggling
        ("Projectile launched at 30° with 20 m/s. Find max height.", False, 45, 2),
        ("Time of flight for projectile at 45°?", False, 50, 2),
        ("Range of projectile depends on?", False, 40, 2),
        
        # Forces - doing well
        ("Net force on 5kg object with 10 m/s² acceleration?", True, 10, 3),
        ("Newton's 3rd law states?", True, 8, 3),
        ("Friction opposes motion. True or false?", True, 5, 3),
        
        # Electronic config - not practiced much
        ("Electron configuration of Carbon?", False, 60, 5),
        ("Aufbau principle states?", True, 30, 5),
    ]
    
    base_time = datetime.now() - timedelta(days=14)
    
    for i, (q, is_correct, time_taken, node_id) in enumerate(questions_data):
        # Get node info
        cursor.execute("SELECT subject, topic FROM knowledge_nodes WHERE node_id = ?", (node_id,))
        subj, topic = cursor.fetchone()
        
        timestamp = (base_time + timedelta(days=i*0.5)).isoformat()
        
        cursor.execute("""
            INSERT INTO attempts 
            (user_id, node_id, question, user_answer, correct_answer, 
             is_correct, time_taken, difficulty, subject, topic, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'demo_user', node_id, q, 
            'A' if is_correct else 'B', 'A',
            is_correct, time_taken, 'medium', subj, topic, timestamp
        ))
    
    conn.commit()
    return conn


# Simple DB wrapper class
class DemoDB:
    def __init__(self, conn):
        self.conn = conn


# Initialize
if 'demo_db' not in st.session_state:
    conn = create_demo_database()
    st.session_state.demo_db = DemoDB(conn)

db = st.session_state.demo_db
user_id = 'demo_user'

# Import our advanced features
try:
    from bayesian_knowledge_tracker import BayesianKnowledgeTracker
    from intelligent_question_generator import ConceptGraph
    from error_taxonomy_engine import ErrorTaxonomy, FixStrategyEngine
    
    # Initialize
    if 'bkt' not in st.session_state:
        st.session_state.bkt = BayesianKnowledgeTracker(db)
    
    if 'concept_graph' not in st.session_state:
        st.session_state.concept_graph = ConceptGraph()
    
    features_loaded = True
except ImportError as e:
    st.error(f"❌ Could not import advanced features: {e}")
    st.info("Make sure all .py files are in the same directory as this demo.")
    features_loaded = False


if features_loaded:
    # Create tabs for each feature
    tab1, tab2, tab3 = st.tabs([
        "🧠 Feature 1: Bayesian Knowledge Tracing",
        "🗺️ Feature 2: Concept Coverage",
        "🔬 Feature 3: Error Taxonomy"
    ])
    
    # ========================================================================
    # FEATURE 1: Bayesian Knowledge Tracing
    # ========================================================================
    with tab1:
        st.markdown("## 🧠 Bayesian Knowledge Tracing")
        st.caption("Probabilistic student knowledge modeling with forgetting curves")
        
        st.markdown("### How it works:")
        st.info("""
        - **P(Knows Concept)**: Probability you've mastered each concept (0-100%)
        - **Bayesian Updates**: Updates after each question based on correctness
        - **Forgetting Curve**: Tracks knowledge decay over time
        - **Learning Velocity**: Measures improvement rate
        """)
        
        # Get masteries
        bkt = st.session_state.bkt
        masteries = bkt.get_all_concept_masteries(user_id)
        
        if masteries:
            st.markdown("### 📊 Your Knowledge State")
            
            # Display each concept
            for m in masteries:
                concept = f"{m['subject']} → {m['topic']} → {m['subtopic']}"
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{concept}**")
                
                with col2:
                    mastery_pct = m['mastery_probability'] * 100
                    color = '🟢' if mastery_pct >= 70 else '🟡' if mastery_pct >= 40 else '🔴'
                    st.metric("Mastery", f"{color} {mastery_pct:.0f}%")
                
                with col3:
                    risk_emoji = {'low': '✅', 'medium': '⚠️', 'high': '🔴'}
                    st.metric("Forgetting", risk_emoji[m['forgetting_risk']])
                
                with col4:
                    st.metric("Days Since", m['days_since_practice'])
                
                # Progress bar
                st.progress(m['mastery_probability'], 
                          text=f"Confidence: {m['confidence']*100:.0f}%")
                
                st.caption(f"Attempts: {m['attempts']} | Learning velocity: {m['learning_velocity']:.3f}")
                st.markdown("---")
            
            # Show spaced repetition recommendations
            st.markdown("### 💡 Spaced Repetition: What to Practice Next")
            
            optimal = bkt.get_optimal_practice_topics(user_id, 5)
            
            for i, topic in enumerate(optimal, 1):
                st.markdown(f"{i}. **{topic['subject']} → {topic['topic']} → {topic['subtopic']}**")
                st.caption(f"   {topic['reason']} (Score: {topic['score']:.1f})")
            
            # Exam predictor
            st.markdown("### 🎯 Exam Performance Predictor")
            
            physics_topics = [
                (m['subject'], m['topic'], m['subtopic'])
                for m in masteries
                if m['subject'] == 'Physics'
            ]
            
            if physics_topics:
                prediction = bkt.predict_exam_performance(user_id, physics_topics, 'medium')
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Predicted Score", f"{prediction['predicted_score']:.0f}%")
                with col2:
                    st.metric("Confidence Range", 
                            f"{prediction['confidence_lower']:.0f}%-{prediction['confidence_upper']:.0f}%")
                with col3:
                    st.metric("Coverage", f"{prediction['coverage']:.0f}%")
        else:
            st.warning("No practice data yet. This demo has pre-loaded sample data.")
    
    
    # ========================================================================
    # FEATURE 2: Concept Coverage
    # ========================================================================
    with tab2:
        st.markdown("## 🗺️ Concept Coverage Intelligence")
        st.caption("Track which concepts you've mastered vs. need to learn")
        
        st.markdown("### How it works:")
        st.info("""
        - **Concept Graph**: Hierarchical map of all topics and subtopics
        - **Coverage Analysis**: Shows what you've practiced vs. not practiced
        - **Intelligent Generation**: Creates questions targeting your gaps
        - **Prerequisite Tracking**: Ensures you master basics before advanced topics
        """)
        
        # Show concept graph structure
        st.markdown("### 📚 Complete Concept Map (Physics)")
        
        concept_graph = st.session_state.concept_graph
        all_concepts = concept_graph.get_all_concepts('Physics')
        
        # Group by topic
        from collections import defaultdict
        by_topic = defaultdict(list)
        for c in all_concepts:
            by_topic[c['topic']].append(c)
        
        for topic, concepts in by_topic.items():
            with st.expander(f"📖 {topic} ({len(concepts)} concepts)"):
                for c in concepts:
                    st.markdown(f"- {c['subtopic']} → {c['concept']}")
        
        # Show what student has practiced
        st.markdown("### ✅ Your Practice Coverage")
        
        practiced_nodes = set()
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT kn.topic, kn.subtopic
            FROM knowledge_nodes kn
            JOIN attempts a ON kn.node_id = a.node_id
            WHERE a.user_id = ?
        """, (user_id,))
        
        for topic, subtopic in cursor.fetchall():
            practiced_nodes.add(f"{topic} → {subtopic}")
        
        all_nodes = set(f"{c['topic']} → {c['subtopic']}" for c in all_concepts)
        not_practiced = all_nodes - practiced_nodes
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Practiced ✅**")
            for node in sorted(practiced_nodes):
                st.success(node)
        
        with col2:
            st.markdown("**Not Practiced Yet ⚪**")
            for node in sorted(list(not_practiced)[:5]):
                st.info(node)
            if len(not_practiced) > 5:
                st.caption(f"... and {len(not_practiced)-5} more")
        
        # Coverage stats
        coverage_pct = len(practiced_nodes) / len(all_nodes) * 100
        st.metric("Coverage Percentage", f"{coverage_pct:.0f}%")
        st.progress(coverage_pct/100, text=f"{len(practiced_nodes)}/{len(all_nodes)} concepts practiced")
        
        # Show prerequisites
        st.markdown("### 🔗 Prerequisite Dependencies")
        
        st.info("Example: To learn **Motion in 2D**, you should first master **Motion in 1D**")
        
        prereq_examples = [
            ("Motion in 2D", ["Motion in 1D"]),
            ("Conservation of Energy", ["Basic concepts (Work-Energy)"]),
            ("Integration", ["Differentiation"])
        ]
        
        for concept, prereqs in prereq_examples:
            st.markdown(f"**{concept}**")
            st.caption(f"   Prerequisites: {', '.join(prereqs)}")
    
    
    # ========================================================================
    # FEATURE 3: Error Taxonomy
    # ========================================================================
    with tab3:
        st.markdown("## 🔬 Error Taxonomy & Fix Strategy")
        st.caption("Understand WHY you make mistakes and get targeted fixes")
        
        st.markdown("### How it works:")
        st.info("""
        - **Error Classification**: Categorizes mistakes into 12 types
        - **Pattern Detection**: Identifies recurring error patterns
        - **Fix Strategies**: Provides specific remediation for each error type
        - **Targeted Practice**: Generates questions to fix weak spots
        """)
        
        # Show all 12 error types
        st.markdown("### 📋 The 12 Error Types")
        
        for error_type, info in ErrorTaxonomy.ERROR_TYPES.items():
            with st.expander(f"{info['icon']} {info['name']} ({info['severity']} severity)"):
                st.markdown(f"**Description:** {info['description']}")
                
                # Show fix strategy
                if error_type in FixStrategyEngine.REMEDIATION_STRATEGIES:
                    strategy = FixStrategyEngine.REMEDIATION_STRATEGIES[error_type]
                    
                    st.markdown("**Immediate Actions:**")
                    for action in strategy['immediate_actions']:
                        st.markdown(f"- {action}")
                    
                    st.markdown(f"**Practice Type:** {strategy['practice_type']}")
                    st.markdown(f"**Follow-up:** {strategy['follow_up']}")
        
        # Demo error detection
        st.markdown("### 🎯 Try Error Detection")
        
        st.markdown("Let's analyze a sample wrong answer:")
        
        sample_q = st.text_area(
            "Question",
            "A car accelerates from 0 to 60 m/s in 10 seconds. What is its acceleration?"
        )
        
        sample_explanation = st.text_area(
            "Why the answer was wrong",
            "Student forgot to use the correct formula. Used distance formula instead of a = (v-u)/t"
        )
        
        if st.button("🔍 Detect Error Type"):
            errors = ErrorTaxonomy.detect_error_patterns(
                sample_q, "B", "A", sample_explanation, 20
            )
            
            st.markdown("### Detected Error Types:")
            for error in errors:
                st.markdown(f"{error['icon']} **{error['name']}** - Confidence: {error['confidence']*100:.0f}%")
                st.caption(error['description'])
        
        # Show sample error analysis from demo data
        st.markdown("### 📊 Your Error Patterns (Demo Data)")
        
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT question, topic, time_taken
            FROM attempts
            WHERE user_id = ? AND is_correct = 0
        """, (user_id,))
        
        wrong_attempts = cursor.fetchall()
        
        if wrong_attempts:
            st.metric("Total Errors", len(wrong_attempts))
            
            # Simulate error classification
            error_counts = defaultdict(int)
            for q, topic, time_taken in wrong_attempts:
                errors = ErrorTaxonomy.detect_error_patterns(q, "B", "A", "", time_taken)
                if errors:
                    error_counts[errors[0]['type']] += 1
            
            st.markdown("**Top Error Types:**")
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                info = ErrorTaxonomy.ERROR_TYPES[error_type]
                st.markdown(f"{info['icon']} {info['name']}: {count} times")


# Summary
st.markdown("---")
st.markdown("## 🎉 Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🧠 Feature 1")
    st.success("Bayesian Knowledge Tracing tracks P(knows concept) with forgetting curves")

with col2:
    st.markdown("### 🗺️ Feature 2")
    st.info("Concept Coverage maps learning gaps and generates targeted questions")

with col3:
    st.markdown("### 🔬 Feature 3")
    st.warning("Error Taxonomy classifies mistakes and provides fix strategies")

st.markdown("---")
st.markdown("### 💼 Resume Impact")
st.code("""
✅ Implemented Bayesian Knowledge Tracing (BKT) for probabilistic mastery modeling
✅ Built concept graph with intelligent question generation targeting learning gaps  
✅ Created error taxonomy engine with 12 classification types and remediation strategies
✅ Integrated educational psychology principles: spaced repetition, prerequisite tracking, IRT
""")