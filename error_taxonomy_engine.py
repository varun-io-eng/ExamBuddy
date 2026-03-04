"""
error_taxonomy_engine_COMPATIBLE.py - Compatible with AuthDatabase
Works without node_id column
"""

import re
from collections import defaultdict, Counter
from datetime import datetime, timedelta


class ErrorTaxonomy:
    """Error classification system"""
    
    ERROR_TYPES = {
        'conceptual_misunderstanding': {
            'name': 'Conceptual Misunderstanding',
            'icon': '🧠',
            'description': 'Fundamental concept not understood',
            'severity': 'high'
        },
        'formula_memorization': {
            'name': 'Formula Memorization Without Understanding',
            'icon': '📐',
            'description': 'Knows formula but not derivation/application',
            'severity': 'high'
        },
        'calculation_error': {
            'name': 'Calculation/Arithmetic Error',
            'icon': '🔢',
            'description': 'Correct approach but arithmetic mistake',
            'severity': 'low'
        },
        'unit_error': {
            'name': 'Unit Conversion Error',
            'icon': '📏',
            'description': 'Incorrect unit handling',
            'severity': 'medium'
        },
        'sign_error': {
            'name': 'Sign/Direction Error',
            'icon': '➕',
            'description': 'Wrong sign or direction',
            'severity': 'medium'
        },
        'incomplete_analysis': {
            'name': 'Incomplete Analysis',
            'icon': '📋',
            'description': 'Missed important factors/conditions',
            'severity': 'high'
        },
        'formula_confusion': {
            'name': 'Formula Confusion',
            'icon': '🔀',
            'description': 'Applied wrong formula',
            'severity': 'high'
        },
        'diagram_misinterpretation': {
            'name': 'Diagram Misinterpretation',
            'icon': '📊',
            'description': 'Misread diagram or graph',
            'severity': 'medium'
        },
        'logic_error': {
            'name': 'Logical Reasoning Error',
            'icon': '🤔',
            'description': 'Faulty logical deduction',
            'severity': 'high'
        },
        'time_pressure_error': {
            'name': 'Time Pressure Error',
            'icon': '⏱️',
            'description': 'Rushed decision, careless mistake',
            'severity': 'low'
        },
        'prerequisite_gap': {
            'name': 'Prerequisite Knowledge Gap',
            'icon': '🔗',
            'description': 'Missing foundational knowledge',
            'severity': 'high'
        },
        'pattern_recognition_failure': {
            'name': 'Pattern Recognition Failure',
            'icon': '🎯',
            'description': 'Failed to recognize standard problem type',
            'severity': 'medium'
        }
    }
    
    @staticmethod
    def detect_error_patterns(question, user_answer, correct_answer, explanation, time_taken=None):
        """Detect error type patterns"""
        question_lower = question.lower() if question else ""
        explanation_lower = explanation.lower() if explanation else ""
        
        error_scores = defaultdict(float)
        
        # Pattern detection
        formula_keywords = ['formula', 'equation', 'use', 'apply']
        if any(kw in explanation_lower for kw in formula_keywords):
            error_scores['formula_memorization'] += 0.4
            error_scores['formula_confusion'] += 0.3
        
        calc_keywords = ['calculate', 'compute', 'arithmetic']
        if any(kw in explanation_lower for kw in calc_keywords):
            error_scores['calculation_error'] += 0.5
        
        unit_keywords = ['unit', 'convert', 'meter', 'second']
        if any(kw in question_lower for kw in unit_keywords):
            error_scores['unit_error'] += 0.4
        
        sign_keywords = ['negative', 'positive', 'direction', 'sign']
        if any(kw in explanation_lower for kw in sign_keywords):
            error_scores['sign_error'] += 0.5
        
        concept_keywords = ['concept', 'understand', 'definition']
        if any(kw in explanation_lower for kw in concept_keywords):
            error_scores['conceptual_misunderstanding'] += 0.6
        
        missing_keywords = ['consider', 'account for', 'factor']
        if any(kw in explanation_lower for kw in missing_keywords):
            error_scores['incomplete_analysis'] += 0.5
        
        if time_taken and time_taken < 15:
            error_scores['time_pressure_error'] += 0.6
        
        visual_keywords = ['diagram', 'graph', 'figure']
        if any(kw in question_lower for kw in visual_keywords):
            error_scores['diagram_misinterpretation'] += 0.3
        
        logic_keywords = ['therefore', 'because', 'reasoning']
        if any(kw in explanation_lower for kw in logic_keywords):
            error_scores['logic_error'] += 0.4
        
        prereq_keywords = ['first', 'basics', 'fundamental']
        if any(kw in explanation_lower for kw in prereq_keywords):
            error_scores['prerequisite_gap'] += 0.5
        
        # Default
        if not error_scores:
            error_scores['conceptual_misunderstanding'] = 0.5
        
        # Normalize
        total = sum(error_scores.values())
        if total > 0:
            error_scores = {k: v/total for k, v in error_scores.items()}
        
        # Return top 3
        sorted_errors = sorted(error_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {
                'type': error_type,
                'confidence': round(confidence, 2),
                **ErrorTaxonomy.ERROR_TYPES[error_type]
            }
            for error_type, confidence in sorted_errors[:3]
            if confidence > 0.1
        ]


class FixStrategyEngine:
    """Generates remediation strategies"""
    
    REMEDIATION_STRATEGIES = {
        'conceptual_misunderstanding': {
            'immediate_actions': [
                'Review concept definition and derivation',
                'Watch visual explanation',
                'Draw concept map'
            ],
            'practice_type': 'conceptual_mcqs',
            'practice_count': 5,
            'difficulty': 'easy',
            'explanation_style': 'intuitive',
            'follow_up': 'Explain concept in own words'
        },
        'formula_memorization': {
            'immediate_actions': [
                'Show step-by-step derivation',
                'Explain physical meaning of each term',
                'Practice conceptual questions'
            ],
            'practice_type': 'derivation_based',
            'practice_count': 4,
            'difficulty': 'medium',
            'explanation_style': 'mathematical',
            'follow_up': 'Why does this formula work?'
        },
        'calculation_error': {
            'immediate_actions': [
                'Practice mental math',
                'Review arithmetic operations',
                'Use calculator then verify'
            ],
            'practice_type': 'calculation_focused',
            'practice_count': 3,
            'difficulty': 'easy',
            'explanation_style': 'step_by_step',
            'follow_up': 'Double-check calculations'
        },
        'unit_error': {
            'immediate_actions': [
                'Create unit conversion cheat sheet',
                'Practice unit conversions',
                'Write units next to numbers'
            ],
            'practice_type': 'unit_conversion',
            'practice_count': 5,
            'difficulty': 'easy',
            'explanation_style': 'systematic',
            'follow_up': 'Verify final units make sense'
        },
        'sign_error': {
            'immediate_actions': [
                'Draw coordinate system',
                'Mark positive/negative directions',
                'Practice with vectors'
            ],
            'practice_type': 'directional',
            'practice_count': 4,
            'difficulty': 'medium',
            'explanation_style': 'visual',
            'follow_up': 'Define positive direction first'
        },
        'incomplete_analysis': {
            'immediate_actions': [
                'Create checklist of factors',
                'Identify all variables',
                'Use systematic framework'
            ],
            'practice_type': 'comprehensive_analysis',
            'practice_count': 4,
            'difficulty': 'medium',
            'explanation_style': 'systematic',
            'follow_up': 'List all given information first'
        },
        'formula_confusion': {
            'immediate_actions': [
                'Create formula comparison table',
                'Identify when to use each',
                'Practice problem type recognition'
            ],
            'practice_type': 'formula_selection',
            'practice_count': 5,
            'difficulty': 'medium',
            'explanation_style': 'comparative',
            'follow_up': 'What scenario is this formula for?'
        },
        'diagram_misinterpretation': {
            'immediate_actions': [
                'Read diagrams slowly',
                'Label all parts',
                'Redraw with annotations'
            ],
            'practice_type': 'diagram_based',
            'practice_count': 4,
            'difficulty': 'medium',
            'explanation_style': 'visual',
            'follow_up': 'Annotate diagrams before answering'
        },
        'logic_error': {
            'immediate_actions': [
                'Break into smaller steps',
                'Verify each step',
                'Practice deductive reasoning'
            ],
            'practice_type': 'logical_reasoning',
            'practice_count': 4,
            'difficulty': 'medium',
            'explanation_style': 'step_by_step',
            'follow_up': 'Does each step follow logically?'
        },
        'time_pressure_error': {
            'immediate_actions': [
                'Practice with timer',
                'Build speed gradually',
                'Recognize when rushing'
            ],
            'practice_type': 'timed_practice',
            'practice_count': 6,
            'difficulty': 'easy',
            'explanation_style': 'quick_tips',
            'follow_up': 'Slow down - speed comes from mastery'
        },
        'prerequisite_gap': {
            'immediate_actions': [
                'Review prerequisite concepts',
                'Master foundations first',
                'Create dependency map'
            ],
            'practice_type': 'prerequisite_review',
            'practice_count': 6,
            'difficulty': 'easy',
            'explanation_style': 'foundational',
            'follow_up': 'Complete prerequisites first'
        },
        'pattern_recognition_failure': {
            'immediate_actions': [
                'Study problem patterns',
                'Build mental library',
                'Categorize before solving'
            ],
            'practice_type': 'pattern_recognition',
            'practice_count': 5,
            'difficulty': 'medium',
            'explanation_style': 'pattern_based',
            'follow_up': 'What type of problem is this?'
        }
    }
    
    def __init__(self, db, gemini_service):
        self.db = db
        self.gemini = gemini_service
    
    def analyze_error_history(self, user_id, days=30):
        """
        Analyze error patterns - COMPATIBLE with AuthDatabase
        """
        cursor = self.db.conn.cursor()
        
        # Get recent wrong attempts (no node_id needed)
        cursor.execute("""
            SELECT question, user_answer, correct_answer, timestamp, 
                   subject, topic, difficulty, time_taken
            FROM attempts
            WHERE user_id = ? AND is_correct = 0
            AND datetime(timestamp) > datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC
        """, (user_id, days))
        
        wrong_attempts = cursor.fetchall()
        
        error_counts = Counter()
        error_by_topic = defaultdict(list)
        recent_errors = []
        
        for attempt in wrong_attempts[:50]:
            question, user_ans, correct_ans, ts, subject, topic, diff, time_taken = attempt
            
            # Detect error types
            errors = ErrorTaxonomy.detect_error_patterns(
                question, user_ans, correct_ans, "", time_taken
            )
            
            for error in errors:
                error_type = error['type']
                error_counts[error_type] += error['confidence']
                error_by_topic[topic].append(error_type)
                
                if len(recent_errors) < 10:
                    recent_errors.append({
                        'timestamp': ts,
                        'topic': topic,
                        'error_type': error_type,
                        'confidence': error['confidence']
                    })
        
        # Find persistent errors
        persistent = []
        for error_type, count in error_counts.most_common():
            if count >= 3:
                persistent.append({
                    'error_type': error_type,
                    'frequency': count,
                    **ErrorTaxonomy.ERROR_TYPES[error_type]
                })
        
        return {
            'total_errors': len(wrong_attempts),
            'analyzed_errors': len(wrong_attempts[:50]),
            'top_error_types': [
                {'type': et, 'count': round(cnt, 1), **ErrorTaxonomy.ERROR_TYPES[et]}
                for et, cnt in error_counts.most_common(5)
            ],
            'persistent_errors': persistent,
            'error_by_topic': dict(error_by_topic),
            'recent_errors': recent_errors
        }


__all__ = ['ErrorTaxonomy', 'FixStrategyEngine']