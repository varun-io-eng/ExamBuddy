"""
ml_trainer.py - Collects Data and Trains ML Model
UPDATED: Enhanced for unified ML+BKT insights system
Runs in background to continuously improve the model
"""

import streamlit as st
from ml_difficulty_predictor import MLDifficultyPredictor
import numpy as np
from collections import defaultdict


class MLDataCollector:
    """
    Collects training data from student attempts
    Calculates true difficulty of questions
    """
    
    def __init__(self, db):
        self.db = db
    
    def calculate_question_difficulty(self, question_id, attempts):
        """
        Calculate true difficulty from student attempts
        
        Uses Item Response Theory (IRT) principles:
        - If many students get it wrong → Hard
        - If many students get it right → Easy
        - Adjusted for student ability
        """
        if not attempts or len(attempts) < 3:
            return 0.5  # Default medium
        
        # Simple version: percentage who got it wrong
        incorrect_count = sum(1 for a in attempts if not a['is_correct'])
        difficulty = incorrect_count / len(attempts)
        
        # Adjust for time taken
        avg_time = np.mean([a.get('time_taken', 30) for a in attempts])
        if avg_time > 60:
            difficulty += 0.1  # Time-consuming = harder
        elif avg_time < 20:
            difficulty -= 0.1  # Quick = easier
        
        # Clamp between 0 and 1
        difficulty = max(0.1, min(0.9, difficulty))
        
        return difficulty
    
    def collect_training_data(self):
        """
        Collect training data from database
        
        Returns list of training samples
        """
        print("📊 Collecting training data from database...")
        
        cursor = self.db.conn.cursor()
        
        # Get all unique questions that have been attempted
        cursor.execute("""
            SELECT DISTINCT question, subject, topic, difficulty
            FROM attempts
            WHERE question IS NOT NULL AND question != ''
        """)
        
        questions = cursor.fetchall()
        
        training_data = []
        
        for question, subject, topic, labeled_difficulty in questions:
            # Get all attempts for this question
            cursor.execute("""
                SELECT user_id, is_correct, time_taken
                FROM attempts
                WHERE question = ?
            """, (question,))
            
            attempts = cursor.fetchall()
            
            if len(attempts) < 3:
                continue  # Need at least 3 attempts to calculate difficulty
            
            # Convert to dict format
            attempts_list = [
                {
                    'user_id': a[0],
                    'is_correct': bool(a[1]),
                    'time_taken': a[2] if a[2] else 30
                }
                for a in attempts
            ]
            
            # Calculate true difficulty from actual performance
            true_difficulty = self.calculate_question_difficulty(question, attempts_list)
            
            training_data.append({
                'question': question,
                'subject': subject or 'Physics',
                'topic': topic or 'General',
                'labeled_difficulty': labeled_difficulty,
                'student_attempts': attempts_list,
                'true_difficulty': true_difficulty
            })
        
        print(f"✅ Collected {len(training_data)} training samples")
        return training_data
    
    def get_student_history(self, user_id):
        """Get student's attempt history with enhanced information"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT question, is_correct, time_taken, subject, topic, difficulty, timestamp
            FROM attempts
            WHERE user_id = ?
            ORDER BY timestamp ASC
        """, (user_id,))
        
        attempts = cursor.fetchall()
        
        history = []
        for a in attempts:
            history.append({
                'question': a[0],
                'is_correct': bool(a[1]),
                'time_taken': a[2] if a[2] else 30,
                'subject': a[3],
                'topic': a[4],
                'difficulty': a[5],
                'timestamp': a[6]
            })
        
        return history
    
    def get_student_performance_summary(self, user_id):
        """
        Get comprehensive performance summary for context building
        NEW METHOD for unified insights
        """
        history = self.get_student_history(user_id)
        
        if not history:
            return None
        
        # Calculate metrics
        total = len(history)
        correct = sum(1 for h in history if h['is_correct'])
        accuracy = correct / total if total > 0 else 0
        
        # Time analysis
        times = [h['time_taken'] for h in history if h['time_taken']]
        avg_time = sum(times) / len(times) if times else 30
        
        # Topic performance
        topic_perf = defaultdict(lambda: {'total': 0, 'correct': 0})
        for h in history:
            key = f"{h['subject']}: {h['topic']}"
            topic_perf[key]['total'] += 1
            if h['is_correct']:
                topic_perf[key]['correct'] += 1
        
        # Identify strengths and weaknesses
        topic_scores = {
            topic: perf['correct'] / perf['total']
            for topic, perf in topic_perf.items()
            if perf['total'] >= 3
        }
        
        strong_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        weak_topics = sorted(topic_scores.items(), key=lambda x: x[1])[:3]
        
        # Learning trend
        if total >= 20:
            recent = history[-10:]
            older = history[-20:-10]
            recent_acc = sum(1 for h in recent if h['is_correct']) / len(recent)
            older_acc = sum(1 for h in older if h['is_correct']) / len(older)
            trend = recent_acc - older_acc
        else:
            trend = 0
        
        return {
            'total_attempts': total,
            'accuracy': accuracy,
            'avg_time': avg_time,
            'strong_topics': strong_topics,
            'weak_topics': weak_topics,
            'learning_trend': trend,
            'time_pressure_indicator': 'HIGH' if avg_time < 15 or avg_time > 90 else 'NORMAL'
        }


class MLTrainer:
    """
    Trains and manages the ML model
    Enhanced for unified ML+BKT system
    """
    
    def __init__(self, db):
        self.db = db
        self.collector = MLDataCollector(db)
        self.predictor = MLDifficultyPredictor()
    
    def train_model(self, min_samples=20):
        """
        Train the ML model on collected data
        """
        # Collect data
        training_data = self.collector.collect_training_data()
        
        if len(training_data) < min_samples:
            st.warning(f"⚠️ Need at least {min_samples} questions with attempts to train. Currently have {len(training_data)}.")
            st.info("Keep practicing! The model will train automatically once enough data is collected.")
            return False
        
        # Train
        st.info("🧠 Training ML model... This may take a minute.")
        success = self.predictor.train(training_data, epochs=50)
        
        if success:
            st.success("✅ ML model trained successfully!")
            st.balloons()
            return True
        else:
            st.error("❌ Training failed. Need more data.")
            return False
    
    def check_and_retrain(self):
        """
        Check if model needs retraining
        Retrain if significant new data is available
        """
        # Count total attempts
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attempts")
        total_attempts = cursor.fetchone()[0]
        
        # Check if we have enough new data
        if total_attempts > 50 and not self.predictor.is_trained:
            return self.train_model()
        
        return self.predictor.is_trained
    
    def get_model_stats(self):
        """Get statistics about the trained model"""
        training_data = self.collector.collect_training_data()
        
        stats = {
            'is_trained': self.predictor.is_trained,
            'training_samples': len(training_data),
            'unique_students': len(set(
                a['user_id'] 
                for td in training_data 
                for a in td['student_attempts']
            )),
            'subjects_covered': len(set(td['subject'] for td in training_data)),
            'topics_covered': len(set(td['topic'] for td in training_data))
        }
        
        return stats
    
    def get_training_readiness(self):
        """
        Check if system is ready for training
        NEW METHOD for unified insights
        """
        stats = self.get_model_stats()
        
        readiness = {
            'ready': stats['training_samples'] >= 20,
            'progress': min(stats['training_samples'] / 20.0, 1.0),
            'samples_needed': max(0, 20 - stats['training_samples']),
            'quality_score': self._calculate_data_quality(stats)
        }
        
        return readiness
    
    def _calculate_data_quality(self, stats):
        """Calculate quality score of training data"""
        quality = 0
        
        # More samples = better
        if stats['training_samples'] >= 50:
            quality += 30
        elif stats['training_samples'] >= 30:
            quality += 20
        elif stats['training_samples'] >= 20:
            quality += 10
        
        # More students = better diversity
        if stats['unique_students'] >= 10:
            quality += 30
        elif stats['unique_students'] >= 5:
            quality += 20
        elif stats['unique_students'] >= 3:
            quality += 10
        
        # More subjects = better coverage
        if stats['subjects_covered'] >= 3:
            quality += 20
        elif stats['subjects_covered'] >= 2:
            quality += 10
        
        # More topics = better granularity
        if stats['topics_covered'] >= 10:
            quality += 20
        elif stats['topics_covered'] >= 5:
            quality += 10
        
        return quality


def demonstrate_ml_power(db):
    """
    Demo function to show ML capabilities
    For testing and demonstration
    """
    st.markdown("## 🧠 ML Model Demo")
    
    trainer = MLTrainer(db)
    predictor = trainer.predictor
    
    # Show model stats
    st.markdown("### 📊 Model Statistics")
    stats = trainer.get_model_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", "✅ Trained" if stats['is_trained'] else "⏳ Not Trained")
    with col2:
        st.metric("Training Samples", stats['training_samples'])
    with col3:
        st.metric("Students", stats['unique_students'])
    with col4:
        st.metric("Topics", stats['topics_covered'])
    
    # Show readiness
    readiness = trainer.get_training_readiness()
    
    if not readiness['ready']:
        st.warning(f"⏳ Need {readiness['samples_needed']} more samples to train")
        st.progress(readiness['progress'], text=f"Progress: {readiness['progress']*100:.0f}%")
    
    st.metric("Data Quality Score", f"{readiness['quality_score']}/100")
    
    # Train button
    if not stats['is_trained'] and readiness['ready']:
        if st.button("🚀 Train ML Model Now", type="primary"):
            trainer.train_model()
            st.rerun()
    
    # If trained, show predictions
    if stats['is_trained']:
        st.markdown("---")
        st.markdown("### 🎯 Test Difficulty Prediction")
        
        test_question = st.text_area(
            "Enter a question to predict its difficulty:",
            "A car accelerates from 0 to 60 m/s in 10 seconds. What is its acceleration?"
        )
        
        subject = st.selectbox("Subject", ["Physics", "Chemistry", "Mathematics"])
        topic = st.text_input("Topic", "Kinematics")
        
        if st.button("Predict Difficulty"):
            difficulty = predictor.predict_difficulty(test_question, subject, topic)
            
            # Convert to 1-5 scale
            difficulty_5 = difficulty * 5
            
            st.metric("Predicted Difficulty", f"{difficulty_5:.1f} / 5.0")
            
            # Show bar
            progress_color = "🟢" if difficulty < 0.4 else "🟡" if difficulty < 0.7 else "🔴"
            st.progress(difficulty, text=f"{progress_color} Difficulty: {difficulty*100:.0f}%")
            
            # Interpretation
            if difficulty < 0.3:
                st.success("✅ This question is **Easy** - Most students will get it right")
            elif difficulty < 0.6:
                st.info("⚡ This question is **Medium** - Good for practice")
            else:
                st.warning("🔥 This question is **Hard** - Challenging for most students")
            
            # Context-aware suggestion
            if hasattr(st.session_state, 'student_context'):
                ctx = st.session_state.student_context
                student_ability = ctx.get('accuracy', 0.5)
                
                st.markdown("---")
                st.markdown("### 💡 Personalized Recommendation")
                
                if abs(difficulty - student_ability) < 0.15:
                    st.success(f"✅ **Perfect for you!** This question matches your current ability level ({student_ability*5:.1f}/5.0)")
                elif difficulty > student_ability + 0.2:
                    st.warning(f"⚠️ **Too Hard:** This question ({difficulty*5:.1f}/5) is above your current level ({student_ability*5:.1f}/5). Try easier questions first.")
                elif difficulty < student_ability - 0.2:
                    st.info(f"ℹ️ **Too Easy:** This question ({difficulty*5:.1f}/5) is below your level ({student_ability*5:.1f}/5). Challenge yourself!")


def render_ml_diagnostics(db):
    """
    Show detailed ML system diagnostics
    NEW FUNCTION for unified insights
    """
    st.markdown("### 🔍 ML System Diagnostics")
    
    trainer = MLTrainer(db)
    
    # Training data quality
    st.markdown("#### 📊 Training Data Quality")
    readiness = trainer.get_training_readiness()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Readiness", "✅ Ready" if readiness['ready'] else "⏳ Not Ready")
        st.metric("Quality Score", f"{readiness['quality_score']}/100")
    
    with col2:
        st.metric("Progress", f"{readiness['progress']*100:.0f}%")
        if not readiness['ready']:
            st.metric("Samples Needed", readiness['samples_needed'])
    
    # Detailed stats
    stats = trainer.get_model_stats()
    
    st.markdown("#### 📈 Detailed Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Training Samples", stats['training_samples'])
        st.caption("Unique questions with 3+ attempts")
    
    with col2:
        st.metric("Unique Students", stats['unique_students'])
        st.caption("Different students in training data")
    
    with col3:
        st.metric("Subject Coverage", stats['subjects_covered'])
        st.caption("Different subjects covered")
    
    # Recommendations
    st.markdown("#### 💡 Recommendations")
    
    if readiness['quality_score'] < 40:
        st.warning("⚠️ Low quality data. Encourage more students to practice varied topics.")
    elif readiness['quality_score'] < 70:
        st.info("ℹ️ Good data quality. Adding more diverse questions will improve predictions.")
    else:
        st.success("✅ Excellent data quality! The model has strong training data.")


# Export
__all__ = ['MLDataCollector', 'MLTrainer', 'demonstrate_ml_power', 'render_ml_diagnostics']