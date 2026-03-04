"""
ml_difficulty_predictor.py - Neural Network for Question Difficulty Prediction
This is YOUR trained ML model - not just API calls!
"""

import numpy as np
import pandas as pd
import pickle
import os
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Try to import torch, if not available use simple neural network
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ PyTorch not available. Using simple neural network instead.")


class SimpleNeuralNetwork:
    """
    Simple neural network implementation without PyTorch
    For when PyTorch is not available
    """
    def __init__(self, input_size, hidden_size=64):
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # Initialize weights
        self.W1 = np.random.randn(input_size, hidden_size) * 0.01
        self.b1 = np.zeros((1, hidden_size))
        self.W2 = np.random.randn(hidden_size, 1) * 0.01
        self.b2 = np.zeros((1, 1))
    
    def sigmoid(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def relu(self, x):
        return np.maximum(0, x)
    
    def forward(self, X):
        # Forward pass
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.relu(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self.sigmoid(self.z2)
        return self.a2
    
    def predict(self, X):
        return self.forward(X)



if TORCH_AVAILABLE:
    class DifficultyPredictorNN(nn.Module):
        """
        PyTorch Neural Network for Difficulty Prediction
        Architecture: Input -> Hidden(128) -> Hidden(64) -> Output(1)
        """
        def __init__(self, input_size):
            super(DifficultyPredictorNN, self).__init__()
            self.fc1 = nn.Linear(input_size, 128)
            self.fc2 = nn.Linear(128, 64)
            self.fc3 = nn.Linear(64, 32)
            self.fc4 = nn.Linear(32, 1)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.2)
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x):
            x = self.relu(self.fc1(x))
            x = self.dropout(x)
            x = self.relu(self.fc2(x))
            x = self.dropout(x)
            x = self.relu(self.fc3(x))
            x = self.sigmoid(self.fc4(x))
            return x
else:
    # Placeholder class when PyTorch is not available
    class DifficultyPredictorNN:
        """Placeholder when PyTorch is not available"""
        def __init__(self, input_size):
            pass
        
        def forward(self, x):
            pass


class MLDifficultyPredictor:
    """
    Main ML Model for Question Difficulty Prediction
    Learns from student performance data
    """
    
    def __init__(self, model_path='ml_models'):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)
        
        # Feature extractors
        self.text_vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.scaler = StandardScaler()
        
        # Model
        self.model = None
        self.is_trained = False
        
        # Student ability tracking
        self.student_abilities = {}  # {user_id: ability_score}
        
        # Load if exists
        self.load_model()
    
    def extract_features(self, question_text, subject, topic, student_history=None):
        """
        Extract features from question and student history
        
        Features:
        1. Text features (TF-IDF of question)
        2. Question length
        3. Has numbers (calculation-heavy)
        4. Subject encoding
        5. Student history features
        """
        features = []
        
        # Text features (TF-IDF)
        if hasattr(self.text_vectorizer, 'vocabulary_'):
            text_vec = self.text_vectorizer.transform([question_text]).toarray()[0]
        else:
            text_vec = np.zeros(100)
        features.extend(text_vec)
        
        # Question characteristics
        features.append(len(question_text.split()))  # Word count
        features.append(1 if any(char.isdigit() for char in question_text) else 0)  # Has numbers
        features.append(question_text.count('?'))  # Number of questions
        
        # Subject encoding (one-hot)
        subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology']
        subject_encoding = [1 if subject == s else 0 for s in subjects]
        features.extend(subject_encoding)
        
        # Student history features
        if student_history and len(student_history) > 0:
            recent = student_history[-10:]  # Last 10 attempts
            features.append(np.mean([a['is_correct'] for a in recent]))  # Recent accuracy
            features.append(np.mean([a.get('time_taken', 30) for a in recent]))  # Avg time
            features.append(len(student_history))  # Total attempts
        else:
            features.extend([0.5, 30, 0])  # Default values
        
        return np.array(features)
    
    def train(self, training_data, epochs=50):
        """
        Train the neural network
        
        training_data format:
        [
            {
                'question': 'text',
                'subject': 'Physics',
                'topic': 'Forces',
                'student_attempts': [
                    {'user_id': 1, 'is_correct': True, 'time_taken': 25},
                    {'user_id': 2, 'is_correct': False, 'time_taken': 60},
                    ...
                ],
                'true_difficulty': 0.65  # 0-1 scale (calculated from attempts)
            },
            ...
        ]
        """
        print("🧠 Starting ML Model Training...")
        print(f"Training samples: {len(training_data)}")
        
        if len(training_data) < 20:
            print("⚠️ Need at least 20 training samples. Collecting more data...")
            return False
        
        # Prepare data
        X_list = []
        y_list = []
        
        # First pass: fit vectorizer on all questions
        all_questions = [d['question'] for d in training_data]
        self.text_vectorizer.fit(all_questions)
        
        for data in training_data:
            # Extract features
            features = self.extract_features(
                data['question'],
                data['subject'],
                data['topic'],
                student_history=None  # Use average student
            )
            X_list.append(features)
            y_list.append(data['true_difficulty'])
        
        X = np.array(X_list)
        y = np.array(y_list).reshape(-1, 1)
        
        # Normalize features
        X = self.scaler.fit_transform(X)
        
        # Train model
        if TORCH_AVAILABLE:
            self._train_pytorch(X, y, epochs)
        else:
            self._train_simple(X, y, epochs)
        
        self.is_trained = True
        self.save_model()
        
        print("✅ Training complete!")
        return True
    
    def _train_pytorch(self, X, y, epochs):
        """Train using PyTorch"""
        input_size = X.shape[1]
        self.model = DifficultyPredictorNN(input_size)
        
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)
        
        for epoch in range(epochs):
            # Forward pass
            outputs = self.model(X_tensor)
            loss = criterion(outputs, y_tensor)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")
    
    def _train_simple(self, X, y, epochs):
        """Train using simple neural network"""
        input_size = X.shape[1]
        self.model = SimpleNeuralNetwork(input_size)
        
        learning_rate = 0.01
        
        for epoch in range(epochs):
            # Forward pass
            predictions = self.model.predict(X)
            
            # Calculate loss (MSE)
            loss = np.mean((predictions - y) ** 2)
            
            # Backward pass (gradient descent)
            m = X.shape[0]
            
            # Output layer gradients
            dz2 = predictions - y
            dW2 = (1/m) * np.dot(self.model.a1.T, dz2)
            db2 = (1/m) * np.sum(dz2, axis=0, keepdims=True)
            
            # Hidden layer gradients
            da1 = np.dot(dz2, self.model.W2.T)
            dz1 = da1 * (self.model.z1 > 0)  # ReLU derivative
            dW1 = (1/m) * np.dot(X.T, dz1)
            db1 = (1/m) * np.sum(dz1, axis=0, keepdims=True)
            
            # Update weights
            self.model.W2 -= learning_rate * dW2
            self.model.b2 -= learning_rate * db2
            self.model.W1 -= learning_rate * dW1
            self.model.b1 -= learning_rate * db1
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss:.4f}")
    
    def predict_difficulty(self, question_text, subject, topic, user_id=None, student_history=None):
        """
        Predict difficulty of a question for a specific student
        
        Returns: difficulty score (0-1 scale, where 0.5 = medium)
        """
        if not self.is_trained:
            # Return default if not trained
            return 0.5  # Medium difficulty
        
        # Extract features
        features = self.extract_features(question_text, subject, topic, student_history)
        features = self.scaler.transform([features])
        
        # Predict
        if TORCH_AVAILABLE:
            self.model.eval()
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features)
                difficulty = self.model(features_tensor).item()
        else:
            difficulty = self.model.predict(features)[0][0]
        
        return float(difficulty)
    
    def predict_student_ability(self, user_id, student_history):
        """
        Predict student's current ability level
        
        Returns: ability score (0-1 scale)
        """
        if not student_history or len(student_history) < 5:
            return 0.5  # Default medium ability
        
        # Calculate weighted average (recent attempts matter more)
        recent = student_history[-20:]
        
        # Weights: exponential decay (recent = more important)
        weights = np.exp(np.linspace(-2, 0, len(recent)))
        weights = weights / weights.sum()
        
        # Calculate accuracy
        accuracies = np.array([1 if a['is_correct'] else 0 for a in recent])
        weighted_accuracy = np.sum(accuracies * weights)
        
        # Adjust for difficulty of questions attempted
        if hasattr(recent[0], 'get') and recent[0].get('difficulty'):
            avg_difficulty = np.mean([
                {'easy': 0.3, 'medium': 0.5, 'hard': 0.8}.get(a.get('difficulty', 'medium'), 0.5)
                for a in recent
            ])
            # Adjust ability based on difficulty attempted
            ability = (weighted_accuracy * 0.7) + (avg_difficulty * 0.3)
        else:
            ability = weighted_accuracy
        
        # Cache it
        self.student_abilities[user_id] = ability
        
        return ability
    
    def select_optimal_questions(self, user_id, available_questions, student_history, count=10):
        """
        Select questions optimally matched to student ability
        
        Optimal zone: student_ability ± 0.15 (challenging but doable)
        """
        student_ability = self.predict_student_ability(user_id, student_history)
        
        # Score each question
        scored_questions = []
        for q in available_questions:
            question_difficulty = self.predict_difficulty(
                q.get('question', ''),
                q.get('subject', 'Physics'),
                q.get('topic', ''),
                user_id,
                student_history
            )
            
            # Score based on how close to optimal zone
            optimal_min = student_ability - 0.05
            optimal_max = student_ability + 0.2  # Slightly above ability (growth zone)
            
            if optimal_min <= question_difficulty <= optimal_max:
                score = 1.0  # Perfect match
            else:
                # Penalty for being outside optimal zone
                distance = min(
                    abs(question_difficulty - optimal_min),
                    abs(question_difficulty - optimal_max)
                )
                score = max(0, 1.0 - distance * 2)
            
            scored_questions.append({
                'question': q,
                'difficulty': question_difficulty,
                'score': score
            })
        
        # Sort by score
        scored_questions.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top questions
        return [sq['question'] for sq in scored_questions[:count]]
    
    def get_student_profile(self, user_id, student_history):
        """
        Get comprehensive student profile
        """
        ability = self.predict_student_ability(user_id, student_history)
        
        # Calculate topic strengths/weaknesses
        topic_performance = {}
        for attempt in student_history:
            topic = attempt.get('topic', 'Unknown')
            if topic not in topic_performance:
                topic_performance[topic] = {'correct': 0, 'total': 0}
            topic_performance[topic]['total'] += 1
            if attempt['is_correct']:
                topic_performance[topic]['correct'] += 1
        
        # Convert to abilities
        topic_abilities = {}
        for topic, perf in topic_performance.items():
            topic_abilities[topic] = perf['correct'] / perf['total'] if perf['total'] > 0 else 0.5
        
        # Sort topics
        strong_topics = sorted(topic_abilities.items(), key=lambda x: x[1], reverse=True)[:3]
        weak_topics = sorted(topic_abilities.items(), key=lambda x: x[1])[:3]
        
        # Learning velocity (improvement rate)
        if len(student_history) >= 20:
            first_half = student_history[:len(student_history)//2]
            second_half = student_history[len(student_history)//2:]
            
            first_accuracy = sum(1 for a in first_half if a['is_correct']) / len(first_half)
            second_accuracy = sum(1 for a in second_half if a['is_correct']) / len(second_half)
            
            velocity = second_accuracy - first_accuracy
        else:
            velocity = 0
        
        return {
            'ability': ability,
            'ability_level': self._ability_to_level(ability),
            'strong_topics': strong_topics,
            'weak_topics': weak_topics,
            'learning_velocity': velocity,
            'total_attempts': len(student_history),
            'optimal_difficulty_range': (ability - 0.05, ability + 0.2)
        }
    
    def _ability_to_level(self, ability):
        """Convert ability score to readable level"""
        if ability < 0.2:
            return "Beginner (1/5)"
        elif ability < 0.4:
            return "Elementary (2/5)"
        elif ability < 0.6:
            return "Intermediate (3/5)"
        elif ability < 0.8:
            return "Advanced (4/5)"
        else:
            return "Expert (5/5)"
    
    def save_model(self):
        """Save trained model to disk"""
        try:
            model_data = {
                'vectorizer': self.text_vectorizer,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'student_abilities': self.student_abilities
            }
            
            # Save model weights
            if TORCH_AVAILABLE and self.model:
                torch.save(self.model.state_dict(), f'{self.model_path}/model_weights.pth')
                model_data['input_size'] = list(self.model.parameters())[0].shape[1]
            elif self.model:
                model_data['model_weights'] = {
                    'W1': self.model.W1,
                    'b1': self.model.b1,
                    'W2': self.model.W2,
                    'b2': self.model.b2,
                    'input_size': self.model.input_size,
                    'hidden_size': self.model.hidden_size
                }
            
            # Save other data
            with open(f'{self.model_path}/model_data.pkl', 'wb') as f:
                pickle.dump(model_data, f)
            
            print("💾 Model saved successfully!")
        except Exception as e:
            print(f"❌ Error saving model: {e}")
    
    def load_model(self):
        """Load trained model from disk"""
        try:
            # Load model data
            with open(f'{self.model_path}/model_data.pkl', 'rb') as f:
                model_data = pickle.load(f)
            
            self.text_vectorizer = model_data['vectorizer']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            self.student_abilities = model_data.get('student_abilities', {})
            
            # Load model weights
            if TORCH_AVAILABLE and os.path.exists(f'{self.model_path}/model_weights.pth'):
                input_size = model_data['input_size']
                self.model = DifficultyPredictorNN(input_size)
                self.model.load_state_dict(torch.load(f'{self.model_path}/model_weights.pth'))
                self.model.eval()
            elif 'model_weights' in model_data:
                weights = model_data['model_weights']
                self.model = SimpleNeuralNetwork(weights['input_size'], weights['hidden_size'])
                self.model.W1 = weights['W1']
                self.model.b1 = weights['b1']
                self.model.W2 = weights['W2']
                self.model.b2 = weights['b2']
            
            print("✅ Model loaded successfully!")
        except FileNotFoundError:
            print("📝 No saved model found. Will train from scratch.")
        except Exception as e:
            print(f"⚠️ Error loading model: {e}")


# Export
__all__ = ['MLDifficultyPredictor']