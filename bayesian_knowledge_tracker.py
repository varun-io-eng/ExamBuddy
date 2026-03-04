"""
bayesian_knowledge_tracker.py - Compatible with AuthDatabase Schema
UPDATED: Enhanced for ML+BKT unified insights and context injection
Works with existing database without node_id or knowledge_nodes table
"""

import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json


class BayesianKnowledgeTracker:
    """
    Bayesian Knowledge Tracing compatible with AuthDatabase schema
    
    Works with: user_id, question, subject, topic, is_correct, timestamp
    Does NOT require: node_id or knowledge_nodes table
    """
    
    def __init__(self, db):
        self.db = db
        
        # BKT Parameters
        self.P_L0 = 0.1      # Initial knowledge (10%)
        self.P_T = 0.3       # Learning rate (30% per correct attempt)
        self.P_S = 0.15      # Slip rate (15% - know but get wrong)
        self.P_G = 0.25      # Guess rate (25% - don't know but get right)
        
        # Forgetting parameters
        self.FORGETTING_RATE = 0.05  # 5% per day
        self.PRACTICE_THRESHOLD_DAYS = 7
    
    def calculate_concept_mastery(self, user_id, subject, topic, subtopic=None):
        """
        Calculate P(student knows concept) using Bayesian Knowledge Tracing
        Compatible with AuthDatabase schema (no node_id required)
        """
        cursor = self.db.conn.cursor()
        
        # Get all attempts for this concept
        if subtopic:
            # Try to match subtopic in topic field
            cursor.execute("""
                SELECT is_correct, timestamp, time_taken
                FROM attempts
                WHERE user_id = ? AND subject = ? AND (topic = ? OR topic LIKE ?)
                ORDER BY timestamp ASC
            """, (user_id, subject, topic, f"%{subtopic}%"))
        else:
            cursor.execute("""
                SELECT is_correct, timestamp, time_taken
                FROM attempts
                WHERE user_id = ? AND subject = ? AND topic = ?
                ORDER BY timestamp ASC
            """, (user_id, subject, topic))
        
        attempts = cursor.fetchall()
        
        if not attempts:
            return {
                'mastery_probability': self.P_L0,
                'confidence': 0.0,
                'attempts': 0,
                'last_practiced': None,
                'forgetting_risk': 'low',
                'learning_velocity': 0.0,
                'mastery_before_forgetting': self.P_L0,
                'days_since_practice': 0,
                'forgetting_factor': 1.0,
                'mastery_history': [self.P_L0]
            }
        
        # Bayesian update for each attempt
        P_L = self.P_L0
        mastery_history = [P_L]
        
        for is_correct, timestamp, time_taken in attempts:
            # Update based on correctness
            if is_correct:
                # P(L_new | correct)
                P_correct_given_learned = 1 - self.P_S
                P_correct_given_not_learned = self.P_G
                
                numerator = P_L * P_correct_given_learned
                denominator = (P_L * P_correct_given_learned + 
                             (1 - P_L) * P_correct_given_not_learned)
                
                P_L_after = numerator / denominator if denominator > 0 else P_L
                P_L = P_L_after + (1 - P_L_after) * self.P_T
            else:
                # P(L_new | incorrect)
                P_incorrect_given_learned = self.P_S
                P_incorrect_given_not_learned = 1 - self.P_G
                
                numerator = P_L * P_incorrect_given_learned
                denominator = (P_L * P_incorrect_given_learned + 
                             (1 - P_L) * P_incorrect_given_not_learned)
                
                P_L = numerator / denominator if denominator > 0 else P_L * 0.9
            
            # Adjust for time taken (if available)
            if time_taken:
                time_factor = min(time_taken / 60.0, 1.0)
                P_L = P_L * (1 - 0.1 * time_factor)
            
            # Clamp
            P_L = max(0.01, min(0.99, P_L))
            mastery_history.append(P_L)
        
        # Calculate forgetting
        last_timestamp = attempts[-1][1]
        try:
            if 'T' in last_timestamp or ' ' in last_timestamp:
                last_practiced = datetime.fromisoformat(last_timestamp.replace(' ', 'T'))
            else:
                last_practiced = datetime.strptime(last_timestamp, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            last_practiced = datetime.now()
        
        days_since = (datetime.now() - last_practiced).days
        
        # Apply forgetting curve
        forgetting_factor = np.exp(-self.FORGETTING_RATE * days_since)
        P_L_current = P_L * forgetting_factor
        P_L_current = max(self.P_L0, P_L_current)
        
        # Determine forgetting risk
        if days_since > 14:
            forgetting_risk = 'high'
        elif days_since > 7:
            forgetting_risk = 'medium'
        else:
            forgetting_risk = 'low'
        
        # Confidence based on attempts
        confidence = min(len(attempts) / 20.0, 1.0)
        
        # Learning velocity
        if len(mastery_history) >= 3:
            x = np.arange(len(mastery_history))
            y = np.array(mastery_history)
            velocity = np.polyfit(x, y, 1)[0]
        else:
            velocity = 0.0
        
        return {
            'mastery_probability': round(P_L_current, 3),
            'mastery_before_forgetting': round(P_L, 3),
            'confidence': round(confidence, 3),
            'attempts': len(attempts),
            'last_practiced': last_practiced.strftime('%Y-%m-%d'),
            'days_since_practice': days_since,
            'forgetting_risk': forgetting_risk,
            'forgetting_factor': round(forgetting_factor, 3),
            'learning_velocity': round(velocity, 4),
            'mastery_history': mastery_history
        }
    
    def get_all_concept_masteries(self, user_id):
        """
        Get mastery for all concepts (subject, topic pairs)
        Compatible with AuthDatabase - uses subject and topic columns
        """
        cursor = self.db.conn.cursor()
        
        # Get all unique subject-topic combinations the user has practiced
        cursor.execute("""
            SELECT DISTINCT subject, topic
            FROM attempts
            WHERE user_id = ? AND subject IS NOT NULL AND topic IS NOT NULL
            ORDER BY subject, topic
        """, (user_id,))
        
        concepts = cursor.fetchall()
        
        masteries = []
        for subject, topic in concepts:
            mastery = self.calculate_concept_mastery(user_id, subject, topic, None)
            mastery['subject'] = subject
            mastery['topic'] = topic
            mastery['subtopic'] = None  # Not available in this schema
            masteries.append(mastery)
        
        return masteries
    
    def get_concepts_needing_review(self, user_id, threshold=0.6):
        """Get concepts that need review with priority scoring"""
        all_masteries = self.get_all_concept_masteries(user_id)
        
        needs_review = []
        
        for mastery in all_masteries:
            review_score = 0
            reasons = []
            
            if mastery['mastery_probability'] < threshold:
                review_score += 3
                reasons.append(f"Low mastery ({mastery['mastery_probability']*100:.0f}%)")
            
            if mastery['forgetting_risk'] == 'high':
                review_score += 2
                reasons.append(f"High forgetting risk ({mastery['days_since_practice']} days)")
            elif mastery['forgetting_risk'] == 'medium':
                review_score += 1
                reasons.append("Medium forgetting risk")
            
            if mastery['learning_velocity'] < -0.02:
                review_score += 2
                reasons.append("Declining trend")
            
            if review_score > 0:
                needs_review.append({
                    'subject': mastery['subject'],
                    'topic': mastery['topic'],
                    'subtopic': None,
                    'mastery': mastery['mastery_probability'],
                    'review_score': review_score,
                    'reasons': reasons,
                    'priority': 'high' if review_score >= 3 else 'medium' if review_score >= 2 else 'low'
                })
        
        needs_review.sort(key=lambda x: x['review_score'], reverse=True)
        return needs_review
    
    def predict_exam_performance(self, user_id, exam_topics, exam_difficulty='medium'):
        """
        Predict student's performance on an exam
        exam_topics: List of (subject, topic, subtopic) tuples
        """
        topic_masteries = []
        
        for subject, topic, subtopic in exam_topics:
            mastery = self.calculate_concept_mastery(user_id, subject, topic, subtopic)
            topic_masteries.append(mastery['mastery_probability'])
        
        if not topic_masteries:
            return {
                'predicted_score': 50.0,
                'confidence_lower': 30.0,
                'confidence_upper': 70.0,
                'confidence': 0.0,
                'topics_covered': 0,
                'topics_total': len(exam_topics),
                'coverage': 0.0
            }
        
        avg_mastery = np.mean(topic_masteries)
        
        difficulty_factors = {'easy': 1.1, 'medium': 1.0, 'hard': 0.85}
        factor = difficulty_factors.get(exam_difficulty, 1.0)
        
        predicted_score = avg_mastery * 100 * factor
        
        std_dev = np.std(topic_masteries) if len(topic_masteries) > 1 else 0.2
        n_topics = len(topic_masteries)
        confidence = min(n_topics / 10.0, 1.0)
        
        margin = std_dev * 100 * (1 - confidence * 0.5)
        
        return {
            'predicted_score': round(predicted_score, 1),
            'confidence_lower': round(max(0, predicted_score - margin), 1),
            'confidence_upper': round(min(100, predicted_score + margin), 1),
            'confidence': round(confidence, 2),
            'topics_covered': len(topic_masteries),
            'topics_total': len(exam_topics),
            'coverage': round(len(topic_masteries) / len(exam_topics) * 100, 1) if len(exam_topics) > 0 else 0
        }
    
    def get_optimal_practice_topics(self, user_id, count=5):
        """
        Get optimal topics to practice (spaced repetition)
        Enhanced with exam-aware prioritization
        """
        all_masteries = self.get_all_concept_masteries(user_id)
        
        if not all_masteries:
            return []
        
        scored_topics = []
        
        for mastery in all_masteries:
            P_L = mastery['mastery_probability']
            days = mastery['days_since_practice']
            velocity = mastery['learning_velocity']
            
            # Spaced repetition score
            mastery_score = (1 - P_L) * 10
            
            if days < 3:
                time_score = 0
            elif days < 7:
                time_score = days * 2
            elif days < 14:
                time_score = 10 + (days - 7) * 1.5
            else:
                time_score = 20
            
            velocity_score = -velocity * 100 if velocity < 0 else 0
            
            total_score = mastery_score + time_score + velocity_score
            
            scored_topics.append({
                'subject': mastery['subject'],
                'topic': mastery['topic'],
                'subtopic': None,
                'mastery': P_L,
                'days_since': days,
                'score': total_score,
                'reason': self._get_practice_reason(P_L, days, velocity)
            })
        
        scored_topics.sort(key=lambda x: x['score'], reverse=True)
        return scored_topics[:count]
    
    def _get_practice_reason(self, mastery, days, velocity):
        """Generate human-readable reason"""
        if mastery < 0.4:
            return f"📚 Needs learning ({mastery*100:.0f}% mastery)"
        elif days > 10:
            return f"🔄 Needs review ({days} days since practice)"
        elif velocity < -0.02:
            return "📉 Declining performance"
        elif 0.4 <= mastery < 0.7 and days > 5:
            return f"⚡ Spaced repetition optimal ({mastery*100:.0f}% mastery)"
        else:
            return f"✅ Maintenance practice ({mastery*100:.0f}% mastery)"
    
    def get_study_plan_for_exam(self, user_id, exam_date, hours_per_day=3):
        """
        Generate a study plan for exam preparation
        NEW METHOD for context-aware planning
        """
        from datetime import datetime, timedelta
        
        # Calculate days until exam
        if isinstance(exam_date, str):
            exam_date = datetime.strptime(exam_date, '%Y-%m-%d')
        days_until = (exam_date - datetime.now()).days
        
        if days_until <= 0:
            return None
        
        # Get all topics and their priorities
        all_masteries = self.get_all_concept_masteries(user_id)
        needs_review = self.get_concepts_needing_review(user_id, threshold=0.7)
        
        # Calculate total study hours available
        total_hours = days_until * hours_per_day
        
        # Allocate time based on priorities
        plan = {
            'days_until_exam': days_until,
            'total_hours_available': total_hours,
            'high_priority_topics': [],
            'medium_priority_topics': [],
            'low_priority_topics': [],
            'revision_schedule': []
        }
        
        # Categorize topics
        for mastery in all_masteries:
            topic_key = f"{mastery['subject']}: {mastery['topic']}"
            
            if mastery['mastery_probability'] < 0.5:
                plan['high_priority_topics'].append({
                    'topic': topic_key,
                    'current_mastery': mastery['mastery_probability'],
                    'estimated_hours': 4,
                    'priority': 'HIGH'
                })
            elif mastery['mastery_probability'] < 0.7:
                plan['medium_priority_topics'].append({
                    'topic': topic_key,
                    'current_mastery': mastery['mastery_probability'],
                    'estimated_hours': 2,
                    'priority': 'MEDIUM'
                })
            else:
                plan['low_priority_topics'].append({
                    'topic': topic_key,
                    'current_mastery': mastery['mastery_probability'],
                    'estimated_hours': 1,
                    'priority': 'LOW - Revision only'
                })
        
        # Generate revision schedule
        revision_points = [
            days_until - 7,  # 1 week before
            days_until - 3,  # 3 days before
            days_until - 1   # 1 day before
        ]
        
        for day in revision_points:
            if day > 0:
                plan['revision_schedule'].append({
                    'day': day,
                    'focus': 'Full revision of all topics',
                    'type': 'REVISION'
                })
        
        return plan
    
    def update_mastery_in_db(self, user_id):
        """
        Compatibility method - not needed for AuthDatabase
        Returns count for compatibility
        """
        all_masteries = self.get_all_concept_masteries(user_id)
        return len(all_masteries)
    
    def get_weak_topics_for_context(self, user_id, threshold=0.6, limit=5):
        """
        Get weak topics formatted for context injection
        NEW METHOD for structured context building
        """
        all_masteries = self.get_all_concept_masteries(user_id)
        
        weak_topics = [
            {
                'topic': f"{m['subject']}: {m['topic']}",
                'mastery': m['mastery_probability'],
                'days_since': m['days_since_practice'],
                'trend': 'declining' if m['learning_velocity'] < -0.02 else 'stable'
            }
            for m in all_masteries
            if m['mastery_probability'] < threshold
        ]
        
        # Sort by mastery (lowest first)
        weak_topics.sort(key=lambda x: x['mastery'])
        
        return weak_topics[:limit]
    
    def get_mastery_summary_for_context(self, user_id):
        """
        Get mastery summary formatted for context injection
        NEW METHOD for LLM context
        """
        all_masteries = self.get_all_concept_masteries(user_id)
        
        if not all_masteries:
            return {
                'total_topics': 0,
                'average_mastery': 0,
                'topics_above_70': 0,
                'topics_below_50': 0,
                'needs_urgent_review': 0
            }
        
        total = len(all_masteries)
        avg = sum(m['mastery_probability'] for m in all_masteries) / total
        above_70 = sum(1 for m in all_masteries if m['mastery_probability'] >= 0.7)
        below_50 = sum(1 for m in all_masteries if m['mastery_probability'] < 0.5)
        urgent = sum(1 for m in all_masteries 
                    if m['mastery_probability'] < 0.5 and m['days_since_practice'] > 7)
        
        return {
            'total_topics': total,
            'average_mastery': round(avg, 2),
            'topics_above_70': above_70,
            'topics_below_50': below_50,
            'needs_urgent_review': urgent,
            'mastery_distribution': {
                'expert (>80%)': sum(1 for m in all_masteries if m['mastery_probability'] >= 0.8),
                'good (70-80%)': sum(1 for m in all_masteries if 0.7 <= m['mastery_probability'] < 0.8),
                'moderate (50-70%)': sum(1 for m in all_masteries if 0.5 <= m['mastery_probability'] < 0.7),
                'weak (<50%)': sum(1 for m in all_masteries if m['mastery_probability'] < 0.5)
            }
        }


# Export
__all__ = ['BayesianKnowledgeTracker']