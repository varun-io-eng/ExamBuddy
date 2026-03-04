"""
advanced_features_ui.py - UI Components for Advanced ML Features
Renders tabs for Bayesian Knowledge Tracing, Concept Coverage, and Error Analysis
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime


def render_bayesian_knowledge_tab(user_id, db, bkt_tracker):
    """
    Render Bayesian Knowledge Tracing Tab
    Shows probabilistic mastery levels and forgetting risks
    """
    st.markdown("## 🧠 Bayesian Knowledge State")
    st.caption("Probabilistic model of your knowledge across all topics")
    
    # Get all concept masteries
    all_masteries = bkt_tracker.get_all_concept_masteries(user_id)
    
    if not all_masteries:
        st.info("📚 Start practicing to build your knowledge state model!")
        st.markdown("""
        **What you'll see here:**
        - 🎯 Probability you've mastered each concept (P(knows))
        - ⏰ Forgetting risk based on time since practice
        - 📈 Learning velocity (rate of improvement)
        - 🔮 Predicted exam performance
        - 📋 Smart review recommendations
        """)
        return
    
    # Overall stats
    st.markdown("### 📊 Overall Knowledge State")
    
    avg_mastery = sum(m['mastery_probability'] for m in all_masteries) / len(all_masteries)
    high_risk_count = sum(1 for m in all_masteries if m['forgetting_risk'] == 'high')
    mastered_count = sum(1 for m in all_masteries if m['mastery_probability'] >= 0.7)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Average Mastery P(knows)",
            f"{avg_mastery*100:.1f}%",
            help="Average probability you know each concept"
        )
    
    with col2:
        st.metric(
            "Mastered Concepts",
            f"{mastered_count}/{len(all_masteries)}",
            help="Concepts with P(knows) ≥ 70%"
        )
    
    with col3:
        st.metric(
            "High Forgetting Risk",
            high_risk_count,
            delta=f"{-high_risk_count if high_risk_count > 0 else 0}",
            delta_color="inverse",
            help="Concepts not practiced in 14+ days"
        )
    
    with col4:
        total_attempts = sum(m['attempts'] for m in all_masteries)
        st.metric(
            "Total Practice Sessions",
            total_attempts,
            help="Total questions answered"
        )
    
    st.divider()
    
    # Detailed concept breakdown
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📚 Concept Mastery Details")
        render_mastery_table(all_masteries)
    
    with col2:
        st.markdown("### ⚠️ Review Priorities")
        render_review_recommendations(bkt_tracker, user_id)
    
    st.divider()
    
    # Mastery distribution
    render_mastery_distribution(all_masteries)
    
    st.divider()
    
    # Optimal practice recommendations
    st.markdown("### 🎯 Optimal Practice Plan (Spaced Repetition)")
    optimal_topics = bkt_tracker.get_optimal_practice_topics(user_id, count=10)
    
    if optimal_topics:
        for i, topic in enumerate(optimal_topics[:5], 1):
            with st.expander(f"{i}. {topic['subject']} → {topic['topic']}", expanded=(i==1)):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**Reason:** {topic['reason']}")
                    st.progress(
                        topic['mastery'], 
                        text=f"Current Mastery: {topic['mastery']*100:.0f}%"
                    )
                
                with col2:
                    st.metric("Days Since Practice", topic['days_since'])
                    st.metric("Priority Score", f"{topic['score']:.0f}")


def render_mastery_table(all_masteries):
    """Render detailed mastery table"""
    # Sort by mastery probability
    sorted_masteries = sorted(all_masteries, key=lambda x: x['mastery_probability'])
    
    for mastery in sorted_masteries:
        # Color coding
        if mastery['mastery_probability'] >= 0.7:
            color = "🟢"
            status = "Mastered"
        elif mastery['mastery_probability'] >= 0.4:
            color = "🟡"
            status = "Developing"
        else:
            color = "🔴"
            status = "Needs Work"
        
        # Forgetting risk
        risk_icons = {'low': '✅', 'medium': '⚠️', 'high': '🚨'}
        risk_icon = risk_icons.get(mastery['forgetting_risk'], '❓')
        
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"{color} **{mastery['subject']} → {mastery['topic']}**")
                if mastery['subtopic']:
                    st.caption(f"└─ {mastery['subtopic']}")
            
            with col2:
                st.metric(
                    "P(knows)",
                    f"{mastery['mastery_probability']*100:.1f}%",
                    delta=f"{mastery['learning_velocity']*100:+.1f}%" if abs(mastery['learning_velocity']) > 0.001 else None
                )
            
            with col3:
                st.write(f"{risk_icon} {mastery['forgetting_risk'].title()} Risk")
                st.caption(f"{mastery['days_since_practice']} days ago")
            
            with col4:
                st.caption(f"{mastery['attempts']} attempts")
            
            st.divider()


def render_review_recommendations(bkt_tracker, user_id):
    """Render review recommendations"""
    needs_review = bkt_tracker.get_concepts_needing_review(user_id, threshold=0.6)
    
    if not needs_review:
        st.success("🎉 All concepts well-maintained!")
        st.info("Keep practicing regularly to maintain mastery")
    else:
        st.warning(f"Found {len(needs_review)} concepts needing review")
        
        for concept in needs_review[:5]:
            priority_colors = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            
            priority_icon = priority_colors.get(concept['priority'], '❓')
            
            st.markdown(f"{priority_icon} **{concept['topic']}**")
            st.caption(f"Mastery: {concept['mastery']*100:.0f}%")
            
            for reason in concept['reasons'][:2]:
                st.caption(f"• {reason}")
            
            st.divider()


def render_mastery_distribution(all_masteries):
    """Render mastery distribution histogram"""
    st.markdown("### 📊 Mastery Distribution")
    
    mastery_values = [m['mastery_probability'] * 100 for m in all_masteries]
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=mastery_values,
        nbinsx=20,
        marker_color='rgba(99, 102, 241, 0.7)',
        marker_line_color='rgba(99, 102, 241, 1)',
        marker_line_width=1.5,
        name='Concepts'
    ))
    
    # Add vertical lines for thresholds
    fig.add_vline(x=40, line_dash="dash", line_color="orange", annotation_text="Developing")
    fig.add_vline(x=70, line_dash="dash", line_color="green", annotation_text="Mastered")
    
    fig.update_layout(
        title="Distribution of Concept Mastery Levels",
        xaxis_title="Mastery Probability (%)",
        yaxis_title="Number of Concepts",
        template='plotly_white',
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_concept_coverage_tab(user_id, db, question_generator):
    """
    Render Concept Coverage Tab
    Shows concept graph coverage and generates targeted questions
    """
    st.markdown("## 🗺️ Concept Coverage Analysis")
    st.caption("Identify knowledge gaps and generate targeted practice questions")
    
    # Subject selection
    subject = st.selectbox(
        "📚 Select Subject",
        ["Physics", "Chemistry", "Mathematics", "Biology"],
        key="coverage_subject_select"
    )
    
    # Get coverage analysis
    coverage = question_generator.analyze_concept_coverage(user_id, subject)
    report = question_generator.get_coverage_report(user_id, subject)
    
    # Overall stats
    st.markdown("### 📊 Coverage Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Concepts", report['total_concepts'])
    
    with col2:
        st.metric(
            "Coverage",
            f"{report['coverage_percentage']:.0f}%",
            help="Concepts you've attempted"
        )
    
    with col3:
        st.metric(
            "Mastery",
            f"{report['mastery_percentage']:.0f}%",
            help="Concepts with ≥70% mastery"
        )
    
    with col4:
        st.metric(
            "Needs Work",
            report['weak_count'],
            delta=f"-{report['weak_count']}",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Coverage visualization
    col1, col2 = st.columns([2, 3])
    
    with col1:
        render_coverage_pie_chart(coverage)
    
    with col2:
        st.markdown("### 📋 Coverage Breakdown")
        
        tabs = st.tabs(["🔴 Weak", "🟡 Developing", "🟢 Mastered", "⚪ Not Attempted"])
        
        with tabs[0]:  # Weak
            if coverage['weak']:
                for concept in coverage['weak'][:10]:
                    st.markdown(f"**{concept['topic']} → {concept['subtopic']}**")
                    st.progress(concept['mastery'], text=f"{concept['mastery']*100:.0f}%")
            else:
                st.success("No weak areas!")
        
        with tabs[1]:  # Developing
            if coverage['developing']:
                for concept in coverage['developing'][:10]:
                    st.markdown(f"**{concept['topic']} → {concept['subtopic']}**")
                    st.progress(concept['mastery'], text=f"{concept['mastery']*100:.0f}%")
            else:
                st.info("No concepts in development")
        
        with tabs[2]:  # Mastered
            if coverage['mastered']:
                for concept in coverage['mastered'][:10]:
                    st.success(f"**{concept['topic']} → {concept['subtopic']}** ✅")
            else:
                st.info("Keep practicing!")
        
        with tabs[3]:  # Not Attempted
            if coverage['not_attempted']:
                for concept in coverage['not_attempted'][:15]:
                    st.info(f"{concept['topic']} → {concept['subtopic']}")
            else:
                st.success("All concepts attempted!")
    
    st.divider()
    
    # Generate intelligent questions
    st.markdown("### 🎲 Generate Coverage-Aware Questions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        question_count = st.slider("Number of questions", 5, 20, 10)
    
    with col2:
        difficulty = st.selectbox(
            "Difficulty Mode",
            ["adaptive", "easy", "medium", "hard"]
        )
    
    if st.button("🚀 Generate Targeted Questions", type="primary"):
        with st.spinner("Generating questions targeting your gaps..."):
            questions = question_generator.generate_targeted_questions(
                user_id, subject, question_count, difficulty
            )
            
            if questions:
                st.success(f"✅ Generated {len(questions)} targeted questions!")
                
                # Show allocation
                st.markdown("**Question Allocation:**")
                allocation = {
                    'weak': sum(1 for q in questions if q.get('generated_by') == 'remediation'),
                    'new': sum(1 for q in questions if q.get('generated_by') == 'new_learning'),
                    'retention': sum(1 for q in questions if q.get('generated_by') == 'progression')
                }
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Weak Areas", allocation['weak'])
                with col2:
                    st.metric("New Concepts", allocation['new'])
                with col3:
                    st.metric("Retention Check", allocation['retention'])
                
                # Store in session state
                st.session_state.generated_questions = questions
                st.info("Questions ready! Go to Practice tab to attempt them.")
            else:
                st.error("Failed to generate questions. Try again.")


def render_coverage_pie_chart(coverage):
    """Render coverage distribution pie chart"""
    labels = ['Not Attempted', 'Weak (<50%)', 'Developing (50-70%)', 'Mastered (≥70%)']
    values = [
        len(coverage['not_attempted']),
        len(coverage['weak']),
        len(coverage['developing']),
        len(coverage['mastered'])
    ]
    colors = ['#94a3b8', '#ef4444', '#f59e0b', '#10b981']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker_colors=colors,
        hole=0.4,
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Concept Coverage Distribution",
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_error_analysis_tab(user_id, db, error_engine):
    """
    Render Error Analysis Tab
    Shows error taxonomy classification and fix strategies
    """
    st.markdown("## 🔬 Error Pattern Analysis")
    st.caption("Identify mistake patterns and get personalized remediation strategies")
    
    # Get error analysis
    days_to_analyze = st.slider(
        "Analyze last N days",
        min_value=3,
        max_value=30,
        value=7,
        help="Number of recent days to analyze"
    )
    
    error_analysis = error_engine.analyze_error_history(user_id, days=days_to_analyze)
    
    if error_analysis['total_errors'] == 0:
        st.info("🎯 No errors found in the selected period. Keep practicing!")
        
        st.markdown("""
        **What you'll see here:**
        - 📊 Error type distribution (12 categories)
        - 🔍 Persistent vs one-time mistakes
        - 💡 Personalized fix strategies
        - 📈 Error trend analysis
        - 🎯 Practice recommendations
        """)
        return
    
    # Overall error stats
    st.markdown("### 📊 Error Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Errors",
            error_analysis['total_errors'],
            help="Wrong answers in selected period"
        )
    
    with col2:
        st.metric(
            "Unique Error Types",
            len(error_analysis['top_error_types']),
            help="Different types of mistakes"
        )
    
    with col3:
        st.metric(
            "Persistent Errors",
            len(error_analysis['persistent_errors']),
            delta=f"-{len(error_analysis['persistent_errors'])}",
            delta_color="inverse",
            help="Errors repeated 3+ times"
        )
    
    with col4:
        if error_analysis['top_error_types']:
            most_common = error_analysis['top_error_types'][0]
            st.metric(
                "Most Common",
                most_common['type'].replace('_', ' ').title(),
                help=f"{most_common['count']} occurrences"
            )
    
    st.divider()
    
    # Error distribution
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_error_distribution_chart(error_analysis['top_error_types'])
    
    with col2:
        st.markdown("### 🚨 Persistent Errors")
        if error_analysis['persistent_errors']:
            for error_dict in error_analysis['persistent_errors'][:5]:
                error_type = error_dict['error_type']
                count = error_dict['frequency']
                st.error(f"**{error_type.replace('_', ' ').title()}**")
                st.caption(f"Occurred {count:.1f} times")
                st.divider()
        else:
            st.success("No persistent error patterns! 🎉")
    
    st.divider()
    
    # Fix strategies
    st.markdown("### 💡 Personalized Fix Strategies")
    
    if error_analysis['persistent_errors']:
        for error_dict in error_analysis['persistent_errors'][:3]:
            render_fix_strategy(error_dict['error_type'], error_dict['frequency'], error_engine)
    else:
        st.info("Practice more to identify patterns and get personalized strategies")


def render_error_distribution_chart(top_error_types):
    """Render error type distribution chart"""
    st.markdown("### 📊 Error Type Distribution")
    
    if not top_error_types:
        st.info("No error data available")
        return
    
    # Prepare data
    error_types = [error['type'].replace('_', ' ').title() for error in top_error_types]
    counts = [error['count'] for error in top_error_types]
    
    # Create bar chart
    fig = go.Figure(data=[go.Bar(
        x=counts,
        y=error_types,
        orientation='h',
        marker=dict(
            color=counts,
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title="Frequency")
        )
    )])
    
    fig.update_layout(
        title="Error Types by Frequency",
        xaxis_title="Number of Occurrences",
        yaxis_title="Error Type",
        template='plotly_white',
        height=max(300, len(error_types) * 30)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_fix_strategy(error_type, frequency, error_engine):
    """
    Render fix strategy for a specific error type
    
    FIXED: Changed function signature from invalid dict access to proper parameters
    """
    from error_taxonomy_engine import ErrorTaxonomy, FixStrategyEngine
    
    # Get error info
    error_info = ErrorTaxonomy.ERROR_TYPES.get(error_type, {})
    icon = error_info.get('icon', '❓')
    name = error_info.get('name', error_type.replace('_', ' ').title())
    severity = error_info.get('severity', 'medium')
    
    # Get fix strategy
    strategy = FixStrategyEngine.REMEDIATION_STRATEGIES.get(error_type, {})
    
    # Color based on severity
    severity_colors = {
        'high': '🔴',
        'medium': '🟡',
        'low': '🟢'
    }
    
    with st.expander(f"{icon} {name} ({frequency:.1f} occurrences)", expanded=(frequency >= 3)):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"**Diagnosis:** {error_info.get('description', 'Pattern detected')}")
            st.markdown(f"**Severity:** {severity_colors.get(severity, '')} {severity.title()}")
        
        with col2:
            st.metric("Occurrences", f"{frequency:.1f}")
        
        st.divider()
        
        if strategy:
            st.markdown("**🎯 Immediate Actions:**")
            for action in strategy.get('immediate_actions', []):
                st.markdown(f"✓ {action}")
            
            st.divider()
            
            st.markdown("**📚 Practice Recommendations:**")
            st.info(f"Complete {strategy.get('practice_count', 5)} {strategy.get('practice_type', 'practice')} questions at {strategy.get('difficulty', 'medium')} difficulty")
            
            st.markdown("**💡 Follow-up Check:**")
            st.success(strategy.get('follow_up', 'Review and practice carefully'))
        else:
            st.warning("No specific strategy available. Practice mindfully and review concepts.")


# Export all functions
__all__ = [
    'render_bayesian_knowledge_tab',
    'render_concept_coverage_tab',
    'render_error_analysis_tab'
]