"""
analytics.py - Advanced Analytics and Visualization
UPDATED: Enhanced for ML+BKT unified insights integration
Compatible with AuthDatabase (no knowledge_nodes table dependency)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from ui_professional import render_progress_bar as render_mastery_bar

# Simple fallback functions
def render_insight_card(type, message, confidence=0.8):
    import streamlit as st
    icons = {'performance': '📊', 'recommendation': '💡', 'behavior': '🎯', 'warning': '⚠️', 
             'success': '✅', 'info': 'ℹ️', 'error': '❌'}
    icon = icons.get(type, '💡')
    
    if type == 'success':
        st.success(f"{icon} {message}")
    elif type == 'warning':
        st.warning(f"{icon} {message}")
    elif type == 'error':
        st.error(f"{icon} {message}")
    else:
        st.info(f"{icon} {message}")

def render_knowledge_node(subject, topic, mastery, attempts, last_practiced):
    import streamlit as st
    
    # Color code based on mastery
    if mastery >= 70:
        color = "🟢"
    elif mastery >= 40:
        color = "🟡"
    else:
        color = "🔴"
    
    st.markdown(f"{color} **{topic}**")
    st.progress(mastery/100, text=f"{mastery:.0f}% mastery")
    st.caption(f"{attempts} attempts • Last: {last_practiced}")

def render_analytics_dashboard(user_id, db):
    """Render comprehensive analytics dashboard"""
    st.markdown("### 📊 Analytics Hub")
    st.caption("Deep insights into your learning journey")
    
    # Get data
    analytics = db.get_analytics_data(user_id)
    overall = analytics['overall']
    
    if overall[0] == 0:
        # This should rarely show now — app.py guards with render_empty_state first
        # But kept as a safety fallback
        st.info("📚 Take your first exam from the **Upload & Take Exam** tab to unlock analytics!")
        return
    
    # Overall metrics
    render_overall_metrics(overall)
    
    st.divider()
    
    # Two-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        render_daily_progress_chart(analytics['daily'])
        render_difficulty_distribution(analytics['by_difficulty'])
    
    with col2:
        render_topic_performance_chart(analytics['topics'])
        render_accuracy_trend(analytics['daily'])
    
    st.divider()
    
    # Topic mastery heatmap
    render_topic_heatmap(analytics['topics'])
    
    st.divider()
    
    # AI-powered insights (basic - full insights in ML+BKT tab)
    render_ai_insights(user_id, db, analytics)

def render_overall_metrics(overall):
    """Render top-level KPI metrics"""
    total_q, correct, avg_time, study_days, first, last = overall
    
    accuracy = (correct / total_q * 100) if total_q > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📝 Total Questions",
            value=total_q,
            delta=None
        )
    
    with col2:
        st.metric(
            label="🎯 Overall Accuracy",
            value=f"{accuracy:.1f}%",
            delta=None
        )
    
    with col3:
        avg_time_display = f"{avg_time:.1f}s" if avg_time else "N/A"
        st.metric(
            label="⚡ Avg Time/Question",
            value=avg_time_display,
            delta=None
        )
    
    with col4:
        st.metric(
            label="📅 Study Days",
            value=study_days,
            delta=None
        )

def render_daily_progress_chart(daily_data):
    """Render daily progress line chart"""
    st.markdown("#### 📈 Daily Progress")
    
    if not daily_data or len(daily_data) == 0:
        st.info("No daily data yet")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(daily_data, columns=['date', 'questions', 'accuracy', 'avg_time'])
    df = df.sort_values('date')
    
    # Create dual-axis chart
    fig = go.Figure()
    
    # Questions attempted (bar)
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['questions'],
        name='Questions',
        marker_color='rgba(102, 126, 234, 0.6)',
        yaxis='y'
    ))
    
    # Accuracy trend (line)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['accuracy'],
        name='Accuracy %',
        mode='lines+markers',
        marker=dict(color='#10B981', size=8),
        line=dict(color='#10B981', width=3),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='Daily Activity & Accuracy Trend',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Questions Attempted', side='left'),
        yaxis2=dict(title='Accuracy %', side='right', overlaying='y', range=[0, 100]),
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_topic_performance_chart(topics_data):
    """Render topic-wise performance"""
    st.markdown("#### 📚 Topic Performance")
    
    if not topics_data or len(topics_data) == 0:
        st.info("No topic data yet")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(topics_data, 
                     columns=['subject', 'topic', 'attempts', 'accuracy', 
                             'mastery', 'confidence', 'avg_time'])
    
    # Sort by accuracy
    df = df.sort_values('accuracy', ascending=True).head(10)
    
    # Create horizontal bar chart
    fig = px.bar(
        df,
        x='accuracy',
        y='topic',
        orientation='h',
        color='accuracy',
        color_continuous_scale=['#EF4444', '#F59E0B', '#10B981'],
        labels={'accuracy': 'Accuracy %', 'topic': 'Topic'},
        title='Topics by Accuracy (Lower = Needs Practice)'
    )
    
    fig.update_layout(
        template='plotly_white',
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_difficulty_distribution(difficulty_data):
    """Render difficulty distribution"""
    st.markdown("#### 💪 Performance by Difficulty")
    
    if not difficulty_data or len(difficulty_data) == 0:
        st.info("No difficulty data yet")
        return
    
    df = pd.DataFrame(difficulty_data, columns=['difficulty', 'attempts', 'accuracy'])
    
    # Create grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['difficulty'],
        y=df['attempts'],
        name='Attempts',
        marker_color='rgba(102, 126, 234, 0.6)'
    ))
    
    fig.add_trace(go.Bar(
        x=df['difficulty'],
        y=df['accuracy'],
        name='Accuracy %',
        marker_color='rgba(16, 185, 129, 0.6)'
    ))
    
    fig.update_layout(
        title='Questions Attempted vs Accuracy by Difficulty',
        xaxis=dict(title='Difficulty Level'),
        yaxis=dict(title='Count / Percentage'),
        barmode='group',
        template='plotly_white',
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_accuracy_trend(daily_data):
    """Render accuracy improvement trend"""
    st.markdown("#### 📊 Accuracy Improvement Trend")
    
    if not daily_data or len(daily_data) < 3:
        st.info("Need more data for trend analysis")
        return
    
    df = pd.DataFrame(daily_data, columns=['date', 'questions', 'accuracy', 'avg_time'])
    df = df.sort_values('date')
    
    # Calculate 7-day moving average
    df['ma7'] = df['accuracy'].rolling(window=min(7, len(df)), min_periods=1).mean()
    
    fig = go.Figure()
    
    # Daily accuracy (scatter)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['accuracy'],
        mode='markers',
        name='Daily',
        marker=dict(color='rgba(102, 126, 234, 0.5)', size=8)
    ))
    
    # Moving average (line)
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['ma7'],
        mode='lines',
        name='7-Day Avg',
        line=dict(color='#10B981', width=3)
    ))
    
    fig.update_layout(
        title='Accuracy Over Time with Moving Average',
        xaxis=dict(title='Date'),
        yaxis=dict(title='Accuracy %', range=[0, 100]),
        template='plotly_white',
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_topic_heatmap(topics_data):
    """Render topic mastery heatmap"""
    st.markdown("#### 🗺️ Topic Mastery Heatmap")
    
    if not topics_data or len(topics_data) == 0:
        st.info("No topic data for heatmap")
        return
    
    df = pd.DataFrame(topics_data,
                     columns=['subject', 'topic', 'attempts', 'accuracy',
                             'mastery', 'confidence', 'avg_time'])
    
    # Pivot for heatmap
    pivot = df.pivot_table(
        values='mastery',
        index='topic',
        columns='subject',
        aggfunc='mean',
        fill_value=0
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[
            [0, '#FEE2E2'],
            [0.4, '#FEF3C7'],
            [0.7, '#D1FAE5'],
            [1, '#10B981']
        ],
        text=pivot.values.round(1),
        texttemplate='%{text}%',
        textfont={"size": 10},
        colorbar=dict(title="Mastery %")
    ))
    
    fig.update_layout(
        title='Mastery Level Across Subjects & Topics',
        xaxis=dict(title='Subject'),
        yaxis=dict(title='Topic'),
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_ai_insights(user_id, db, analytics):
    """Render AI-generated insights (basic version)"""
    st.markdown("#### 🧠 Quick Insights")
    st.caption("💡 For comprehensive AI insights, check the ML+BKT Insights tab")
    
    insights = db.get_learning_insights(user_id)
    
    if insights:
        for insight in insights[:3]:  # Show only top 3
            render_insight_card(
                insight['type'],
                insight['message'],
                insight.get('confidence', 0.8)
            )
    
    # Performance summary
    overall = analytics['overall']
    total_q = overall[0]
    correct = overall[1]
    accuracy = (correct / total_q * 100) if total_q > 0 else 0
    
    # Generate dynamic insights
    if accuracy >= 80:
        render_insight_card('success', 
            f"Excellent performance! Your {accuracy:.1f}% accuracy shows strong understanding. "
            "Consider challenging yourself with harder difficulty levels.",
            0.9)
    elif accuracy < 50:
        render_insight_card('warning',
            f"Your {accuracy:.1f}% accuracy suggests some concepts need review. "
            "Focus on understanding fundamentals before moving to complex problems.",
            0.85)
    
    # Study consistency insight
    study_days = overall[3]
    if study_days >= 5:
        render_insight_card('info',
            f"Great consistency! You've studied {study_days} different days. "
            "Regular practice is key to retention.",
            0.9)
    elif total_q >= 10 and study_days < 3:
        render_insight_card('warning',
            "Try spreading your practice across more days for better retention "
            "instead of intensive sessions.",
            0.75)

def render_knowledge_graph(user_id, db):
    """Render interactive knowledge graph visualization - Compatible with AuthDatabase"""
    st.markdown("### 🧠 Knowledge Graph")
    st.caption("Visual map of your learning progress across topics")
    
    # Get topic performance from attempts table (no knowledge_nodes needed)
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT 
            subject,
            topic,
            COUNT(*) as practice_count,
            CAST(SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100 as mastery_level,
            MAX(timestamp) as last_practiced
        FROM attempts
        WHERE user_id = ? AND subject IS NOT NULL AND topic IS NOT NULL
        GROUP BY subject, topic
        ORDER BY subject, topic
    """, (user_id,))
    
    nodes = cursor.fetchall()
    
    if not nodes:
        st.info("📚 Start practicing to build your knowledge graph!")
        st.markdown("""
        **Knowledge graphs help you:**
        - Visualize topic dependencies
        - Identify knowledge gaps
        - Track mastery progress
        - Plan efficient study paths
        """)
        return
    
    # Group by subject
    subjects = {}
    for node in nodes:
        subject, topic, practice_count, mastery_level, last_practiced = node
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append({
            'topic': topic,
            'subtopic': topic,
            'mastery': mastery_level,
            'attempts': practice_count,
            'last_practiced': last_practiced,
            'confidence': min(practice_count / 10.0, 1.0) * 100
        })
    
    # Render each subject
    for subject, topics in subjects.items():
        st.markdown(f"#### 📖 {subject}")
        
        # Create columns for topics
        cols = st.columns(min(3, len(topics)))
        
        for idx, topic_data in enumerate(topics):
            with cols[idx % 3]:
                render_knowledge_node(
                    subject,
                    topic_data['subtopic'],
                    topic_data['mastery'],
                    topic_data['attempts'],
                    topic_data['last_practiced']
                )
        
        # Mastery summary
        avg_mastery = sum(t['mastery'] for t in topics) / len(topics)
        render_mastery_bar(avg_mastery, f"{subject} Overall Mastery")
        
        st.divider()
    
    # Overall knowledge graph stats
    st.markdown("#### 📊 Knowledge Graph Statistics")
    
    total_nodes = len(nodes)
    mastered = sum(1 for n in nodes if n[3] >= 70)
    in_progress = sum(1 for n in nodes if 40 <= n[3] < 70)
    needs_work = sum(1 for n in nodes if n[3] < 40)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📚 Total Topics", total_nodes)
    with col2:
        st.metric("✅ Mastered", mastered, f"{mastered/total_nodes*100:.0f}%" if total_nodes > 0 else "0%")
    with col3:
        st.metric("📈 In Progress", in_progress)
    with col4:
        st.metric("🎯 Needs Focus", needs_work)


def render_study_streak_calendar(user_id, db):
    """Render a calendar showing study streak"""
    st.markdown("### 📅 Study Streak Calendar")
    
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT DATE(timestamp) as date, COUNT(*) as questions
        FROM attempts
        WHERE user_id = ?
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 90
    """, (user_id,))
    
    data = cursor.fetchall()
    
    if not data:
        st.info("No study data yet")
        return
    
    # Create calendar visualization
    df = pd.DataFrame(data, columns=['date', 'questions'])
    df['date'] = pd.to_datetime(df['date'])
    
    fig = px.density_heatmap(
        df,
        x=df['date'].dt.day_name(),
        y=df['date'].dt.isocalendar().week,
        z='questions',
        color_continuous_scale='Greens',
        title='Study Activity Heatmap (Last 90 Days)'
    )
    
    fig.update_layout(
        xaxis_title='Day of Week',
        yaxis_title='Week',
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Streak calculation
    dates = sorted([d[0] for d in data], reverse=True)
    current_streak = 1
    
    for i in range(len(dates) - 1):
        d1 = datetime.strptime(dates[i], '%Y-%m-%d')
        d2 = datetime.strptime(dates[i+1], '%Y-%m-%d')
        if (d1 - d2).days == 1:
            current_streak += 1
        else:
            break
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔥 Current Streak", f"{current_streak} days")
    with col2:
        st.metric("📊 Total Study Days", len(dates))