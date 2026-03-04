"""
database.py - Advanced SQLite Database with Adaptive Learning
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta

class AdvancedDB:
    """Production-grade SQLite database with advanced analytics"""
    
    def __init__(self, db_name="exam_buddy_pro.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """Create comprehensive database schema"""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Knowledge graph - hierarchical topic structure
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                subtopic TEXT,
                difficulty_level TEXT DEFAULT 'Medium',
                mastery_level REAL DEFAULT 0.0,
                confidence_score REAL DEFAULT 0.0,
                last_practiced TIMESTAMP,
                practice_count INTEGER DEFAULT 0,
                UNIQUE(subject, topic, subtopic)
            )
        """)
        
        # Detailed attempt tracking with performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                node_id INTEGER,
                question TEXT NOT NULL,
                user_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                time_taken INTEGER,
                difficulty TEXT,
                hesitation_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (node_id) REFERENCES knowledge_nodes(node_id)
            )
        """)
        
        # Chat interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                topic_detected TEXT,
                sentiment TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Study sessions with detailed metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                accuracy REAL,
                avg_time_per_question REAL,
                topics_covered TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # AI-generated recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                rec_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Learning patterns and insights
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                insight_data TEXT NOT NULL,
                confidence REAL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Exam mode attempts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_attempts (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                exam_type TEXT,
                total_questions INTEGER,
                correct_answers INTEGER,
                duration_minutes INTEGER,
                score_percentage REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        self.conn.commit()
        
        # Create indexes for performance
        self.create_indexes()
    
    def create_indexes(self):
        """Create indexes for faster queries"""
        cursor = self.conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_attempts_node ON attempts(node_id)",
            "CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON attempts(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_knowledge_subject ON knowledge_nodes(subject)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON study_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chats_user ON chats(user_id)"
        ]
        
        for idx in indexes:
            cursor.execute(idx)
        
        self.conn.commit()
    
    def get_or_create_user(self, username="default_user"):
        """Get or create user with unique ID"""
        cursor = self.conn.cursor()
        user_id = hashlib.md5(username.encode()).hexdigest()
        
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, username))
        
        # Update last active
        cursor.execute("""
            UPDATE users SET last_active = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        
        self.conn.commit()
        return user_id
    
    def get_or_create_node(self, subject, topic, subtopic=None):
        """Get or create knowledge graph node"""
        cursor = self.conn.cursor()
        
        # Check if exists
        cursor.execute("""
            SELECT node_id FROM knowledge_nodes
            WHERE subject=? AND topic=? AND (subtopic=? OR (subtopic IS NULL AND ? IS NULL))
        """, (subject, topic, subtopic, subtopic))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Create new node
        cursor.execute("""
            INSERT INTO knowledge_nodes (subject, topic, subtopic)
            VALUES (?, ?, ?)
        """, (subject, topic, subtopic))
        self.conn.commit()
        return cursor.lastrowid
    
    def save_attempt(self, user_id, node_id, question, user_answer, 
                     correct_answer, is_correct, time_taken, difficulty, session_id=None):
        """Save detailed attempt with performance metrics"""
        cursor = self.conn.cursor()
        
        # Calculate hesitation score (normalized time)
        hesitation = min(time_taken / 60.0, 1.0) if time_taken else 0.5
        
        cursor.execute("""
            INSERT INTO attempts 
            (user_id, node_id, question, user_answer, correct_answer, 
             is_correct, time_taken, difficulty, hesitation_score, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, node_id, question, user_answer, correct_answer,
              is_correct, time_taken, difficulty, hesitation, session_id))
        self.conn.commit()
        
        # Update knowledge node
        self.update_mastery(node_id, is_correct, time_taken)
    
    def update_mastery(self, node_id, is_correct, time_taken):
        """Advanced mastery calculation using weighted moving average"""
        cursor = self.conn.cursor()
        
        # Get recent performance (last 10 attempts)
        cursor.execute("""
            SELECT is_correct, time_taken, hesitation_score FROM attempts
            WHERE node_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (node_id,))
        
        recent = cursor.fetchall()
        
        if not recent:
            return
        
        # Calculate weighted mastery
        # More recent attempts have higher weight
        total_weight = 0
        weighted_score = 0
        
        for i, (correct, time_val, hesitation) in enumerate(recent):
            weight = 1.0 / (i + 1)  # Exponential decay
            
            # Score factors: correctness (70%), speed (30%)
            speed_bonus = 1.0 - (hesitation * 0.3)
            score = (correct * 0.7 + speed_bonus * 0.3) if correct else 0
            
            weighted_score += score * weight
            total_weight += weight
        
        mastery = (weighted_score / total_weight) * 100
        
        # Calculate confidence (consistency measure)
        accuracies = [1 if r[0] else 0 for r in recent]
        avg = sum(accuracies) / len(accuracies)
        variance = sum((x - avg) ** 2 for x in accuracies) / len(accuracies)
        confidence = max(0, 1 - variance) * 100
        
        # Update node
        cursor.execute("""
            UPDATE knowledge_nodes
            SET mastery_level = ?,
                confidence_score = ?,
                last_practiced = CURRENT_TIMESTAMP,
                practice_count = practice_count + 1
            WHERE node_id = ?
        """, (mastery, confidence, node_id))
        self.conn.commit()
    
    def get_adaptive_difficulty(self, user_id, topic=None, subject=None):
        """
        Calculate adaptive difficulty using multi-factor analysis
        Returns: (difficulty_level, accuracy_percentage, recommendation_reason)
        """
        cursor = self.conn.cursor()
        
        # Build query based on filters
        query = """
            SELECT 
                AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy,
                AVG(time_taken) as avg_time,
                COUNT(*) as attempt_count
            FROM attempts a
            JOIN knowledge_nodes kn ON a.node_id = kn.node_id
            WHERE a.user_id = ?
            AND a.timestamp > datetime('now', '-7 days')
        """
        
        params = [user_id]
        
        if subject:
            query += " AND kn.subject = ?"
            params.append(subject)
        
        if topic:
            query += " AND kn.topic = ?"
            params.append(topic)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        accuracy = result[0] if result[0] else 50.0
        avg_time = result[1] if result[1] else 30.0
        attempts = result[2] if result[2] else 0
        
        # Adaptive difficulty algorithm
        if attempts < 5:
            return "Medium", accuracy, "Building baseline - starting with medium difficulty"
        
        # Multi-criteria decision
        if accuracy < 40:
            if avg_time > 45:
                return "Easy", accuracy, "Low accuracy + slow speed = Easy recommended"
            return "Easy", accuracy, "Below 40% accuracy - focus on fundamentals"
        
        elif accuracy < 70:
            if avg_time < 25:
                return "Medium", accuracy, "Good speed but accuracy needs work"
            return "Medium", accuracy, "Moderate performance - continue current level"
        
        else:  # accuracy >= 70
            if accuracy > 85 and avg_time < 30:
                return "Hard", accuracy, "High accuracy + good speed = Ready for challenge!"
            return "Hard", accuracy, "Strong performance - time for harder questions"
    
    def get_weak_topics(self, user_id, limit=5):
        """Identify weak topics using comprehensive metrics"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                kn.subject,
                kn.topic,
                kn.subtopic,
                kn.mastery_level,
                kn.confidence_score,
                COUNT(a.attempt_id) as attempts,
                AVG(CASE WHEN a.is_correct THEN 100.0 ELSE 0.0 END) as accuracy,
                AVG(a.time_taken) as avg_time,
                MAX(a.timestamp) as last_attempt
            FROM knowledge_nodes kn
            JOIN attempts a ON kn.node_id = a.node_id
            WHERE a.user_id = ?
            GROUP BY kn.node_id
            HAVING attempts >= 3
            ORDER BY 
                kn.mastery_level ASC,
                kn.confidence_score ASC,
                accuracy ASC
            LIMIT ?
        """, (user_id, limit))
        
        return cursor.fetchall()
    
    def get_analytics_data(self, user_id):
        """Comprehensive analytics aggregation"""
        cursor = self.conn.cursor()
        
        # Overall statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
                AVG(time_taken) as avg_time,
                COUNT(DISTINCT DATE(timestamp)) as study_days,
                MIN(timestamp) as first_attempt,
                MAX(timestamp) as last_attempt
            FROM attempts
            WHERE user_id = ?
        """, (user_id,))
        
        overall = cursor.fetchone()
        
        # Topic-wise performance with trends
        cursor.execute("""
            SELECT 
                kn.subject,
                kn.topic,
                COUNT(*) as attempts,
                AVG(CASE WHEN a.is_correct THEN 100.0 ELSE 0.0 END) as accuracy,
                kn.mastery_level,
                kn.confidence_score,
                AVG(a.time_taken) as avg_time
            FROM attempts a
            JOIN knowledge_nodes kn ON a.node_id = kn.node_id
            WHERE a.user_id = ?
            GROUP BY kn.subject, kn.topic
            ORDER BY accuracy ASC
        """, (user_id,))
        
        topics = cursor.fetchall()
        
        # Daily progress for last 30 days
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as questions,
                AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy,
                AVG(time_taken) as avg_time
            FROM attempts
            WHERE user_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        """, (user_id,))
        
        daily = cursor.fetchall()
        
        # Performance by difficulty
        cursor.execute("""
            SELECT 
                difficulty,
                COUNT(*) as attempts,
                AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy
            FROM attempts
            WHERE user_id = ?
            GROUP BY difficulty
        """, (user_id,))
        
        by_difficulty = cursor.fetchall()
        
        return {
            'overall': overall,
            'topics': topics,
            'daily': daily,
            'by_difficulty': by_difficulty
        }
    
    def save_chat(self, user_id, user_msg, ai_msg, topic=None):
        """Save chat with optional topic detection"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO chats (user_id, user_message, ai_response, topic_detected)
            VALUES (?, ?, ?, ?)
        """, (user_id, user_msg, ai_msg, topic))
        self.conn.commit()
    
    def get_study_recommendations(self, user_id):
        """Generate intelligent, personalized recommendations"""
        recommendations = []
        
        # Get weak topics
        weak = self.get_weak_topics(user_id, 3)
        
        for topic_data in weak:
            subject, topic, subtopic, mastery, confidence, attempts, accuracy, avg_time, last_attempt = topic_data
            
            # Determine priority
            if mastery < 30:
                priority = 'high'
                icon = '🔴'
            elif mastery < 60:
                priority = 'medium'
                icon = '🟡'
            else:
                priority = 'low'
                icon = '🟢'
            
            # Build recommendation
            display_topic = f"{topic} - {subtopic}" if subtopic else topic
            reason = f"Mastery: {mastery:.1f}% | Accuracy: {accuracy:.1f}% | {attempts} attempts"
            
            recommendations.append({
                'type': 'revision',
                'title': f"{icon} Practice: {display_topic}",
                'reason': reason,
                'priority': priority,
                'subject': subject
            })
        
        # Add streak recommendation
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp)) as days
            FROM attempts
            WHERE user_id = ?
            AND timestamp > datetime('now', '-7 days')
        """, (user_id,))
        
        recent_days = cursor.fetchone()[0]
        
        if recent_days < 3:
            recommendations.append({
                'type': 'consistency',
                'title': '📅 Build Study Streak',
                'reason': f'Active {recent_days} days this week - aim for 5!',
                'priority': 'medium'
            })
        
        return recommendations
    
    def get_learning_insights(self, user_id):
        """Generate AI-powered learning insights"""
        cursor = self.conn.cursor()
        insights = []
        
        # Best time of day analysis
        cursor.execute("""
            SELECT 
                CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                AVG(CASE WHEN is_correct THEN 100.0 ELSE 0.0 END) as accuracy
            FROM attempts
            WHERE user_id = ?
            GROUP BY hour
            HAVING COUNT(*) >= 3
            ORDER BY accuracy DESC
            LIMIT 1
        """, (user_id,))
        
        best_hour = cursor.fetchone()
        if best_hour:
            hour = best_hour[0]
            acc = best_hour[1]
            time_period = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
            insights.append({
                'type': 'timing',
                'message': f"📊 You perform best in the {time_period} ({hour}:00) with {acc:.1f}% accuracy",
                'confidence': 0.8
            })
        
        # Speed vs accuracy pattern
        cursor.execute("""
            SELECT AVG(time_taken), AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END)
            FROM attempts
            WHERE user_id = ? AND time_taken IS NOT NULL
        """, (user_id,))
        
        speed_data = cursor.fetchone()
        if speed_data[0]:
            avg_time = speed_data[0]
            accuracy = speed_data[1] * 100
            
            if avg_time < 20 and accuracy < 60:
                insights.append({
                    'type': 'behavior',
                    'message': '⚡ You tend to rush - slowing down might improve accuracy',
                    'confidence': 0.7
                })
            elif avg_time > 50 and accuracy > 80:
                insights.append({
                    'type': 'behavior',
                    'message': '🎯 Great accuracy! With practice, you can maintain it at faster speed',
                    'confidence': 0.75
                })
        
        return insights
    
    def close(self):
        """Close database connection"""
        self.conn.close()