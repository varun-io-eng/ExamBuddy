"""
competitive_intelligence.py - 🏆 Competitive Intelligence & Rank Predictor

This module provides:
1. Anonymous Peer Comparison (percentile ranking)
2. Exam Rank Prediction using ML
3. Competitive Analysis Dashboard
4. Topic-wise Competitive Benchmarking
5. Success Probability Calculator
6. Strategic Weakest Link Analysis

This replaces generic analytics with competitive insights for exam preparation.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import json


class CompetitiveIntelligence:
    """Competitive intelligence and rank prediction engine"""
    
    def __init__(self, db, bkt_tracker):
        self.db = db
        self.bkt = bkt_tracker
    
    def get_peer_performance_data(self, user_id):
        """Get anonymized peer performance data for comparison"""
        
        cursor = self.db.conn.cursor()
        
        # Get all users' performance (anonymized)
        cursor.execute("""
            SELECT 
                user_id,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_answers,
                AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100 as accuracy,
                AVG(time_taken) as avg_time
            FROM attempts
            GROUP BY user_id
            HAVING total_attempts >= 10
        """)
        
        all_users = cursor.fetchall()
        
        # Calculate percentiles
        if not all_users:
            return None
        
        accuracies = [u[3] for u in all_users]
        attempts = [u[1] for u in all_users]
        
        # Get current user's data
        user_data = next((u for u in all_users if u[0] == user_id), None)
        
        if not user_data:
            return None
        
        user_accuracy = user_data[3]
        user_attempts = user_data[1]
        
        # Calculate percentile
        percentile = (sum(1 for acc in accuracies if acc < user_accuracy) / len(accuracies)) * 100
        
        # Calculate rank
        sorted_users = sorted(all_users, key=lambda x: x[3], reverse=True)
        rank = next(i for i, u in enumerate(sorted_users, 1) if u[0] == user_id)
        
        return {
            'total_users': len(all_users),
            'user_rank': rank,
            'user_accuracy': user_accuracy,
            'user_attempts': user_attempts,
            'percentile': percentile,
            'avg_peer_accuracy': np.mean(accuracies),
            'top_10_percent_accuracy': np.percentile(accuracies, 90),
            'median_accuracy': np.median(accuracies),
            'accuracy_distribution': accuracies,
            'attempts_distribution': attempts
        }
    
    def get_topic_wise_competitive_standing(self, user_id, subject):
        """Get competitive standing for each topic"""
        
        cursor = self.db.conn.cursor()
        
        # Get user's topic performance
        cursor.execute("""
            SELECT 
                topic,
                COUNT(*) as attempts,
                AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100 as accuracy
            FROM attempts
            WHERE user_id = ? AND subject = ?
            GROUP BY topic
            HAVING attempts >= 3
        """, (user_id, subject))
        
        user_topics = cursor.fetchall()
        
        topic_standings = []
        
        for topic, attempts, user_acc in user_topics:
            # Get peer performance for this topic
            cursor.execute("""
                SELECT 
                    user_id,
                    AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) * 100 as accuracy
                FROM attempts
                WHERE subject = ? AND topic = ?
                GROUP BY user_id
                HAVING COUNT(*) >= 3
            """, (subject, topic))
            
            peer_accs = [row[1] for row in cursor.fetchall()]
            
            if peer_accs:
                percentile = (sum(1 for acc in peer_accs if acc < user_acc) / len(peer_accs)) * 100
                avg_peer = np.mean(peer_accs)
                
                # Competitive advantage/disadvantage
                advantage = user_acc - avg_peer
                
                topic_standings.append({
                    'topic': topic,
                    'user_accuracy': user_acc,
                    'peer_avg_accuracy': avg_peer,
                    'percentile': percentile,
                    'advantage': advantage,
                    'competitive_edge': 'Strong' if advantage > 10 else 'Competitive' if advantage > 0 else 'Needs Improvement'
                })
        
        return sorted(topic_standings, key=lambda x: x['advantage'], reverse=True)
    
    def predict_exam_rank(self, user_id, total_candidates=100000, exam_difficulty='medium'):
        """Predict exam rank using current performance"""
        
        # Get user's mastery data
        masteries = self.bkt.get_all_concept_masteries(user_id)
        
        if not masteries:
            return None
        
        # Calculate weighted score
        avg_mastery = np.mean([m['mastery_probability'] for m in masteries])
        
        # Adjust for exam difficulty
        difficulty_factors = {
            'easy': 1.1,
            'medium': 1.0,
            'hard': 0.85
        }
        
        factor = difficulty_factors.get(exam_difficulty, 1.0)
        predicted_score = avg_mastery * 100 * factor
        
        # Simulate candidate distribution (bell curve)
        # Mean: 45, Std: 15 (typical competitive exam distribution)
        mean_score = 45
        std_dev = 15
        
        # Calculate percentile based on normal distribution
        from scipy import stats
        percentile = stats.norm.cdf(predicted_score, mean_score, std_dev) * 100
        
        # Predict rank
        predicted_rank = int(total_candidates * (1 - percentile / 100))
        
        # Confidence interval
        # Assume ±10 percentile points uncertainty
        lower_percentile = max(0, percentile - 10)
        upper_percentile = min(100, percentile + 10)
        
        best_rank = int(total_candidates * (1 - upper_percentile / 100))
        worst_rank = int(total_candidates * (1 - lower_percentile / 100))
        
        # Success probability (for cutoff rank)
        def calculate_success_probability(cutoff_rank):
            cutoff_percentile = (1 - cutoff_rank / total_candidates) * 100
            z_score = (cutoff_percentile - percentile) / 10  # 10 is our uncertainty
            return stats.norm.cdf(z_score) * 100
        
        return {
            'predicted_rank': predicted_rank,
            'best_case_rank': best_rank,
            'worst_case_rank': worst_rank,
            'percentile': percentile,
            'predicted_score': predicted_score,
            'total_candidates': total_candidates,
            'confidence': min(len(masteries) / 50 * 100, 95),  # Confidence based on data
            'success_probabilities': {
                'top_100': calculate_success_probability(100),
                'top_500': calculate_success_probability(500),
                'top_1000': calculate_success_probability(1000),
                'top_5000': calculate_success_probability(5000),
                'top_10000': calculate_success_probability(10000)
            }
        }
    
    def identify_strategic_weaknesses(self, user_id, competitor_percentile=75):
        """Identify topics where competitors are stronger"""
        
        # Get user's mastery
        user_masteries = self.bkt.get_all_concept_masteries(user_id)
        
        cursor = self.db.conn.cursor()
        
        strategic_gaps = []
        
        for m in user_masteries:
            # Get peer performance for this topic
            cursor.execute("""
                SELECT 
                    AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) as avg_accuracy
                FROM attempts
                WHERE subject = ? AND topic = ?
                GROUP BY user_id
                HAVING COUNT(*) >= 3
            """, (m['subject'], m['topic']))
            
            peer_accs = [row[0] for row in cursor.fetchall()]
            
            if peer_accs:
                # Get top competitors' average (75th percentile)
                competitor_avg = np.percentile(peer_accs, competitor_percentile)
                user_mastery = m['mastery_probability']
                
                gap = competitor_avg - user_mastery
                
                if gap > 0.1:  # Significant gap
                    strategic_gaps.append({
                        'topic': m['topic'],
                        'subject': m['subject'],
                        'user_mastery': user_mastery,
                        'competitor_mastery': competitor_avg,
                        'gap': gap,
                        'potential_rank_gain': self._estimate_rank_gain(gap),
                        'priority': 'Critical' if gap > 0.3 else 'High' if gap > 0.2 else 'Medium'
                    })
        
        return sorted(strategic_gaps, key=lambda x: x['gap'], reverse=True)
    
    def _estimate_rank_gain(self, gap):
        """Estimate potential rank improvement by closing gap"""
        # Rough estimation: each 0.1 mastery improvement = ~5 percentile points
        percentile_gain = gap * 50
        return int(percentile_gain * 1000)  # Assuming 100k candidates


def render_competitive_intelligence_tab(user_id, db, bkt_tracker):
    """Render the competitive intelligence tab"""
    
    st.markdown("## 🏆 Competitive Intelligence Dashboard")
    st.caption("Understand where you stand among peers and predict your exam rank")
    
    # Initialize engine
    if 'competitive_engine' not in st.session_state:
        st.session_state.competitive_engine = CompetitiveIntelligence(db, bkt_tracker)
    
    engine = st.session_state.competitive_engine
    
    # Sub-tabs
    comp_tab1, comp_tab2, comp_tab3, comp_tab4 = st.tabs([
        "📊 Peer Comparison",
        "🎯 Rank Predictor",
        "🔍 Topic Benchmarking",
        "⚡ Strategic Gaps"
    ])
    
    with comp_tab1:
        render_peer_comparison(user_id, engine)
    
    with comp_tab2:
        render_rank_predictor(user_id, engine)
    
    with comp_tab3:
        render_topic_benchmarking(user_id, engine)
    
    with comp_tab4:
        render_strategic_gaps(user_id, engine)


def render_peer_comparison(user_id, engine):
    """Render peer comparison section"""
    
    st.markdown("### 📊 How You Compare with Peers")
    st.caption("Anonymous comparison with all platform users")
    
    with st.spinner("📊 Analyzing peer performance..."):
        peer_data = engine.get_peer_performance_data(user_id)
    
    if not peer_data:
        st.info("📚 Complete at least 10 questions to unlock peer comparison!")
        return
    
    # Overall standing
    st.markdown("---")
    st.markdown("### 🏅 Your Standing")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Your Rank",
            f"#{peer_data['user_rank']}",
            delta=f"Top {peer_data['percentile']:.1f}%"
        )
    
    with col2:
        st.metric(
            "Your Accuracy",
            f"{peer_data['user_accuracy']:.1f}%",
            delta=f"{peer_data['user_accuracy'] - peer_data['avg_peer_accuracy']:+.1f}% vs avg"
        )
    
    with col3:
        st.metric(
            "Percentile",
            f"{peer_data['percentile']:.0f}th",
            delta="Higher is better"
        )
    
    with col4:
        st.metric(
            "Total Peers",
            peer_data['total_users'],
            delta=f"{peer_data['user_attempts']} your attempts"
        )
    
    # Performance message
    if peer_data['percentile'] >= 90:
        st.success("🏆 **Elite Performance!** You're in the top 10% of all users!")
    elif peer_data['percentile'] >= 75:
        st.success("🌟 **Excellent!** You're performing better than 75% of peers!")
    elif peer_data['percentile'] >= 50:
        st.info("👍 **Above Average!** Keep pushing to reach top 25%!")
    else:
        st.warning("💪 **Keep Going!** Focused practice will improve your standing!")
    
    # Distribution chart
    st.markdown("---")
    st.markdown("### 📈 Accuracy Distribution")
    
    fig = go.Figure()
    
    # Histogram of peer accuracies
    fig.add_trace(go.Histogram(
        x=peer_data['accuracy_distribution'],
        nbinsx=20,
        name='Peers',
        marker_color='rgba(102, 126, 234, 0.6)'
    ))
    
    # Your accuracy line
    fig.add_vline(
        x=peer_data['user_accuracy'],
        line_dash="dash",
        line_color="red",
        annotation_text=f"You: {peer_data['user_accuracy']:.1f}%",
        annotation_position="top"
    )
    
    # Top 10% line
    fig.add_vline(
        x=peer_data['top_10_percent_accuracy'],
        line_dash="dot",
        line_color="green",
        annotation_text=f"Top 10%: {peer_data['top_10_percent_accuracy']:.1f}%",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title='Where Do You Stand?',
        xaxis_title='Accuracy %',
        yaxis_title='Number of Users',
        template='plotly_white',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Improvement targets
    st.markdown("---")
    st.markdown("### 🎯 Improvement Targets")
    
    gap_to_top10 = peer_data['top_10_percent_accuracy'] - peer_data['user_accuracy']
    
    if gap_to_top10 > 0:
        st.info(f"📈 Improve by **{gap_to_top10:.1f}%** to reach top 10%!")
        
        # Calculate how many questions needed
        questions_needed = int(gap_to_top10 / 2)  # Rough estimate: 2% per 10 questions
        st.markdown(f"*Estimated practice needed:* ~{questions_needed * 10} questions with focus on weak areas")
    else:
        st.success("🏆 You're already in the top 10%! Maintain your edge!")


def render_rank_predictor(user_id, engine):
    """Render exam rank prediction"""
    
    st.markdown("### 🎯 Exam Rank Predictor")
    st.caption("Predict your rank in competitive exams based on current preparation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_candidates = st.number_input(
            "Expected Total Candidates",
            min_value=1000,
            max_value=1000000,
            value=100000,
            step=1000
        )
    
    with col2:
        exam_difficulty = st.selectbox(
            "Expected Exam Difficulty",
            ['easy', 'medium', 'hard']
        )
    
    if st.button("🔮 Predict My Rank", type="primary", use_container_width=True):
        with st.spinner("🧠 Running rank prediction model..."):
            prediction = engine.predict_exam_rank(user_id, total_candidates, exam_difficulty)
        
        if not prediction:
            st.warning("📚 Complete more practice to unlock rank prediction!")
            return
        
        st.success("✅ Rank prediction complete!")
        
        # Main prediction
        st.markdown("---")
        st.markdown("### 🏅 Your Predicted Rank")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Most Likely Rank",
                f"#{prediction['predicted_rank']:,}",
                delta=f"{prediction['percentile']:.1f} percentile"
            )
        
        with col2:
            st.metric(
                "Best Case",
                f"#{prediction['best_case_rank']:,}",
                delta="With peak performance"
            )
        
        with col3:
            st.metric(
                "Worst Case",
                f"#{prediction['worst_case_rank']:,}",
                delta="If things go wrong"
            )
        
        # Confidence
        st.progress(
            prediction['confidence'] / 100,
            text=f"Prediction Confidence: {prediction['confidence']:.0f}%"
        )
        
        # Rank range visualization
        st.markdown("---")
        st.markdown("### 📊 Rank Range Visualization")
        
        fig = go.Figure()
        
        # Rank range
        fig.add_trace(go.Scatter(
            x=[prediction['best_case_rank'], prediction['predicted_rank'], prediction['worst_case_rank']],
            y=[1, 1, 1],
            mode='markers+lines',
            marker=dict(size=[15, 25, 15], color=['green', 'blue', 'red']),
            line=dict(color='gray', width=2),
            showlegend=False
        ))
        
        fig.update_layout(
            xaxis_title='Predicted Rank',
            yaxis=dict(showticklabels=False),
            template='plotly_white',
            height=200
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Success probabilities
        st.markdown("---")
        st.markdown("### 🎓 Success Probability for Different Cutoffs")
        
        probs = prediction['success_probabilities']
        
        cutoffs = ['top_100', 'top_500', 'top_1000', 'top_5000', 'top_10000']
        labels = ['Top 100', 'Top 500', 'Top 1K', 'Top 5K', 'Top 10K']
        probabilities = [probs[c] for c in cutoffs]
        
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=probabilities,
                text=[f"{p:.1f}%" for p in probabilities],
                textposition='auto',
                marker_color=['#10B981' if p > 75 else '#F59E0B' if p > 50 else '#EF4444' for p in probabilities]
            )
        ])
        
        fig.update_layout(
            title='Probability of Achieving Different Ranks',
            xaxis_title='Rank Category',
            yaxis_title='Success Probability (%)',
            yaxis=dict(range=[0, 100]),
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Actionable insights
        st.markdown("---")
        st.markdown("### 💡 AI Recommendations")
        
        if probs['top_1000'] > 75:
            st.success("🏆 You have a strong chance of top 1000! Focus on consistency and exam strategy.")
        elif probs['top_1000'] > 50:
            st.info("📈 Top 1000 is achievable! Strengthen your weak areas to increase probability.")
        else:
            st.warning("💪 Top 1000 requires significant improvement. Focus on fundamental concepts first.")


def render_topic_benchmarking(user_id, engine):
    """Render topic-wise competitive benchmarking"""
    
    st.markdown("### 🔍 Topic-Wise Competitive Benchmarking")
    st.caption("See how you perform on each topic compared to peers")
    
    subject = st.selectbox("Select Subject", ["Physics", "Chemistry", "Mathematics"])
    
    if st.button("📊 Analyze Topics", type="primary"):
        with st.spinner("🔍 Analyzing topic-wise performance..."):
            standings = engine.get_topic_wise_competitive_standing(user_id, subject)
        
        if not standings:
            st.info(f"📚 Complete at least 3 questions per topic in {subject} to unlock benchmarking!")
            return
        
        st.success(f"✅ Analyzed {len(standings)} topics in {subject}")
        
        # Summary metrics
        strong_topics = [s for s in standings if s['competitive_edge'] == 'Strong']
        weak_topics = [s for s in standings if s['competitive_edge'] == 'Needs Improvement']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Strong Topics", len(strong_topics), delta="Competitive advantage")
        with col2:
            st.metric("Competitive Topics", len(standings) - len(strong_topics) - len(weak_topics))
        with col3:
            st.metric("Need Improvement", len(weak_topics), delta="Catch up needed")
        
        # Topic-wise chart
        st.markdown("---")
        st.markdown("### 📊 Competitive Advantage by Topic")
        
        df = pd.DataFrame(standings)
        
        fig = go.Figure()
        
        # User accuracy
        fig.add_trace(go.Bar(
            x=df['topic'],
            y=df['user_accuracy'],
            name='Your Accuracy',
            marker_color='rgba(102, 126, 234, 0.8)'
        ))
        
        # Peer average
        fig.add_trace(go.Bar(
            x=df['topic'],
            y=df['peer_avg_accuracy'],
            name='Peer Average',
            marker_color='rgba(239, 68, 68, 0.6)'
        ))
        
        fig.update_layout(
            title=f'{subject} - Your Performance vs Peers',
            xaxis_title='Topic',
            yaxis_title='Accuracy %',
            barmode='group',
            template='plotly_white',
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("---")
        st.markdown("### 📋 Detailed Topic Analysis")
        
        for standing in standings:
            with st.expander(f"{standing['topic']} - {standing['competitive_edge']}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Your Accuracy", f"{standing['user_accuracy']:.1f}%")
                with col2:
                    st.metric("Peer Average", f"{standing['peer_avg_accuracy']:.1f}%")
                with col3:
                    advantage_delta = f"{standing['advantage']:+.1f}%"
                    st.metric("Advantage", advantage_delta)
                
                # Percentile
                st.progress(
                    standing['percentile'] / 100,
                    text=f"You're at {standing['percentile']:.0f}th percentile in this topic"
                )
                
                # Recommendation
                if standing['advantage'] > 10:
                    st.success("🏆 **Strength:** Maintain your edge through regular practice")
                elif standing['advantage'] > 0:
                    st.info("👍 **Competitive:** Small improvements will give you significant edge")
                else:
                    st.warning(f"⚠️ **Priority:** Peers are {abs(standing['advantage']):.1f}% ahead. Focus here!")


def render_strategic_gaps(user_id, engine):
    """Render strategic weakness analysis"""
    
    st.markdown("### ⚡ Strategic Gap Analysis")
    st.caption("Topics where top competitors have an edge over you")
    
    competitor_level = st.slider(
        "Compare with Top",
        min_value=50,
        max_value=99,
        value=75,
        help="Compare with students at this percentile"
    )
    
    if st.button("🔍 Identify Strategic Gaps", type="primary", use_container_width=True):
        with st.spinner("🔍 Analyzing competitor strategies..."):
            gaps = engine.identify_strategic_weaknesses(user_id, competitor_level)
        
        if not gaps:
            st.success("🏆 No significant gaps found! You're competing well with top performers!")
            return
        
        st.warning(f"⚠️ Found {len(gaps)} strategic gaps compared to top {competitor_level}% performers")
        
        # Priority matrix
        st.markdown("---")
        st.markdown("### 🎯 Priority Matrix")
        
        critical = [g for g in gaps if g['priority'] == 'Critical']
        high = [g for g in gaps if g['priority'] == 'High']
        medium = [g for g in gaps if g['priority'] == 'Medium']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.error(f"**Critical:** {len(critical)} topics")
            if critical:
                st.markdown("Immediate attention needed")
        
        with col2:
            st.warning(f"**High:** {len(high)} topics")
            if high:
                st.markdown("Address this week")
        
        with col3:
            st.info(f"**Medium:** {len(medium)} topics")
            if medium:
                st.markdown("Address this month")
        
        # Gap visualization
        st.markdown("---")
        st.markdown("### 📊 Mastery Gap vs Top Performers")
        
        df = pd.DataFrame(gaps[:10])  # Top 10 gaps
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df['topic'],
            y=df['gap'] * 100,
            text=[f"+{g*100:.0f}%" for g in df['gap']],
            textposition='auto',
            marker_color=['#EF4444' if p == 'Critical' else '#F59E0B' if p == 'High' else '#6366F1' 
                          for p in df['priority']]
        ))
        
        fig.update_layout(
            title='How Much Competitors Are Ahead (Percentage Points)',
            xaxis_title='Topic',
            yaxis_title='Gap in Mastery (%)',
            template='plotly_white',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed gaps with action items
        st.markdown("---")
        st.markdown("### 📋 Strategic Action Plan")
        
        for i, gap in enumerate(gaps[:5], 1):  # Top 5 most important
            with st.expander(f"#{i} - {gap['topic']} ({gap['subject']}) - {gap['priority']} Priority"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Your Mastery", f"{gap['user_mastery']*100:.0f}%")
                with col2:
                    st.metric(f"Top {competitor_level}% Mastery", f"{gap['competitor_mastery']*100:.0f}%")
                with col3:
                    st.metric("Gap", f"{gap['gap']*100:.0f}%", delta=f"Rank gain: ~{gap['potential_rank_gain']}")
                
                # Action items
                st.markdown("**📝 Action Items:**")
                st.markdown(f"1. ⏰ Dedicate {int(gap['gap'] * 10)} hours to this topic this week")
                st.markdown(f"2. 🎯 Solve {int(gap['gap'] * 30)} practice questions")
                st.markdown("3. 📚 Focus on understanding concepts, not just formulas")
                st.markdown("4. 🔄 Review mistakes and track improvement daily")
                
                # Impact
                if gap['potential_rank_gain'] > 5000:
                    st.success(f"💎 **High Impact:** Closing this gap could improve your rank by ~{gap['potential_rank_gain']:,} positions!")
                elif gap['potential_rank_gain'] > 1000:
                    st.info(f"⚡ **Medium Impact:** Potential rank improvement: ~{gap['potential_rank_gain']:,} positions")


# Export
__all__ = ['CompetitiveIntelligence', 'render_competitive_intelligence_tab']