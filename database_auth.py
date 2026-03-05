"""
database_auth.py - Database with User Authentication
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
import json


class AuthDatabase:
    """Enhanced database with user authentication"""
    
    def __init__(self, db_name="exam_buddy_auth.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables"""
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                theme_preference TEXT DEFAULT 'dark',
                exam_type TEXT DEFAULT 'JEE Main',
                onboarding_subject TEXT DEFAULT 'Physics',
                is_onboarded INTEGER DEFAULT 0
            )
        """)
        # Migrate existing DBs safely
        for col, dfn in [
            ("exam_type",          "TEXT DEFAULT 'JEE Main'"),
            ("onboarding_subject", "TEXT DEFAULT 'Physics'"),
            ("is_onboarded",       "INTEGER DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {dfn}")
            except Exception:
                pass
        
        # User sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Attempts table (with user_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                question TEXT,
                user_answer TEXT,
                correct_answer TEXT,
                is_correct INTEGER,
                time_taken REAL,
                subject TEXT,
                topic TEXT,
                difficulty TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Exams table (with user_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_name TEXT,
                total_questions INTEGER,
                correct_answers INTEGER,
                wrong_answers INTEGER,
                unattempted INTEGER,
                total_score REAL,
                max_score REAL,
                percentage REAL,
                time_taken REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Knowledge nodes table (with user_id)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject TEXT,
                topic TEXT,
                subtopic TEXT,
                mastery_level REAL DEFAULT 0,
                practice_count INTEGER DEFAULT 0,
                last_practiced TEXT,
                confidence_score REAL DEFAULT 0.5,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        self.conn.commit()
    
    # ==================== AUTHENTICATION METHODS ====================
    
    def hash_password(self, password, salt=None):
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        pwd_hash = hashlib.pbkdf2_hmac('sha256', 
                                        password.encode('utf-8'), 
                                        salt.encode('utf-8'), 
                                        100000)
        return pwd_hash.hex(), salt
    
    def register_user(self, username, email, password):
        """Register a new user"""
        cursor = self.conn.cursor()
        
        # Check if username or email exists
        cursor.execute("SELECT user_id FROM users WHERE username = ? OR email = ?", 
                      (username, email))
        if cursor.fetchone():
            return None, "Username or email already exists"
        
        # Hash password
        pwd_hash, salt = self.hash_password(password)
        
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
            """, (username, email, pwd_hash, salt))
            self.conn.commit()
            
            user_id = cursor.lastrowid
            return user_id, "Registration successful"
        
        except Exception as e:
            return None, f"Registration failed: {str(e)}"
    
    def login_user(self, username, password):
        """Login user and return user_id if successful"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT user_id, password_hash, salt FROM users 
            WHERE username = ? OR email = ?
        """, (username, username))
        
        result = cursor.fetchone()
        
        if not result:
            return None, "Invalid username or password"
        
        user_id, stored_hash, salt = result
        
        # Verify password
        pwd_hash, _ = self.hash_password(password, salt)
        
        if pwd_hash == stored_hash:
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            self.conn.commit()
            
            return user_id, "Login successful"
        else:
            return None, "Invalid username or password"
    
    def get_user_info(self, user_id):
        """Get user information"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT user_id, username, email, created_at, last_login, theme_preference
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'email': result[2],
                'created_at': result[3],
                'last_login': result[4],
                'theme_preference': result[5]
            }
        return None
    
    def update_theme_preference(self, user_id, theme):
        """Update user's theme preference"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE users SET theme_preference = ? WHERE user_id = ?
        """, (theme, user_id))
        self.conn.commit()
    
    # ==================== DATA RECORDING METHODS ====================
    
    def record_attempt(self, user_id, question, user_answer, correct_answer, 
                      is_correct, time_taken, subject, topic, difficulty):
        """Record a question attempt"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO attempts 
            (user_id, question, user_answer, correct_answer, is_correct, 
             time_taken, subject, topic, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, question, user_answer, correct_answer, int(is_correct),
              time_taken, subject, topic, difficulty))
        self.conn.commit()
    
    def record_exam(self, user_id, exam_name, total_questions, correct_answers,
                   wrong_answers, unattempted, total_score, max_score, 
                   percentage, time_taken):
        """Record exam results"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO exams 
            (user_id, exam_name, total_questions, correct_answers, wrong_answers,
             unattempted, total_score, max_score, percentage, time_taken)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, exam_name, total_questions, correct_answers, wrong_answers,
              unattempted, total_score, max_score, percentage, time_taken))
        self.conn.commit()
    
    # ==================== ANALYTICS METHODS ====================
    
    def get_user_analytics(self, user_id):
        """Get comprehensive analytics for a specific user"""
        cursor = self.conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_questions,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                AVG(time_taken) as avg_time,
                COUNT(DISTINCT DATE(timestamp)) as study_days,
                MIN(timestamp) as first_attempt,
                MAX(timestamp) as last_attempt
            FROM attempts
            WHERE user_id = ?
        """, (user_id,))
        overall = cursor.fetchone()
        
        # Daily progress
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as questions,
                ROUND(AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0.0 END), 1) as accuracy,
                AVG(time_taken) as avg_time
            FROM attempts
            WHERE user_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
            LIMIT 30
        """, (user_id,))
        daily = cursor.fetchall()
        
        # Topic-wise performance
        cursor.execute("""
            SELECT 
                subject,
                topic,
                COUNT(*) as attempts,
                ROUND(AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0.0 END), 1) as accuracy,
                0 as mastery,
                0.5 as confidence,
                AVG(time_taken) as avg_time
            FROM attempts
            WHERE user_id = ?
            GROUP BY subject, topic
            ORDER BY attempts DESC
        """, (user_id,))
        topics = cursor.fetchall()
        
        # Difficulty-wise performance
        cursor.execute("""
            SELECT 
                difficulty,
                COUNT(*) as attempts,
                ROUND(AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0.0 END), 1) as accuracy
            FROM attempts
            WHERE user_id = ?
            GROUP BY difficulty
        """, (user_id,))
        by_difficulty = cursor.fetchall()
        
        # Exam history
        cursor.execute("""
            SELECT 
                exam_name,
                total_questions,
                correct_answers,
                percentage,
                time_taken,
                timestamp
            FROM exams
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (user_id,))
        exams = cursor.fetchall()
        
        return {
            'overall': overall,
            'daily': daily,
            'topics': topics,
            'by_difficulty': by_difficulty,
            'exams': exams
        }
    
    def get_user_exam_count(self, user_id):
        """Get total number of exams taken by user"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM exams WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]
    
    def get_user_question_count(self, user_id):
        """Get total questions attempted by user"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM attempts WHERE user_id = ?", (user_id,))
        return cursor.fetchone()[0]



    def get_weak_topics(self, user_id, limit=5):
        """Get weak topics for user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT topic, 
                   COUNT(*) as attempts,
                   ROUND(AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0.0 END), 1) as accuracy
            FROM attempts
            WHERE user_id = ?
            GROUP BY topic
            HAVING accuracy < 60
            ORDER BY accuracy ASC
            LIMIT ?
        """, (user_id, limit))
        
        results = cursor.fetchall()
        return [{'topic': r[0], 'attempts': r[1], 'accuracy': r[2]} for r in results]
    
    def get_adaptive_difficulty(self, user_id, current_difficulty="Medium", subject=None):
        """Get adaptive difficulty based on user performance"""
        cursor = self.conn.cursor()
        
        # Build query based on whether subject is specified
        if subject:
            cursor.execute("""
                SELECT AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) as accuracy
                FROM attempts
                WHERE user_id = ? AND subject = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (user_id, subject))
        else:
            cursor.execute("""
                SELECT AVG(CASE WHEN is_correct = 1 THEN 1.0 ELSE 0.0 END) as accuracy
                FROM attempts
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (user_id,))
        
        result = cursor.fetchone()
        if not result or result[0] is None:
            return current_difficulty, 0.0, "No recent attempts found. Starting with Medium difficulty."
        
        accuracy = result[0] * 100
        recommended_difficulty = current_difficulty
        reason = ""
        
        # Adjust difficulty based on performance
        if accuracy >= 80 and current_difficulty == "Easy":
            recommended_difficulty = "Medium"
            reason = f"Great job! {accuracy:.1f}% accuracy. Ready for Medium difficulty."
        elif accuracy >= 80 and current_difficulty == "Medium":
            recommended_difficulty = "Hard"
            reason = f"Excellent! {accuracy:.1f}% accuracy. Challenge yourself with Hard difficulty."
        elif accuracy < 50 and current_difficulty == "Hard":
            recommended_difficulty = "Medium"
            reason = f"Struggling a bit ({accuracy:.1f}%). Let's try Medium difficulty."
        elif accuracy < 50 and current_difficulty == "Medium":
            recommended_difficulty = "Easy"
            reason = f"Need more practice ({accuracy:.1f}%). Starting with Easy difficulty."
        else:
            reason = f"Current accuracy: {accuracy:.1f}%. {current_difficulty} difficulty is good for you."
        
        return recommended_difficulty, accuracy, reason
    

    def get_study_recommendations(self, user_id):
        """Get study recommendations for user"""
        return []
    
    def get_or_create_user(self):
        """Compatibility method - returns user_id 1 by default"""
        # This is for compatibility with old code
        # In production, you'd handle this differently
        return 1
    
    def get_analytics_data(self, user_id):
        """Compatibility wrapper for get_user_analytics"""
        return self.get_user_analytics(user_id)
    
    def update_knowledge_node(self, user_id, subject, topic, mastery_delta):
        """Update knowledge node mastery"""
        # Placeholder for compatibility
        pass
    
    def record_mistake(self, user_id, question, mistake_type, explanation):
        """Record a learning mistake"""
        # Placeholder for compatibility
        pass
    
    def get_learning_insights(self, user_id):
        """Get learning insights for user"""
        # Return empty list for now
        return []

    # ══════════════════════════════════════════════
    # ONBOARDING METHODS
    # ══════════════════════════════════════════════

    def get_onboarding_status(self, user_id):
        """Returns onboarding info for this user."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT is_onboarded, exam_type, onboarding_subject
                FROM users WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'is_onboarded':       bool(row[0]),
                    'exam_type':          row[1] or 'JEE Main',
                    'onboarding_subject': row[2] or 'Physics',
                }
        except Exception:
            pass
        return {'is_onboarded': False, 'exam_type': 'JEE Main', 'onboarding_subject': 'Physics'}

    def save_onboarding(self, user_id, exam_type, onboarding_subject):
        """Save onboarding preferences and mark user as onboarded."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET exam_type=?, onboarding_subject=?, is_onboarded=1
                WHERE user_id=?
            """, (exam_type, onboarding_subject, user_id))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_exam_type(self, user_id):
        """Quick helper — returns user's exam type string."""
        return self.get_onboarding_status(user_id).get('exam_type', 'JEE Main')


# Export
__all__ = ['AuthDatabase']