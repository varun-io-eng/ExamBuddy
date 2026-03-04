"""
ml_integration.py - Integrate ML Model into Existing App
UPDATED: Combined ML + BKT insights tab with Structured Context Injection
"""

import streamlit as st
from ml_difficulty_predictor import MLDifficultyPredictor
from ml_trainer import MLTrainer, MLDataCollector
from bayesian_knowledge_tracker import BayesianKnowledgeTracker
import plotly.graph_objects as go
import plotly.express as px
import json


def initialize_ml_system(db):
    """
    Initialize ML system
    Call this once in your app's main()
    """
    if 'ml_predictor' not in st.session_state:
        st.session_state.ml_predictor = MLDifficultyPredictor()
        st.session_state.ml_trainer = MLTrainer(db)
        st.session_state.bkt_tracker = BayesianKnowledgeTracker(db)
        
        # Try to load existing model
        if st.session_state.ml_predictor.is_trained:
            st.sidebar.success("🧠 ML Model: Active")
        else:
            st.sidebar.info("📊 ML Model: Collecting data...")


def build_student_context(user_id, db, exam_type="JEE"):
    """
    Build structured context for LLM injection
    This makes every LLM call student-aware and exam-aware
    """
    bkt = st.session_state.bkt_tracker
    collector = MLDataCollector(db)
    
    # Get student history
    student_history = collector.get_student_history(user_id)
    
    if len(student_history) < 5:
        # Minimal context for new students
        return {
            'exam': exam_type,
            'total_attempts': len(student_history),
            'weak_topics': [],
            'mastery_scores': {},
            'panic_under_pressure': 'UNKNOWN',
            'strategy_preference': 'Unknown',
            'negative_marking_risk': 'UNKNOWN',
            'ability_level': 'Beginner',
            'context_string': f"""Student Profile:
- Exam: {exam_type}
- Status: New student (< 5 attempts)
- Learning Phase: Initial assessment"""
        }
    
    # Get all concept masteries from BKT
    all_masteries = bkt.get_all_concept_masteries(user_id)
    
    # Identify weak topics (mastery < 60%)
    weak_topics = [
        f"{m['subject']}: {m['topic']}"
        for m in all_masteries
        if m['mastery_probability'] < 0.6
    ][:5]  # Top 5 weak topics
    
    # Build mastery scores dictionary
    mastery_scores = {
        f"{m['subject']}: {m['topic']}": round(m['mastery_probability'], 2)
        for m in all_masteries[:10]  # Top 10 topics
    }
    
    # Analyze time pressure behavior
    time_taken = [h['time_taken'] for h in student_history if h.get('time_taken')]
    avg_time = sum(time_taken) / len(time_taken) if time_taken else 30
    
    # Students who take < 15s or > 90s are likely panicking
    panic_under_pressure = 'YES' if avg_time < 15 or avg_time > 90 else 'NO'
    
    # Determine strategy preference
    recent_attempts = student_history[-20:] if len(student_history) >= 20 else student_history
    accuracy = sum(1 for a in recent_attempts if a['is_correct']) / len(recent_attempts)
    
    if accuracy > 0.7:
        strategy = 'Aggressive (High accuracy, can take risks)'
    elif accuracy < 0.4:
        strategy = 'Conservative (Focus on easier questions first)'
    else:
        strategy = 'Balanced (Moderate risk-taking)'
    
    # Calculate negative marking risk
    if accuracy < 0.5:
        negative_marking_risk = 'HIGH'
    elif accuracy < 0.7:
        negative_marking_risk = 'MEDIUM'
    else:
        negative_marking_risk = 'LOW'
    
    # Determine ability level
    if accuracy < 0.3:
        ability_level = 'Beginner (1-2/5)'
    elif accuracy < 0.5:
        ability_level = 'Elementary (2-3/5)'
    elif accuracy < 0.7:
        ability_level = 'Intermediate (3-4/5)'
    elif accuracy < 0.85:
        ability_level = 'Advanced (4-5/5)'
    else:
        ability_level = 'Expert (5/5)'
    
    # Build context string for LLM injection
    context_string = f"""Student Profile:
- Exam: {exam_type}
- Ability Level: {ability_level}
- Total Practice: {len(student_history)} questions
- Current Accuracy: {accuracy*100:.1f}%
- Weak Topics: {', '.join(weak_topics) if weak_topics else 'None identified'}
- Mastery Scores: {json.dumps(mastery_scores, indent=2)}
- Panic Under Time Pressure: {panic_under_pressure}
- Strategy Preference: {strategy}
- Negative Marking Risk: {negative_marking_risk}
- Average Time Per Question: {avg_time:.1f}s"""
    
    return {
        'exam': exam_type,
        'ability_level': ability_level,
        'total_attempts': len(student_history),
        'accuracy': accuracy,
        'weak_topics': weak_topics,
        'mastery_scores': mastery_scores,
        'panic_under_pressure': panic_under_pressure,
        'strategy_preference': strategy,
        'negative_marking_risk': negative_marking_risk,
        'avg_time': avg_time,
        'context_string': context_string
    }


def render_unified_insights_tab(user_id, db, exam_type="JEE"):
    """
    UNIFIED TAB: ML + BKT Insights combined
    Shows comprehensive learning profile with both ML and Bayesian analysis
    """
    st.markdown("## 🧠 Learning Intelligence Hub")
    st.caption("Your personalized insights powered by Machine Learning + Bayesian Knowledge Tracing")
    
    # Build student context
    student_context = build_student_context(user_id, db, exam_type)
    
    # Store in session state for LLM injection
    st.session_state.student_context = student_context
    
    # Get components
    predictor = st.session_state.ml_predictor
    bkt = st.session_state.bkt_tracker
    collector = MLDataCollector(db)
    
    # Get student history
    student_history = collector.get_student_history(user_id)
    
    if len(student_history) < 5:
        st.info("📚 Complete at least 5 questions to unlock your comprehensive learning profile!")
        st.markdown("""
        **What you'll get:**
        - 🎯 Precise ability level (ML-powered)
        - 🧮 Bayesian mastery tracking per topic
        - 📊 Predicted exam performance
        - 💡 Context-aware AI recommendations
        - 📈 Learning velocity analysis
        - 🎓 Weak area identification
        - ⚡ Time pressure analysis
        - 🎯 Optimal practice suggestions
        """)
        return
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 1: Student Profile Overview
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("### 🎯 Your Learning Profile")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Ability Level",
            student_context['ability_level'].split('(')[0].strip(),
            delta=None
        )
        st.progress(student_context['accuracy'], text=f"{student_context['accuracy']*100:.0f}% Accuracy")
    
    with col2:
        st.metric(
            "Exam Type",
            student_context['exam'],
            delta=None
        )
        st.caption(f"Strategy: {student_context['strategy_preference'].split('(')[0]}")
    
    with col3:
        st.metric(
            "Time Pressure",
            student_context['panic_under_pressure'],
            delta=None,
            delta_color="inverse"
        )
        st.caption(f"Avg: {student_context['avg_time']:.1f}s/question")
    
    with col4:
        st.metric(
            "Negative Marking Risk",
            student_context['negative_marking_risk'],
            delta=None,
            delta_color="inverse"
        )
        st.caption(f"{student_context['total_attempts']} total attempts")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 2: ML Analysis + BKT Mastery
    # ═══════════════════════════════════════════════════════════════════
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🤖 ML-Powered Analysis")
        
        if predictor.is_trained:
            profile = predictor.get_student_profile(user_id, student_history)
        else:
            profile = _calculate_simple_profile(student_history)
        
        # ML Ability visualization
        ability_display = profile['ability'] * 5
        st.metric(
            "ML Ability Score",
            f"{ability_display:.2f} / 5.0",
            delta=f"{profile.get('learning_velocity', 0)*100:+.1f}% velocity"
        )
        
        # Optimal difficulty range
        optimal_min, optimal_max = profile['optimal_difficulty_range']
        st.info(f"📊 **Optimal Challenge Zone:** {optimal_min*5:.1f} - {optimal_max*5:.1f}")
        
        # Learning velocity indicator
        velocity = profile.get('learning_velocity', 0)
        if velocity > 0.1:
            st.success(f"🚀 Rapidly improving: {velocity*100:.1f}%/session")
        elif velocity > 0:
            st.info(f"📈 Steady progress: {velocity*100:.1f}%/session")
        elif velocity < -0.05:
            st.warning(f"📉 Performance declining: {abs(velocity)*100:.1f}%")
        else:
            st.info("➡️ Stable performance")
    
    with col2:
        st.markdown("### 🧮 Bayesian Knowledge Tracking")
        
        # Get concepts needing review
        needs_review = bkt.get_concepts_needing_review(user_id, threshold=0.6)
        
        if needs_review:
            st.warning(f"⚠️ {len(needs_review)} topics need review")
            
            # Show top 3 priority topics
            for i, concept in enumerate(needs_review[:3], 1):
                priority_icon = "🔴" if concept['priority'] == 'high' else "🟡" if concept['priority'] == 'medium' else "🟢"
                st.markdown(f"{priority_icon} **{i}. {concept['subject']}: {concept['topic']}**")
                st.caption(f"Mastery: {concept['mastery']*100:.0f}% | {', '.join(concept['reasons'])}")
        else:
            st.success("✅ All topics above 60% mastery!")
        
        # Forgetting risk analysis
        all_masteries = bkt.get_all_concept_masteries(user_id)
        high_risk = sum(1 for m in all_masteries if m['forgetting_risk'] == 'high')
        if high_risk > 0:
            st.warning(f"🕐 {high_risk} topics at high forgetting risk (>14 days)")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 3: Topic Strengths & Weaknesses
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("### 📊 Topic Analysis: Strengths & Weaknesses")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💪 Your Strengths")
        if profile['strong_topics']:
            for topic, score in profile['strong_topics']:
                # Get BKT mastery for comparison
                bkt_mastery = next(
                    (m['mastery_probability'] for m in all_masteries 
                     if f"{m['subject']}: {m['topic']}" == topic),
                    None
                )
                
                st.success(f"**{topic}**")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.caption(f"ML: {score*100:.0f}%")
                with col_b:
                    if bkt_mastery:
                        st.caption(f"BKT: {bkt_mastery*100:.0f}%")
        else:
            st.info("Keep practicing to identify strengths!")
    
    with col2:
        st.markdown("#### 🎯 Areas to Improve")
        if student_context['weak_topics']:
            for topic in student_context['weak_topics']:
                mastery = student_context['mastery_scores'].get(topic, 0)
                st.warning(f"**{topic}**")
                st.caption(f"Current: {mastery*100:.0f}% | Target: 70%+")
                st.progress(mastery, text=f"{mastery*100:.0f}%")
        else:
            st.success("Great! No significant weak areas detected.")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4: Optimal Practice Recommendations (BKT)
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("### 🎯 Optimal Practice Plan (Spaced Repetition)")
    
    optimal_topics = bkt.get_optimal_practice_topics(user_id, count=5)
    
    if optimal_topics:
        st.info("📚 **These topics are mathematically optimal to practice right now:**")
        
        for i, topic_data in enumerate(optimal_topics, 1):
            with st.expander(f"{i}. {topic_data['subject']}: {topic_data['topic']} - {topic_data['reason']}"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Current Mastery", f"{topic_data['mastery']*100:.0f}%")
                with col_b:
                    st.metric("Days Since", f"{topic_data['days_since']}")
                with col_c:
                    st.metric("Priority Score", f"{topic_data['score']:.1f}")
                
                st.caption("**Why now?** This topic is at the optimal point in the forgetting curve for maximum retention gain.")
    else:
        st.info("Start practicing more topics to get personalized recommendations!")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 5: Context-Aware AI Insights
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("### 💡 Context-Aware AI Recommendations")
    st.caption("These insights are generated with your complete profile injected into the AI")
    
    # Generate recommendations with context injection
    recommendations = generate_context_aware_recommendations(student_context, profile, needs_review)
    
    for rec in recommendations:
        if rec['type'] == 'success':
            st.success(rec['message'])
        elif rec['type'] == 'warning':
            st.warning(rec['message'])
        elif rec['type'] == 'info':
            st.info(rec['message'])
        elif rec['type'] == 'error':
            st.error(rec['message'])
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 6: Exam Performance Prediction
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("### 🎓 Predicted Exam Performance")
    
    # Get all topics the student has practiced
    exam_topics = [
        (m['subject'], m['topic'], None)
        for m in all_masteries
    ]
    
    if exam_topics:
        prediction = bkt.predict_exam_performance(
            user_id,
            exam_topics,
            exam_difficulty='medium'
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Predicted Score",
                f"{prediction['predicted_score']:.1f}%",
                delta=None
            )
        
        with col2:
            st.metric(
                "Confidence Range",
                f"{prediction['confidence_lower']:.0f}-{prediction['confidence_upper']:.0f}%",
                delta=None
            )
        
        with col3:
            st.metric(
                "Topics Covered",
                f"{prediction['topics_covered']}/{prediction['topics_total']}",
                delta=f"{prediction['coverage']:.0f}%"
            )
        
        with col4:
            st.metric(
                "Prediction Confidence",
                f"{prediction['confidence']*100:.0f}%",
                delta=None
            )
        
        # Visual prediction
        fig = go.Figure()
        
        fig.add_trace(go.Indicator(
            mode = "gauge+number+delta",
            value = prediction['predicted_score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Predicted Exam Score"},
            delta = {'reference': 60, 'increasing': {'color': "green"}},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 40], 'color': "lightgray"},
                    {'range': [40, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 60
                }
            }
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"📊 Based on {prediction['topics_covered']} practiced topics with {prediction['confidence']*100:.0f}% confidence")
    
    st.divider()
    
    # ═══════════════════════════════════════════════════════════════════
    # SECTION 7: Learning Progress Visualization
    # ═══════════════════════════════════════════════════════════════════
    if len(student_history) >= 10:
        st.markdown("### 📈 Your Learning Journey")
        render_ability_trend(student_history)
    
    # Show context string (for debugging/transparency)
    with st.expander("🔍 View Your Student Context (Used for AI)"):
        st.code(student_context['context_string'], language='text')
        st.caption("This context is injected into every AI recommendation to make them personalized and exam-aware.")


def generate_context_aware_recommendations(student_context, ml_profile, bkt_needs_review):
    """
    Generate AI recommendations with structured context injection
    This is where we inject student profile before LLM calls
    """
    recommendations = []
    
    # Ability-based recommendations
    ability = ml_profile['ability']
    accuracy = student_context['accuracy']
    
    # Context-aware difficulty recommendation
    if ability < 0.4:
        recommendations.append({
            'type': 'info',
            'message': f"🎯 **{student_context['exam']} Strategy:** Your current level ({ability*5:.1f}/5) suggests focusing on fundamentals. Given your {student_context['negative_marking_risk']} negative marking risk, stick to questions you're 70%+ confident about."
        })
    elif ability > 0.7:
        recommendations.append({
            'type': 'success',
            'message': f"🌟 **Advanced Level ({ability*5:.1f}/5):** Challenge yourself! Your {student_context['negative_marking_risk']} negative marking risk means you can afford to attempt harder questions. Target difficulty 4-5/5."
        })
    
    # Time pressure recommendation
    if student_context['panic_under_pressure'] == 'YES':
        avg_time = student_context['avg_time']
        if avg_time < 15:
            recommendations.append({
                'type': 'warning',
                'message': f"⚡ **Time Pressure Alert:** You're averaging {avg_time:.1f}s per question (very fast). For {student_context['exam']}, this suggests rushing. Aim for 25-30s to reduce errors, especially on your weak topics: {', '.join(student_context['weak_topics'][:2])}."
            })
        else:
            recommendations.append({
                'type': 'warning',
                'message': f"🕐 **Time Management:** You're taking {avg_time:.1f}s per question (slow). For {student_context['exam']}, practice time-bound sets. Start with easier questions to build speed, then gradually increase difficulty."
            })
    
    # Velocity-based recommendations
    velocity = ml_profile.get('learning_velocity', 0)
    if velocity < -0.05:
        recommendations.append({
            'type': 'error',
            'message': f"📉 **Performance Declining ({velocity*100:.1f}%):** Your accuracy is dropping. Given your weak topics ({', '.join(student_context['weak_topics'][:3])}), take a 1-day break, then revise fundamentals before attempting new questions."
        })
    elif velocity > 0.15:
        recommendations.append({
            'type': 'success',
            'message': f"🚀 **Rapid Growth ({velocity*100:.1f}%/session):** Excellent momentum! Your {student_context['strategy_preference']} is working. Keep this pace but also review your strong topics every 7 days to prevent forgetting."
        })
    
    # BKT-based review recommendations
    if bkt_needs_review and len(bkt_needs_review) > 0:
        top_review = bkt_needs_review[0]
        recommendations.append({
            'type': 'warning',
            'message': f"🔄 **Urgent Review:** {top_review['subject']}: {top_review['topic']} needs immediate attention. Mastery: {top_review['mastery']*100:.0f}%. Reasons: {', '.join(top_review['reasons'])}. Allocate 60% of your next session to this."
        })
    
    # Strategy recommendation based on negative marking
    if student_context['negative_marking_risk'] == 'HIGH':
        recommendations.append({
            'type': 'info',
            'message': f"⚠️ **{student_context['exam']} Strategy:** With {accuracy*100:.0f}% accuracy (HIGH negative marking risk), adopt conservative strategy: Skip questions where you're <60% confident. Focus on accuracy over quantity."
        })
    elif student_context['negative_marking_risk'] == 'LOW':
        recommendations.append({
            'type': 'success',
            'message': f"✅ **{student_context['exam']} Strategy:** With {accuracy*100:.0f}% accuracy (LOW negative marking risk), you can be aggressive. Attempt all questions within your optimal difficulty range ({ml_profile['optimal_difficulty_range'][0]*5:.1f}-{ml_profile['optimal_difficulty_range'][1]*5:.1f})."
        })
    
    # Weak topic prioritization
    if student_context['weak_topics']:
        weakest = student_context['weak_topics'][0]
        mastery = student_context['mastery_scores'].get(weakest, 0)
        recommendations.append({
            'type': 'info',
            'message': f"📚 **Priority Focus:** {weakest} ({mastery*100:.0f}% mastery) should be your #1 priority. In {student_context['exam']}, this topic typically has 8-12% weightage. Improving to 70% could add 5-8 marks."
        })
    
    return recommendations


def enhance_adaptive_practice(user_id, db, available_questions):
    """
    Enhance existing adaptive practice with ML + Context Injection
    Call this in your adaptive practice function
    """
    predictor = st.session_state.ml_predictor
    collector = MLDataCollector(db)
    
    st.markdown("### 🧠 ML-Powered Question Selection")
    
    # Get student history
    student_history = collector.get_student_history(user_id)
    
    # Get student context
    student_context = build_student_context(user_id, db)
    
    if not predictor.is_trained or len(student_history) < 5:
        st.info("📊 ML model is learning... Using standard adaptive practice for now.")
        st.caption(f"Current profile: {student_context['ability_level']}")
        return available_questions[:10]
    
    # Use ML to select optimal questions
    optimal_questions = predictor.select_optimal_questions(
        user_id,
        available_questions,
        student_history,
        count=10
    )
    
    # Show what ML did with context
    with st.expander("🔍 See How ML Selected These Questions"):
        st.markdown("**Your Context:**")
        st.code(student_context['context_string'], language='text')
        
        student_ability = predictor.predict_student_ability(user_id, student_history)
        
        st.markdown(f"**Selection Strategy:**")
        st.write(f"- Your Ability: {student_ability*5:.1f}/5.0")
        st.write(f"- Optimal Range: {(student_ability-0.05)*5:.1f} - {(student_ability+0.2)*5:.1f}")
        st.write(f"- Strategy: {student_context['strategy_preference']}")
        st.write(f"- Time Pressure: {student_context['panic_under_pressure']}")
        
        st.markdown("**Selected Questions:**")
        for i, q in enumerate(optimal_questions[:3], 1):
            difficulty = predictor.predict_difficulty(
                q.get('question', ''),
                q.get('subject', 'Physics'),
                q.get('topic', ''),
                user_id,
                student_history
            )
            st.write(f"{i}. Difficulty: {difficulty*5:.1f}/5.0 - {q.get('topic', 'Unknown topic')}")
    
    return optimal_questions


def render_ml_training_section(db):
    """
    Show ML model training interface
    Add this as a section in settings or admin panel
    """
    st.markdown("### 🤖 ML Model Management")
    
    trainer = st.session_state.ml_trainer
    
    # Get stats
    stats = trainer.get_model_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_icon = "✅" if stats['is_trained'] else "⏳"
        st.metric("Model Status", f"{status_icon} {'Trained' if stats['is_trained'] else 'Not Trained'}")
    
    with col2:
        st.metric("Training Data", f"{stats['training_samples']} questions")
    
    with col3:
        st.metric("Students", stats['unique_students'])
    
    with col4:
        st.metric("Coverage", f"{stats['subjects_covered']} subjects")
    
    st.divider()
    
    # Training controls
    if not stats['is_trained']:
        if stats['training_samples'] >= 20:
            st.success("✅ Ready to train! You have enough data.")
            if st.button("🚀 Train ML Model Now", type="primary", use_container_width=True):
                with st.spinner("Training ML model... This may take 1-2 minutes..."):
                    success = trainer.train_model()
                    if success:
                        st.success("🎉 Model trained successfully!")
                        st.balloons()
                        st.rerun()
        else:
            needed = 20 - stats['training_samples']
            st.info(f"📊 Collecting data... Need {needed} more questions with student attempts to train the model.")
            st.progress(stats['training_samples'] / 20, text=f"Progress: {stats['training_samples']}/20")
    else:
        st.success("✅ ML model is active and making predictions!")
        
        if st.button("🔄 Retrain Model (with new data)"):
            with st.spinner("Retraining..."):
                trainer.train_model()
                st.success("Model retrained!")
                st.rerun()


def render_ability_trend(student_history):
    """Render ability trend over time"""
    st.markdown("#### 📊 Your Ability Over Time")
    
    # Calculate rolling ability
    window_size = 10
    abilities = []
    timestamps = []
    
    for i in range(len(student_history) - window_size + 1):
        window = student_history[i:i+window_size]
        accuracy = sum(1 for a in window if a['is_correct']) / len(window)
        abilities.append(accuracy * 5)
        timestamps.append(i + window_size)
    
    # Create chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(range(len(abilities))),
        y=abilities,
        mode='lines+markers',
        name='Ability',
        line=dict(color='#10B981', width=3),
        marker=dict(size=8)
    ))
    
    # Add trend line
    if len(abilities) > 3:
        z = np.polyfit(range(len(abilities)), abilities, 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=list(range(len(abilities))),
            y=p(range(len(abilities))),
            mode='lines',
            name='Trend',
            line=dict(color='rgba(255, 0, 0, 0.5)', width=2, dash='dash')
        ))
    
    fig.update_layout(
        xaxis_title="Practice Session",
        yaxis_title="Ability Level (1-5)",
        yaxis=dict(range=[0, 5]),
        template='plotly_white',
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _calculate_simple_profile(student_history):
    """Simple profile calculation when ML model isn't trained yet"""
    if not student_history:
        return {
            'ability': 0.5,
            'ability_level': 'Intermediate (3/5)',
            'strong_topics': [],
            'weak_topics': [],
            'learning_velocity': 0,
            'total_attempts': 0,
            'optimal_difficulty_range': (0.45, 0.65)
        }
    
    # Calculate overall accuracy
    accuracy = sum(1 for a in student_history if a['is_correct']) / len(student_history)
    
    # Topic performance
    from collections import defaultdict
    topic_perf = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    for attempt in student_history:
        topic = f"{attempt.get('subject', 'Unknown')}: {attempt.get('topic', 'Unknown')}"
        topic_perf[topic]['total'] += 1
        if attempt['is_correct']:
            topic_perf[topic]['correct'] += 1
    
    topic_abilities = {
        topic: perf['correct'] / perf['total']
        for topic, perf in topic_perf.items()
        if perf['total'] > 0
    }
    
    strong = sorted(topic_abilities.items(), key=lambda x: x[1], reverse=True)[:3]
    weak = sorted(topic_abilities.items(), key=lambda x: x[1])[:3]
    
    # Learning velocity
    if len(student_history) >= 20:
        first_half = student_history[:len(student_history)//2]
        second_half = student_history[len(student_history)//2:]
        first_acc = sum(1 for a in first_half if a['is_correct']) / len(first_half)
        second_acc = sum(1 for a in second_half if a['is_correct']) / len(second_half)
        velocity = second_acc - first_acc
    else:
        velocity = 0
    
    # Determine level
    if accuracy < 0.2:
        level = "Beginner (1/5)"
    elif accuracy < 0.4:
        level = "Elementary (2/5)"
    elif accuracy < 0.6:
        level = "Intermediate (3/5)"
    elif accuracy < 0.8:
        level = "Advanced (4/5)"
    else:
        level = "Expert (5/5)"
    
    return {
        'ability': accuracy,
        'ability_level': level,
        'strong_topics': strong,
        'weak_topics': weak,
        'learning_velocity': velocity,
        'total_attempts': len(student_history),
        'optimal_difficulty_range': (accuracy - 0.05, accuracy + 0.2)
    }


# Import numpy for trend line
import numpy as np


# Export
__all__ = [
    'initialize_ml_system',
    'build_student_context',
    'render_unified_insights_tab',
    'enhance_adaptive_practice',
    'render_ml_training_section'
]