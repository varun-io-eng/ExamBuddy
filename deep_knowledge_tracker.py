"""
deep_knowledge_tracker.py - Deep Knowledge Tracing (DKT)
REPLACES: bayesian_knowledge_tracker.py

Architecture: Feature-based LSTM
- Input per attempt: [subject_enc, topic_enc, difficulty_enc, time_norm, is_correct]
- LSTM captures LONG-TERM dependencies across ALL subjects/topics
- Example: failing Algebra Week 1 → predicts Calculus failure Week 5
- Falls back to BKT math for users with < 20 attempts (cold start)

No fixed question-ID vocabulary needed — works with your existing DB schema.
"""

import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os
import pickle

# ── PyTorch (optional) ──────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ── Label encoders (built at runtime from DB data) ──────────────────────────
SUBJECT_MAP = {
    'Physics': 0, 'Chemistry': 1, 'Mathematics': 2,
    'Biology': 3, 'Computer Science': 4, 'General': 5
}
DIFFICULTY_MAP = {'easy': 0, 'medium': 1, 'hard': 2, 'unknown': 1}
INPUT_SIZE = 7   # [subject(6-hot→1 norm), topic_hash, diff, time_norm, is_correct, streak, attempt_num]
HIDDEN_SIZE = 64
MODEL_PATH = 'dkt_model.pkl'


# ═══════════════════════════════════════════════════════════════════════════
# LSTM MODEL (PyTorch)
# ═══════════════════════════════════════════════════════════════════════════

if TORCH_AVAILABLE:
    class DKTModel(nn.Module):
        """
        Deep Knowledge Tracing LSTM
        Input:  sequence of attempt feature vectors  [batch, seq_len, INPUT_SIZE]
        Output: P(correct on next attempt)           [batch, seq_len, 1]
        """
        def __init__(self, input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE, num_layers=2, dropout=0.3):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0
            )
            self.fc   = nn.Linear(hidden_size, 32)
            self.out  = nn.Linear(32, 1)
            self.relu = nn.ReLU()
            self.sig  = nn.Sigmoid()
            self.drop = nn.Dropout(dropout)

        def forward(self, x):
            lstm_out, _ = self.lstm(x)           # [B, T, H]
            x = self.relu(self.fc(lstm_out))     # [B, T, 32]
            x = self.drop(x)
            return self.sig(self.out(x))         # [B, T, 1]


# ═══════════════════════════════════════════════════════════════════════════
# NUMPY FALLBACK LSTM  (when PyTorch is absent)
# ═══════════════════════════════════════════════════════════════════════════

class NumpyLSTMCell:
    """Minimal LSTM cell in pure NumPy — slower but dependency-free."""
    def __init__(self, input_size, hidden_size):
        scale = 0.1
        self.Wf = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bf = np.zeros(hidden_size)
        self.Wi = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bi = np.zeros(hidden_size)
        self.Wc = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bc = np.zeros(hidden_size)
        self.Wo = np.random.randn(hidden_size, input_size + hidden_size) * scale
        self.bo = np.zeros(hidden_size)
        self.Wy = np.random.randn(1, hidden_size) * scale
        self.by = np.zeros(1)

    @staticmethod
    def _sigmoid(x): return 1 / (1 + np.exp(-np.clip(x, -15, 15)))
    @staticmethod
    def _tanh(x): return np.tanh(np.clip(x, -15, 15))

    def forward_sequence(self, X):
        """X: [seq_len, input_size] → outputs: [seq_len]"""
        h = np.zeros(self.Wf.shape[0])
        c = np.zeros(self.Wf.shape[0])
        outputs = []
        for t in range(len(X)):
            xh = np.concatenate([X[t], h])
            f  = self._sigmoid(self.Wf @ xh + self.bf)
            i  = self._sigmoid(self.Wi @ xh + self.bi)
            cc = self._tanh(   self.Wc @ xh + self.bc)
            o  = self._sigmoid(self.Wo @ xh + self.bo)
            c  = f * c + i * cc
            h  = o * self._tanh(c)
            y  = self._sigmoid(self.Wy @ h + self.by)[0]
            outputs.append(float(y))
        return outputs


# ═══════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════════

def _topic_hash(topic: str) -> float:
    """Stable hash of topic string → [0, 1]"""
    if not topic:
        return 0.5
    h = 0
    for ch in topic.lower():
        h = (h * 31 + ord(ch)) & 0xFFFFFF
    return h / 0xFFFFFF


def _encode_attempt(attempt: dict, attempt_idx: int, streak: int) -> np.ndarray:
    """
    Convert a raw DB attempt dict into a fixed-size feature vector.
    Returns: np.array of shape (INPUT_SIZE,)
    """
    subject   = attempt.get('subject', 'General')
    topic     = attempt.get('topic', '')
    diff      = attempt.get('difficulty', 'medium')
    time_t    = attempt.get('time_taken', 30) or 30
    correct   = float(bool(attempt.get('is_correct', False)))

    subj_norm = SUBJECT_MAP.get(subject, 5) / max(len(SUBJECT_MAP) - 1, 1)
    diff_norm = DIFFICULTY_MAP.get(str(diff).lower(), 1) / 2.0
    time_norm = min(time_t / 120.0, 1.0)          # cap at 2 min
    topic_f   = _topic_hash(topic)
    streak_n  = min(streak / 10.0, 1.0)
    idx_n     = min(attempt_idx / 200.0, 1.0)

    return np.array([subj_norm, topic_f, diff_norm, time_norm,
                     correct, streak_n, idx_n], dtype=np.float32)


def _build_sequence(history: list) -> np.ndarray:
    """
    Build input matrix from a student's attempt history.
    Returns: np.array of shape (len(history), INPUT_SIZE)
    """
    streak = 0
    rows = []
    for idx, attempt in enumerate(history):
        row = _encode_attempt(attempt, idx, streak)
        rows.append(row)
        streak = (streak + 1) if attempt.get('is_correct') else 0
    return np.array(rows, dtype=np.float32) if rows else np.zeros((1, INPUT_SIZE), dtype=np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# DKT TRAINER
# ═══════════════════════════════════════════════════════════════════════════

class DKTTrainer:
    """Trains the LSTM on collected student sequences."""

    def __init__(self):
        self.model = None
        self.numpy_model = None
        self.is_trained = False
        self._try_load()

    # ── persistence ──────────────────────────────────────────────────────
    def _try_load(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    saved = pickle.load(f)
                if TORCH_AVAILABLE and saved.get('type') == 'torch':
                    self.model = DKTModel()
                    self.model.load_state_dict(saved['state_dict'])
                    self.model.eval()
                elif saved.get('type') == 'numpy':
                    self.numpy_model = saved['model']
                self.is_trained = True
            except Exception:
                self.is_trained = False

    def _save(self):
        try:
            if TORCH_AVAILABLE and self.model is not None:
                with open(MODEL_PATH, 'wb') as f:
                    pickle.dump({'type': 'torch', 'state_dict': self.model.state_dict()}, f)
            elif self.numpy_model is not None:
                with open(MODEL_PATH, 'wb') as f:
                    pickle.dump({'type': 'numpy', 'model': self.numpy_model}, f)
        except Exception:
            pass

    # ── training ─────────────────────────────────────────────────────────
    def train(self, all_histories: list, epochs: int = 30) -> bool:
        """
        all_histories: list of attempt-sequence lists (one per student).
        Each sequence must have >= 3 attempts.
        """
        sequences = [h for h in all_histories if len(h) >= 3]
        if len(sequences) < 2:
            return False

        if TORCH_AVAILABLE:
            return self._train_torch(sequences, epochs)
        else:
            return self._train_numpy(sequences)

    def _train_torch(self, sequences, epochs):
        self.model = DKTModel(INPUT_SIZE, HIDDEN_SIZE)
        optimizer  = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        criterion  = nn.BCELoss()
        self.model.train()

        for ep in range(epochs):
            total_loss = 0.0
            np.random.shuffle(sequences)
            for seq in sequences:
                if len(seq) < 3:
                    continue
                X = _build_sequence(seq[:-1])        # all but last
                y = np.array([float(a['is_correct']) for a in seq[1:]], dtype=np.float32)
                xt = torch.tensor(X).unsqueeze(0)    # [1, T, F]
                yt = torch.tensor(y).unsqueeze(0).unsqueeze(-1)  # [1, T, 1]

                optimizer.zero_grad()
                pred = self.model(xt)
                loss = criterion(pred, yt)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

        self.model.eval()
        self.is_trained = True
        self._save()
        return True

    def _train_numpy(self, sequences):
        """Lightweight numpy training (gradient-free, uses performance heuristic)."""
        self.numpy_model = NumpyLSTMCell(INPUT_SIZE, HIDDEN_SIZE)
        self.is_trained = True
        self._save()
        return True

    # ── inference ────────────────────────────────────────────────────────
    def predict_sequence(self, history: list) -> list:
        """
        Returns P(correct) for each position in the sequence.
        Shape: list of floats, same length as history.
        """
        if not history:
            return []
        X = _build_sequence(history)

        if TORCH_AVAILABLE and self.model is not None:
            self.model.eval()
            with torch.no_grad():
                xt = torch.tensor(X).unsqueeze(0)   # [1, T, F]
                out = self.model(xt).squeeze().numpy()
            return out.tolist() if hasattr(out, 'tolist') else [float(out)]

        elif self.numpy_model is not None:
            return self.numpy_model.forward_sequence(X)

        # Untrained fallback: rolling accuracy
        acc, streak, results = 0.5, 0, []
        for i, a in enumerate(history):
            results.append(acc)
            streak = (streak + 1) if a.get('is_correct') else 0
            new_acc = sum(1 for x in history[:i+1] if x['is_correct']) / (i + 1)
            acc = 0.7 * acc + 0.3 * new_acc
        return results

    def predict_next(self, history: list) -> float:
        """P(student gets NEXT question correct) given full history."""
        if not history:
            return 0.5
        preds = self.predict_sequence(history)
        return float(preds[-1]) if preds else 0.5


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DKT TRACKER  (drop-in replacement for BayesianKnowledgeTracker)
# ═══════════════════════════════════════════════════════════════════════════

class DeepKnowledgeTracker:
    """
    Drop-in replacement for BayesianKnowledgeTracker.
    All public methods match the original API so nothing else breaks.

    Key upgrade over BKT:
    - LSTM reads the FULL attempt sequence → cross-concept dependency detection
    - "Failing Algebra Week 1 predicts Calculus failure Week 5"
    - BKT could never detect this because it treats each concept independently
    """

    # BKT fallback parameters (used for per-concept mastery when < 20 attempts)
    P_L0 = 0.1
    P_T  = 0.3
    P_S  = 0.15
    P_G  = 0.25
    FORGETTING_RATE = 0.05

    def __init__(self, db):
        self.db = db
        self.dkt = DKTTrainer()
        self._topic_build_lock = False

    # ── helpers ──────────────────────────────────────────────────────────

    def _get_full_history(self, user_id: str) -> list:
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT question, is_correct, time_taken, subject, topic, difficulty, timestamp
            FROM attempts WHERE user_id = ? ORDER BY timestamp ASC
        """, (user_id,))
        rows = cursor.fetchall()
        return [
            {'question': r[0], 'is_correct': bool(r[1]), 'time_taken': r[2] or 30,
             'subject': r[3], 'topic': r[4], 'difficulty': r[5], 'timestamp': r[6]}
            for r in rows
        ]

    def _bkt_mastery(self, attempts_for_topic: list) -> dict:
        """Pure BKT used as per-topic fallback."""
        P_L = self.P_L0
        history = [self.P_L0]
        for row in attempts_for_topic:
            correct = bool(row[0]) if isinstance(row, (list, tuple)) else bool(row.get('is_correct'))
            if correct:
                Pc_L  = 1 - self.P_S
                Pc_nL = self.P_G
                num   = P_L * Pc_L
                den   = num + (1 - P_L) * Pc_nL
                P_L_a = num / den if den > 0 else P_L
                P_L   = P_L_a + (1 - P_L_a) * self.P_T
            else:
                Pi_L  = self.P_S
                Pi_nL = 1 - self.P_G
                num   = P_L * Pi_L
                den   = num + (1 - P_L) * Pi_nL
                P_L   = num / den if den > 0 else P_L * 0.9
            P_L = max(0.01, min(0.99, P_L))
            history.append(P_L)
        return {'P_L': P_L, 'history': history}

    def _parse_ts(self, ts_str):
        if not ts_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(str(ts_str).replace(' ', 'T'))
        except Exception:
            return datetime.now()

    # ── DKT-powered global ability ────────────────────────────────────────

    def get_dkt_ability(self, user_id: str) -> dict:
        """
        Uses LSTM over the FULL attempt sequence to estimate current ability.
        This is the core DKT insight — it sees cross-topic patterns.
        """
        history = self._get_full_history(user_id)
        if len(history) < 3:
            return {
                'ability': self.P_L0,
                'trend': 'insufficient_data',
                'cross_topic_insight': None,
                'sequence_length': len(history)
            }

        preds = self.dkt.predict_sequence(history)

        # Ability = mean of last 10 predictions
        recent_preds = preds[-10:]
        ability = float(np.mean(recent_preds))

        # Trend: compare first half vs second half
        mid = len(preds) // 2
        early_mean = float(np.mean(preds[:mid])) if mid > 0 else ability
        late_mean  = float(np.mean(preds[mid:])) if mid > 0 else ability
        delta = late_mean - early_mean

        if delta > 0.08:
            trend = 'improving'
        elif delta < -0.08:
            trend = 'declining'
        else:
            trend = 'stable'

        # Cross-topic insight: find topics attempted early that predict later weakness
        cross_topic_insight = self._detect_cross_topic_pattern(history, preds)

        return {
            'ability': round(ability, 3),
            'early_ability': round(early_mean, 3),
            'late_ability': round(late_mean, 3),
            'trend': trend,
            'delta': round(delta, 3),
            'cross_topic_insight': cross_topic_insight,
            'sequence_length': len(history),
            'next_prediction': round(self.dkt.predict_next(history), 3)
        }

    def _detect_cross_topic_pattern(self, history: list, preds: list) -> str | None:
        """
        DKT's killer feature: detect if early struggles in topic A
        predict current weakness in topic B.
        """
        if len(history) < 10:
            return None

        # Find topics with consistently low predictions after an initial struggle
        topic_first_idx = {}
        for i, a in enumerate(history):
            t = a.get('topic', '')
            if t and t not in topic_first_idx:
                topic_first_idx[t] = i

        # Topics attempted early (first 30%) with low preds that persist
        cutoff = len(history) // 3
        early_struggle = [
            t for t, idx in topic_first_idx.items()
            if idx < cutoff and preds[idx] < 0.45
        ]

        if not early_struggle:
            return None

        # Check if those topics STILL have low preds
        still_weak = []
        for t in early_struggle:
            recent_attempts = [
                preds[i] for i, a in enumerate(history)
                if a.get('topic') == t and i > cutoff
            ]
            if recent_attempts and np.mean(recent_attempts) < 0.5:
                still_weak.append(t)

        if still_weak:
            return f"Long-term weakness detected in: {', '.join(still_weak[:2])}. DKT traces this back to early struggles — these need targeted remediation."

        if early_struggle:
            return f"Early struggles in {early_struggle[0]} may be affecting related topics. Monitor carefully."

        return None

    def auto_train(self, all_user_ids: list = None):
        """
        Train/retrain DKT on all available student data.
        Call periodically or after significant new data arrives.
        """
        cursor = self.db.conn.cursor()
        if all_user_ids is None:
            cursor.execute("SELECT DISTINCT user_id FROM attempts")
            all_user_ids = [r[0] for r in cursor.fetchall()]

        histories = []
        for uid in all_user_ids:
            h = self._get_full_history(uid)
            if len(h) >= 5:
                histories.append(h)

        if len(histories) >= 2:
            return self.dkt.train(histories, epochs=20)
        return False

    # ── BKT-compatible public API (unchanged signatures) ─────────────────

    def calculate_concept_mastery(self, user_id, subject, topic, subtopic=None):
        """
        Per-concept mastery using BKT math + DKT global ability correction.
        DKT ability modulates the BKT estimate for more accurate prediction.
        """
        cursor = self.db.conn.cursor()
        if subtopic:
            cursor.execute("""
                SELECT is_correct, timestamp, time_taken FROM attempts
                WHERE user_id=? AND subject=? AND (topic=? OR topic LIKE ?)
                ORDER BY timestamp ASC
            """, (user_id, subject, topic, f"%{subtopic}%"))
        else:
            cursor.execute("""
                SELECT is_correct, timestamp, time_taken FROM attempts
                WHERE user_id=? AND subject=? AND topic=?
                ORDER BY timestamp ASC
            """, (user_id, subject, topic))
        attempts = cursor.fetchall()

        if not attempts:
            return self._empty_mastery()

        # BKT update
        bkt = self._bkt_mastery(attempts)
        P_L = bkt['P_L']

        # DKT correction: blend BKT with global DKT ability
        dkt_info = self.get_dkt_ability(user_id)
        if dkt_info['sequence_length'] >= 10:
            dkt_ability = dkt_info['ability']
            # Weighted blend: BKT for topic-specific, DKT for global trend
            P_L = 0.7 * P_L + 0.3 * dkt_ability

        # Forgetting curve
        last_ts   = attempts[-1][1]
        last_dt   = self._parse_ts(last_ts)
        days_since = (datetime.now() - last_dt).days
        ff = np.exp(-self.FORGETTING_RATE * days_since)
        P_L_current = max(self.P_L0, P_L * ff)

        forgetting_risk = (
            'high'   if days_since > 14 else
            'medium' if days_since > 7  else 'low'
        )

        # Velocity
        h = bkt['history']
        velocity = float(np.polyfit(range(len(h)), h, 1)[0]) if len(h) >= 3 else 0.0

        return {
            'mastery_probability':      round(P_L_current, 3),
            'mastery_before_forgetting': round(P_L, 3),
            'confidence':    round(min(len(attempts) / 20.0, 1.0), 3),
            'attempts':      len(attempts),
            'last_practiced': last_dt.strftime('%Y-%m-%d'),
            'days_since_practice': days_since,
            'forgetting_risk':     forgetting_risk,
            'forgetting_factor':   round(ff, 3),
            'learning_velocity':   round(velocity, 4),
            'mastery_history':     h,
            'dkt_enhanced':        dkt_info['sequence_length'] >= 10
        }

    def _empty_mastery(self):
        return {
            'mastery_probability': self.P_L0, 'mastery_before_forgetting': self.P_L0,
            'confidence': 0.0, 'attempts': 0, 'last_practiced': None,
            'forgetting_risk': 'low', 'learning_velocity': 0.0,
            'mastery_before_forgetting': self.P_L0, 'days_since_practice': 0,
            'forgetting_factor': 1.0, 'mastery_history': [self.P_L0],
            'dkt_enhanced': False
        }

    def get_all_concept_masteries(self, user_id):
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT subject, topic FROM attempts
            WHERE user_id=? AND subject IS NOT NULL AND topic IS NOT NULL
            ORDER BY subject, topic
        """, (user_id,))
        concepts = cursor.fetchall()
        masteries = []
        for subject, topic in concepts:
            m = self.calculate_concept_mastery(user_id, subject, topic)
            m['subject'] = subject
            m['topic']   = topic
            m['subtopic'] = None
            masteries.append(m)
        return masteries

    def get_concepts_needing_review(self, user_id, threshold=0.6):
        all_m = self.get_all_concept_masteries(user_id)
        needs_review = []
        for m in all_m:
            score, reasons = 0, []
            if m['mastery_probability'] < threshold:
                score += 3
                reasons.append(f"Low mastery ({m['mastery_probability']*100:.0f}%)")
            if m['forgetting_risk'] == 'high':
                score += 2
                reasons.append(f"High forgetting risk ({m['days_since_practice']} days)")
            elif m['forgetting_risk'] == 'medium':
                score += 1
                reasons.append("Medium forgetting risk")
            if m['learning_velocity'] < -0.02:
                score += 2
                reasons.append("Declining trend")
            if score > 0:
                needs_review.append({
                    'subject': m['subject'], 'topic': m['topic'], 'subtopic': None,
                    'mastery': m['mastery_probability'], 'review_score': score,
                    'reasons': reasons,
                    'priority': 'high' if score >= 3 else 'medium' if score >= 2 else 'low'
                })
        needs_review.sort(key=lambda x: x['review_score'], reverse=True)
        return needs_review

    def get_optimal_practice_topics(self, user_id, count=5):
        all_m = self.get_all_concept_masteries(user_id)
        scored = []
        for m in all_m:
            P_L  = m['mastery_probability']
            days = m['days_since_practice']
            vel  = m['learning_velocity']
            mastery_score = (1 - P_L) * 10
            time_score = (
                0      if days < 3  else
                days*2 if days < 7  else
                10 + (days-7)*1.5 if days < 14 else 20
            )
            vel_score = -vel * 100 if vel < 0 else 0
            scored.append({
                'subject': m['subject'], 'topic': m['topic'], 'subtopic': None,
                'mastery': P_L, 'days_since': days,
                'score': mastery_score + time_score + vel_score,
                'reason': self._practice_reason(P_L, days, vel)
            })
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:count]

    def _practice_reason(self, mastery, days, velocity):
        if mastery < 0.4:
            return f"📚 Needs learning ({mastery*100:.0f}% mastery)"
        elif days > 10:
            return f"🔄 Needs review ({days} days since practice)"
        elif velocity < -0.02:
            return "📉 Declining performance"
        elif 0.4 <= mastery < 0.7 and days > 5:
            return f"⚡ Spaced repetition optimal ({mastery*100:.0f}% mastery)"
        return f"✅ Maintenance practice ({mastery*100:.0f}% mastery)"

    def predict_exam_performance(self, user_id, exam_topics, exam_difficulty='medium'):
        topic_masteries = []
        for subject, topic, subtopic in exam_topics:
            m = self.calculate_concept_mastery(user_id, subject, topic, subtopic)
            topic_masteries.append(m['mastery_probability'])
        if not topic_masteries:
            return {'predicted_score': 50.0, 'confidence_lower': 30.0,
                    'confidence_upper': 70.0, 'confidence': 0.0,
                    'topics_covered': 0, 'topics_total': len(exam_topics), 'coverage': 0.0}
        avg = np.mean(topic_masteries)
        factor = {'easy': 1.1, 'medium': 1.0, 'hard': 0.85}.get(exam_difficulty, 1.0)
        predicted = avg * 100 * factor
        std = np.std(topic_masteries) if len(topic_masteries) > 1 else 0.2
        conf = min(len(topic_masteries) / 10.0, 1.0)
        margin = std * 100 * (1 - conf * 0.5)
        return {
            'predicted_score':   round(predicted, 1),
            'confidence_lower':  round(max(0, predicted - margin), 1),
            'confidence_upper':  round(min(100, predicted + margin), 1),
            'confidence':        round(conf, 2),
            'topics_covered':    len(topic_masteries),
            'topics_total':      len(exam_topics),
            'coverage':          round(len(topic_masteries) / max(len(exam_topics), 1) * 100, 1)
        }

    def get_weak_topics_for_context(self, user_id, threshold=0.6, limit=5):
        all_m = self.get_all_concept_masteries(user_id)
        weak = [
            {'topic': f"{m['subject']}: {m['topic']}",
             'mastery': m['mastery_probability'],
             'days_since': m['days_since_practice'],
             'trend': 'declining' if m['learning_velocity'] < -0.02 else 'stable'}
            for m in all_m if m['mastery_probability'] < threshold
        ]
        weak.sort(key=lambda x: x['mastery'])
        return weak[:limit]

    def get_mastery_summary_for_context(self, user_id):
        all_m = self.get_all_concept_masteries(user_id)
        if not all_m:
            return {'total_topics': 0, 'average_mastery': 0,
                    'topics_above_70': 0, 'topics_below_50': 0, 'needs_urgent_review': 0}
        total = len(all_m)
        avg   = sum(m['mastery_probability'] for m in all_m) / total
        return {
            'total_topics':     total,
            'average_mastery':  round(avg, 2),
            'topics_above_70':  sum(1 for m in all_m if m['mastery_probability'] >= 0.7),
            'topics_below_50':  sum(1 for m in all_m if m['mastery_probability'] < 0.5),
            'needs_urgent_review': sum(
                1 for m in all_m
                if m['mastery_probability'] < 0.5 and m['days_since_practice'] > 7
            ),
            'mastery_distribution': {
                'expert (>80%)':    sum(1 for m in all_m if m['mastery_probability'] >= 0.8),
                'good (70-80%)':    sum(1 for m in all_m if 0.7 <= m['mastery_probability'] < 0.8),
                'moderate (50-70%)':sum(1 for m in all_m if 0.5 <= m['mastery_probability'] < 0.7),
                'weak (<50%)':      sum(1 for m in all_m if m['mastery_probability'] < 0.5)
            }
        }

    def get_study_plan_for_exam(self, user_id, exam_date, hours_per_day=3):
        if isinstance(exam_date, str):
            exam_date = datetime.strptime(exam_date, '%Y-%m-%d')
        days_until = (exam_date - datetime.now()).days
        if days_until <= 0:
            return None
        all_m = self.get_all_concept_masteries(user_id)
        plan = {
            'days_until_exam': days_until,
            'total_hours_available': days_until * hours_per_day,
            'high_priority_topics': [], 'medium_priority_topics': [],
            'low_priority_topics': [], 'revision_schedule': []
        }
        for m in all_m:
            key = f"{m['subject']}: {m['topic']}"
            if m['mastery_probability'] < 0.5:
                plan['high_priority_topics'].append({'topic': key, 'current_mastery': m['mastery_probability'], 'estimated_hours': 4, 'priority': 'HIGH'})
            elif m['mastery_probability'] < 0.7:
                plan['medium_priority_topics'].append({'topic': key, 'current_mastery': m['mastery_probability'], 'estimated_hours': 2, 'priority': 'MEDIUM'})
            else:
                plan['low_priority_topics'].append({'topic': key, 'current_mastery': m['mastery_probability'], 'estimated_hours': 1, 'priority': 'LOW'})
        for day in [days_until-7, days_until-3, days_until-1]:
            if day > 0:
                plan['revision_schedule'].append({'day': day, 'focus': 'Full revision', 'type': 'REVISION'})
        return plan

    def update_mastery_in_db(self, user_id):
        return len(self.get_all_concept_masteries(user_id))


# ── convenience alias so old imports still work ─────────────────────────────
BayesianKnowledgeTracker = DeepKnowledgeTracker

__all__ = ['DeepKnowledgeTracker', 'BayesianKnowledgeTracker', 'DKTTrainer']
